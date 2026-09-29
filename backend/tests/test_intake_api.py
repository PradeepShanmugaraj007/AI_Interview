import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app import main
from app.interview.repository import InterviewRepository


class IntakeApiTests(unittest.TestCase):
    def test_upload_creates_a_candidate_without_returning_resume_or_full_phone(self):
        with tempfile.TemporaryDirectory() as tmp:
            main.repository = InterviewRepository(Path(tmp))
            client = TestClient(main.app)
            response = client.post(
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
        client = TestClient(main.app)
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_intake_ui_html(self):
        client = TestClient(main.app)
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Candidate interview", response.text)
        self.assertIn("form id=\"candidate-form\"", response.text)

    def test_list_candidates(self):
        client = TestClient(main.app)
        response = client.get("/candidates")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)


if __name__ == "__main__":
    unittest.main()
