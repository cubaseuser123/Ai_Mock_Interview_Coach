"""
config.py - Centralized configuration and logging setup.
""" 
import os 
import logging 
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in env variables.")

logging.basicConfig(
    level = logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("InterviewCoach")

#these are optional since langsmith is not essential for this project to run, so its imports failing must not crash the project either.

LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "").strip().lower() == "true"
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "ai-mock-interview-coach")

if LANGSMITH_TRACING and not LANGSMITH_API_KEY:
    logger.warning(
        "LANGSMITH_TRACING is true but LANGSMITH_API_KEY is missing -"
        "tracing disabled. The app will continue normally."
    )
    LANGMITH_TRACING = False 


# Suppress noisy SDK loggers — we only want our own logs visible
logging.getLogger("google_genai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("google.auth").setLevel(logging.WARNING)