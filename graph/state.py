"""
graph/state.py — The state dictionary for our LangGraph workflow.
"""
from typing import TypedDict, Annotated
import operator

class InterviewState(TypedDict):
    # User inputs
    target_role: str
    focus_area: str
    experience_level: str
    background: str
    specific_topics: list[str]
    resume_content: str
    
    # Planner output
    interview_plan: dict
    trending_topics: str
    evaluation_dimensions: list[str]
    
    # Interview loop data
    conversation_history: Annotated[list[dict], operator.add]
    current_turn: int
    max_turns: int
    difficulty_level: int
    candidate_strengths_so_far: list[str]
    areas_to_probe: list[str]
    interview_complete: bool

    # v4 bookkeeping: one TOPIC label per interviewer turn, in order. Lets the
    # graph count consecutive questions per topic deterministically and hand
    # the interviewer a real number to enforce its HARD CAP against.
    topic_history: list[str]

    # v5 only: which interviewer mode is active ("v5" turns on the analyst +
    # code-decided directives), the running list of the candidate's claims
    # (for contradiction checks), and the latest analyst report (for traces).
    interviewer_version: str
    claims_ledger: list[str]
    last_analysis: dict

    # Evaluation and Coaching outputs
    per_answer_scores: list[dict]
    overall_assessment: str
    coaching_report: str
    final_output: str

    # Experiment-only: scripted candidate answers and prompt override
    candidate_script: list[str]
    prompt_override: str  # if non-empty, replaces the default interviewer.md