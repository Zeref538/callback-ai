from callback_ai.ingest.claim_merger import merge_claims
from callback_ai.ingest.schemas import Claim


def test_non_conflicting_claims_merge_and_union_tech():
    resume = [Claim(claim_id="r1", source="resume", subject="project", text="Built a caching layer", tech=["Redis"])]
    portfolio = [Claim(claim_id="p1", source="portfolio", subject="project", text="Built a caching layer", tech=["Python"])]

    inventory = merge_claims(resume, portfolio)

    assert len(inventory.claims) == 1
    assert set(inventory.claims[0].tech) == {"Redis", "Python"}
    assert inventory.conflicts == []


def test_conflicting_metric_values_are_flagged_not_resolved():
    resume = [
        Claim(claim_id="r1", source="resume", subject="metric", text="reduced latency", tech=["Redis"], metric_value="30%")
    ]
    portfolio = [
        Claim(claim_id="p1", source="portfolio", subject="metric", text="reduced latency", tech=["Redis"], metric_value="50%")
    ]

    inventory = merge_claims(resume, portfolio)

    assert len(inventory.conflicts) == 1
    assert inventory.conflicts[0].subject == "metric"
    assert {c.metric_value for c in inventory.conflicts[0].claims} == {"30%", "50%"}
    # Conflicting claims are kept in the flat list too, not silently dropped.
    assert len(inventory.claims) == 2


def test_unrelated_claims_stay_separate():
    resume = [Claim(claim_id="r1", source="resume", subject="skill", text="Proficient in Go", tech=["Go"])]
    portfolio = [Claim(claim_id="p1", source="portfolio", subject="project", text="Built a mobile app", tech=["Swift"])]

    inventory = merge_claims(resume, portfolio)

    assert len(inventory.claims) == 2
    assert inventory.conflicts == []
