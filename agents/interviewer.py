"""
agents/interviewer.py — The Interviewer agent.
"""
from graph.state import InterviewState
from utils.llm import get_llm
from utils.helpers import read_prompt, format_history
from langchain_core.prompts import PromptTemplate

def interviewer_node(state: InterviewState) -> dict:
    """Determines the next question to ask."""
    llm = get_llm(temperature=0.8)

    template = read_prompt("interviewer.md", __file__)
    prompt = PromptTemplate.from_template(template)

    history_str = format_history(state["conversation_history"])

    formatted_prompt = prompt.format(
        target_role = state["target_role"],
        experience_level = state["experience_level"],
        focus_area= state["focus_area"],
        difficulty_level= state["difficulty_level"],
        areas_to_probe=", ".join(state["areas_to_probe"]),
        candidate_strengths_so_far=", ".join(state["candidate_strengths_so_far"]),
        conversation_history=history_str
    )

    response = llm.invoke(formatted_prompt) #not using pydantic schema here we need a free form question from the llm
    interviewer_text = response.content 

    return{
        "conversation_history" : [{"role" : "interviewer", "text" : interviewer_text}] #just appending this one field to the conversation history list[dict]
    }