"""
graph/workflow.py — LangGraph setup and conditional logic.
"""
from langgraph.graph import StateGraph, START, END
from graph.state import InterviewState
from agents.planner import planner_node
from agents.interviewer import interviewer_node
from agents.evaluator import evaluator_node
from agents.coach import coach_node
from rich.console import Console

console = Console()


def human_input_node(state: InterviewState) -> dict:
    """
    Collects the candidate's typed answer.

    This node is not an AI agent. It only reads keyboard input. The
    interviewer question is already streamed live by interviewer_node, so
    there is no need to re-print it here.
    """
    if state.get("interview_complete", False):
        return {}

    user_text = console.input("\n[bold green]You:[/bold green] ")
    current = state.get("current_turn", 0)

    return {
        "conversation_history": [{"role": "candidate", "text": user_text}],
        "current_turn": current + 1
    }


def should_continue(state: InterviewState) -> str:
    """
    Conditional edge: end the interview when the interviewee says it is
    complete OR when we hit the hard turn cap — whichever comes first.

    This is a plain Python function — NOT an LLM call. This is a deliberate
    design choice: the LLM gets to say we are done early, but the hard cap
    still exists as a backstop.
    """

    if state["interview_complete"] or state["current_turn"] >= state["max_turns"]:
        return "evaluator"
    return "interviewer"


def build_graph(human_input=human_input_node):
    """Constructs and compiles the LangGraph state machine"""
    workflow = StateGraph(InterviewState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("interviewer", interviewer_node)
    workflow.add_node("human_input", human_input)
    workflow.add_node("evaluator", evaluator_node)
    workflow.add_node("coach", coach_node)

    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "interviewer")
    workflow.add_edge("interviewer", "human_input")

    workflow.add_conditional_edges(
        "human_input",
        should_continue,
        {
            "interviewer": "interviewer",
            "evaluator": "evaluator"
        }
    )

    workflow.add_edge("evaluator", "coach")
    workflow.add_edge("coach", END)

    return workflow.compile()
