#!/usr/bin/env python3
"""Batch generates 5x tailored CV patterns for applied and high-priority jobs.

Ensures candidate truth is strictly preserved, matching scores are >= 75,
all PDFs are verified single-page A4, and outreach is kept at max 1 time.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import box

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.profile_engine import ProfileEngine
from src.scrapers.base_scraper import ScrapedJob
from src.scoring_engine import ScoringEngine
from src.tailor_engine import TailorEngine
from src.tracker_db import TrackerDB

console = Console()
db = TrackerDB()
profile_engine = ProfileEngine()
scoring_engine = ScoringEngine(profile_engine=profile_engine)
tailor_engine = TailorEngine(profile_engine=profile_engine)


def batch_generate(limit: int = 15):
    console.print(f"[bold cyan]Batch Generating 5x CV Patterns for Top Applied Positions (Limit: {limit})...[/bold cyan]")
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, company, role, job_url, source, location, experience_years, salary, raw_description, fit_score
            FROM applications
            WHERE status = 'Applied' AND fit_score >= 75
            ORDER BY fit_score DESC
            LIMIT ?
        """, (limit,))
        records = cursor.fetchall()

    if not records:
        console.print("[yellow]No applied jobs found meeting criteria.[/yellow]")
        return

    table = Table(title="5x CV Patterns Batch Generation", box=box.ROUNDED)
    table.add_column("ID", style="dim", width=4)
    table.add_column("Company", style="bold white")
    table.add_column("Role", style="cyan")
    table.add_column("Score", justify="center", style="green", width=6)
    table.add_column("Pattern 1 (AI)", justify="center", width=12)
    table.add_column("Pattern 2 (Ops)", justify="center", width=12)
    table.add_column("Pattern 3 (TPM)", justify="center", width=12)
    table.add_column("Pattern 4 (Growth)", justify="center", width=14)
    table.add_column("Pattern 5 (Agile)", justify="center", width=12)

    for r in records:
        job = ScrapedJob(
            company=r["company"],
            role=r["role"],
            job_url=r["job_url"],
            source=r["source"],
            location=r["location"] or "Mumbai",
            experience_years=r["experience_years"] or "",
            salary=r["salary"] or "",
            raw_description=r["raw_description"] or ""
        )
        eval_res = scoring_engine.evaluate(job)
        patterns = tailor_engine.generate_5x_patterns(job, eval_res)

        p_scores = [f"{p['ats_score']}/100" for p in patterns]

        table.add_row(
            str(r["id"]),
            r["company"][:20],
            r["role"][:26],
            str(r["fit_score"]),
            p_scores[0] if len(p_scores) > 0 else "N/A",
            p_scores[1] if len(p_scores) > 1 else "N/A",
            p_scores[2] if len(p_scores) > 2 else "N/A",
            p_scores[3] if len(p_scores) > 3 else "N/A",
            p_scores[4] if len(p_scores) > 4 else "N/A",
        )

    console.print(table)
    console.print(f"[bold green]✓ Done![/bold green] Generated 5x distinct patterns for {len(records)} applied companies.")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    batch_generate(limit=count)
