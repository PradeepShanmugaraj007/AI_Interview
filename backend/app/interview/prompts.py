"""Prompt assembly for the single per-turn interview model call."""

from __future__ import annotations

from .models import InterviewProfile, Question


IDENTITY = """You are Ava, an AI assistant conducting a first-round phone interview.
You are speaking aloud over a phone line. Be warm, brief, accessible, and neutral.

Hard rules:
- You must clearly disclose that you are an AI and ask for consent to transcribe
  interview answers before asking an interview question. If declined, acknowledge
  and end the call; do not pressure the candidate.
- Ask one question at a time. Keep each spoken turn below 45 words.
- Ask only the server-provided questions or a brief clarification of the active
  question. Do not invent requirements or ask unrelated questions.
- Assess only job-relevant evidence in the answer. Never evaluate accent, voice,
  fluency, personality, age, gender, caste, religion, nationality, disability,
  health, family status, or any other protected/personal characteristic.
- A score is an evidence summary for a human recruiter, never an automatic hiring
  or rejection decision. If an answer is insufficient, ask one short clarification
  before finalising its score.
- If the candidate asks to stop, skip, repeat, or speak to a human, comply.
"""


def system_prompt(profile: InterviewProfile) -> str:
    questions = "\n".join(
        f"- {question.question_id} | {question.competency} | {question.prompt}"
        for question in profile.plan.questions
    )
    return (
        f"{IDENTITY}\n"
        f"# Role\n{profile.plan.job_title}\n\n"
        f"# Approved question plan\n{questions}\n\n"
        f"# Scoring guidance\n{profile.plan.scoring_guidance}\n"
    )


def render_turn(profile: InterviewProfile, candidate_said: str) -> str:
    active = profile.active_question
    parts = [f'Candidate just said: "{candidate_said}"', ""]
    if not profile.transcription_consent:
        parts.extend(
            [
                "The candidate has not yet given verbal consent to transcription.",
                "State that you are an AI interviewer and ask whether they consent to having interview answers transcribed for recruiter review.",
                "Set transcription_consent true only for a clear yes. Do not score an answer yet.",
            ]
        )
    elif active is None and not profile.finished_questions:
        first = profile.plan.questions[0]
        parts.extend(
            [
                "Thank the candidate and ask this exact first planned question:",
                first.prompt,
                "Set answer_assessment.final to false; there is no answer to score yet.",
            ]
        )
    elif active is not None:
        parts.extend(_active_question_instruction(profile, active))
    else:
        parts.extend(
            [
                "All planned questions are complete. Thank the candidate, explain that a recruiter will review job-relevant evidence, and end the call.",
                "Set should_end_call true.",
            ]
        )
    parts.append("Return the spoken turn and structured state only.")
    return "\n".join(parts)


def _active_question_instruction(profile: InterviewProfile, active: Question) -> list[str]:
    next_index = profile.active_question_index + 1
    lines = [
        f"Active question id: {active.question_id}",
        f"Active question: {active.prompt}",
        "Assess the candidate's latest response only against this active question and its competency.",
        "Use score 0 to 4 only when the answer is final: 0 no relevant evidence, 1 minimal, 2 partial, 3 strong, 4 exceptional concrete evidence.",
        "Evidence must quote or closely paraphrase the candidate's job-relevant answer, not a résumé claim.",
    ]
    if next_index < len(profile.plan.questions):
        following = profile.plan.questions[next_index]
        lines.extend(
            [
                "If the answer is sufficient, finalise its assessment and then ask this exact next planned question:",
                following.prompt,
                "If it is not sufficient, set final false and ask one focused clarification about the active question instead.",
            ]
        )
    else:
        lines.extend(
            [
                "If the answer is sufficient, finalise its assessment, thank the candidate, and set should_end_call true.",
                "If it is not sufficient, set final false and ask one focused clarification about the active question instead.",
            ]
        )
    return lines
