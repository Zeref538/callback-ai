"""FR-16: full text session in the terminal."""
import argparse
from pathlib import Path

from callback_ai.config import settings
from callback_ai.ingest.claim_merger import merge_claims
from callback_ai.ingest.job_post_parser import parse_job_post
from callback_ai.ingest.portfolio_parser import parse_portfolio_link
from callback_ai.ingest.resume_parser import parse_resume
from callback_ai.interview.persona import get_persona
from callback_ai.interview.session_engine import InterviewSession
from callback_ai.llm.router import build_chat
from callback_ai.memory.session_store import SessionLogger


def _ask(question: str) -> str:
    print(f"\nInterviewer: {question}")
    return input("You: ")


def main() -> None:
    parser = argparse.ArgumentParser(description="callback-ai: adaptive interview simulator")
    parser.add_argument("--job-post", required=True, type=Path, help="path to a job posting text file")
    parser.add_argument("--resume", type=Path, help="path to a resume text file")
    parser.add_argument("--portfolio-link", help="URL to a portfolio page")
    parser.add_argument("--persona", default="neutral", choices=["friendly", "neutral", "adversarial"])
    parser.add_argument("--budget", type=int, default=settings.question_budget)
    args = parser.parse_args()

    chat = build_chat()
    rubric = parse_job_post(args.job_post.read_text(encoding="utf-8"), chat)

    resume_claims = parse_resume(args.resume.read_text(encoding="utf-8"), chat) if args.resume else []
    portfolio_claims = parse_portfolio_link(args.portfolio_link, chat) if args.portfolio_link else []
    inventory = merge_claims(resume_claims, portfolio_claims)

    if inventory.conflicts:
        print(f"Note: {len(inventory.conflicts)} conflicting claim(s) found between your sources.")

    logger = SessionLogger()
    session = InterviewSession(
        rubric=rubric,
        claims=inventory.claims,
        persona=get_persona(args.persona),
        chat=chat,
        logger=logger,
        budget=args.budget,
    )

    print(f"Starting a {args.budget}-question session ({args.persona} interviewer). Session id: {logger.session_id}")
    session.run(ask_fn=_ask)
    print(f"\nSession complete. Log: {logger.path}")


if __name__ == "__main__":
    main()
