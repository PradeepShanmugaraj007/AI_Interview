import unittest

from app.interview.resume import extract_resume_text, prompt_safe_resume


class ResumeTests(unittest.TestCase):
    def test_text_resume_is_extracted_and_personal_fields_are_removed_from_prompt(self):
        text = (
            "Priya Example\nEmail: priya@example.com\nPhone: +91 98765 43210\n"
            "Gender: Female\nDate of birth: 01/01/1990\n"
            "Built a payment reconciliation service in Python and reduced failures by 30 percent.\n"
        )
        extracted = extract_resume_text(text.encode(), "resume.txt")
        safe = prompt_safe_resume(extracted)

        self.assertIn("payment reconciliation service", safe)
        self.assertNotIn("priya@example.com", safe)
        self.assertNotIn("98765", safe)
        self.assertNotIn("Female", safe)
        self.assertNotIn("01/01/1990", safe)

    def test_docx_resume_is_extracted(self):
        import io
        import zipfile
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            xml = (
                "<w:p><w:t>Rajesh Kumar Senior Backend Engineer with 8 years experience. "
                "Architected Kafka streaming pipelines and reduced data processing latency by 40 percent.</w:t></w:p>"
            )
            zf.writestr("word/document.xml", xml)
        extracted = extract_resume_text(buffer.getvalue(), "resume.docx")
        self.assertIn("Architected Kafka streaming pipelines", extracted)

    def test_short_resume_is_rejected(self):
        from app.interview.resume import ResumeError
        short_text = "Too short"
        with self.assertRaises(ResumeError):
            extract_resume_text(short_text.encode(), "short.txt")

    def test_planner_extracts_resume_claim_into_questions(self):
        import asyncio
        from app.interview.planner import InterviewPlanner

        planner = InterviewPlanner()
        resume_text = (
            "Senior Infrastructure Engineer\n"
            "- Designed high-availability Kubernetes clusters across three cloud regions.\n"
            "- Built zero-downtime database failover automation with PostgreSQL.\n"
        )
        plan = asyncio.run(planner.create(
            job_title="DevOps Lead",
            role_rubric="Kubernetes, Cloud, High Availability",
            resume_text=resume_text
        ))
        self.assertEqual(plan.job_title, "DevOps Lead")
        self.assertTrue(len(plan.questions) >= 4)
        # Check that one question specifically asks about the resume achievement
        prompts_text = " ".join(q.prompt for q in plan.questions)
        self.assertTrue(
            "Kubernetes" in prompts_text or "PostgreSQL" in prompts_text or "Designed" in prompts_text or "Built" in prompts_text
        )


if __name__ == "__main__":
    unittest.main()
