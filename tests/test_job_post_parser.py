import json

from callback_ai.ingest import job_post_parser
from callback_ai.ingest.rubric_cache import hash_job_post
from conftest import FakeChat

RESPONSE = json.dumps({
    "target_position": "Backend Engineer",
    "competencies": [
        {"name": "System Design", "weight": 0.4, "seniority_bar": "mid", "description": "Designs scalable systems"},
        {"name": "Communication", "weight": 0.6, "seniority_bar": "mid", "description": "Explains tradeoffs clearly"},
    ],
})


def test_parse_job_post_returns_rubric(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    chat = FakeChat([RESPONSE])

    rubric = job_post_parser.parse_job_post("We need a backend engineer...", chat)

    assert rubric.target_position == "Backend Engineer"
    assert len(rubric.competencies) == 2
    assert rubric.job_post_hash == hash_job_post("We need a backend engineer...")


def test_same_job_post_hits_cache_no_second_llm_call(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    chat = FakeChat([RESPONSE])
    text = "We need a backend engineer..."

    job_post_parser.parse_job_post(text, chat)
    job_post_parser.parse_job_post(text, chat)  # should hit cache, not consume a second response

    assert len(chat.calls) == 1


def test_different_job_post_produces_different_hash(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    chat = FakeChat([RESPONSE, RESPONSE])

    r1 = job_post_parser.parse_job_post("Job post A", chat)
    r2 = job_post_parser.parse_job_post("Job post B", chat)

    assert r1.job_post_hash != r2.job_post_hash
