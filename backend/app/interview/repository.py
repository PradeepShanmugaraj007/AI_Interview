"""Repository supporting both PostgreSQL and SQLite.

Stores candidates, résumés, tailored question plans, and reviewable outcomes.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None  # type: ignore[assignment]
    dict_row = None  # type: ignore[assignment]

from .models import InterviewPlan

log = logging.getLogger(__name__)


class InterviewRepository:
    def __init__(self, data_dir: Path, database_url: str | None = None) -> None:
        self._data_dir = data_dir
        self._resumes_dir = data_dir / "resumes"
        self._resumes_dir.mkdir(parents=True, exist_ok=True)
        self._database_url = database_url
        self._is_postgres = bool(
            database_url and (database_url.startswith("postgresql://") or database_url.startswith("postgres://"))
        )

        if self._is_postgres and psycopg is not None:
            try:
                log.info("Using PostgreSQL repository connection")
                self._init_postgres()
            except Exception as exc:
                log.warning("PostgreSQL connection failed (%s); falling back to SQLite", exc)
                self._is_postgres = False
                self._db_path = data_dir / "interviews.sqlite3"
                self._init_sqlite()
        else:
            self._db_path = data_dir / "interviews.sqlite3"
            self._init_sqlite()

    def _connect_postgres(self):
        return psycopg.connect(self._database_url, row_factory=dict_row)

    def _connect_sqlite(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_postgres(self) -> None:
        with self._connect_postgres() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS candidates (
                        id VARCHAR(64) PRIMARY KEY,
                        full_name VARCHAR(255) NOT NULL,
                        phone VARCHAR(50) NOT NULL,
                        email VARCHAR(255) NOT NULL,
                        job_title VARCHAR(255) NOT NULL,
                        role_rubric TEXT NOT NULL,
                        timezone VARCHAR(100) NOT NULL,
                        contact_consent BOOLEAN NOT NULL,
                        resume_filename VARCHAR(255) NOT NULL,
                        resume_text TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS interviews (
                        id VARCHAR(64) PRIMARY KEY,
                        candidate_id VARCHAR(64) NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
                        status VARCHAR(50) NOT NULL,
                        call_sid VARCHAR(100),
                        plan_json TEXT NOT NULL,
                        result_json TEXT,
                        created_at TEXT NOT NULL,
                        started_at TEXT,
                        completed_at TEXT
                    );
                    """
                )

    def _init_sqlite(self) -> None:
        with self._connect_sqlite() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS candidates (
                    id TEXT PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    email TEXT NOT NULL,
                    job_title TEXT NOT NULL,
                    role_rubric TEXT NOT NULL,
                    timezone TEXT NOT NULL,
                    contact_consent INTEGER NOT NULL,
                    resume_filename TEXT NOT NULL,
                    resume_text TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS interviews (
                    id TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL REFERENCES candidates(id),
                    status TEXT NOT NULL,
                    call_sid TEXT,
                    plan_json TEXT NOT NULL,
                    result_json TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT
                );
                """
            )

    def create_candidate(
        self,
        *,
        full_name: str,
        phone: str,
        email: str,
        job_title: str,
        role_rubric: str,
        timezone: str,
        contact_consent: bool,
        resume_filename: str,
        resume_contents: bytes,
        resume_text: str,
    ) -> dict[str, Any]:
        candidate_id = str(uuid4())
        extension = Path(resume_filename).suffix.lower()
        stored_name = f"{candidate_id}{extension}"
        resume_path = self._resumes_dir / stored_name
        resume_path.write_bytes(resume_contents)
        try:
            resume_path.chmod(0o600)
        except OSError:
            pass
        created_at = _now()

        if self._is_postgres and psycopg is not None:
            with self._connect_postgres() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO candidates
                           (id, full_name, phone, email, job_title, role_rubric, timezone,
                            contact_consent, resume_filename, resume_text, created_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            candidate_id, full_name, phone, email, job_title, role_rubric, timezone,
                            contact_consent, stored_name, resume_text, created_at,
                        ),
                    )
        else:
            with self._connect_sqlite() as connection:
                connection.execute(
                    """INSERT INTO candidates
                       (id, full_name, phone, email, job_title, role_rubric, timezone,
                        contact_consent, resume_filename, resume_text, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        candidate_id, full_name, phone, email, job_title, role_rubric, timezone,
                        int(contact_consent), stored_name, resume_text, created_at,
                    ),
                )
        return self.get_candidate(candidate_id)  # type: ignore[return-value]

    def get_candidate(self, candidate_id: str) -> dict[str, Any] | None:
        if self._is_postgres and psycopg is not None:
            with self._connect_postgres() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM candidates WHERE id = %s", (candidate_id,))
                    row = cur.fetchone()
            return dict(row) if row else None
        else:
            with self._connect_sqlite() as connection:
                row = connection.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
            return _candidate_dict(row) if row else None

    def list_candidates(self) -> list[dict[str, Any]]:
        if self._is_postgres and psycopg is not None:
            with self._connect_postgres() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM candidates ORDER BY created_at DESC")
                    rows = cur.fetchall()
            return [dict(row) for row in rows]
        else:
            with self._connect_sqlite() as connection:
                rows = connection.execute(
                    "SELECT * FROM candidates ORDER BY created_at DESC"
                ).fetchall()
            return [_candidate_dict(row) for row in rows]

    def create_interview(self, candidate_id: str, plan: InterviewPlan) -> dict[str, Any]:
        interview_id = str(uuid4())
        created_at = _now()
        plan_str = json.dumps(plan.to_dict())

        if self._is_postgres and psycopg is not None:
            with self._connect_postgres() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO interviews (id, candidate_id, status, plan_json, created_at)
                           VALUES (%s, %s, 'planned', %s, %s)""",
                        (interview_id, candidate_id, plan_str, created_at),
                    )
        else:
            with self._connect_sqlite() as connection:
                connection.execute(
                    """INSERT INTO interviews (id, candidate_id, status, plan_json, created_at)
                       VALUES (?, ?, 'planned', ?, ?)""",
                    (interview_id, candidate_id, plan_str, created_at),
                )
        return self.get_interview(interview_id)  # type: ignore[return-value]

    def mark_dialled(self, interview_id: str, call_sid: str) -> None:
        now = _now()
        if self._is_postgres and psycopg is not None:
            with self._connect_postgres() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE interviews SET status = 'in_progress', call_sid = %s, started_at = %s
                           WHERE id = %s""",
                        (call_sid, now, interview_id),
                    )
        else:
            with self._connect_sqlite() as connection:
                connection.execute(
                    """UPDATE interviews SET status = 'in_progress', call_sid = ?, started_at = ?
                       WHERE id = ?""",
                    (call_sid, now, interview_id),
                )

    def complete_interview(self, interview_id: str, result: dict[str, Any]) -> None:
        now = _now()
        result_str = json.dumps(result)
        if self._is_postgres and psycopg is not None:
            with self._connect_postgres() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE interviews SET status = 'completed', result_json = %s, completed_at = %s
                           WHERE id = %s""",
                        (result_str, now, interview_id),
                    )
        else:
            with self._connect_sqlite() as connection:
                connection.execute(
                    """UPDATE interviews SET status = 'completed', result_json = ?, completed_at = ?
                       WHERE id = ?""",
                    (result_str, now, interview_id),
                )

    def get_interview(self, interview_id: str) -> dict[str, Any] | None:
        if self._is_postgres and psycopg is not None:
            with self._connect_postgres() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM interviews WHERE id = %s", (interview_id,))
                    row = cur.fetchone()
            return _normalize_interview_dict(row) if row else None
        else:
            with self._connect_sqlite() as connection:
                row = connection.execute("SELECT * FROM interviews WHERE id = ?", (interview_id,)).fetchone()
            return _interview_dict(row) if row else None

    def get_interview_by_call_sid(self, call_sid: str) -> dict[str, Any] | None:
        if self._is_postgres and psycopg is not None:
            with self._connect_postgres() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM interviews WHERE call_sid = %s ORDER BY created_at DESC LIMIT 1", (call_sid,))
                    row = cur.fetchone()
            return _normalize_interview_dict(row) if row else None
        else:
            with self._connect_sqlite() as connection:
                row = connection.execute("SELECT * FROM interviews WHERE call_sid = ? ORDER BY created_at DESC LIMIT 1", (call_sid,)).fetchone()
            return _interview_dict(row) if row else None

    def get_active_interview_for_candidate(self, candidate_id: str) -> dict[str, Any] | None:
        if self._is_postgres and psycopg is not None:
            with self._connect_postgres() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM interviews WHERE candidate_id = %s AND status = 'in_progress' ORDER BY created_at DESC LIMIT 1",
                        (candidate_id,),
                    )
                    row = cur.fetchone()
            return _normalize_interview_dict(row) if row else None
        else:
            with self._connect_sqlite() as connection:
                row = connection.execute(
                    "SELECT * FROM interviews WHERE candidate_id = ? AND status = 'in_progress' ORDER BY created_at DESC LIMIT 1",
                    (candidate_id,),
                ).fetchone()
            return _interview_dict(row) if row else None

    def update_interview_status(
        self,
        interview_id: str,
        status: str,
        result: dict[str, Any] | None = None,
    ) -> None:
        now = _now()
        result_str = json.dumps(result) if result else None
        if self._is_postgres and psycopg is not None:
            with self._connect_postgres() as conn:
                with conn.cursor() as cur:
                    if result_str:
                        cur.execute(
                            """UPDATE interviews SET status = %s, result_json = %s, completed_at = %s
                               WHERE id = %s""",
                            (status, result_str, now, interview_id),
                        )
                    else:
                        cur.execute(
                            """UPDATE interviews SET status = %s, completed_at = %s
                               WHERE id = %s""",
                            (status, now, interview_id),
                        )
        else:
            with self._connect_sqlite() as connection:
                if result_str:
                    connection.execute(
                        """UPDATE interviews SET status = ?, result_json = ?, completed_at = ?
                           WHERE id = ?""",
                        (status, result_str, now, interview_id),
                    )
                else:
                    connection.execute(
                        """UPDATE interviews SET status = ?, completed_at = ?
                           WHERE id = ?""",
                        (status, now, interview_id),
                    )

    def interview_context(self, interview_id: str) -> tuple[dict[str, Any], InterviewPlan] | None:
        interview = self.get_interview(interview_id)
        if not interview:
            return None
        candidate = self.get_candidate(interview["candidate_id"])
        if not candidate:
            return None
        return candidate, InterviewPlan.from_dict(interview["plan"])

    def list_interviews_for_candidate(self, candidate_id: str) -> list[dict[str, Any]]:
        if self._is_postgres and psycopg is not None:
            with self._connect_postgres() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM interviews WHERE candidate_id = %s ORDER BY created_at DESC",
                        (candidate_id,),
                    )
                    rows = cur.fetchall()
            return [_normalize_interview_dict(dict(row)) for row in rows]
        else:
            with self._connect_sqlite() as connection:
                rows = connection.execute(
                    "SELECT * FROM interviews WHERE candidate_id = ? ORDER BY created_at DESC",
                    (candidate_id,),
                ).fetchall()
            return [_interview_dict(row) for row in rows]

    def list_interviews(self, limit: int = 100) -> list[dict[str, Any]]:
        if self._is_postgres and psycopg is not None:
            with self._connect_postgres() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM interviews ORDER BY created_at DESC LIMIT %s", (limit,))
                    rows = cur.fetchall()
            return [_normalize_interview_dict(dict(row)) for row in rows]
        else:
            with self._connect_sqlite() as connection:
                rows = connection.execute(
                    "SELECT * FROM interviews ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
            return [_interview_dict(row) for row in rows]

    def list_candidates_crm(self) -> list[dict[str, Any]]:
        candidates = self.list_candidates()
        interviews = self.list_interviews(limit=500)

        latest_by_candidate: dict[str, dict[str, Any]] = {}
        for iv in interviews:
            cid = iv["candidate_id"]
            if cid not in latest_by_candidate:
                latest_by_candidate[cid] = iv

        results = []
        for c in candidates:
            iv = latest_by_candidate.get(c["id"])
            latest_info = None
            if iv:
                res = iv.get("result") or {}
                latest_info = {
                    "id": iv["id"],
                    "status": iv["status"],
                    "score": res.get("overall_score"),
                    "recommendation": res.get("recommendation"),
                    "completed_at": iv.get("completed_at"),
                    "started_at": iv.get("started_at"),
                    "created_at": iv.get("created_at"),
                }
            results.append({
                "id": c["id"],
                "full_name": c["full_name"],
                "phone": c["phone"],
                "phone_last_four": c["phone"][-4:] if c.get("phone") else "",
                "email": c.get("email", ""),
                "job_title": c["job_title"],
                "timezone": c["timezone"],
                "contact_consent": c["contact_consent"],
                "resume_filename": c.get("resume_filename", ""),
                "created_at": c["created_at"],
                "latest_interview": latest_info,
            })
        return results

    def get_crm_stats(self) -> dict[str, Any]:
        candidates = self.list_candidates()
        interviews = self.list_interviews(limit=1000)

        completed = [iv for iv in interviews if iv.get("status") == "completed"]
        in_progress = [iv for iv in interviews if iv.get("status") == "in_progress"]

        shortlisted = 0
        review_needed = 0
        scores: list[float] = []

        for iv in completed:
            res = iv.get("result") or {}
            rec = res.get("recommendation")
            score = res.get("overall_score")
            if rec == "recommend_human_shortlist_review":
                shortlisted += 1
            elif rec == "recommend_human_review_before_rejecting":
                review_needed += 1
            if isinstance(score, (int, float)):
                scores.append(float(score))

        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
        shortlist_rate = round((shortlisted / len(completed)) * 100, 1) if completed else 0.0

        return {
            "total_candidates": len(candidates),
            "total_interviews": len(interviews),
            "completed_interviews": len(completed),
            "in_progress_interviews": len(in_progress),
            "shortlisted_count": shortlisted,
            "review_needed_count": review_needed,
            "shortlist_rate": shortlist_rate,
            "average_score": avg_score,
        }


def _candidate_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "full_name": row["full_name"],
        "phone": row["phone"],
        "email": row["email"],
        "job_title": row["job_title"],
        "role_rubric": row["role_rubric"],
        "timezone": row["timezone"],
        "contact_consent": bool(row["contact_consent"]),
        "resume_filename": row["resume_filename"],
        "resume_text": row["resume_text"],
        "created_at": row["created_at"],
    }


def _interview_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "candidate_id": row["candidate_id"],
        "status": row["status"],
        "call_sid": row["call_sid"],
        "plan": json.loads(row["plan_json"]),
        "result": json.loads(row["result_json"]) if row["result_json"] else None,
        "created_at": row["created_at"],
        "started_at": row["started_at"],
        "completed_at": row["completed_at"],
    }


def _normalize_interview_dict(row: dict[str, Any]) -> dict[str, Any]:
    plan_raw = row["plan_json"]
    plan = json.loads(plan_raw) if isinstance(plan_raw, str) else plan_raw
    result_raw = row.get("result_json")
    result = json.loads(result_raw) if isinstance(result_raw, str) else result_raw

    return {
        "id": row["id"],
        "candidate_id": row["candidate_id"],
        "status": row["status"],
        "call_sid": row.get("call_sid"),
        "plan": plan,
        "result": result,
        "created_at": str(row["created_at"]),
        "started_at": str(row["started_at"]) if row.get("started_at") else None,
        "completed_at": str(row["completed_at"]) if row.get("completed_at") else None,
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
