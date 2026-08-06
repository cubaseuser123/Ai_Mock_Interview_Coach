"""
agents/coach.py — The Coach agent.
"""
from graph.state import InterviewState 
from utils.llm import get_llm
from utils.helpers import read_prompt
from langchain_core.prompts import PromptTemplate
import json 

def coach_node(state: InterviewState) -> dict:
    """Generates the final coaching report as markdown."""
    llm = get_llm(temperature=0.5)

    template = read_prompt("coach.md", __file__)
    prompt = PromptTemplate.from_template(template)

    formatted = prompt.format(
        target_role = state["target_role"],
        evaluation_result = json.dumps({
            "scores" : state.get("per_answer_scores", []),
            "summary" : state.get("overall_assessment", "")
        }, indent=2)
    ) #used json dumps string so that it is easily readable for the LLM. 

    result = llm.invoke(formatted) #no pydantic here too we need free form markdown text 
    return {"coaching_report" : result.content}