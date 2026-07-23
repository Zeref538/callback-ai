"""Deterministic merge of resume + portfolio claims into one inventory.

No LLM involved: merging feeds the evidence gate later, and a quote must trace
back to a specific source text, so guessing here would break that guarantee.
"""
from difflib import SequenceMatcher

from callback_ai.ingest.schemas import Claim, ClaimInventory, ConflictingClaim

SIMILARITY_THRESHOLD = 0.6


def _similar(a: Claim, b: Claim) -> bool:
    if a.subject != b.subject:
        return False
    if a.tech and b.tech and set(t.lower() for t in a.tech) & set(t.lower() for t in b.tech):
        return True
    return SequenceMatcher(None, a.text.lower(), b.text.lower()).ratio() >= SIMILARITY_THRESHOLD


def merge_claims(resume_claims: list[Claim], portfolio_claims: list[Claim]) -> ClaimInventory:
    all_claims = list(resume_claims) + list(portfolio_claims)
    groups: list[list[Claim]] = []

    for claim in all_claims:
        placed = False
        for group in groups:
            if any(_similar(claim, existing) for existing in group):
                group.append(claim)
                placed = True
                break
        if not placed:
            groups.append([claim])

    merged: list[Claim] = []
    conflicts: list[ConflictingClaim] = []

    for group in groups:
        if len(group) == 1:
            merged.append(group[0])
            continue

        metric_values = {c.metric_value for c in group if c.metric_value is not None}
        if len(metric_values) > 1:
            # Same subject, differing facts -> surface as a conflict, don't pick a winner.
            conflicts.append(ConflictingClaim(subject=group[0].subject, claims=group))
            merged.extend(group)
        else:
            # Non-conflicting duplicates/overlap -> keep the richer claim (union of tech).
            base = group[0]
            merged_tech = sorted({t for c in group for t in c.tech})
            merged.append(base.model_copy(update={"tech": merged_tech}))

    return ClaimInventory(claims=merged, conflicts=conflicts)
