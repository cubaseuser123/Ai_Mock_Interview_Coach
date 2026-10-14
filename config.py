"""
config.py - Centralized configuration and logging setup.
""" 
import os 
import logging 
from dotenv import load_dotenv

# override=True: values in .env win over stale keys left in the OS environment.
# Model provider settings (LLM_PROVIDER, GROQ_API_KEY, ANTHROPIC_API_KEY, ...)
# are read in utils/llm.py.
load_dotenv(override=True)

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
    LANGSMITH_TRACING = False


# Suppress noisy SDK loggers — we only want our own logs visible
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("google.auth").setLevel(logging.WARNING)