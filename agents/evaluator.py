"""
agents/evaluator.py — The Evaluator agent.
"""
from graph.state import InterviewState
from utils.llm import get_llm
from utils.helpers import read_prompt, format_history
from models.schemas import EvaluationResult
from langchain_core.prompts import PromptTemplate 

def evaluator_node(state: InterviewState) -> dict:
    """Scores all Q&A pairs from the interview."""
    llm = get_llm(temperature=0.2).with_structured_output(EvaluationResult) #has to be pydantic schema again

    history_str = format_history(state["conversation_history"])

    template = read_prompt("evaluator.md", __file__)
    prompt = PromptTemplate.from_template(template)

    formatted = prompt.format(
        target_role = state["target_role"],
        experience_level = state["experience_level"],
        evaluation_dimensions = ", ".join(state["evaluation_dimensions"]),
        conversation_history=history_str
    )

    result = llm.invoke(formatted)

    return{
        "per_answer_scores" : [score.model_dump() for score in result.per_answer_scores],
        "overall_assessment" : result.overall_assessment
    } #just converting the pydantic objects to dict for the the graph state here