"""
agents/planner.py — The Session Planner agent.
"""
from graph.state import InterviewState
from utils.search import search_interview_trends
from utils.llm import get_llm
from utils.helpers import read_prompt
from models.schemas import InterviewPlan 
from langchain_core.prompts import PromptTemplate

def planner_node(state: InterviewState) -> dict:
    """Generates the initial interview plan."""
    llm = get_llm().with_structured_output(InterviewPlan) #forcing strict pydantic schema to the llm response 
    trends = search_interview_trends(state["target_role"]) #web search with jinareader to find trends

    template = read_prompt("planner.md", __file__)
    prompt = PromptTemplate.from_template(template)
    formatted_prompt = prompt.format(
        target_role = state["target_role"],
        focus_area = state["focus_area"],
        experience_level = state["experience_level"],
        trending_topics = trends 
    )

    result = llm.invoke(formatted_prompt) #LLM call but with the strict schema defined

    #updated state so that we can pass this to the next agent in line. 
    return {
        "trending_topics" : trends, 
        "interview_plan" : result.model_dump(),
        "evaluation_dimensions" : result.evaluation_dimensions,
        "areas_to_probe" : result.topics,
        "max_turns" : 5,
        "current_turn" : 0,
        "difficulty_level" : 2 if state["experience_level"] == "intern" else 3,
        "candidate_strengths_so_far" : []
    }