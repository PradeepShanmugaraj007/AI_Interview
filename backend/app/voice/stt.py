"""Deepgram streaming transcription over Twilio's mu-law 8kHz media stream.

Emits two kinds of events. Interim results drive barge-in (we need to know the
candidate started talking within ~300ms, long before we know what they said).
Final results drive the turn engine.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator, Callable

import websockets

from ..config import settings

log = logging.getLogger(__name__)

DEEPGRAM_URL = (
    "wss://api.deepgram.com/v1/listen"
    "?encoding=mulaw&sample_rate=8000&channels=1"
    "&model=nova-2-phonecall"
    "&interim_results=true&endpointing=300&punctuate=true"
    # smart_format keeps numbers and emails readable, which matters because we
    # extract email addresses and headcounts straight out of the transcript.
    "&smart_format=true"
)


class Transcriber:
    """Wraps one Deepgram socket for the life of one call."""

    def __init__(self, on_speech_started: Callable[[], None] | None = None) -> None:
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._finals: asyncio.Queue[str] = asyncio.Queue()
        self._on_speech_started = on_speech_started
        self._speaking = False

    async def __aenter__(self) -> "Transcriber":
        self._ws = await websockets.connect(
            DEEPGRAM_URL,
            additional_headers={"Authorization": f"Token {settings.deepgram_api_key}"},
        )
        self._reader = asyncio.create_task(self._read())
        return self

    async def __aexit__(self, *exc) -> None:
        self._reader.cancel()
        if self._ws:
            await self._ws.close()

    async def feed(self, audio: bytes) -> None:
        """Push one Twilio media frame (20ms of mu-law) into the recognizer."""
        if self._ws:
            await self._ws.send(audio)

    async def finals(self) -> AsyncIterator[str]:
        while True:
            yield await self._finals.get()

    async def _read(self) -> None:
        assert self._ws
        try:
            async for raw in self._ws:
                msg = json.loads(raw)
                if msg.get("type") != "Results":
                    continue

                alt = msg["channel"]["alternatives"][0]
                text = alt.get("transcript", "").strip()
                if not text:
                    continue

                # Interim with content == candidate is talking. This is the
                # barge-in trigger; it fires well before is_final.
                if not self._speaking:
                    self._speaking = True
                    if self._on_speech_started:
                        self._on_speech_started()

                if msg.get("is_final") and msg.get("speech_final"):
                    self._speaking = False
                    await self._finals.put(text)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - never kill the call on STT error
            log.error("deepgram reader died: %s", exc)
