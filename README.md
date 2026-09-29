# AI Candidate Voice Interviewer

An automated, consent-first first-round voice interview system that ingests candidate résumés, plans grounded interview questions, dials the candidate via standard telephony, and generates an evidence-backed recruiter scorecard.

---

## Architecture Overview

```
+-----------------------------------------------------------------------------------+
|  [ Recruiter Web Intake UI ]                                                      |
|        │ Upload Résumé + E.164 Phone Number                                       |
|        ▼                                                                          |
|  [ FastAPI Backend ] ──► [ Résumé Extraction & PII Redaction ]                    |
|        │                               │                                          |
|        │                               ▼                                          |
|        ▼                        [ Claude LLM / Fallback ] ──► [ Question Plan ]   |
|  [ Twilio Outbound Call ]                                  │                      |
|        │                                                   │                      |
|        ▼ (WebSocket wss://.../media)                       ▼                      |
|  [ Voice Engine ] ◄─────────────────────────────── [ Question Rubric ]            |
|    ├── STT: Deepgram (Nova-2 8kHz mulaw)                                          |
|    ├── Turn Engine: Conversational State Machine                                  |
|    └── TTS: ElevenLabs (Streaming 8kHz mulaw)                                     |
|        │                                                                          |
|        ▼                                                                          |
|  [ PostgreSQL Database ] ──► [ Weighted Score 0-100% + Evidence Quotes ]          |
+-----------------------------------------------------------------------------------+
```

---

## Tech Stack

- **Backend**: FastAPI, Python 3.11, Uvicorn, WebSockets
- **Database**: PostgreSQL (with psycopg 3) & SQLite fallback
- **Telephony**: Twilio Voice Media Streams (8kHz G.711 mu-law)
- **Speech-to-Text (STT)**: Deepgram streaming API (`nova-2-phonecall`)
- **Text-to-Speech (TTS)**: ElevenLabs low-latency streaming API (`eleven_flash_v2_5`)
- **Intelligence**: Anthropic Claude & deterministic achievement-extraction fallback
- **Frontend**: Clean Vanilla HTML5/CSS3/JavaScript (no external dependencies)

---

## Quick Start

### 1. Prerequisites
- Python 3.10+
- PostgreSQL database
- Twilio, Deepgram & ElevenLabs API keys
- `ngrok` (for local development telephony webhook)

### 2. Setup & Installation

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment Configuration

```bash
cp .env.example .env
```
Open `.env` and fill in your API credentials, PostgreSQL connection, and ngrok public domain.

### 4. Running the Application

**Terminal 1 (Backend Server):**
```bash
cd backend
source .venv/bin/activate
uvicorn --env-file .env app.main:app --reload --port 8000
```

**Terminal 2 (Ngrok Tunnel):**
```bash
ngrok http 8000 --url=your-subdomain.ngrok-free.dev
```

Open `http://localhost:8000/` in your browser.

---

## Running Automated Tests

Run the test suite covering compliance, résumé parsing, domain models, PostgreSQL round-trips, and turn engine dialogues:

```bash
cd backend
python -m unittest discover -s tests -v
```

---

## Detailed Architecture Guide

For deep technical specifications on the streaming audio pipeline, barge-in logic, and scoring models, see [ARCHITECTURE.md](ARCHITECTURE.md).
