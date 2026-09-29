import unittest
from datetime import datetime, timezone

from app.compliance.tcpa import ComplianceGate


class ComplianceGateTests(unittest.TestCase):
    def test_requires_contact_consent_and_respects_candidate_timezone(self):
        gate = ComplianceGate()
        mid_morning_india = datetime(2026, 1, 1, 5, 0, tzinfo=timezone.utc)

        self.assertFalse(
            gate.may_call(
                "+919876543210",
                contact_consent=False,
                timezone="Asia/Kolkata",
                now=mid_morning_india,
            ).allowed
        )
        self.assertTrue(
            gate.may_call(
                "+919876543210",
                contact_consent=True,
                timezone="Asia/Kolkata",
                now=mid_morning_india,
            ).allowed
        )


if __name__ == "__main__":
    unittest.main()
