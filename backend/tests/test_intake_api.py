import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app import main
from app.interview.repository import InterviewRepository


class IntakeApiTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig_repo = main.repository
        main.repository = InterviewRepository(Path(self._tmp.name))
        self.client = TestClient(main.app)

    def tearDown(self):
        main.repository = self._orig_repo
        self._tmp.cleanup()

    def test_upload_creates_a_candidate_without_returning_resume_or_full_phone(self):
        response = self.client.post(
            "/candidates",
            data={
                "full_name": "Priya Example",
                "phone": "+919876543210",
                "job_title": "Backend engineer",
                "timezone": "Asia/Kolkata",
                "role_rubric": "Python and API design",
                "contact_consent": "true",
            },
            files={
                "resume": (
                    "priya.txt",
                    b"Built Python APIs with FastAPI and PostgreSQL, reducing response times by thirty percent. " * 2,
                    "text/plain",
                )
            },
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["phone_last_four"], "3210")
        self.assertNotIn("resume_text", body)
        self.assertNotIn("phone", body)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_intake_ui_html(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue("Interviewer CRM" in response.text or "Candidate interview" in response.text)

        legacy = self.client.get("/legacy")
        self.assertEqual(legacy.status_code, 200)
        self.assertIn("Candidate interview", legacy.text)
        self.assertIn('form id="candidate-form"', legacy.text)

    def test_list_candidates(self):
        response = self.client.get("/candidates")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_crm_endpoints(self):
        # Check initial CRM stats
        stats_resp = self.client.get("/api/crm/stats")
        self.assertEqual(stats_resp.status_code, 200)
        stats = stats_resp.json()
        self.assertEqual(stats["total_candidates"], 0)
        self.assertEqual(stats["completed_interviews"], 0)

        # Upload a candidate via CRM endpoint
        create_resp = self.client.post(
            "/api/crm/candidates",
            data={
                "full_name": "Karthik Dev",
                "phone": "+919876543211",
                "job_title": "Full Stack Dev",
                "timezone": "Asia/Kolkata",
                "role_rubric": "React and Node.js",
                "contact_consent": "true",
            },
            files={
                "resume": (
                    "karthik.txt",
                    b"Developed full-stack web applications with modern React and asynchronous APIs. " * 3,
                    "text/plain",
                )
            },
        )
        self.assertEqual(create_resp.status_code, 201)
        cid = create_resp.json()["id"]

        # Check CRM candidates list
        crm_candidates_resp = self.client.get("/api/crm/candidates")
        self.assertEqual(crm_candidates_resp.status_code, 200)
        candidates = crm_candidates_resp.json()
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["full_name"], "Karthik Dev")

        # Check CRM candidate detail
        detail_resp = self.client.get(f"/api/crm/candidates/{cid}")
        self.assertEqual(detail_resp.status_code, 200)
        detail = detail_resp.json()
        self.assertEqual(detail["candidate"]["full_name"], "Karthik Dev")
        self.assertIsInstance(detail["interviews"], list)


if __name__ == "__main__":
    unittest.main()
