"""
agents/planner.py — The Session Planner agent.
"""
from graph.state import InterviewState
from utils.search import search_interview_trends
from utils.llm import get_llm, with_structured_output
from utils.helpers import read_prompt
from models.schemas import InterviewPlan
from langchain_core.prompts import PromptTemplate

def planner_node(state: InterviewState) -> dict:
    """Generates the initial interview plan."""
    llm = with_structured_output(get_llm(), InterviewPlan) #forcing strict pydantic schema to the llm response
    trends = search_interview_trends(state["target_role"]) #web search with jinareader to find trends

    resume_text = state.get("resume_content", " ")
    if not resume_text.strip():
        resume_text = "No resume provided. Plan from the role and area alone."

    template = read_prompt("planner.md", __file__)
    prompt = PromptTemplate.from_template(template)
    formatted_prompt = prompt.format(
        target_role = state["target_role"],
        focus_area = state["focus_area"],
        experience_level = state["experience_level"],
        trending_topics = trends,
        resume_content = resume_text 
    )

    result = llm.invoke(formatted_prompt) #LLM call but with the strict schema defined

    #updated state so that we can pass this to the next agent in line. 
    return {
        "trending_topics" : trends, 
        "interview_plan" : result.model_dump(),
        "evaluation_dimensions" : result.evaluation_dimensions,
        "areas_to_probe" : result.topics,
        # Honor an explicitly-set max_turns (e.g. experiments); default 5 for
        # the interactive app, where no caller pre-sets it.
        "max_turns" : state.get("max_turns") or 5,
        "current_turn" : 0,
        "difficulty_level" : 2 if state["experience_level"] == "intern" else 3,
        "candidate_strengths_so_far" : []
    }