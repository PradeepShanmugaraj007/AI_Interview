"""Bridge a Twilio media stream to a consent-first candidate interview."""

from __future__ import annotations

import asyncio
import base64
import json
import logging

import httpx
from fastapi import WebSocket

from ..interview.models import InterviewProfile
from ..interview.repository import InterviewRepository
from ..interview.turn_engine import InterviewTurnEngine
from . import tts
from .stt import Transcriber

log = logging.getLogger(__name__)

OPENING_LINE = (
    "Hello, this is Ava, an AI interview assistant calling about your application. "
    "Before we continue, do you consent to having your interview answers transcribed for recruiter review?"
)


class CallSession:
    def __init__(self, ws: WebSocket, repository: InterviewRepository) -> None:
        self._ws = ws
        self._repository = repository
        self._stream_sid: str | None = None
        self._profile: InterviewProfile | None = None
        self._engine: InterviewTurnEngine | None = None
        self._speaking: asyncio.Task | None = None

    async def run(self) -> InterviewProfile | None:
        await self._ws.accept()
        async with httpx.AsyncClient(timeout=30.0) as http:
            self._http = http
            async with Transcriber(on_speech_started=self._on_barge_in) as stt:
                pump = asyncio.create_task(self._pump_twilio_to_stt(stt))
                consume = asyncio.create_task(self._consume_transcripts(stt))
                _, pending = await asyncio.wait(
                    {pump, consume}, return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
                await asyncio.gather(pump, consume, return_exceptions=True)
        return self._profile

    async def _pump_twilio_to_stt(self, stt: Transcriber) -> None:
        async for raw in self._ws.iter_text():
            msg = json.loads(raw)
            event = msg.get("event")
            if event == "start":
                self._stream_sid = msg["start"]["streamSid"]
                interview_id = (msg["start"].get("customParameters") or {}).get("interview_id")
                context = self._repository.interview_context(str(interview_id or ""))
                if context is None:
                    log.warning("media stream arrived without a valid interview id")
                    await self._ws.close(code=1008)
                    return
                candidate, plan = context
                self._profile = InterviewProfile(
                    call_sid=msg["start"]["callSid"],
                    candidate_id=candidate["id"],
                    interview_id=str(interview_id),
                    plan=plan,
                    ai_disclosed=True,
                )
                self._engine = InterviewTurnEngine(self._profile)
                await self._speak(OPENING_LINE)
            elif event == "media":
                await stt.feed(base64.b64decode(msg["media"]["payload"]))
            elif event == "stop":
                return

    async def _consume_transcripts(self, stt: Transcriber) -> None:
        async for said in stt.finals():
            if self._profile is None or self._engine is None:
                continue
            log.info("candidate response received for interview %s", self._profile.interview_id)
            result = await self._engine.take_turn(said)
            await self._speak(str(result["say"]))
            if result.get("should_end_call") or self._profile.candidate_requested_stop:
                await self._hang_up()
                return

    async def _speak(self, text: str) -> None:
        self._cancel_speech()
        self._speaking = asyncio.create_task(self._stream_speech(text))

    async def _stream_speech(self, text: str) -> None:
        try:
            async for chunk in tts.synthesize(text, self._http):
                await self._ws.send_text(
                    json.dumps(
                        {
                            "event": "media",
                            "streamSid": self._stream_sid,
                            "media": {"payload": base64.b64encode(chunk).decode()},
                        }
                    )
                )
        except asyncio.CancelledError:
            await self._ws.send_text(json.dumps({"event": "clear", "streamSid": self._stream_sid}))
            raise

    def _on_barge_in(self) -> None:
        if self._speaking and not self._speaking.done():
            self._speaking.cancel()

    def _cancel_speech(self) -> None:
        if self._speaking and not self._speaking.done():
            self._speaking.cancel()

    async def _hang_up(self) -> None:
        if self._speaking:
            await asyncio.gather(self._speaking, return_exceptions=True)
        await self._ws.close()
