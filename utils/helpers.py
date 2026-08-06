"""
utils/helpers.py — Shared utility functions used by multiple agents.
"""
import os 

def read_prompt(filename: str, caller_file: str) -> str:
    """
    Reads a prompt template file from the prompts/ directory.

    Args:
        filename: The name of the prompt file (e.g., "planner.md").
        caller_file: Pass __file__ from the calling module so the pathresolves correctly regardless of where python is run from.
    """
    project_root = os.path.join(os.path.dirname(caller_file), "..")
    path = os.path.join(project_root, "prompts", filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
    
def format_history(history: list[dict]) -> str:
    """
    Converts the conversation history list into a readable string for LLM prompts.

    Example output:
        Interviewer: Tell me about a time...
        Candidate: Sure, at my last role...
    """
    lines = []
    for msg in history:
        role = msg["role"].capitalize()
        text = msg["text"] 
        lines.append(f"{role}: {text}")
    return "\n".join(lines)
