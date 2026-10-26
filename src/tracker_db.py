"""Application Tracker & Database SQLite Engine."""

from __future__ import annotations

import datetime
import json
import logging
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
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
                        recommended_angle = ?, raw_description = ?, last_action_date = ?, notes = ?
                    WHERE id = ?
                """, (
                    job.company, job.role, job.source, job.location, job.experience_years, job.salary,
                    fit_score, decision, final_status, job.hr_name, job.hr_email, matching_skills,
                    gap_analysis, recommended_angle, job.raw_description, now, new_notes, job_id
                ))
            else:
                cursor.execute("""
                    INSERT INTO applications (
                        company, role, job_url, source, location, experience_years, salary,
                        fit_score, decision, status, hr_name, hr_email, matching_skills,
                        gap_analysis, recommended_angle, raw_description, last_action_date, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.company, job.role, job.job_url, job.source, job.location, job.experience_years, job.salary,
                    fit_score, decision, final_status, job.hr_name, job.hr_email, matching_skills,
                    gap_analysis, recommended_angle, job.raw_description, now, notes
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
        applied_date: Optional[str] = None
    ) -> bool:
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
            if notes:
                query += ", notes = CASE WHEN notes IS NULL OR notes = '' THEN ? ELSE notes || '\n' || ? END"
                params.extend([notes, notes])

            query += " WHERE id = ?"
            params.append(job_id)

            cursor.execute(query, params)
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
