"""
utils/llm.py — Factory for the LLM model.
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from config import GEMINI_API_KEY

def get_llm(temperature: float = 0.7):
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=GEMINI_API_KEY,
        temperature=temperature
    )
