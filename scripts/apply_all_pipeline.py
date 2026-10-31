"""Comprehensive Batch Application Runner for JobIt.

Applies to all ranked positions (including Executive Intern, Founder's Office,
APM, Product Operations, Supply Chain, and Technical PM) meeting candidate criteria.
Generates tailored 1-page A4 ATS CVs and outreach drafts for every position.
"""

from __future__ import annotations

import datetime
import logging
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.profile_engine import ProfileEngine
from src.scoring_engine import ScoringEngine
from src.scrapers.base_scraper import ScrapedJob
from src.tailor_engine import TailorEngine
from src.outreach_engine import OutreachEngine
from src.tracker_db import TrackerDB

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("batch_applier")


def run_batch_applications(min_score: int = 70):
    db = TrackerDB()
    profile_engine = ProfileEngine()
    scoring_engine = ScoringEngine(profile_engine=profile_engine)
    tailor_engine = TailorEngine(profile_engine=profile_engine)
    outreach_engine = OutreachEngine(profile_engine=profile_engine)

    apps = db.get_all_applications(min_score=min_score)
    # Target applications that are Ranked and have fit_score >= min_score, strictly skipping Founder's Office
    target_apps = []
    for a in apps:
        if a.get("status") != "Ranked" or a.get("fit_score", 0) < min_score:
            continue
        role_lower = a.get("role", "").lower()
        if any(fkw in role_lower for fkw in ["founder", "chief of staff"]):
            db.update_status(a["id"], status="Filtered", notes="Skipped by candidate preference: Founder's Office")
            continue
        target_apps.append(a)

    # Prioritize Executive / Officer / Intern roles first, then by score descending
    def sort_key(app):
        role_lower = app.get("role", "").lower()
        is_exec_intern = any(kw in role_lower for kw in ["executive", "officer", "assistant", "intern"])
        score = app.get("fit_score", 0)
        return (1 if is_exec_intern else 0, score)

    target_apps.sort(key=sort_key, reverse=True)

    total_targets = len(target_apps)
    logger.info(f"Identified {total_targets} ranked positions eligible for application (Score >= {min_score}).")

    applied_count = 0
    errors = 0

    for idx, app in enumerate(target_apps, 1):
        job_id = app["id"]
        company = app["company"]
        role = app["role"]
        score = app.get("fit_score", 0)

        logger.info(f"[{idx}/{total_targets}] Applying: Job #{job_id} | {role} at {company} (Score: {score})")

        try:
            job = ScrapedJob(
                company=company,
                role=role,
                job_url=app["job_url"],
                source=app.get("source", "Web"),
                location=app.get("location", "Mumbai"),
                experience_years=app.get("experience_years", ""),
                salary=app.get("salary", ""),
                raw_description=app.get("raw_description", ""),
                hr_name=app.get("hr_name"),
                hr_email=app.get("hr_email"),
            )

            # Evaluate fit
            eval_result = scoring_engine.evaluate(job)

            # Tailor 1-page CV
            outputs = tailor_engine.tailor(job, eval_result)
            pdf_path = outputs["pdf_path"]

            # Generate outreach draft
            outreach = outreach_engine.process_outreach(job, pdf_path=pdf_path, dry_run=True)
            contact = outreach["draft"]["contact"]

            now_str = datetime.datetime.now().isoformat()
            db.update_status(
                job_id=job_id,
                status="Applied",
                notes=f"Auto-applied in batch on {now_str[:10]}",
                tailored_cv_path=pdf_path,
                applied_date=now_str
            )
            db.update_outreach_contact(
                job_id=job_id,
                hr_name=contact["name"],
                hr_email=contact["primary_email"]
            )
            applied_count += 1
        except Exception as e:
            logger.error(f"Error applying for job #{job_id} ({role} at {company}): {e}")
            errors += 1

    logger.info(f"Batch application run complete! Successfully applied: {applied_count}, Errors: {errors}")


if __name__ == "__main__":
    score_threshold = int(sys.argv[1]) if len(sys.argv) > 1 else 70
    run_batch_applications(min_score=score_threshold)

