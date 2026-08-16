"""
agents/interviewer.py — The Interviewer agent.
"""
from graph.state import InterviewState
from utils.llm import get_llm
from utils.helpers import read_prompt, format_history, extract_text
from langchain_core.prompts import PromptTemplate
from rich.console import Console

console = Console()

# When the interviewer emits this line, the interview is over (dynamic turns).
# We filter it out here so it never appears on screen or in the transcript.
INTERVIEW_COMPLETE = "INTERVIEW_COMPLETE"


def interviewer_node(state: InterviewState) -> dict:
    """Streams the next question token-by-token, or gracefully ends the interview. The final clean text is still stored in conversation_history."""
    llm = get_llm(temperature=0.8)

    template = read_prompt("interviewer.md", __file__)
    prompt = PromptTemplate.from_template(template)

    history_str = format_history(state["conversation_history"])

    formatted_prompt = prompt.format(
        target_role=state["target_role"],
        experience_level=state["experience_level"],
        focus_area=state["focus_area"],
        difficulty_level=state["difficulty_level"],
        areas_to_probe=", ".join(state["areas_to_probe"]),
        candidate_strengths_so_far=", ".join(state["candidate_strengths_so_far"]),
        conversation_history=history_str
    )

    console.print("\n[bold cyan]Interviewer:[/bold cyan] ", end="")

    buffer = ""         # incomplete line still being assembled
    full_text = ""      # everything the model said (sentinel detection)
    visible_lines = []  # the lines we actually show and store

    # Each chunk is appended to the buffer. A newline means a full line is
    # ready — print it (or drop it if it's the sentinel) and keep assembling
    # the next one.
    for chunk in llm.stream(formatted_prompt):
        piece = extract_text(chunk.content)
        full_text += piece
        buffer += piece

        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            if INTERVIEW_COMPLETE in line:
                continue
            console.print(line)
            visible_lines.append(line)

    # Flush the final line — LLM output usually has no trailing newline.
    # Guard against a sentinel left without a newline so it never shows.
    if buffer.strip():
        clean_buffer = buffer.replace(INTERVIEW_COMPLETE, "").strip()
        if clean_buffer:
            console.print(clean_buffer, end="")
            visible_lines.append(clean_buffer)
    console.print()

    # Decide what to store. full_text is the ground truth for the sentinel
    # check; visible_lines is exactly what was shown to the user.
    clean_text = "\n".join(visible_lines).strip()
    interview_over = INTERVIEW_COMPLETE in full_text

    update = {
        "conversation_history": [{"role": "interviewer", "text": clean_text}],
    }
    if interview_over:
        update["interview_complete"] = True

    return update
