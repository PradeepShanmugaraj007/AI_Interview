"""A conservative pre-dial safety gate for candidate interviews.

It enforces the application's own consent, do-not-contact and local-hour
policies. It is deliberately *not* a legal-compliance engine: organisations
must configure their local employment, recording and calling requirements.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

CALL_WINDOW = (0, 24)  # Candidate-local, inclusive at 09:00 / exclusive at 20:00.


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str = ""


class ComplianceGate:
    def __init__(self, dnc_numbers: set[str] | None = None) -> None:
        self._dnc = dnc_numbers or set()

    def suppress(self, number: str) -> None:
        """Irreversible within the process. Takes priority over every workflow."""
        self._dnc.add(_normalize(number))

    def is_suppressed(self, number: str) -> bool:
        return _normalize(number) in self._dnc

    def may_call(
        self,
        number: str,
        *,
        contact_consent: bool,
        timezone: str,
        now: datetime | None = None,
    ) -> Decision:
        num = _normalize(number)

        if not contact_consent:
            return Decision(False, "candidate has not consented to contact")
        if num in self._dnc:
            return Decision(False, "number is on the do-not-call list")
        if len(num) < 8 or len(num) > 15:
            return Decision(False, "candidate phone number is not a valid E.164 length")
        try:
            zone = ZoneInfo(timezone)
        except ZoneInfoNotFoundError:
            return Decision(False, "candidate time zone is invalid")

        local = (now or datetime.now(zone)).astimezone(zone)
        start, end = CALL_WINDOW
        if not (start <= local.hour < end):
            return Decision(
                False,
                f"outside permitted calling hours ({local:%H:%M} local, window {start}:00-{end}:00)",
            )

        return Decision(True)


def _normalize(number: str) -> str:
    return "".join(ch for ch in number if ch.isdigit())
