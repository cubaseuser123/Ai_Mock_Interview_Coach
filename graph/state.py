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
    
    # Evaluation and Coaching outputs
    per_answer_scores: list[dict]
    overall_assessment: str
    coaching_report: str
    final_output: str