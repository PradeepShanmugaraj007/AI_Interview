"""State that belongs to one candidate interview, not to the voice provider."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class Question:
    question_id: str
    prompt: str
    competency: str
    rationale: str
    weight: float = 1.0

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Question":
        return cls(
            question_id=str(value["question_id"]),
            prompt=str(value["prompt"]),
            competency=str(value["competency"]),
            rationale=str(value.get("rationale", "")),
            weight=max(0.1, float(value.get("weight", 1))),
        )


@dataclass(frozen=True)
class InterviewPlan:
    job_title: str
    questions: tuple[Question, ...]
    scoring_guidance: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_title": self.job_title,
            "questions": [asdict(question) for question in self.questions],
            "scoring_guidance": self.scoring_guidance,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "InterviewPlan":
        return cls(
            job_title=str(value["job_title"]),
            questions=tuple(Question.from_dict(item) for item in value["questions"]),
            scoring_guidance=str(value.get("scoring_guidance", "")),
        )


@dataclass
class AnswerAssessment:
    question_id: str
    question: str
    competency: str
    response: str
    score: int
    evidence: str
    rationale: str


@dataclass
class Candidate:
    id: str
    full_name: str
    phone: str
    job_title: str
    timezone: str
    contact_consent: bool
    resume_filename: str
    resume_text: str
    created_at: str
    email: str = ""
    role_rubric: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "full_name": self.full_name,
            "phone": self.phone,
            "email": self.email,
            "job_title": self.job_title,
            "role_rubric": self.role_rubric,
            "timezone": self.timezone,
            "contact_consent": self.contact_consent,
            "resume_filename": self.resume_filename,
            "resume_text": self.resume_text,
            "created_at": self.created_at,
        }

    def to_public_dict(self) -> dict[str, Any]:
        """Never expose full resume text or raw phone in public/UI views."""
        return {
            "id": self.id,
            "full_name": self.full_name,
            "phone_last_four": self.phone[-4:] if len(self.phone) >= 4 else self.phone,
            "job_title": self.job_title,
            "timezone": self.timezone,
            "contact_consent": self.contact_consent,
            "created_at": self.created_at,
        }


@dataclass
class InterviewRecord:
    id: str
    candidate_id: str
    status: str
    plan: InterviewPlan
    created_at: str
    call_sid: str | None = None
    result: dict[str, Any] | None = None
    started_at: str | None = None
    completed_at: str | None = None


@dataclass
class InterviewProfile:
    """Only job-relevant evidence is placed in this object and scorecard."""

    call_sid: str
    candidate_id: str
    interview_id: str
    plan: InterviewPlan
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ai_disclosed: bool = False
    transcription_consent: bool = False
    candidate_requested_stop: bool = False
    active_question_index: int = -1
    answers: list[AnswerAssessment] = field(default_factory=list)
    transcript: list[dict[str, str]] = field(default_factory=list)
    turns: int = 0

    @property
    def active_question(self) -> Question | None:
        if 0 <= self.active_question_index < len(self.plan.questions):
            return self.plan.questions[self.active_question_index]
        return None

    @property
    def finished_questions(self) -> bool:
        return self.active_question_index >= len(self.plan.questions)

    def apply(self, result: dict[str, Any], candidate_said: str) -> None:
        """Accept one model result, clamping it to the server's interview plan."""
        self.ai_disclosed = self.ai_disclosed or bool(result.get("ai_disclosed"))
        self.transcription_consent = self.transcription_consent or bool(
            result.get("transcription_consent")
        )
        self.candidate_requested_stop = self.candidate_requested_stop or bool(
            result.get("candidate_requested_stop")
        )
        self.turns += 1

        # Do not retain a candidate's interview content unless they have agreed
        # to the stated interview/transcription flow.
        if self.transcription_consent:
            self.transcript.append({"speaker": "candidate", "text": candidate_said})
            if result.get("say"):
                self.transcript.append({"speaker": "interviewer", "text": str(result["say"])})

        active = self.active_question
        assessment = result.get("answer_assessment")
        if active and assessment and bool(assessment.get("final")):
            score = min(4, max(0, int(assessment.get("score", 0))))
            self.answers.append(
                AnswerAssessment(
                    question_id=active.question_id,
                    question=active.prompt,
                    competency=active.competency,
                    response=candidate_said,
                    score=score,
                    evidence=str(assessment.get("evidence", ""))[:500],
                    rationale=str(assessment.get("rationale", ""))[:500],
                )
            )
            self.active_question_index += 1
        elif self.transcription_consent and self.active_question_index == -1:
            self.active_question_index = 0

    def overall_score(self) -> float | None:
        if not self.answers:
            return None
        weights = {question.question_id: question.weight for question in self.plan.questions}
        denominator = sum(weights.get(answer.question_id, 1.0) for answer in self.answers)
        return round(
            100 * sum(answer.score * weights.get(answer.question_id, 1.0) for answer in self.answers)
            / (4 * denominator),
            1,
        )

    def recommendation(self) -> str:
        score = self.overall_score()
        if self.candidate_requested_stop or not self.transcription_consent:
            return "interview_not_completed"
        if score is None or len(self.answers) < max(2, len(self.plan.questions) // 2):
            return "more_evidence_needed"
        if score >= 70:
            return "recommend_human_shortlist_review"
        return "recommend_human_review_before_rejecting"

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_sid": self.call_sid,
            "candidate_id": self.candidate_id,
            "interview_id": self.interview_id,
            "started_at": self.started_at.isoformat(),
            "ai_disclosed": self.ai_disclosed,
            "transcription_consent": self.transcription_consent,
            "candidate_requested_stop": self.candidate_requested_stop,
            "questions_completed": len(self.answers),
            "questions_planned": len(self.plan.questions),
            "overall_score": self.overall_score(),
            "recommendation": self.recommendation(),
            "answers": [asdict(answer) for answer in self.answers],
            "transcript": self.transcript,
        }
