"""
main.py — The CLI entry point.
"""
from graph.workflow import build_graph
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
import sys

console = Console()


def print_report(report: str):
    """Format the coaching report nicely using Rich Markdown."""
    console.print()
    console.print(Panel.fit("[bold green]=== Coaching Report ===[/bold green]"))
    console.print(Markdown(report))


def main():
    console.print(Panel.fit("[bold blue]AI Mock Interview Coach[/bold blue]"))

    target_role = console.input("[cyan]Target role (e.g. Data Scientist): [/cyan]")
    experience = console.input("[cyan]Experience level (intern/junior/mid/senior): [/cyan]")
    focus = console.input("[cyan]Focus area (behavioral/technical/case): [/cyan]")

    # [TEACHING COMMENT]
    # We provide ALL state keys that our graph expects.
    # conversation_history starts as an empty list. Because it uses operator.add,
    # the first node's return will be appended to this empty list.
    initial_state = {
        "target_role": target_role,
        "experience_level": experience,
        "focus_area": focus,
        "background": "",
        "specific_topics": [],
        "resume_content": "",
        "conversation_history": [],
        "current_turn": 0,
        "max_turns": 5,
        "difficulty_level": 1,
        "interview_complete": False,
        "candidate_strengths_so_far": [],
        "areas_to_probe": [],
        "evaluation_dimensions": [],
        "interview_plan": {},
        "trending_topics": "",
        "per_answer_scores": [],
        "overall_assessment": "",
        "coaching_report": "",
        "final_output": ""
    }

    console.print("\n[dim]Initializing system and building interview plan...[/dim]")
    graph = build_graph()

    try:
        # We use stream() so the workflow yields at each step,
        # allowing us to print progress or intercept.
        for output in graph.stream(initial_state, {"recursion_limit": 50}):
            # Identify which node just ran
            for key, value in output.items():
                if key == "planner":
                    console.print("[dim]Interview plan ready. Starting interview...[/dim]\n")
                if key == "coach":
                    print_report(value["coaching_report"])

    except KeyboardInterrupt:
        console.print("\n[yellow]Interview cancelled by user.[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]An error occurred: {e}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
