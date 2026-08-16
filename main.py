"""
main.py — The CLI entry point.
"""
import os
import sys
from datetime import datetime
from graph.workflow import build_graph
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.rule import Rule

console = Console()


def print_welcome():
    """Print a welcoming intro panel that explains what the system does."""
    console.print()
    console.print(Panel(
        "[bold blue]AI Mock Interview Coach[/bold blue]\n\n"
        "This system conducts a realistic mock interview tailored to your target role,\n"
        "then delivers structured feedback on your strengths and areas to improve.\n\n"
        "[dim]Powered by Gemini 3.5 Flash · Built with LangGraph[/dim]",
        title="Welcome",
        border_style="blue",
        padding=(1, 2)
    ))
    console.print()


def print_report(report: str):
    """Format the coaching report nicely using Rich Markdown."""
    console.print()
    console.print(Rule("[bold green]Coaching Report[/bold green]", style="green"))
    console.print()
    console.print(Markdown(report))


def save_transcript(target_role: str, experience: str, focus: str, conversation_history: list, report: str):
    """
    Saves the coaching report to a timestamped markdown file in transcripts/.

    [TEACHING COMMENT]
    os.makedirs(..., exist_ok=True) creates the folder if it doesn't exist yet
    without throwing an error if it already does. Clean one-liner for this.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    safe_role = target_role.strip().replace(" ", "_") or "Role"
    filename = f"transcripts/{timestamp}_{safe_role}.md"

    os.makedirs("transcripts", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write("# Mock Interview Transcript\n\n")
        f.write(f"- **Role:** {target_role}\n")
        f.write(f"- **Experience Level:** {experience}\n")
        f.write(f"- **Focus Area:** {focus}\n")
        f.write(f"- **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("---\n\n")
        f.write("## Conversation History\n\n")
        
        for message in conversation_history:
            if message.get("role") == "interviewer":
                f.write(f"**Interviewer:** {message.get('text')}\n\n")
            elif message.get("role") == "candidate":
                f.write(f"**You:** {message.get('text')}\n\n")
                
        f.write("---\n\n")
        f.write("## Coaching Report\n\n")
        f.write(report)

    return filename


def main():
    print_welcome()

    console.print("[bold]Let's set up your session:[/bold]\n")
    target_role = console.input("[cyan]Target role (e.g. Data Scientist): [/cyan]")
    experience  = console.input("[cyan]Experience level (intern/junior/mid/senior): [/cyan]")
    focus       = console.input("[cyan]Focus area (behavioral/technical/case/mixed): [/cyan]")
    background  = console.input("[cyan]Brief background or resume snippet (press Enter to skip): [/cyan]")

    # [TEACHING COMMENT]
    # We provide ALL state keys that our graph expects.
    # conversation_history starts as an empty list. Because it uses operator.add,
    # the first node's return will be appended to this empty list.
    initial_state = {
        "target_role": target_role,
        "experience_level": experience,
        "focus_area": focus,
        "background": background,
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

    console.print("\n[dim]Searching for current interview trends and building your plan...[/dim]")
    graph = build_graph()

    try:
        # We use stream() so the workflow yields at each step,
        # allowing us to print progress or intercept.
        for output in graph.stream(initial_state, {"recursion_limit": 50}):
            # Identify which node just ran
            for key, value in output.items():
                if key == "planner":
                    console.print("[dim]Interview plan ready. Starting your interview...[/dim]\n")
                if key == "human_input":
                    # Check if this was the last turn — if so, warn the user
                    if value.get("current_turn", 0) >= initial_state["max_turns"]:
                        console.print(
                            "\n[dim]That was your final answer. "
                            "Evaluating your performance — this may take a moment...[/dim]\n"
                        )
                if key == "coach":
                    report_content = value.get("coaching_report", "")
                    print_report(report_content)

                    # Save to file
                    saved_path = save_transcript(target_role, experience, focus, [], report_content)
                    console.print(f"\n[bold green]✓ Report saved to {saved_path}[/bold green]\n")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interview cancelled by user.[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]An error occurred: {e}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
