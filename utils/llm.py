"""
utils/llm.py — Factory for the LLM model.

Provider selection (LLM_PROVIDER env var, default "anthropic"):
  1. anthropic — Claude Opus 5.5 for both pipeline and judge. Thinking is
     always on for this model; depth is controlled with `effort` (pipeline
     medium, judge high). `temperature` is not supported and is ignored.
  2. groq      — free tier, openai/gpt-oss-120b. Free limits: 30 RPM, 1K RPD,
     8K TPM, 200K TPD → pacer set to 24 RPM.

Cost tracking: every call is recorded in a thread-safe ledger against
COST_BUDGET_USD. Groq is priced at its paid rates so the ledger acts as a
runaway-loop guard even though the free tier costs $0.
"""
import os
import threading
import time
from collections import deque

from config import logger

# ---------------------------------------------------------------------------
# Provider / model configuration
# ---------------------------------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_JUDGE_MODEL = os.getenv("GROQ_JUDGE_MODEL", "openai/gpt-oss-120b")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY", "")
PIPELINE_MODEL = os.getenv("PIPELINE_MODEL", "claude-opus-5-5")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "claude-opus-5-5")
PIPELINE_EFFORT = os.getenv("PIPELINE_EFFORT", "medium")
JUDGE_EFFORT = os.getenv("JUDGE_EFFORT", "high")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").lower()
USE_GROQ = LLM_PROVIDER == "groq"

# Prices for the ledger guard, USD per million tokens.
# Groq uses its paid-list rates; Claude uses Anthropic's list rates.
PRICES_PER_MTOK = {
    "openai/gpt-oss-120b": {"input": 0.15, "output": 0.75},
    "openai/gpt-oss-20b": {"input": 0.10, "output": 0.50},
    "qwen/qwen3.6-27b": {"input": 0.10, "output": 0.50},
    "claude-opus-5-5": {"input": 4.0, "output": 20.0},
    "claude-sonnet-5-5": {"input": 2.0, "output": 10.0},
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50},
}
_FALLBACK_PRICE = {"input": 4.0, "output": 20.0}

# Hard budget cap for the whole experiment run (env-overridable).
COST_BUDGET_USD = float(os.getenv("COST_BUDGET_USD", "15.0"))

# ---------------------------------------------------------------------------
# Thread-safe cost ledger
# ---------------------------------------------------------------------------
class CostLedger:
    def __init__(self, budget_usd: float):
        self.budget_usd = budget_usd
        self.lock = threading.Lock()
        self.input_tokens = 0
        self.output_tokens = 0
        self.cost_usd = 0.0
        self.calls = 0

    def price_for(self, model: str) -> dict:
        return PRICES_PER_MTOK.get(model, _FALLBACK_PRICE)

    def would_exceed_budget(self, model: str, est_input_tokens: int, est_output_tokens: int) -> bool:
        """Check whether a call of the given estimated size would blow the budget."""
        p = self.price_for(model)
        projected = (
            self.cost_usd
            + est_input_tokens / 1e6 * p["input"]
            + est_output_tokens / 1e6 * p["output"]
        )
        return projected > self.budget_usd

    def record(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Record actual usage from a completed call; returns this call's cost."""
        p = self.price_for(model)
        cost = input_tokens / 1e6 * p["input"] + output_tokens / 1e6 * p["output"]
        with self.lock:
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            self.cost_usd += cost
            self.calls += 1
        return cost

    def summary(self) -> str:
        return (
            f"calls={self.calls} in={self.input_tokens:,} out={self.output_tokens:,} "
            f"cost=${self.cost_usd:.4f} / budget=${self.budget_usd:.2f}"
        )


LEDGER = CostLedger(COST_BUDGET_USD)

# ---------------------------------------------------------------------------
# Rate pacing — Groq free tier: 30 RPM, 8K TPM, 1K RPD, 200K TPD (verified
# live from response headers). The binding constraint is TPM: a transcript-
# judging call carries ~3-4K tokens, so request-only pacing would blow the
# 8K tokens/min cap. We pace against BOTH RPM and a rolling 60s token window,
# self-tuning the per-call estimate from the previous call's actual usage.
# ---------------------------------------------------------------------------
RPM_LIMIT = int(os.getenv("RPM_LIMIT", "24"))
TPM_BUDGET = int(os.getenv("TPM_BUDGET", "6000"))  # safety margin under 8K
_MIN_INTERVAL = 60.0 / RPM_LIMIT
_pace_lock = threading.Lock()
_last_call_ts = 0.0
_token_window = deque()  # (monotonic_ts, est_tokens) for calls in the last 60s
_last_call_tokens = 800  # seed estimate; replaced by actual usage after call 1


def _pace() -> None:
    """Pace calls against RPM and a rolling 60-second token window.

    Holds the lock while waiting: callers are effectively serialized, which
    is exactly what the free-tier limits require (LangSmith evaluators run
    with max_concurrency=1, so contention is minimal anyway).
    """
    global _last_call_ts
    with _pace_lock:
        # RPM component: enforce the minimum gap between calls.
        now = time.monotonic()
        wait = _MIN_INTERVAL - (now - _last_call_ts)
        if wait > 0:
            time.sleep(wait)

        # TPM component: wait until the rolling window has room.
        while True:
            cutoff = time.monotonic() - 60.0
            while _token_window and _token_window[0][0] < cutoff:
                _token_window.popleft()
            window_tokens = sum(t for _, t in _token_window)
            if window_tokens + _last_call_tokens <= TPM_BUDGET:
                break
            time.sleep(5.0)

        _last_call_ts = time.monotonic()
        _token_window.append((time.monotonic(), _last_call_tokens))


def _note_actual_usage(model: str, input_tokens: int, output_tokens: int) -> None:
    """Record real usage and self-tune the next call's token estimate."""
    global _last_call_tokens
    LEDGER.record(model, input_tokens, output_tokens)
    _last_call_tokens = max(500, input_tokens + output_tokens)


def _refuse_if_over_budget(model: str, max_output_tokens: int) -> None:
    if LEDGER.would_exceed_budget(model, 4000, max_output_tokens):
        raise RuntimeError(
            f"Cost budget exhausted: {LEDGER.summary()}. Refusing further API calls."
        )


def _record_usage(model: str, response) -> None:
    usage = getattr(response, "usage_metadata", None) or {}
    LEDGER.record(
        model,
        int(usage.get("input_tokens", 0) or 0),
        int(usage.get("output_tokens", 0) or 0),
    )


def get_llm(temperature: float = 0.7, judge: bool = False):
    """
    Returns a chat model client.

    Claude path (default): Opus 5.5 for pipeline and judge; `judge=True`
    raises effort to high. `temperature` is ignored (Opus 5.5 rejects it).

    Groq path (LLM_PROVIDER=groq): openai/gpt-oss-120b for both pipeline and
    judge. `judge=True` bumps reasoning_effort to medium for sharper rubric
    scoring; pipeline runs at low for speed. Paced against free-tier limits.

    Both paths go through the cost ledger.
    """
    if USE_GROQ:
        return _get_groq_llm(temperature, judge)
    return _get_claude_llm(temperature, judge)


def with_structured_output(llm, schema):
    """Bind a Pydantic schema to the model's output.

    Claude uses native structured outputs (output_config.format): LangChain's
    default method forces tool use, which Opus 5.5 rejects with a 400.
    """
    if USE_GROQ:
        return llm.with_structured_output(schema)
    return llm.with_structured_output(schema, method="json_schema")


def _get_groq_llm(temperature: float, judge: bool):
    from langchain_openai import ChatOpenAI

    # Split across two models so the ~300K tokens of a full 3-experiment run
    # fits under Groq's PER-MODEL 200K tokens/day free cap:
    #   pipeline -> gpt-oss-120b (~90K tokens), judge -> gpt-oss-20b (~160K).
    model = GROQ_JUDGE_MODEL if judge else GROQ_MODEL
    reasoning_effort = "medium" if judge else "low"

    class _GroqGuarded(ChatOpenAI):
        """Paces RPM+TPM, guards the token budget, and records usage."""

        def invoke(self, *args, **kwargs):
            _refuse_if_over_budget(model, 4096)
            _pace()
            response = super().invoke(*args, **kwargs)
            usage = getattr(response, "usage_metadata", None) or {}
            _note_actual_usage(
                model,
                int(usage.get("input_tokens", 0) or 0),
                int(usage.get("output_tokens", 0) or 0),
            )
            return response

        def stream(self, *args, **kwargs):
            _refuse_if_over_budget(model, 4096)
            _pace()
            input_tokens = 0
            output_tokens = 0
            for chunk in super().stream(*args, **kwargs):
                usage = getattr(chunk, "usage_metadata", None) or {}
                input_tokens = int(usage.get("input_tokens", input_tokens) or input_tokens)
                output_tokens = int(usage.get("output_tokens", output_tokens) or output_tokens)
                yield chunk
            _note_actual_usage(model, input_tokens, output_tokens)

    return _GroqGuarded(
        model=model,
        api_key=GROQ_API_KEY,
        base_url=GROQ_BASE_URL,
        temperature=temperature,
        max_retries=6,
        timeout=120,
        # gpt-oss on Groq requires max_completion_tokens (not max_tokens) and
        # supports a reasoning_effort control.
        max_completion_tokens=4096,
        extra_body={"reasoning_effort": reasoning_effort},
    )


def _raise_on_refusal(model: str, stop_reason) -> None:
    # A refusal is an empty or partial answer, and silently scoring it would
    # skew the comparison. Server-side fallbacks are deliberately NOT enabled:
    # a different model answering mid-experiment would contaminate the A/B.
    if stop_reason == "refusal":
        raise RuntimeError(f"{model} declined the request (stop_reason=refusal)")


def _get_claude_llm(temperature: float, judge: bool):
    from langchain_anthropic import ChatAnthropic

    model = JUDGE_MODEL if judge else PIPELINE_MODEL

    class _BudgetGuarded(ChatAnthropic):
        """Thin wrapper: refuses calls that would exceed the budget, fails
        loudly on model refusals, and records real token usage (thinking
        tokens are billed as output and included)."""

        def invoke(self, *args, **kwargs):
            _refuse_if_over_budget(model, 4096)
            response = super().invoke(*args, **kwargs)
            _record_usage(model, response)
            _raise_on_refusal(model, response.response_metadata.get("stop_reason"))
            return response

        def stream(self, *args, **kwargs):
            _refuse_if_over_budget(model, 4096)
            input_tokens = 0
            output_tokens = 0
            stop_reason = None
            for chunk in super().stream(*args, **kwargs):
                usage = getattr(chunk, "usage_metadata", None) or {}
                input_tokens = int(usage.get("input_tokens", input_tokens) or input_tokens)
                output_tokens = int(usage.get("output_tokens", output_tokens) or output_tokens)
                stop_reason = chunk.response_metadata.get("stop_reason") or stop_reason
                yield chunk
            LEDGER.record(model, input_tokens, output_tokens)
            _raise_on_refusal(model, stop_reason)

    # No pacing here: Anthropic rate limits are per account tier, and the SDK
    # already retries 429s with backoff. `thinking` is omitted on purpose:
    # Opus 5.5 always runs adaptive thinking and depth is set via `effort`.
    return _BudgetGuarded(
        model=model,
        api_key=ANTHROPIC_API_KEY,
        effort=JUDGE_EFFORT if judge else PIPELINE_EFFORT,
        max_tokens=16000,  # thinking tokens count against max_tokens
        max_retries=6,
        timeout=300,
    )


def cost_summary() -> str:
    provider = "groq/free-tier" if USE_GROQ else "anthropic"
    return f"[{provider}] {LEDGER.summary()}"
