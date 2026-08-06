"""
models/schemas.py — Pydantic models for structured outputs.
"""
from pydantic import BaseModel, Field 

class InterviewPlan(BaseModel):
    topics: list[str] = Field(description="List of topic areas to cover in the interview.")
    difficulty_curve: str = Field(description="Description of how the difficulty should progress.")
    evaluation_dimensions: list[str] = Field(description="List of dimensions to score the candidate on.")

class AnswerScore(BaseModel):
    question: str = Field(description="The question that was asked.")
    answer : str = Field(description="The candidate's answer.")
    dimension: str = Field(description="The dimension on which we are scoring (e.g., Clarity, Accuracy).")
    score : int = Field(description="Score on 1 to 5.")
    justification : str = Field(description="Brief reason for the score.")

class EvaluationResult(BaseModel):
    per_answer_scores: list[AnswerScore] = Field(description="List of scores for each question/answer pair.")
    overall_assessment: str = Field(description="A brief summary of the candidate's performance.")
