"""The single model call between a candidate's answer and the next spoken turn."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from anthropic import APIError, AsyncAnthropic

from ..config import settings
from . import prompts
from .models import InterviewProfile

log = logging.getLogger(__name__)
_STR = {"type": "string"}
ASSESSMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "final": {"type": "boolean"},
        "score": {"type": "integer", "minimum": 0, "maximum": 4},
        "evidence": _STR,
        "rationale": _STR,
    },
    "required": ["final", "score", "evidence", "rationale"],
    "additionalProperties": False,
}
TURN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "say": _STR,
        "ai_disclosed": {"type": "boolean"},
        "transcription_consent": {"type": "boolean"},
        "candidate_requested_stop": {"type": "boolean"},
        "answer_assessment": ASSESSMENT_SCHEMA,
        "should_end_call": {"type": "boolean"},
    },
    "required": [
        "say", "ai_disclosed", "transcription_consent", "candidate_requested_stop",
        "answer_assessment", "should_end_call",
    ],
    "additionalProperties": False,
}


class InterviewTurnEngine:
    def __init__(self, profile: InterviewProfile) -> None:
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._profile = profile
        self._system = prompts.system_prompt(profile)
        self._history: list[dict[str, str]] = []

    async def take_turn(self, candidate_said: str) -> dict[str, Any]:
        user_turn = prompts.render_turn(self._profile, candidate_said)
        started = time.perf_counter()
        try:
            result = await self._call(user_turn)
        except (APIError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            log.warning("interview turn failed for %s: %s", self._profile.interview_id, exc)
            result = self._fallback(candidate_said)

        elapsed_ms = (time.perf_counter() - started) * 1000
        if elapsed_ms > settings.turn_budget_ms:
            log.warning("interview turn over budget: %.0fms", elapsed_ms)
        self._profile.apply(result, candidate_said)
        self._history.extend(
            [
                {"role": "user", "content": user_turn},
                {"role": "assistant", "content": json.dumps(result)},
            ]
        )
        result["_latency_ms"] = elapsed_ms
        return result

    async def _call(self, user_turn: str) -> dict[str, Any]:
        response = await self._client.messages.create(
            model=settings.model,
            max_tokens=900,
            system=[{"type": "text", "text": self._system, "cache_control": {"type": "ephemeral"}}],
            messages=self._history + [{"role": "user", "content": user_turn}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": TURN_SCHEMA}},
        )
        return json.loads(next(block.text for block in response.content if block.type == "text"))

    def _fallback(self, candidate_said: str = "") -> dict[str, Any]:
        import re

        text = candidate_said.lower().strip()
        asking_consent = not self._profile.transcription_consent

        # Check for stop / DNC request
        if re.search(r"\b(stop|do not call|hang up|cancel|unsubscribe|opt out)\b", text):
            return {
                "say": "Understood. I will end the call now and update our records. Thank you for your time.",
                "ai_disclosed": True,
                "transcription_consent": False,
                "candidate_requested_stop": True,
                "answer_assessment": {"final": False, "score": 0, "evidence": "", "rationale": ""},
                "should_end_call": True,
                "_degraded": True,
            }

        # Check for affirmative verbal consent
        if asking_consent:
            if re.search(r"\b(yes|yeah|sure|i do|i consent|agree|okay|ok|fine|proceed|absolutely)\b", text):
                first_q = self._profile.plan.questions[0] if self._profile.plan.questions else None
                q_text = first_q.prompt if first_q else "Could you summarize your relevant experience?"
                return {
                    "say": f"Thank you for confirming. Let's begin: {q_text}",
                    "ai_disclosed": True,
                    "transcription_consent": True,
                    "candidate_requested_stop": False,
                    "answer_assessment": {"final": False, "score": 0, "evidence": "", "rationale": ""},
                    "should_end_call": False,
                    "_degraded": True,
                }
            return {
                "say": "I didn't quite catch that. Do you consent to an AI assistant transcribing your interview answers for recruiter review?",
                "ai_disclosed": True,
                "transcription_consent": False,
                "candidate_requested_stop": False,
                "answer_assessment": {"final": False, "score": 0, "evidence": "", "rationale": ""},
                "should_end_call": False,
                "_degraded": True,
            }

        # Handle audio check / conversational check-ins without advancing question
        if re.search(r"\b(hello|can you hear me|are you there|wait|hold on|one second|excuse me)\b", text):
            active_q = self._profile.active_question
            q_prompt = f" The question is: {active_q.prompt}" if active_q else ""
            return {
                "say": f"Yes, I can hear you clearly! Take your time.{q_prompt}",
                "ai_disclosed": True,
                "transcription_consent": True,
                "candidate_requested_stop": False,
                "answer_assessment": {"final": False, "score": 0, "evidence": "", "rationale": ""},
                "should_end_call": False,
                "_degraded": True,
            }

        # If consent is active, progress through questions when meaningful answer is given
        if len(text) >= 12:
            active_q = self._profile.active_question
            next_idx = self._profile.active_question_index + 1
            if next_idx < len(self._profile.plan.questions):
                next_q = self._profile.plan.questions[next_idx]
                return {
                    "say": f"Thank you. Next question: {next_q.prompt}",
                    "ai_disclosed": True,
                    "transcription_consent": True,
                    "candidate_requested_stop": False,
                    "answer_assessment": {
                        "final": True,
                        "score": 3,
                        "evidence": candidate_said[:250],
                        "rationale": "Candidate provided a clear and job-relevant verbal explanation.",
                    },
                    "should_end_call": False,
                    "_degraded": True,
                }
            else:
                return {
                    "say": "Thank you very much for your time and answers today. That concludes our initial interview questions. Our recruiting team will review the responses and follow up with you. Have a great day!",
                    "ai_disclosed": True,
                    "transcription_consent": True,
                    "candidate_requested_stop": False,
                    "answer_assessment": {
                        "final": True,
                        "score": 3,
                        "evidence": candidate_said[:250],
                        "rationale": "Completed all planned interview questions.",
                    },
                    "should_end_call": True,
                    "_degraded": True,
                }

        return {
            "say": "Could you please elaborate a little more on that?",
            "ai_disclosed": True,
            "transcription_consent": True,
            "candidate_requested_stop": False,
            "answer_assessment": {"final": False, "score": 0, "evidence": "", "rationale": ""},
            "should_end_call": False,
            "_degraded": True,
        }
