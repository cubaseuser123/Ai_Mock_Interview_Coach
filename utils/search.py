"""
utils/search.py — Simple web scraper using Jina Reader.
"""
import os

import httpx
from config import logger
from langsmith import traceable

# Experiments set DISABLE_WEB_SEARCH=1 so every prompt version plans from the
# same fixed trends text; live web results change run to run and would add
# noise to the comparison. The interactive app always does the real search.
FIXED_TRENDS = "Recent trends show a focus on microservices, system design, and database optimization."

@traceable(run_type="tool")
def search_interview_trends(role: str) -> str:
    if os.getenv("DISABLE_WEB_SEARCH") == "1":
        return FIXED_TRENDS

    # Reddit r/cscareerquestions gives real, recent candidate experiences
    # with actual questions being asked — much higher signal than HN threads.
    url_to_search = (
        f"https://www.reddit.com/r/cscareerquestions/search/"
        f"?q={role.replace(' ', '+')}+interview+questions&sort=top&t=year"
    )
    jina_url = f"https://r.jina.ai/{url_to_search}"

    logger.info(f"Searching for trends at {jina_url}")

    try:
        response = httpx.get(jina_url, timeout=15.0)
        response.raise_for_status()
        return response.text[:3000]
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return "Could not retrieve current trends. Use general knowledge."
