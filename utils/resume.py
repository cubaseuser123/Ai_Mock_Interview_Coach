"""
utils/resume.py - Extracts clean text from a candidate's PDF resume.

This module just takes a PDF from the disk and turns it into a plain string the planner can read. No API calls, no token cost
"""
import os 
import pymupdf
from config import logger 

MAX_RESUME_PAGES = 5 
MAX_RESUME_CHARS = 8000

def extract_resume_text(path : str) -> str: 
    """
    Reads a PDF resume and returns its text. 

    Raises ValueError with a user-safe message whenever the file is missing.
    """
    if not os.path.exists(path):
        raise ValueError("That file does not exist. Double check the path.")
    
    if not path.lower().endswith(".pdf"):
        raise ValueError("Only PDF resumes are supported right now.")
    
    try:
        document = pymupdf.open(path)
    except Exception as e:
        logger.error("Could not open resume %s: %s", path, e)
        raise ValueError("Could not open the file as a PDF.")

    try:
        if document.needs_pass:
            raise ValueError("That PDF is password-protected. Save it without a password and retry.")

        if document.page_count > MAX_RESUME_PAGES:
            raise ValueError(
                f"Resume has {document.page_count} pages - "
                f"max supported is {MAX_RESUME_PAGES}."
            )
        
        parts = []
        for page in document:
            parts.append(page.get_text())
    finally:
        document.close()
    
    text = "\n".join(parts).strip()

    if len(text) > MAX_RESUME_CHARS:
        text = text[:MAX_RESUME_CHARS] + "\n[truncated]"

    if len(text) == 0:
        raise ValueError(
            "No extractable text found. This looks like a scanned or image-only"
            "PDF - convert it to a text PDF and retry."
        )

    logger.info("Extracted %d characters from %s", len(text), path)
    return text 