"""Resume extraction with deliberate data minimisation for model prompts."""

from __future__ import annotations

import re
import zipfile
from html import unescape
from io import BytesIO


class ResumeError(ValueError):
    pass


_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d .()\-]{6,}\d)(?!\w)")
_SENSITIVE_FIELD = re.compile(
    r"\b(date of birth|\bdob\b|age|gender|sex|marital status|religion|caste|nationality|"
    r"disability|health condition|pregnan\w*)\b",
    re.IGNORECASE,
)


def extract_resume_text(contents: bytes, filename: str) -> str:
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix == "pdf":
        try:
            from pypdf import PdfReader

            text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(contents)).pages)
        except Exception as exc:
            raise ResumeError("This PDF could not be read. Upload a text-based PDF, DOCX, or TXT file.") from exc
    elif suffix == "docx":
        try:
            with zipfile.ZipFile(BytesIO(contents)) as document:
                xml = document.read("word/document.xml").decode("utf-8", errors="ignore")
            text = unescape(re.sub(r"<[^>]+>", " ", xml))
        except (KeyError, zipfile.BadZipFile) as exc:
            raise ResumeError("This DOCX file could not be read.") from exc
    elif suffix == "txt":
        text = contents.decode("utf-8", errors="replace")
    else:
        raise ResumeError("Supported résumé formats are PDF, DOCX, and TXT.")

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 80:
        raise ResumeError("The résumé has too little readable text. A scanned PDF may need OCR first.")
    return text[:50_000]


def prompt_safe_resume(text: str) -> str:
    """Remove obvious personal details; job evidence remains available to the planner."""
    kept = [line for line in text.splitlines() if not _SENSITIVE_FIELD.search(line)]
    safe = "\n".join(kept)
    safe = _EMAIL.sub("[redacted email]", safe)
    safe = _PHONE.sub("[redacted phone]", safe)
    return safe[:18_000]
