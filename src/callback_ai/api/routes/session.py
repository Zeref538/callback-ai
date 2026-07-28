"""FastAPI routes wrapping session_engine for the web UI.

ponytail: sessions live in a process-local dict, not a database -- fine for a
single-user portfolio demo; swap for real storage if this ever needs multiple
concurrent users or to survive a server restart.
"""
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from callback_ai.ingest.document import UnsupportedDocument, extract_text

from callback_ai.api.schemas import (
    AnswerRequest,
    AnswerResponse,
    InterviewerInfo,
    StartSessionRequest,
    StartSessionResponse,
)
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

MAX_UPLOAD_BYTES = 5 * 1024 * 1024   # 5 MB -- a resume or job post, not a book
MAX_JOB_POST_CHARS = 20_000          # a posting, not a novel -- caps token cost/abuse
MAX_SESSIONS = 200                   # in-process store; evict oldest so memory can't grow unbounded


def _remember_session(session_id: str, session: InterviewSession) -> None:
    SESSIONS[session_id] = session
    while len(SESSIONS) > MAX_SESSIONS:
        SESSIONS.pop(next(iter(SESSIONS)))  # dict is insertion-ordered -> FIFO eviction


@router.post("/extract")
async def extract_document(file: UploadFile = File(...)) -> dict:
    """Turn an uploaded resume / job-post file (PDF, DOCX, TXT, MD) into text
    the setup form can drop straight into a textarea."""
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is larger than 5 MB.")
    try:
        text = extract_text(file.filename or "", data)
    except UnsupportedDocument as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"text": text, "chars": len(text)}


class TTSRequest(BaseModel):
    text: str
    voice: str = "en-US-AndrewNeural"
    rate: float = 1.0   # 1.0 = normal; mapped to edge-tts's +/-N% form


# Only allow real Microsoft neural voice ids, so this endpoint can't be pointed
# at arbitrary strings. edge-tts hits a public Microsoft endpoint (free, no key).
_VOICE_RE = re.compile(r"^[a-zA-Z]{2}-[a-zA-Z]+-[A-Za-z]+Neural$")


@router.post("/tts")
async def text_to_speech(req: TTSRequest) -> StreamingResponse:
    """Natural neural speech for an interviewer's question. Free, no API key
    (edge-tts / Microsoft public voices). Falls back to browser Web Speech on
    the client if this fails."""
    import edge_tts

    text = req.text.strip()[:1200]  # a question, not an essay
    if not text:
        raise HTTPException(status_code=422, detail="empty text")
    voice = req.voice if _VOICE_RE.match(req.voice) else "en-US-AndrewNeural"
    pct = max(-40, min(40, round((req.rate - 1.0) * 100)))
    rate = f"{'+' if pct >= 0 else ''}{pct}%"

    async def stream():
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]

    return StreamingResponse(stream(), media_type="audio/mpeg")


# How much the chosen seniority shifts a persona's probe threshold: a senior
# candidate gets pressed harder, a junior a little less.
_SENIORITY_DELTA = {"junior": -0.1, "mid": 0.0, "senior": 0.1}


@router.post("/sessions", response_model=StartSessionResponse)
def start_session(req: StartSessionRequest) -> StartSessionResponse:
    job_post = req.job_post.strip()
    if len(job_post) < 20:
        raise HTTPException(status_code=422, detail="Paste a job post (at least a sentence or two) to start.")
    if len(job_post) > MAX_JOB_POST_CHARS:
        raise HTTPException(status_code=422, detail=f"Job post is too long (max {MAX_JOB_POST_CHARS:,} characters).")
    if req.persona not in {"friendly", "neutral", "adversarial"}:
        raise HTTPException(status_code=422, detail="Unknown interviewer.")

    chat = build_chat()

    # Fold seniority into the rubric text (so competencies reflect the level and
    # the cache keys on it) before parsing.
    job_text = job_post
    if req.seniority in _SENIORITY_DELTA and req.seniority != "mid":
        job_text = f"[Target seniority level: {req.seniority}]\n{job_post}"

    # The three ingest parses are independent LLM calls -- run them together so
    # setup latency is one call's worth, not three back to back.
    with ThreadPoolExecutor(max_workers=3) as pool:
        f_rubric = pool.submit(parse_job_post, job_text, chat)
        f_resume = pool.submit(parse_resume, req.resume, chat) if req.resume else None
        f_portfolio = pool.submit(parse_portfolio_link, req.portfolio_link, chat) if req.portfolio_link else None
        rubric = f_rubric.result()
        resume_claims = f_resume.result() if f_resume else []
        portfolio_claims = f_portfolio.result() if f_portfolio else []
    inventory = merge_claims(resume_claims, portfolio_claims)

    persona = get_persona(req.persona)
    delta = _SENIORITY_DELTA.get(req.seniority or "mid", 0.0)
    if delta:
        persona = replace(persona, probe_threshold=max(0.0, min(1.0, persona.probe_threshold + delta)))

    logger = SessionLogger()
    session = InterviewSession(
        rubric=rubric,
        claims=inventory.claims,
        persona=persona,
        chat=chat,
        logger=logger,
        budget=req.budget,
    )
    _remember_session(logger.session_id, session)

    question = session.next_question()
    persona = session.persona
    return StartSessionResponse(
        session_id=logger.session_id,
        question=question,
        competency=session._current_competency,
        competencies=[c.name for c in rubric.competencies],
        budget=req.budget,
        conflicts=len(inventory.conflicts),
        interviewer=InterviewerInfo(
            key=persona.key, name=persona.name, role=persona.role,
            opening=persona.opening, accent=persona.accent, style=persona.style,
            voice_pitch=persona.voice_pitch, voice_rate=persona.voice_rate, voice_hint=persona.voice_hint,
            neural_voice=persona.neural_voice,
        ),
    )


@router.post("/sessions/{session_id}/answer", response_model=AnswerResponse)
def submit_answer(session_id: str, req: AnswerRequest) -> AnswerResponse:
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="unknown session")
    if session.done:
        raise HTTPException(status_code=409, detail="This interview is already finished.")
    if not req.answer.strip():
        raise HTTPException(status_code=422, detail="Answer can't be empty.")

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
