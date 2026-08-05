"""
graph/state.py — The state dictionary for our LangGraph workflow.
"""
from typing import TypedDict

class InterviewState(TypedDict):
    #user inputs
    target_role: str
    focus_area: str 
    experience_level: str

    #planner output
    interview_plan: dict 
    trending_topics: str 
    evaluate_dimensions: list[str]

    conversation_history: list[dict]

    current_turn : int 
    max_turns: int 
    difficulty_level : int 
    candidate_strengths_so_far: list[str]
    areas_to_probe: list[str]
    interview_complete: bool

    #evaluation and coaching outputs
    evluation_result: dict
    coaching_report : str 
