# AI Candidate Interviewer

This application turns the supplied voice-sales prototype into a consent-first,
résumé-led first-round interview service. A recruiter uploads a candidate's
résumé and E.164 mobile number, chooses a role, then starts an outbound AI
voice interview. The caller asks a small question plan grounded in the résumé,
transcribes answers only after spoken consent, and creates a reviewable
per-question scorecard.

The scorecard is a recruiter aid, not an automatic employment decision.

## What is implemented

- Browser intake at `/` for résumé upload, contact consent, phone number, role,
  requirements/rubric, and candidate time zone.
- PDF, DOCX and TXT résumé extraction. Obvious contact and sensitive fields are
  removed before résumé text is sent to the question planner.
- A four-to-six-question plan generated from résumé evidence plus the job
  rubric. If no model key is configured, a deterministic local plan supports
  demos and tests.
- An explicit AI disclosure and spoken consent gate before answer transcription
  or scoring.
- Twilio media-stream calling, Deepgram transcription, ElevenLabs speech, and
  a single structured model response per candidate turn.
- Weighted 0–4 answer scores with answer evidence and rationale. The output is
  a `recommend_human_shortlist_review`, `more_evidence_needed`, or
  `recommend_human_review_before_rejecting` recommendation—not an auto-reject.
- Local SQLite persistence for the MVP, restrictive local résumé file
  permissions, a candidate-local calling-hours check, and an in-process
  do-not-contact list.

## Run locally

```bash
cd /Users/pradeep/Documents/ChatGPT/interview/backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# populate .env (use a secret manager instead outside local development)
.venv/bin/uvicorn --env-file .env app.main:app --reload --port 8000
```

Open `http://localhost:8000`. Use a public HTTPS/WSS endpoint for `PUBLIC_HOST`
when Twilio needs to reach your machine, for example a tunnel in development.

Required configuration:

- `ANTHROPIC_API_KEY` and optional `ANTHROPIC_MODEL`
- `DEEPGRAM_API_KEY`
- `ELEVENLABS_API_KEY` and optional `ELEVENLABS_VOICE_ID`
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`
- `PUBLIC_HOST`, without a scheme
- `DATA_DIR`, optional local development storage path

## Review a result

`GET /interviews/{interview_id}` returns the planned questions and, after a
completed call, its transcript, per-answer evidence, weighted score, and human
review recommendation. In production, protect this endpoint with recruiter
authentication and role-based access.

## Verify

```bash
cd /Users/pradeep/Documents/ChatGPT/interview/backend
.venv/bin/python -m unittest discover -s tests -v
```

## Before production

This is a working MVP, not a completed hiring-compliance program. Add SSO and
recruiter authorization, encrypted managed storage, audit/retention/deletion
controls, secure secret management, a persistent do-not-contact service,
provider webhook validation, rate limiting, failure monitoring, candidate
accommodations and a jurisdiction-specific review of calling, recording,
privacy, and employment rules. Calibrate scoring against human-reviewed cases
and monitor for disparate impact before using it to help prioritize candidates.
