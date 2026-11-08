"""Application Tracker & Database SQLite Engine."""

from __future__ import annotations

import datetime
import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.scrapers.base_scraper import ScrapedJob
from src.scoring_engine import EvaluationResult

logger = logging.getLogger(__name__)


def get_default_db_path() -> Path:
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "data" / "jobit.db"


class TrackerDB:
    """Manages SQLite storage for job applications, fit evaluations, and pipeline stages."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_default_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initializes tables and indexes."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    role TEXT NOT NULL,
                    job_url TEXT UNIQUE NOT NULL,
                    source TEXT NOT NULL,
                    location TEXT DEFAULT 'Mumbai',
                    experience_years TEXT,
                    salary TEXT,
                    fit_score INTEGER DEFAULT 0,
                    decision TEXT DEFAULT 'PENDING',
                    status TEXT NOT NULL DEFAULT 'Scraped',
                    tailored_cv_path TEXT,
                    hr_name TEXT,
                    hr_email TEXT,
                    matching_skills TEXT,
                    gap_analysis TEXT,
                    recommended_angle TEXT,
                    raw_description TEXT,
                    applied_date TIMESTAMP,
                    last_action_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    pillar TEXT,
                    lab_builds TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            try:
                cursor.execute("ALTER TABLE applications ADD COLUMN pillar TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE applications ADD COLUMN lab_builds TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE applications ADD COLUMN proof_screenshot_path TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE applications ADD COLUMN submission_url TEXT")
            except sqlite3.OperationalError:
                pass
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_apps_status ON applications(status);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_apps_score ON applications(fit_score);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_apps_url ON applications(job_url);
            """)
            conn.commit()

    def upsert_job(
        self,
        job: ScrapedJob,
        eval_result: Optional[EvaluationResult] = None,
        status: Optional[str] = None,
        notes: Optional[str] = None
    ) -> int:
        """Inserts or updates a job application."""
        now = datetime.datetime.now().isoformat()
        fit_score = eval_result.fit_score if eval_result else 0
        decision = eval_result.decision if eval_result else "PENDING"
        matching_skills = json.dumps(eval_result.matching_skills) if eval_result else "[]"
        gap_analysis = eval_result.gap_analysis if eval_result else ""
        recommended_angle = eval_result.recommended_angle if eval_result else ""
        pillar = eval_result.pillar if eval_result else None
        lab_builds = json.dumps(eval_result.matched_lab_builds) if eval_result and eval_result.matched_lab_builds else "[]"
        
        default_status = "Scraped"
        if eval_result and eval_result.is_filtered_out:
            default_status = "Filtered"
        elif eval_result and eval_result.decision == "APPLY":
            default_status = "Ranked"

        final_status = status or default_status

        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Check if job_url exists
            cursor.execute("SELECT id, status, notes, tailored_cv_path FROM applications WHERE job_url = ?", (job.job_url,))
            existing = cursor.fetchone()

            if existing:
                job_id = existing["id"]
                # Preserve existing tailored CV or notes if already present
                existing_cv = existing["tailored_cv_path"]
                existing_notes = existing["notes"] or ""
                new_notes = f"{existing_notes}\n{notes}".strip() if notes else existing_notes

                cursor.execute("""
                    UPDATE applications
                    SET company = ?, role = ?, source = ?, location = ?, experience_years = ?, salary = ?,
                        fit_score = ?, decision = ?, status = ?, hr_name = COALESCE(?, hr_name),
                        hr_email = COALESCE(?, hr_email), matching_skills = ?, gap_analysis = ?,
                        recommended_angle = ?, raw_description = ?, last_action_date = ?, notes = ?,
                        pillar = COALESCE(?, pillar), lab_builds = COALESCE(?, lab_builds)
                    WHERE id = ?
                """, (
                    job.company, job.role, job.source, job.location, job.experience_years, job.salary,
                    fit_score, decision, final_status, job.hr_name, job.hr_email, matching_skills,
                    gap_analysis, recommended_angle, job.raw_description, now, new_notes,
                    pillar, lab_builds, job_id
                ))
            else:
                cursor.execute("""
                    INSERT INTO applications (
                        company, role, job_url, source, location, experience_years, salary,
                        fit_score, decision, status, hr_name, hr_email, matching_skills,
                        gap_analysis, recommended_angle, raw_description, last_action_date, notes,
                        pillar, lab_builds
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.company, job.role, job.job_url, job.source, job.location, job.experience_years, job.salary,
                    fit_score, decision, final_status, job.hr_name, job.hr_email, matching_skills,
                    gap_analysis, recommended_angle, job.raw_description, now, notes,
                    pillar, lab_builds
                ))
                job_id = cursor.lastrowid

            conn.commit()
            return job_id

    def get_job_by_id(self, job_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM applications WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            if row:
                d = dict(row)
                if d.get("matching_skills"):
                    try:
                        d["matching_skills"] = json.loads(d["matching_skills"])
                    except Exception:
                        pass
                return d
            return None

    def get_job_by_url(self, job_url: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM applications WHERE job_url = ?", (job_url,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_all_applications(self, status: Optional[str] = None, min_score: Optional[int] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM applications WHERE 1=1"
            params: List[Any] = []
            if status:
                query += " AND status = ?"
                params.append(status)
            if min_score is not None:
                query += " AND fit_score >= ?"
                params.append(min_score)

            query += " ORDER BY fit_score DESC, last_action_date DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                if item.get("matching_skills"):
                    try:
                        item["matching_skills"] = json.loads(item["matching_skills"])
                    except Exception:
                        pass
                results.append(item)
            return results

    def update_status(
        self,
        job_id: int,
        status: str,
        notes: Optional[str] = None,
        tailored_cv_path: Optional[str] = None,
        applied_date: Optional[str] = None,
        proof_screenshot_path: Optional[str] = None,
        submission_url: Optional[str] = None
    ) -> bool:
        # Proof-of-Submission Firewall Enforcement
        if status in ("Applied", "APPLIED_VERIFIED"):
            if not proof_screenshot_path or not os.path.exists(proof_screenshot_path):
                logger.warning(
                    f"PoS Firewall: Blocked attempt to mark job {job_id} as '{status}' without verified screenshot proof. Diverting to NEEDS_HUMAN_CLICK."
                )
                status = "NEEDS_HUMAN_CLICK"
                reason = "[PoS Firewall] Reverted fake apply: Requires verified screenshot proof on disk."
                notes = f"{notes}\n{reason}" if notes else reason

        now = datetime.datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "UPDATE applications SET status = ?, last_action_date = ?"
            params = [status, now]

            if tailored_cv_path:
                query += ", tailored_cv_path = ?"
                params.append(tailored_cv_path)
            if applied_date:
                query += ", applied_date = ?"
                params.append(applied_date)
            if proof_screenshot_path:
                query += ", proof_screenshot_path = ?"
                params.append(proof_screenshot_path)
            if submission_url:
                query += ", submission_url = ?"
                params.append(submission_url)
            if notes:
                query += ", notes = CASE WHEN notes IS NULL OR notes = '' THEN ? ELSE notes || '\n' || ? END"
                params.extend([notes, notes])

            query += " WHERE id = ?"
            params.append(job_id)

            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0

    def mark_applied_verified(
        self,
        job_id: int,
        proof_screenshot_path: str,
        submission_url: str,
        submitted_at: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """Enforces Proof-of-Submission (PoS) Firewall.
        A job CANNOT be marked APPLIED_VERIFIED without:
        1. A verified post-submission screenshot file existing on disk.
        2. A valid submission URL.
        3. A valid submission timestamp.
        """
        if not proof_screenshot_path or not os.path.exists(proof_screenshot_path):
            raise ValueError(
                f"PoS Firewall Rejection: Missing or non-existent proof screenshot '{proof_screenshot_path}'. "
                "A verified screenshot file must exist on disk before marking APPLIED_VERIFIED."
            )
        if not submission_url or not submission_url.startswith("http"):
            raise ValueError(
                f"PoS Firewall Rejection: Invalid submission URL '{submission_url}'. "
                "A valid http/https submission URL is required."
            )

        ts = submitted_at or datetime.datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE applications
                SET status = 'APPLIED_VERIFIED',
                    proof_screenshot_path = ?,
                    submission_url = ?,
                    applied_date = ?,
                    last_action_date = ?,
                    notes = CASE WHEN notes IS NULL OR notes = '' THEN ? ELSE notes || '\n' || ? END
                WHERE id = ?
            """, (
                proof_screenshot_path,
                submission_url,
                ts,
                ts,
                notes or f"PoS Verified submission at {submission_url}",
                notes or f"PoS Verified submission at {submission_url}",
                job_id
            ))
            conn.commit()
            return cursor.rowcount > 0

    def mark_needs_human_click(
        self,
        job_id: int,
        reason: str,
        screenshot_path: Optional[str] = None
    ) -> bool:
        """Logs bot-wall, captcha or manual submission barrier without faking applied status."""
        now = datetime.datetime.now().isoformat()
        note_msg = f"NEEDS_HUMAN_CLICK: {reason}"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE applications
                SET status = 'NEEDS_HUMAN_CLICK',
                    last_action_date = ?,
                    notes = CASE WHEN notes IS NULL OR notes = '' THEN ? ELSE notes || '\n' || ? END,
                    proof_screenshot_path = COALESCE(?, proof_screenshot_path)
                WHERE id = ?
            """, (now, note_msg, note_msg, screenshot_path, job_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_outreach_contact(self, job_id: int, hr_name: str, hr_email: str, status: Optional[str] = None) -> bool:
        now = datetime.datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute("""
                    UPDATE applications
                    SET hr_name = ?, hr_email = ?, status = ?, last_action_date = ?
                    WHERE id = ?
                """, (hr_name, hr_email, status, now, job_id))
            else:
                cursor.execute("""
                    UPDATE applications
                    SET hr_name = ?, hr_email = ?, last_action_date = ?
                    WHERE id = ?
                """, (hr_name, hr_email, now, job_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_pipeline_stats(self) -> Dict[str, int]:
        """Returns application count grouped by status."""
        stages = ["Scraped", "Filtered", "Ranked", "Tailored", "Applied", "Emailed", "Interview", "Rejected"]
        stats = {stage: 0 for stage in stages}
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, count(*) as cnt FROM applications GROUP BY status")
            for row in cursor.fetchall():
                st = row["status"]
                cnt = row["cnt"]
                stats[st] = cnt
        return stats

    def get_follow_up_alerts(self, days_threshold: int = 4) -> List[Dict[str, Any]]:
        """Identifies applications that were emailed or applied > N days ago without follow up."""
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days_threshold)).isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM applications
                WHERE status IN ('Applied', 'Emailed')
                  AND last_action_date <= ?
                ORDER BY last_action_date ASC
            """, (cutoff,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
