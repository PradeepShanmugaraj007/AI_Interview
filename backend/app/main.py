"""Candidate intake, voice interview, and human-review scorecard API."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
from twilio.rest import Client as TwilioClient

from .compliance.tcpa import ComplianceGate
from .config import settings
from .interview.planner import InterviewPlanner
from .interview.repository import InterviewRepository
from .interview.resume import ResumeError, extract_resume_text
from .voice.session import CallSession

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(title="AI Candidate Interviewer")
repository = InterviewRepository(settings.data_dir, settings.database_url)
gate = ComplianceGate()
planner = InterviewPlanner()
MAX_RESUME_BYTES = 5 * 1024 * 1024
ALLOWED_RESUME_SUFFIXES = {".pdf", ".docx", ".txt"}


@app.get("/", response_class=HTMLResponse)
async def intake_page() -> HTMLResponse:
    return HTMLResponse((Path(__file__).parent / "web" / "index.html").read_text(encoding="utf-8"))


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "missing_env": settings.missing_for_call(), "model": settings.model}


@app.post("/candidates", status_code=201)
async def create_candidate(
    full_name: str = Form(...),
    phone: str = Form(...),
    job_title: str = Form(...),
    timezone: str = Form("Asia/Kolkata"),
    email: str = Form(""),
    role_rubric: str = Form(""),
    contact_consent: bool = Form(...),
    resume: UploadFile = File(...),
) -> JSONResponse:
    """Save a candidate application. A spoken consent check still happens on-call."""
    full_name = _bounded(full_name, "full name", 120)
    job_title = _bounded(job_title, "job title", 160)
    timezone = _bounded(timezone, "time zone", 80)
    phone = _normalise_phone(phone)
    if not contact_consent:
        raise HTTPException(422, "Candidate contact consent is required before an automated call.")
    if not resume.filename or Path(resume.filename).suffix.lower() not in ALLOWED_RESUME_SUFFIXES:
        raise HTTPException(422, "Upload a PDF, DOCX, or TXT résumé.")

    contents = await resume.read(MAX_RESUME_BYTES + 1)
    if len(contents) > MAX_RESUME_BYTES:
        raise HTTPException(413, "The résumé exceeds the 5 MB upload limit.")
    try:
        resume_text = extract_resume_text(contents, resume.filename)
    except ResumeError as exc:
        raise HTTPException(422, str(exc)) from exc

    candidate = repository.create_candidate(
        full_name=full_name,
        phone=phone,
        email=email.strip()[:254],
        job_title=job_title,
        role_rubric=role_rubric.strip()[:6_000],
        timezone=timezone,
        contact_consent=contact_consent,
        resume_filename=resume.filename,
        resume_contents=contents,
        resume_text=resume_text,
    )
    return JSONResponse(_candidate_view(candidate), status_code=201)


@app.get("/candidates")
async def list_candidates() -> list[dict]:
    return [_candidate_view(candidate) for candidate in repository.list_candidates()]


@app.post("/candidates/{candidate_id}/interviews", status_code=201)
async def start_interview(candidate_id: str) -> JSONResponse:
    """Prepare tailored questions, then place an outbound interview call."""
    candidate = repository.get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(404, "Candidate not found")

    decision = gate.may_call(
        candidate["phone"],
        contact_consent=candidate["contact_consent"],
        timezone=candidate["timezone"],
    )
    if not decision.allowed:
        raise HTTPException(409, decision.reason)
    missing = settings.missing_for_call()
    if missing:
        raise HTTPException(503, {"message": "Call provider is not configured", "missing_env": missing})

    plan = await planner.create(
        job_title=candidate["job_title"],
        role_rubric=candidate["role_rubric"],
        resume_text=candidate["resume_text"],
    )
    interview = repository.create_interview(candidate_id, plan)
    try:
        call = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token).calls.create(
            to=candidate["phone"],
            from_=settings.twilio_from_number,
            twiml=(
                "<Response><Connect><Stream "
                f'url="wss://{settings.public_host}/media">'
                f'<Parameter name="interview_id" value="{interview["id"]}" />'
                "</Stream></Connect></Response>"
            ),
        )
    except Exception as exc:  # Provider errors should not leave the UI pretending a call was placed.
        log.exception("failed to place interview %s", interview["id"])
        raise HTTPException(502, "The call provider could not place the interview call.") from exc

    repository.mark_dialled(interview["id"], call.sid)
    interview = repository.get_interview(interview["id"])
    return JSONResponse(interview, status_code=201)


@app.get("/interviews/{interview_id}")
async def get_interview(interview_id: str) -> dict:
    interview = repository.get_interview(interview_id)
    if not interview:
        raise HTTPException(404, "Interview not found")
    return interview


@app.websocket("/media")
async def media(ws: WebSocket) -> None:
    profile = await CallSession(ws, repository).run()
    if not profile:
        return
    repository.complete_interview(profile.interview_id, profile.to_dict())
    if profile.candidate_requested_stop:
        candidate = repository.get_candidate(profile.candidate_id)
        if candidate:
            gate.suppress(candidate["phone"])
    log.info(
        "interview %s ended: answers=%d score=%s recommendation=%s",
        profile.interview_id,
        len(profile.answers),
        profile.overall_score(),
        profile.recommendation(),
    )


def _normalise_phone(value: str) -> str:
    compact = re.sub(r"[\s().-]", "", value.strip())
    if not re.fullmatch(r"\+\d{8,15}", compact):
        raise HTTPException(422, "Use an E.164 phone number, for example +919876543210.")
    return compact


def _bounded(value: str, label: str, limit: int) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise HTTPException(422, f"{label.capitalize()} is required.")
    if len(cleaned) > limit:
        raise HTTPException(422, f"{label.capitalize()} must be at most {limit} characters.")
    return cleaned


def _candidate_view(candidate: dict) -> dict:
    """Never expose résumé text or a full phone number through the intake UI."""
    return {
        "id": candidate["id"],
        "full_name": candidate["full_name"],
        "phone_last_four": candidate["phone"][-4:],
        "job_title": candidate["job_title"],
        "timezone": candidate["timezone"],
        "contact_consent": candidate["contact_consent"],
        "created_at": candidate["created_at"],
    }
