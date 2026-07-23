"""Persona sets prompt tone + probe aggressiveness. Never touches the
evidence gate or scoring rubric -- those stay persona-invariant to protect
reproducibility (NFR-5) and the grading-consistency metric."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Persona:
    name: str
    tone: str
    probe_threshold: float  # coverage_score below this triggers a probe
    feedback_prefix: str


PERSONAS: dict[str, Persona] = {
    "friendly": Persona(
        name="friendly",
        tone="encouraging, softens follow-ups",
        probe_threshold=0.3,
        feedback_prefix="Nice effort —",
    ),
    "neutral": Persona(
        name="neutral",
        tone="plain, professional",
        probe_threshold=0.45,
        feedback_prefix="",
    ),
    "adversarial": Persona(
        name="adversarial",
        tone="terse, skeptical, challenges vague numbers directly",
        probe_threshold=0.6,
        feedback_prefix="Let's be precise:",
    ),
}


def get_persona(name: str) -> Persona:
    try:
        return PERSONAS[name]
    except KeyError:
        raise ValueError(f"unknown persona {name!r}, choose one of {sorted(PERSONAS)}") from None
