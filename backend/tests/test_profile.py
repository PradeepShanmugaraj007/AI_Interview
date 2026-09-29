import unittest

from app.interview.models import InterviewPlan, InterviewProfile, Question


PLAN = InterviewPlan(
    job_title="Backend engineer",
    questions=(
        Question("project", "Tell me about the service you built.", "ownership", "Résumé evidence", 1.5),
        Question("reasoning", "How did you verify reliability?", "reasoning", "Validation evidence", 1.0),
    ),
    scoring_guidance="Job evidence only.",
)


def result(*, consent=False, final=False, score=0):
    return {
        "say": "Thank you.",
        "ai_disclosed": True,
        "transcription_consent": consent,
        "candidate_requested_stop": False,
        "answer_assessment": {
            "final": final,
            "score": score,
            "evidence": "Candidate explained a concrete service.",
            "rationale": "Evidence was relevant.",
        },
        "should_end_call": False,
    }


class InterviewProfileTests(unittest.TestCase):
    def test_scores_only_active_server_question_and_recommends_human_review(self):
        profile = InterviewProfile("CA1", "candidate-1", "interview-1", PLAN)

        profile.apply(result(consent=True), "Yes, I consent.")
        self.assertEqual(profile.active_question.question_id, "project")
        self.assertEqual(profile.answers, [])
        self.assertEqual(profile.transcript[0]["speaker"], "candidate")

        profile.apply(result(final=True, score=4), "I owned the service and reduced failures.")
        self.assertEqual(profile.active_question.question_id, "reasoning")
        self.assertEqual(profile.answers[0].question_id, "project")

        profile.apply(result(final=True, score=3), "I used tracing, retries, and load tests.")
        self.assertTrue(profile.finished_questions)
        self.assertEqual(profile.overall_score(), 90.0)
        self.assertEqual(profile.recommendation(), "recommend_human_shortlist_review")

    def test_content_is_not_retained_before_transcription_consent(self):
        profile = InterviewProfile("CA1", "candidate-1", "interview-1", PLAN)
        profile.apply(result(), "No, I do not consent.")
        self.assertEqual(profile.transcript, [])
        self.assertEqual(profile.recommendation(), "interview_not_completed")

    def test_candidate_domain_model(self):
        from app.interview.models import Candidate
        candidate = Candidate(
            id="c-123",
            full_name="Pradeep S",
            phone="+919876543210",
            job_title="Backend Engineer",
            timezone="Asia/Kolkata",
            contact_consent=True,
            resume_filename="resume.pdf",
            resume_text="Experienced engineer...",
            created_at="2026-09-29T12:00:00Z",
        )
        self.assertEqual(candidate.to_public_dict()["phone_last_four"], "3210")
        self.assertNotIn("resume_text", candidate.to_public_dict())
        self.assertEqual(candidate.to_dict()["id"], "c-123")

    def test_database_configuration(self):
        from app.config import settings
        self.assertEqual(settings.db_name, "interview")
        self.assertIn("interview", settings.database_url)

    def test_turn_engine_conversational_flow(self):
        import asyncio
        from app.interview.turn_engine import InterviewTurnEngine

        profile = InterviewProfile("call-123", "cand-123", "int-123", PLAN)
        engine = InterviewTurnEngine(profile)

        # 1. Candidate says Yes to consent
        t1 = asyncio.run(engine.take_turn("Yes, I consent to being interviewed."))
        self.assertTrue(profile.transcription_consent)
        self.assertIn("Let's begin", t1["say"])
        self.assertEqual(profile.active_question_index, 0)

        # 2. Candidate answers Question 1
        t2 = asyncio.run(engine.take_turn("I designed and built the payments microservice in Python with FastAPI."))
        self.assertEqual(len(profile.answers), 1)
        self.assertEqual(profile.answers[0].question_id, "project")
        self.assertEqual(profile.answers[0].score, 3)

        # 3. Candidate answers Question 2
        t3 = asyncio.run(engine.take_turn("I set up Prometheus metrics, alerts, and automated load tests to verify reliability."))
        self.assertEqual(len(profile.answers), 2)
        self.assertTrue(profile.finished_questions)
        self.assertIn("concludes", t3["say"])
        self.assertTrue(t3["should_end_call"])

        # 4. Check score and shortlist recommendation
        self.assertIsNotNone(profile.overall_score())
        self.assertGreaterEqual(profile.overall_score(), 70.0)
        self.assertEqual(profile.recommendation(), "recommend_human_shortlist_review")


if __name__ == "__main__":
    unittest.main()
