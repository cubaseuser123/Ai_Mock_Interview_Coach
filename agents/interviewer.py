"""
agents/interviewer.py — The Interviewer agent.
"""
import re

from agents.v5_directives import prepare_v5_turn
from graph.state import InterviewState
from utils.llm import get_llm
from utils.helpers import read_prompt, format_history, extract_text
from langchain_core.prompts import PromptTemplate
from rich.console import Console

console = Console()

# When the interviewer emits this line, the interview is over (dynamic turns).
# We filter it out here so it never appears on screen or in the transcript.
INTERVIEW_COMPLETE = "INTERVIEW_COMPLETE"

# v4 convention: the interviewer prefixes every turn with a machine-readable
# topic label on its own line, e.g. "TOPIC: kafka-outbox". We strip that line
# from the transcript (so neither the candidate nor the judges ever see it) and
# use it to keep a deterministic count of consecutive questions per topic — the
# number the v4 prompt needs to enforce its HARD CAP and its early-exit budget.
TOPIC_LINE_RE = re.compile(
    r"^\s*[`*_\s]*TOPIC\s*[`*_\s]*[:\-]\s*(?P<rest>.+?)\s*$", re.IGNORECASE
)


def _normalise_topic(raw: str) -> str:
    """Reduce a raw topic token to a stable lowercase label."""
    return raw.strip().strip("`*_-#. ").lower()


def _parse_topic_line(line: str):
    """Split a line into (topic_label, remainder_text).

    Returns (None, None) when the line is not a TOPIC tag. The label is the
    first token after the tag; anything the model wrote after it is returned as
    `remainder_text` so a drifted one-line tag can never swallow the actual
    question out of the transcript.
    """
    match = TOPIC_LINE_RE.match(line)
    if not match:
        return None, None

    # The model sometimes bolds/backticks the tag ("**TOPIC:** kafka-outbox"),
    # which leaves markdown characters at the start of the captured text.
    rest = match.group("rest").lstrip("`*_ ").strip()
    if not rest:
        return None, None

    parts = rest.split(None, 1)
    label = _normalise_topic(parts[0])
    remainder = parts[1].strip() if len(parts) > 1 else ""
    return label, remainder


def _consecutive_topic_run(topic_history: list[str]) -> int:
    """How many questions in a row were asked on the current (last) topic."""
    if not topic_history:
        return 0
    count = 0
    for label in reversed(topic_history):
        if label == topic_history[-1]:
            count += 1
        else:
            break
    return count


def interviewer_node(state: InterviewState) -> dict:
    """Streams the next question token-by-token, or gracefully ends the interview.

    Also maintains the v4 turn/topic bookkeeping: it tells the model how many
    questions it has left, how many consecutive questions it has already spent
    on the current topic, and how many distinct topics are covered — then
    records the topic label the model declared for this turn.
    """
    llm = get_llm(temperature=0.8)

    template = state.get("prompt_override") or read_prompt("interviewer.md", __file__)
    prompt = PromptTemplate.from_template(template)

    history_str = format_history(state["conversation_history"])

    # --- v4 bookkeeping: derive the counters that the prompt needs -----------
    topic_history = list(state.get("topic_history") or [])
    turns_remaining = max(0, state.get("max_turns", 5) - state.get("current_turn", 0))
    turns_on_current_topic = _consecutive_topic_run(topic_history)
    topics_covered = len({label for label in topic_history if label})

    # --- v5: analyst reads the last answer, code decides this turn ----------
    v5 = None
    if state.get("interviewer_version") == "v5":
        v5 = prepare_v5_turn(state, turns_remaining)

    formatted_prompt = prompt.format(
        target_role=state["target_role"],
        experience_level=state["experience_level"],
        focus_area=state["focus_area"],
        difficulty_level=state["difficulty_level"],
        areas_to_probe=", ".join(state["areas_to_probe"]),
        candidate_strengths_so_far=", ".join(state["candidate_strengths_so_far"]),
        conversation_history=history_str,
        # v1/v2/v3 templates simply ignore these extra keywords (str.format
        # tolerates unused names), so only v4's prompt consumes them.
        turns_remaining=turns_remaining,
        turns_on_current_topic=turns_on_current_topic,
        topics_covered=topics_covered,
        # Only interviewer_v5.md consumes these two.
        current_topic=v5["plan"]["topic"] if v5 else "",
        directives=v5["plan"]["directives"] if v5 else "",
    )

    console.print("\n[bold cyan]Interviewer:[/bold cyan] ", end="")

    buffer = ""         # incomplete line still being assembled
    full_text = ""      # everything the model said (sentinel detection)
    visible_lines = []  # the lines we actually show and store
    declared_topic = "" # this turn's TOPIC label, if the model supplied one

    # Each chunk is appended to the buffer. A newline means a full line is
    # ready — print it (or drop the sentinel / TOPIC tag) and keep assembling
    # the next one.
    for chunk in llm.stream(formatted_prompt):
        piece = extract_text(chunk.content)
        full_text += piece
        buffer += piece

        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            if INTERVIEW_COMPLETE in line:
                continue

            label, remainder = _parse_topic_line(line)
            if label is not None:
                if not declared_topic:
                    declared_topic = label
                if remainder:
                    console.print(remainder)
                    visible_lines.append(remainder)
                continue

            console.print(line)
            visible_lines.append(line)

    # Flush the final line — LLM output usually has no trailing newline.
    # Guard against a sentinel (or a TOPIC tag) left without a newline.
    if buffer.strip():
        label, remainder = _parse_topic_line(buffer)
        if label is not None:
            if not declared_topic:
                declared_topic = label
            if remainder:
                console.print(remainder, end="")
                visible_lines.append(remainder)
        else:
            clean_buffer = buffer.replace(INTERVIEW_COMPLETE, "").strip()
            if clean_buffer:
                console.print(clean_buffer, end="")
                visible_lines.append(clean_buffer)
    console.print()

    # Decide what to store. full_text is the ground truth for the sentinel
    # check; visible_lines is exactly what was shown to the user.
    clean_text = "\n".join(visible_lines).strip()
    interview_over = INTERVIEW_COMPLETE in full_text

    # If the model forgot its tag, treat the turn as a continuation of the
    # current topic ("unknown" on the very first turn). That is the
    # conservative reading: an omitted tag can never be used to silently reset
    # the consecutive-topic counter and escape the HARD CAP.
    topic_label = declared_topic or (topic_history[-1] if topic_history else "unknown")
    if v5:
        # v5 topics are assigned by code, never taken from the model's output.
        topic_label = v5["plan"]["label"]

    update = {
        "conversation_history": [{"role": "interviewer", "text": clean_text}],
        "topic_history": topic_history + [topic_label],
    }
    if v5:
        update["claims_ledger"] = v5["claims_ledger"]
        update["last_analysis"] = v5["analysis"]
    if interview_over:
        update["interview_complete"] = True

    return update
