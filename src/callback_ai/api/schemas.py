from pydantic import BaseModel

from callback_ai.config import settings


class StartSessionRequest(BaseModel):
    job_post: str
    resume: str | None = None
    portfolio_link: str | None = None
    persona: str = "neutral"
    seniority: str | None = None   # junior | mid | senior -- tunes how hard the agent probes
    budget: int = settings.question_budget


class InterviewerInfo(BaseModel):
    key: str
    name: str
    role: str
    opening: str
    accent: str
    style: str
    voice_pitch: float
    voice_rate: float
    voice_hint: str
    neural_voice: str


class StartSessionResponse(BaseModel):
    session_id: str
    question: str | None
    competency: str | None = None
    competencies: list[str] = []
    budget: int = settings.question_budget
    conflicts: int = 0
    interviewer: InterviewerInfo | None = None


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
