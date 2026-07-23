from pydantic import BaseModel


class CompetencyReport(BaseModel):
    competency: str
    score: float
    evidence_quote: str
    low_confidence: bool = False


class Report(BaseModel):
    competency_reports: list[CompetencyReport]
    overall_summary: str
    top_fixes: list[str]
    model_answers: dict[str, str] = {}  # competency -> stronger model answer, weak competencies only
