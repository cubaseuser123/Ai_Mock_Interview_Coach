"""
utils/helpers.py — Shared utility functions used by multiple agents.
"""
import os 
import hashlib 

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

#we are tracking prompt version changes here based on the hashing that we have done. this is for observability experiments when prompts get changed. 
def compute_prompt_version() -> str:
    """Short hash of prompts/ - changes whenever any prompt file changes."""
    prompts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
    hasher = hashlib.sha256()

    for filename in sorted(os.listdir(prompts_dir)):
        if not filename.endswith(".md"):
            continue 
        hasher.update(filename.encode("utf-8"))
        with open(os.path.join(prompts_dir, filename), "rb") as f:
            hasher.update(f.read())
            
    return hasher.hexdigest()[:8]
    
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


def extract_text(content) -> str:
    """
    Safely extracts a clean string from LLM responses.
    Handles plain strings, lists of content blocks (e.g. Gemini 3.5 reasoning signatures),
    and dict objects.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
        return "".join(parts).strip()
    return str(content)
