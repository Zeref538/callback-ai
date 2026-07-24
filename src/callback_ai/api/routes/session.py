"""FastAPI routes wrapping session_engine for the web UI.

ponytail: sessions live in a process-local dict, not a database -- fine for a
single-user portfolio demo; swap for real storage if this ever needs multiple
concurrent users or to survive a server restart.
"""
from fastapi import APIRouter, HTTPException

from callback_ai.api.schemas import AnswerRequest, AnswerResponse, StartSessionRequest, StartSessionResponse
from callback_ai.grading.report_generator import generate_report
from callback_ai.ingest.claim_merger import merge_claims
from callback_ai.ingest.job_post_parser import parse_job_post
from callback_ai.ingest.portfolio_parser import parse_portfolio_link
from callback_ai.ingest.resume_parser import parse_resume
from callback_ai.interview.persona import get_persona
from callback_ai.interview.session_engine import InterviewSession
from callback_ai.llm.router import build_chat
from callback_ai.memory.delta import compute_delta
from callback_ai.memory.profile_store import load_profile, update_profile
from callback_ai.memory.session_store import SessionLogger

router = APIRouter()

SESSIONS: dict[str, InterviewSession] = {}


@router.post("/sessions", response_model=StartSessionResponse)
def start_session(req: StartSessionRequest) -> StartSessionResponse:
    chat = build_chat()
    rubric = parse_job_post(req.job_post, chat)

    resume_claims = parse_resume(req.resume, chat) if req.resume else []
    portfolio_claims = parse_portfolio_link(req.portfolio_link, chat) if req.portfolio_link else []
    inventory = merge_claims(resume_claims, portfolio_claims)

    logger = SessionLogger()
    session = InterviewSession(
        rubric=rubric,
        claims=inventory.claims,
        persona=get_persona(req.persona),
        chat=chat,
        logger=logger,
        budget=req.budget,
    )
    SESSIONS[logger.session_id] = session

    question = session.next_question()
    return StartSessionResponse(
        session_id=logger.session_id,
        question=question,
        competency=session._current_competency,
        competencies=[c.name for c in rubric.competencies],
        budget=req.budget,
        conflicts=len(inventory.conflicts),
    )


@router.post("/sessions/{session_id}/answer", response_model=AnswerResponse)
def submit_answer(session_id: str, req: AnswerRequest) -> AnswerResponse:
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="unknown session")

    result = session.submit_answer(req.answer)
    # next_question() also flips session.done and logs session_end once the budget is spent.
    next_question = session.next_question()

    return AnswerResponse(
        feedback=result["feedback_line"],
        coverage_score=result["coverage_score"],
        low_confidence=result["low_confidence"],
        done=result["done"],
        next_question=next_question,
        next_competency=session._current_competency if not result["done"] else None,
        turn=session.turn,
    )


@router.get("/sessions/{session_id}/report")
def get_report(session_id: str) -> dict:
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="unknown session")
    if not session.done:
        raise HTTPException(status_code=409, detail="session not finished yet")

    report = generate_report(session.rubric, session.logger.events, session.claims, session.chat, session.gate)

    session_scores = {r.competency: r.score for r in report.competency_reports}
    profile_before = load_profile()
    delta = compute_delta(profile_before, session_scores)
    update_profile(session_scores, session_id)

    return {"report": report.model_dump(), "delta": delta}
