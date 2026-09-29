"""ElevenLabs streaming synthesis, output as mu-law 8kHz for Twilio.

Streams so the first audio frame leaves before the last one is generated —
on a phone line, waiting for a complete utterance adds a second of dead air.
Synthesis is cancellable mid-utterance, which is what makes barge-in work.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

import httpx

from ..config import settings

log = logging.getLogger(__name__)

URL = (
    "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    "?output_format=ulaw_8000"
)


async def synthesize(text: str, client: httpx.AsyncClient) -> AsyncIterator[bytes]:
    """Yield mu-law 8kHz chunks ready to hand straight to Twilio.

    Cancelling the consuming task closes the response and stops generation —
    that is the barge-in path, so nothing here should swallow CancelledError.
    """
    payload = {
        "text": text,
        "model_id": "eleven_flash_v2_5",  # lowest-latency model; quality is fine on 8kHz telephony
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.75},
    }
    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "accept": "audio/basic",
    }

    url = URL.format(voice_id=settings.elevenlabs_voice_id)
    async with client.stream("POST", url, json=payload, headers=headers) as resp:
        if resp.status_code != 200:
            body = await resp.aread()
            log.error("elevenlabs %s: %s", resp.status_code, body[:200])
            return
        async for chunk in resp.aiter_bytes(chunk_size=320):  # ~40ms of mu-law
            yield chunk
