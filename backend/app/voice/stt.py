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
    "&interim_results=true&endpointing=1500&utterance_end_ms=1500&punctuate=true"
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
        self._utterance_buffer: list[str] = []

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

    async def _emit_utterance(self) -> None:
        """Combine all accumulated is_final sentences into one complete answer."""
        if not self._utterance_buffer:
            return
        full_text = " ".join(self._utterance_buffer).strip()
        self._utterance_buffer.clear()
        if full_text:
            log.info("STT completed full candidate utterance: %s", full_text)
            await self._finals.put(full_text)

    async def _read(self) -> None:
        assert self._ws
        try:
            async for raw in self._ws:
                msg = json.loads(raw)
                msg_type = msg.get("type")

                # Handle UtteranceEnd event from Deepgram VAD
                if msg_type == "UtteranceEnd":
                    self._speaking = False
                    await self._emit_utterance()
                    continue

                if msg_type != "Results":
                    continue

                alt = msg["channel"]["alternatives"][0]
                text = alt.get("transcript", "").strip()

                is_final = msg.get("is_final", False)
                speech_final = msg.get("speech_final", False)

                # Interim with content == candidate is talking. Barge-in trigger.
                if text and not self._speaking:
                    self._speaking = True
                    if self._on_speech_started:
                        self._on_speech_started()

                if is_final and text:
                    # Accumulate all finalized chunks into the utterance buffer
                    if not self._utterance_buffer or self._utterance_buffer[-1] != text:
                        self._utterance_buffer.append(text)

                if speech_final:
                    self._speaking = False
                    await self._emit_utterance()

        except asyncio.CancelledError:
            await self._emit_utterance()
            raise
        except Exception as exc:  # noqa: BLE001 - never kill the call on STT error
            log.error("deepgram reader died: %s", exc)
