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
    Prompts the human in the terminal for their answer.

    This node is NOT an AI agent. It simply:
    1. Prints the last interviewer question
    2. Collects the user's typed response
    3. Returns the response as a new conversation history entry
    """
    last_message = state["conversation_history"][-1]["text"]
    console.print(f"\n[bold cyan]Interviewer:[/bold cyan]{last_message}")

    user_text = console.input("\n[bold green]You:[/bold green] ")

    current = state.get("current_turn", 0)

    return{
        "conversation_history" : [{"role" : "candidate", "text" : user_text}],
        "current_turn" : current + 1
    }
    

def should_continue(state: InterviewState) -> str:
    """
    Conditional edge logic: checks if we have hit the max turns.
    If yes, go to the evaluator. If no, loop back to the interviewer.

    This is a plain Python function — NOT an LLM call. This is a deliberate
    design choice because LLM-based routing is non-deterministic and could
    loop forever or exit early. 
    """

    if state["current_turn"] >= state["max_turns"]:
        return "evaluator"
    return "interviewer"


def build_graph():
    """Constructs and compiles the LangGraph state machine"""
    workflow = StateGraph(InterviewState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("interviewer", interviewer_node)
    workflow.add_node("human_input", human_input_node)
    workflow.add_node("evaluator", evaluator_node)
    workflow.add_node("coach", coach_node)

    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "interviewer")
    workflow.add_edge("interviewer", "human_input")

    workflow.add_conditional_edges(
        "human_input",
        should_continue,
        {
            "interviewer" : "interviewer",
            "evaluator" : "evaluator"
        }
    )

    workflow.add_edge("evaluator", "coach")
    workflow.add_edge("coach", END)

    return workflow.compile()