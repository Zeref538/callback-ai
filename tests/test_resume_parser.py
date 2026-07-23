import json

from callback_ai.ingest.resume_parser import parse_resume
from conftest import FakeChat

RESPONSE = json.dumps({
    "claims": [
        {"claim_id": "r1", "subject": "project", "text": "Built a caching layer", "tech": ["Redis"], "metric_value": None},
        {"claim_id": "r2", "subject": "metric", "text": "reduced latency 30%", "tech": [], "metric_value": "30%"},
    ]
})


def test_parse_resume_tags_source_as_resume():
    chat = FakeChat([RESPONSE])
    claims = parse_resume("Some resume text", chat)

    assert len(claims) == 2
    assert all(c.source == "resume" for c in claims)
    assert claims[1].metric_value == "30%"
