"""Shared pydantic types for rubric + claim inventory (FR-1, FR-2)."""
from pydantic import BaseModel


class Competency(BaseModel):
    name: str
    weight: float  # 0-1, sums to ~1 across the rubric
    seniority_bar: str
    description: str


class Rubric(BaseModel):
    job_post_hash: str
    target_position: str | None = None
    competencies: list[Competency]


class Claim(BaseModel):
    claim_id: str
    source: str  # "resume" | "portfolio"
    subject: str  # "project" | "skill" | "metric"
    text: str
    tech: list[str] = []
    metric_value: str | None = None


class ConflictingClaim(BaseModel):
    subject: str
    claims: list[Claim]  # 2+ claims about the same subject with differing facts


class ClaimInventory(BaseModel):
    claims: list[Claim]
    conflicts: list[ConflictingClaim] = []
