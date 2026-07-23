from callback_ai.grading.model_answer import generate_model_answer
from callback_ai.ingest.schemas import Claim
from conftest import FakeChat


def test_generate_model_answer_passes_claims_into_prompt():
    chat = FakeChat(["A stronger answer using your Redis cache work."])
    claims = [Claim(claim_id="r1", source="resume", subject="project", text="Built a Redis cache", tech=["Redis"])]

    result = generate_model_answer("System Design", "I made it fast.", claims, chat)

    assert result == "A stronger answer using your Redis cache work."
    sent_prompt = chat.calls[0][0]["content"]
    assert "Built a Redis cache" in sent_prompt
