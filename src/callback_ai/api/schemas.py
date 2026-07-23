from pydantic import BaseModel

from callback_ai.config import settings


class StartSessionRequest(BaseModel):
    job_post: str
    resume: str | None = None
    portfolio_link: str | None = None
    persona: str = "neutral"
    budget: int = settings.question_budget


class StartSessionResponse(BaseModel):
    session_id: str
    question: str | None
    competency: str | None = None
    competencies: list[str] = []
    budget: int = settings.question_budget
    conflicts: int = 0


class AnswerRequest(BaseModel):
    answer: str


class AnswerResponse(BaseModel):
    feedback: str
    coverage_score: float
    low_confidence: bool
    done: bool
    next_question: str | None = None
    next_competency: str | None = None
    turn: int = 0
