"""
utils/search.py — Simple web scraper using Jina Reader.
"""
import httpx
from config import logger

def search_interview_trends(role: str) -> str:

    url_to_search = f"https://hn.algolia.com/?q={role}+interview"
    jina_url = f"https://r.jina.ai/{url_to_search}"
    
    logger.info(f"Searching for trends at {jina_url}")
    
    try:
        response = httpx.get(jina_url, timeout=10.0)
        response.raise_for_status()
        content = response.text
        return content[:1000]
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return "Could not retrieve current trends. Use general knowledge."

