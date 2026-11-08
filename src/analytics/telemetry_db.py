"""
JobIt v2.0 - Local Conversion Telemetry Database Engine
SQLite backend tracking signals, opportunities, outreach touchpoints, and full funnel telemetry.
File: data/jobit_v2.db
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path("data/jobit_v2.db")


class TelemetryDB:
    """Manages SQLite telemetry schema and analytics queries."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._get_connection() as conn:
            cur = conn.cursor()

            # 1. Signals table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT UNIQUE,
                    funding_stage TEXT,
                    amount_raised TEXT,
                    sector TEXT,
                    location TEXT,
                    founder_names TEXT,
                    source TEXT,
                    source_url TEXT,
                    created_at TEXT
                )
            """)

            # 2. Opportunities table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT,
                    role_title TEXT,
                    pillar TEXT,
                    score INTEGER,
                    status TEXT DEFAULT 'IDENTIFIED',
                    target_dm_name TEXT,
                    target_dm_title TEXT,
                    expected_ctc_quote TEXT,
                    tailored_pdf_path TEXT,
                    notes TEXT,
                    proof_screenshot_path TEXT,
                    submission_url TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    UNIQUE(company_name, role_title)
                )
            """)

            try:
                cur.execute("ALTER TABLE opportunities ADD COLUMN proof_screenshot_path TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                cur.execute("ALTER TABLE opportunities ADD COLUMN submission_url TEXT")
            except sqlite3.OperationalError:
                pass

            # 3. Outreach logs
            cur.execute("""
                CREATE TABLE IF NOT EXISTS outreach_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    opportunity_id INTEGER,
                    company_name TEXT,
                    channel TEXT,
                    touchpoint_type TEXT,
                    message_text TEXT,
                    status TEXT,
                    sent_at TEXT,
                    response_received INTEGER DEFAULT 0,
                    response_sentiment TEXT,
                    response_date TEXT,
                    notes TEXT,
                    FOREIGN KEY(opportunity_id) REFERENCES opportunities(id)
                )
            """)

            # 4. Funnel events
            cur.execute("""
                CREATE TABLE IF NOT EXISTS funnel_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    opportunity_id INTEGER,
                    company_name TEXT,
                    event_type TEXT,
                    event_timestamp TEXT,
                    metadata_json TEXT,
                    FOREIGN KEY(opportunity_id) REFERENCES opportunities(id)
                )
            """)

            conn.commit()

    def record_signal(self, sig_dict: Dict[str, Any]) -> int:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO signals (
                    company_name, funding_stage, amount_raised, sector, location,
                    founder_names, source, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sig_dict.get("company_name"),
                sig_dict.get("funding_stage"),
                sig_dict.get("amount_raised"),
                sig_dict.get("sector"),
                sig_dict.get("hq_location"),
                ", ".join(sig_dict.get("founder_names", [])),
                sig_dict.get("source"),
                sig_dict.get("source_url"),
                sig_dict.get("announcement_date", datetime.now().isoformat())
            ))
            conn.commit()
            return cur.lastrowid or 0

    def record_opportunity(
        self,
        company_name: str,
        role_title: str,
        pillar: str,
        score: int,
        target_dm_name: str = "",
        target_dm_title: str = "",
        expected_ctc_quote: str = "",
        tailored_pdf_path: str = "",
        status: str = "IDENTIFIED",
        notes: str = ""
    ) -> int:
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO opportunities (
                    company_name, role_title, pillar, score, status,
                    target_dm_name, target_dm_title, expected_ctc_quote,
                    tailored_pdf_path, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(company_name, role_title) DO UPDATE SET
                    pillar=excluded.pillar,
                    score=excluded.score,
                    status=excluded.status,
                    target_dm_name=excluded.target_dm_name,
                    target_dm_title=excluded.target_dm_title,
                    expected_ctc_quote=excluded.expected_ctc_quote,
                    tailored_pdf_path=excluded.tailored_pdf_path,
                    updated_at=excluded.updated_at
            """, (
                company_name, role_title, pillar, score, status,
                target_dm_name, target_dm_title, expected_ctc_quote,
                tailored_pdf_path, notes, now, now
            ))
            conn.commit()

            # Record event
            cur.execute("SELECT id FROM opportunities WHERE company_name=? AND role_title=?", (company_name, role_title))
            row = cur.fetchone()
            opp_id = row["id"] if row else 0

            self.record_event(opp_id, company_name, "OPPORTUNITY_IDENTIFIED", {"score": score, "pillar": pillar})
            return opp_id

    def record_event(
        self,
        opportunity_id: int,
        company_name: str,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO funnel_events (
                    opportunity_id, company_name, event_type, event_timestamp, metadata_json
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                opportunity_id, company_name, event_type, now,
                json.dumps(metadata or {})
            ))
            conn.commit()

    def log_outreach(
        self,
        company_name: str,
        channel: str,
        touchpoint_type: str,
        message_text: str,
        status: str = "SENT",
        opportunity_id: Optional[int] = None
    ) -> int:
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO outreach_logs (
                    opportunity_id, company_name, channel, touchpoint_type,
                    message_text, status, sent_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                opportunity_id, company_name, channel, touchpoint_type,
                message_text, status, now
            ))
            log_id = cur.lastrowid or 0
            conn.commit()

        # Update opportunity status to OUTREACH_SENT
        if opportunity_id:
            self.update_status(opportunity_id, "OUTREACH_SENT")
        return log_id

    def update_status(self, opportunity_id: int, new_status: str, notes: str = "") -> None:
        if new_status in ("APPLIED", "APPLIED_VERIFIED", "APPLIED_PORTAL"):
            logger.warning("PoS Firewall: Cannot update to %s via update_status without verified proof. Diverting to NEEDS_HUMAN_CLICK.", new_status)
            new_status = "NEEDS_HUMAN_CLICK"
            notes = (notes + " | " if notes else "") + "[PoS Firewall] Reverted fake apply: Requires verified screenshot proof on disk."

        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE opportunities
                SET status=?, updated_at=?, notes=COALESCE(notes || ' | ' || ?, notes)
                WHERE id=?
            """, (new_status, now, notes if notes else None, opportunity_id))
            cur.execute("SELECT company_name FROM opportunities WHERE id=?", (opportunity_id,))
            row = cur.fetchone()
            company_name = row["company_name"] if row else "Unknown"
            conn.commit()

        self.record_event(opportunity_id, company_name, f"STATUS_{new_status}", {"notes": notes})

    def mark_applied_verified(
        self,
        opportunity_id: int,
        proof_screenshot_path: str,
        submission_url: str,
        submitted_at: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """Enforces Proof-of-Submission (PoS) Firewall on opportunities."""
        import os
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

        ts = submitted_at or datetime.now().isoformat()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE opportunities
                SET status = 'APPLIED_VERIFIED',
                    proof_screenshot_path = ?,
                    submission_url = ?,
                    updated_at = ?,
                    notes = COALESCE(notes || ' | ' || ?, ?)
                WHERE id = ?
            """, (
                proof_screenshot_path,
                submission_url,
                ts,
                notes or f"PoS Verified submission at {submission_url}",
                notes or f"PoS Verified submission at {submission_url}",
                opportunity_id
            ))
            cur.execute("SELECT company_name FROM opportunities WHERE id = ?", (opportunity_id,))
            row = cur.fetchone()
            comp = row["company_name"] if row else "Unknown"
            conn.commit()

        self.record_event(opportunity_id, comp, "STATUS_APPLIED_VERIFIED", {
            "proof_screenshot_path": proof_screenshot_path,
            "submission_url": submission_url,
            "submitted_at": ts
        })
        return True

    def mark_needs_human_click(
        self,
        opportunity_id: int,
        reason: str,
        screenshot_path: Optional[str] = None
    ) -> bool:
        """Logs bot barrier or unconfirmed submission without faking applied status."""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE opportunities
                SET status = 'NEEDS_HUMAN_CLICK',
                    updated_at = ?,
                    proof_screenshot_path = COALESCE(?, proof_screenshot_path),
                    notes = COALESCE(notes || ' | NEEDS_HUMAN_CLICK: ' || ?, ?)
                WHERE id = ?
            """, (now, screenshot_path, reason, reason, opportunity_id))
            cur.execute("SELECT company_name FROM opportunities WHERE id = ?", (opportunity_id,))
            row = cur.fetchone()
            comp = row["company_name"] if row else "Unknown"
            conn.commit()

        self.record_event(opportunity_id, comp, "STATUS_NEEDS_HUMAN_CLICK", {"reason": reason})
        return True

    def get_funnel_summary(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cur = conn.cursor()

            # Total counts
            cur.execute("SELECT COUNT(*) FROM signals")
            total_signals = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM opportunities")
            total_opps = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM opportunities WHERE score >= 70")
            qualified_opps = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM outreach_logs WHERE status in ('SENT', 'DISPATCHED')")
            dms_sent = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM outreach_logs WHERE response_received = 1")
            replies = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM opportunities WHERE status = 'SCREENING_SCHEDULED'")
            screenings = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM opportunities WHERE status = 'OFFER'")
            offers = cur.fetchone()[0]

            return {
                "signals_captured": total_signals,
                "opportunities_identified": total_opps,
                "qualified_opportunities": qualified_opps,
                "outreach_sent": dms_sent,
                "responses_received": replies,
                "screening_calls": screenings,
                "offers_received": offers,
                "response_rate_pct": round((replies / dms_sent * 100), 1) if dms_sent > 0 else 0.0
            }

    def get_pillar_metrics(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    pillar,
                    COUNT(*) as count,
                    AVG(score) as avg_score
                FROM opportunities
                GROUP BY pillar
            """)
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def get_top_opportunities(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM opportunities
                ORDER BY score DESC, created_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(r) for r in cur.fetchall()]

