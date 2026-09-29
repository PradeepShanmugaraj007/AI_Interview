import tempfile
import unittest
from pathlib import Path

from app.interview.models import InterviewPlan, Question
from app.interview.repository import InterviewRepository


class RepositoryTests(unittest.TestCase):
    def test_candidate_and_interview_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            repository = InterviewRepository(Path(tmp))
            candidate = repository.create_candidate(
                full_name="Priya Example",
                phone="+919876543210",
                email="",
                job_title="Backend engineer",
                role_rubric="Python and APIs",
                timezone="Asia/Kolkata",
                contact_consent=True,
                resume_filename="priya.txt",
                resume_contents=b"Built an API service with Python and FastAPI. " * 3,
                resume_text="Built an API service with Python and FastAPI. " * 3,
            )
            plan = InterviewPlan(
                "Backend engineer",
                (Question("api", "How did you design the API?", "API design", "Role evidence"),) * 4,
                "Job evidence only.",
            )
            interview = repository.create_interview(candidate["id"], plan)
            context = repository.interview_context(interview["id"])

            self.assertIsNotNone(context)
            saved_candidate, saved_plan = context
            self.assertEqual(saved_candidate["phone"], "+919876543210")
            self.assertEqual(saved_plan.job_title, "Backend engineer")

    def test_postgres_candidate_and_interview_round_trip(self):
        from app.config import settings
        if not settings.database_url.startswith("postgres"):
            return
        with tempfile.TemporaryDirectory() as tmp:
            try:
                repository = InterviewRepository(Path(tmp), database_url=settings.database_url)
            except Exception as e:
                self.skipTest(f"PostgreSQL connection failed: {e}")
                return

            candidate = repository.create_candidate(
                full_name="Postgres Candidate",
                phone="+919876543210",
                email="postgres@example.com",
                job_title="Full Stack Engineer",
                role_rubric="PostgreSQL and Python",
                timezone="Asia/Kolkata",
                contact_consent=True,
                resume_filename="resume.txt",
                resume_contents=b"Full Stack Engineer with PostgreSQL experience. " * 3,
                resume_text="Full Stack Engineer with PostgreSQL experience. " * 3,
            )
            plan = InterviewPlan(
                "Full Stack Engineer",
                (Question("pg", "How do you optimize queries?", "Database performance", "Role evidence"),) * 4,
                "Job evidence only.",
            )
            interview = repository.create_interview(candidate["id"], plan)
            repository.mark_dialled(interview["id"], "CA_test_sid")
            repository.complete_interview(interview["id"], {"overall_score": 85.0})

            fetched_interview = repository.get_interview(interview["id"])
            self.assertIsNotNone(fetched_interview)
            self.assertEqual(fetched_interview["status"], "completed")
            self.assertEqual(fetched_interview["call_sid"], "CA_test_sid")
            self.assertEqual(fetched_interview["result"]["overall_score"], 85.0)

            context = repository.interview_context(interview["id"])
            self.assertIsNotNone(context)
            saved_candidate, saved_plan = context
            self.assertEqual(saved_candidate["email"], "postgres@example.com")
            self.assertEqual(saved_plan.job_title, "Full Stack Engineer")


if __name__ == "__main__":
    unittest.main()
