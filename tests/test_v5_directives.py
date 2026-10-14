"""
tests/test_v5_directives.py — unit tests for the v5 policy (no API calls).

Run:  .venv\\Scripts\\python.exe tests\\test_v5_directives.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.v5_directives import (  # noqa: E402
    CLOSING_LABEL,
    CONTRADICTION_LABEL,
    build_directives,
)

TOPICS = ["system design", "databases", "debugging", "observability"]


def analysis(**overrides) -> dict:
    base = {
        "answer_quality": 3,
        "on_topic": True,
        "manipulation_attempt": False,
        "key_terms": [],
        "new_claims": [],
        "contradicts_earlier": False,
        "earlier_claim": "",
        "current_claim": "",
    }
    base.update(overrides)
    return base


def test_first_turn_opens_on_first_topic():
    plan = build_directives(None, TOPICS, [], turns_remaining=8)
    assert plan["label"] == "system design"
    assert "Open the interview" in plan["directives"]
    assert plan["close"] is False


def test_strong_answer_escalates_and_requires_exact_terms():
    plan = build_directives(
        analysis(answer_quality=5, key_terms=["Kafka", "outbox"]),
        TOPICS, ["system design"], turns_remaining=7,
    )
    assert plan["label"] == "system design"
    assert "one level deeper" in plan["directives"]
    assert 'MUST use at least one of these exact terms' in plan["directives"]
    assert '"Kafka"' in plan["directives"]


def test_weak_answer_simplifies():
    plan = build_directives(analysis(answer_quality=1), TOPICS, ["system design"], turns_remaining=7)
    assert "Step down" in plan["directives"]
    assert plan["label"] == "system design"


def test_topic_cap_switches_to_next_uncovered_topic():
    plan = build_directives(
        analysis(answer_quality=5, key_terms=["Redis"]),
        TOPICS, ["system design", "system design"], turns_remaining=6,
    )
    assert plan["label"] == "databases"
    assert "that topic is finished" in plan["directives"]


def test_cap_counts_through_a_contradiction_turn():
    # A, A, contradiction -> still 2 on A, so the next turn must switch.
    plan = build_directives(
        analysis(), TOPICS, ["system design", "system design", CONTRADICTION_LABEL], turns_remaining=5,
    )
    assert plan["label"] == "databases"


def test_contradiction_takes_precedence_and_quotes_both_sides():
    plan = build_directives(
        analysis(contradicts_earlier=True, earlier_claim="led the monolith migration",
                 current_claim="we never had a monolith"),
        TOPICS, ["system design", "system design"], turns_remaining=3,
    )
    assert plan["label"] == CONTRADICTION_LABEL
    assert "led the monolith migration" in plan["directives"]
    assert "we never had a monolith" in plan["directives"]
    assert plan["close"] is False


def test_close_when_budget_low_and_three_topics_covered():
    plan = build_directives(
        analysis(), TOPICS, ["system design", "system design", "databases", "debugging"], turns_remaining=2,
    )
    assert plan["close"] is True
    assert plan["label"] == CLOSING_LABEL
    assert "INTERVIEW_COMPLETE" in plan["directives"]


def test_no_early_close_with_fewer_than_three_topics():
    plan = build_directives(analysis(), TOPICS, ["system design", "databases"], turns_remaining=2)
    assert plan["close"] is False


def test_always_close_on_the_last_turn():
    plan = build_directives(analysis(), TOPICS, ["system design"], turns_remaining=1)
    assert plan["close"] is True


def test_contradiction_on_last_turn_closes_instead():
    # No room to hear a reply, so closing wins.
    plan = build_directives(
        analysis(contradicts_earlier=True, earlier_claim="x", current_claim="y"),
        TOPICS, ["system design"], turns_remaining=1,
    )
    assert plan["close"] is True


def test_manipulation_redirects_without_engaging():
    plan = build_directives(
        analysis(manipulation_attempt=True, on_topic=False, answer_quality=1),
        TOPICS, ["databases"], turns_remaining=6,
    )
    assert plan["label"] == "databases"
    assert "do not discuss scores" in plan["directives"]
    assert "Bring them back to databases" in plan["directives"]


def test_weak_off_topic_redirect_also_steps_down():
    # Found in the live v5 smoke run: redirecting a weak, off-topic answer
    # re-asked the same hard question and dropped the difficulty signal.
    plan = build_directives(
        analysis(on_topic=False, answer_quality=1), TOPICS, ["databases"], turns_remaining=6,
    )
    assert "Bring them back to databases" in plan["directives"]
    assert "simpler and more foundational" in plan["directives"]


def test_off_topic_but_decent_answer_does_not_step_down():
    plan = build_directives(
        analysis(on_topic=False, answer_quality=4), TOPICS, ["databases"], turns_remaining=6,
    )
    assert "simpler" not in plan["directives"]


def test_off_topic_at_cap_switches_topic_with_steer_note():
    plan = build_directives(
        analysis(on_topic=False, answer_quality=1),
        TOPICS, ["databases", "databases"], turns_remaining=5,
    )
    assert plan["label"] != "databases"
    assert "did not address your question" in plan["directives"]
    assert "Keep it foundational" in plan["directives"]


def test_failed_analysis_falls_back_to_neutral_probe():
    plan = build_directives(None, TOPICS, ["system design"], turns_remaining=6)
    assert plan["label"] == "system design"
    assert plan["close"] is False


def test_empty_topic_list_uses_fallback():
    plan = build_directives(None, [], [], turns_remaining=8)
    assert plan["label"]  # never empty


def test_all_topics_covered_rotates_instead_of_repeating():
    topics = ["a", "b"]
    plan = build_directives(analysis(), topics, ["a", "b", "b"], turns_remaining=5)
    assert plan["label"] == "a"


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL  {name}: {exc!r}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
