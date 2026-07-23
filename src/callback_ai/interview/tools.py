"""Typed tool registry the agent loop (session_engine.py) dispatches over.

ponytail: these are called as plain Python functions from session_engine's
deterministic loop, not through a provider's function-calling API yet -- the
agentic behavior here is the dynamic branching (probe vs switch, which
competency, whether to call parse_portfolio_link at all), not the wire
protocol. Swap dispatch to real tool-calling (NIM's OpenAI-compatible
tool_choice) if/when the loop needs the model to pick tools itself instead of
probe_policy's deterministic rule.
"""
from callback_ai.ingest.job_post_parser import parse_job_post
from callback_ai.ingest.resume_parser import parse_resume
from callback_ai.ingest.portfolio_parser import parse_portfolio_link
from callback_ai.ingest.claim_merger import merge_claims
from callback_ai.interview.coverage_scorer import score_answer
from callback_ai.interview.probe_policy import decide as decide_next_action
from callback_ai.interview.budget_allocator import allocate_next_competency
from callback_ai.interview.question_bank import generate_question, generate_probe

TOOLS = {
    "parse_job_post": parse_job_post,
    "parse_resume": parse_resume,
    "parse_portfolio_link": parse_portfolio_link,
    "merge_claims": merge_claims,
    "score_answer": score_answer,
    "decide_next_action": decide_next_action,
    "allocate_next_competency": allocate_next_competency,
    "generate_question": generate_question,
    "generate_probe": generate_probe,
    # "update_profile": added in week 3 once memory/profile_store.py exists
}
