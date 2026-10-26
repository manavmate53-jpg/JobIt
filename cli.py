#!/usr/bin/env python3
"""JobIt CLI: Production-grade automated job hunting, resume tailoring, and outreach tracker."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from src.profile_engine import ProfileEngine
from src.scrapers import scrape_portals
from src.scrapers.base_scraper import ScrapedJob
from src.scoring_engine import ScoringEngine
from src.tailor_engine import TailorEngine
from src.outreach_engine import OutreachEngine
from src.tracker_db import TrackerDB

console = Console()
db = TrackerDB()
profile_engine = ProfileEngine()
scoring_engine = ScoringEngine(profile_engine=profile_engine)
tailor_engine = TailorEngine(profile_engine=profile_engine)
outreach_engine = OutreachEngine(profile_engine=profile_engine)


@click.group()
def cli():
    """JobIt: Local-First Automated Job Hunting & Application System."""
    pass


@cli.command("scrape")
@click.option("--portal", default="all", type=click.Choice(["linkedin", "naukri", "all"], case_sensitive=False), help="Target job portal")
@click.option("--keywords", default="Product Manager", help="Search keywords (e.g. 'Associate Product Manager', 'Product Manager')")
@click.option("--location", default="Mumbai", help="Target location (e.g. 'Mumbai', 'Remote')")
@click.option("--limit", default=20, type=int, help="Maximum number of jobs to fetch")
def scrape_cmd(portal: str, keywords: str, location: str, limit: int):
    """Scrapes job postings from LinkedIn and/or Naukri and computes initial fit scores."""
    console.print(Panel(
        f"[bold cyan]Scanning Job Portals[/bold cyan]\n"
        f"Portal: [yellow]{portal.upper()}[/yellow] | Keywords: [green]'{keywords}'[/green] | Location: [magenta]{location}[/magenta] | Limit: {limit}",
        box=box.ROUNDED
    ))

    with console.status("[bold green]Executing scrapers and filtering domain traps...[/bold green]"):
        scraped_jobs = scrape_portals(portal=portal, keywords=keywords, location=location, limit=limit)

    if not scraped_jobs:
        console.print("[yellow]No jobs found matching criteria.[/yellow]")
        return

    table = Table(title="Scraped & Evaluated Postings", box=box.ROUNDED)
    table.add_column("ID", style="dim", width=4)
    table.add_column("Company", style="bold white")
    table.add_column("Role", style="cyan")
    table.add_column("Source", style="blue", width=9)
    table.add_column("Score", justify="center", width=7)
    table.add_column("Decision", justify="center", width=10)
    table.add_column("Status", width=10)

    saved_count = 0
    apply_count = 0

    for job in scraped_jobs:
        eval_result = scoring_engine.evaluate(job)
        job_id = db.upsert_job(job, eval_result)
        saved_count += 1

        score_color = "green" if eval_result.fit_score >= 75 else ("yellow" if eval_result.fit_score >= 55 else "red")
        decision_style = "bold green" if eval_result.decision == "APPLY" else ("bold yellow" if eval_result.decision == "CONSIDER" else "dim red")

        if eval_result.decision == "APPLY":
            apply_count += 1

        table.add_row(
            str(job_id),
            job.company[:24],
            job.role[:32],
            job.source,
            f"[{score_color}]{eval_result.fit_score}[/{score_color}]",
            f"[{decision_style}]{eval_result.decision}[/{decision_style}]",
            "Filtered" if eval_result.is_filtered_out else "Ranked"
        )

    console.print(table)
    console.print(f"[bold green]Done![/bold green] Processed {saved_count} postings. [bold green]{apply_count}[/bold green] marked [bold green]APPLY[/bold green] (score 75+).")


@cli.command("rank")
@click.option("--min-score", default=0, type=int, help="Filter listings by minimum fit score")
@click.option("--decision", default=None, type=click.Choice(["APPLY", "CONSIDER", "SKIP"], case_sensitive=False), help="Filter by decision")
def rank_cmd(min_score: int, decision: str):
    """Reranks and displays all stored jobs with color-coded fit scores."""
    apps = db.get_all_applications(min_score=min_score)
    if decision:
        apps = [a for a in apps if a.get("decision", "").upper() == decision.upper()]

    if not apps:
        console.print("[yellow]No applications match the current filter criteria.[/yellow]")
        return

    table = Table(title="Candidate Fit Ranking Pipeline", box=box.ROUNDED)
    table.add_column("ID", style="bold dim", justify="right")
    table.add_column("Company", style="bold white")
    table.add_column("Role", style="cyan")
    table.add_column("Source", style="blue")
    table.add_column("Location", style="magenta")
    table.add_column("Score", justify="center")
    table.add_column("Decision", justify="center")
    table.add_column("Status", style="yellow")

    for a in apps:
        score = a.get("fit_score", 0)
        dec = a.get("decision", "PENDING")
        score_color = "green" if score >= 75 else ("yellow" if score >= 55 else "red")
        decision_style = "bold green" if dec == "APPLY" else ("bold yellow" if dec == "CONSIDER" else "dim red")

        table.add_row(
            str(a["id"]),
            a["company"],
            a["role"],
            a.get("source", "Web"),
            a.get("location", "Mumbai"),
            f"[{score_color}]{score}[/{score_color}]",
            f"[{decision_style}]{dec}[/{decision_style}]",
            a.get("status", "Scraped")
        )

    console.print(table)


@cli.command("view")
@click.argument("job_id", type=int)
def view_cmd(job_id: int):
    """Displays detailed gap analysis, matching skills, and pitch angle for a job."""
    app = db.get_job_by_id(job_id)
    if not app:
        console.print(f"[bold red]Error:[/bold red] Job #{job_id} not found.")
        return

    skills = app.get("matching_skills") or []
    skills_text = ", ".join(skills) if isinstance(skills, list) else str(skills)

    console.print(Panel(
        f"[bold white]{app['role']}[/bold white] at [bold cyan]{app['company']}[/bold cyan]\n"
        f"Location: {app.get('location')} | Source: {app.get('source')} | Status: [yellow]{app.get('status')}[/yellow]\n"
        f"URL: [link={app['job_url']}]{app['job_url']}[/link]\n\n"
        f"[bold]Fit Score:[/bold] [green]{app.get('fit_score')}/100[/green] | [bold]Decision:[/bold] {app.get('decision')}\n"
        f"[bold]Matching Competencies:[/bold] {skills_text}\n\n"
        f"[bold yellow]Gap Analysis:[/bold yellow]\n{app.get('gap_analysis')}\n\n"
        f"[bold green]Recommended Angle:[/bold green]\n{app.get('recommended_angle')}\n\n"
        f"[bold]Recruiter Contact:[/bold] {app.get('hr_name') or 'Not Found'} ({app.get('hr_email') or 'Pending Permutation'})\n"
        f"[bold]Tailored CV:[/bold] {app.get('tailored_cv_path') or 'Not generated yet (run: jobit tailor ' + str(job_id) + ')'}",
        title=f"Application #{job_id} Deep Dive",
        box=box.ROUNDED
    ))


@cli.command("tailor")
@click.argument("job_id", type=int)
def tailor_cmd(job_id: int):
    """Auto-generates tailored single-page ATS CV and builder cover letter for a job."""
    app = db.get_job_by_id(job_id)
    if not app:
        console.print(f"[bold red]Error:[/bold red] Job #{job_id} not found in database.")
        return

    job = ScrapedJob(
        company=app["company"],
        role=app["role"],
        job_url=app["job_url"],
        source=app["source"],
        location=app.get("location", "Mumbai"),
        experience_years=app.get("experience_years", ""),
        salary=app.get("salary", ""),
        raw_description=app.get("raw_description", ""),
        hr_name=app.get("hr_name"),
        hr_email=app.get("hr_email"),
    )

    console.print(f"[bold cyan]Tailoring application for {job.role} at {job.company}...[/bold cyan]")

    eval_result = scoring_engine.evaluate(job)

    with console.status("[bold green]Compiling ATS HTML, Markdown, and Single-Page PDF via Playwright...[/bold green]"):
        outputs = tailor_engine.tailor(job, eval_result)

    # Update database record
    db.update_status(job_id, status="Tailored", tailored_cv_path=outputs["pdf_path"])

    ats_rep = outputs.get("ats_report")

    # Render ATS Score Breakdown Table
    ats_table = Table(title=f"ATS Compatibility Report ({ats_rep.overall_score}/100)", box=box.ROUNDED)
    ats_table.add_column("ATS Dimension", style="bold cyan")
    ats_table.add_column("Weight", justify="center", style="dim")
    ats_table.add_column("Sub-Score", justify="center", style="bold white")

    ats_table.add_row("Keyword Match", "40%", f"{ats_rep.sub_scores.get('keyword_match', 0)}%")
    ats_table.add_row("Skills Coverage", "20%", f"{ats_rep.sub_scores.get('skills_coverage', 0)}%")
    ats_table.add_row("Title Match", "15%", f"{ats_rep.sub_scores.get('title_match', 0)}%")
    ats_table.add_row("Section Completeness", "15%", f"{ats_rep.sub_scores.get('section_completeness', 0)}%")
    ats_table.add_row("Date Consistency", "10%", f"{ats_rep.sub_scores.get('date_consistency', 0)}%")

    console.print(ats_table)

    console.print(Panel(
        f"[bold green]Successfully Tailored Application #[/bold green][bold white]{job_id}[/bold white]\n\n"
        f"🎯 [bold]Overall ATS Score:[/bold] [bold green]{ats_rep.overall_score}/100[/bold green] ({ats_rep.title_match_type})\n"
        f"📄 [bold]HTML CV:[/bold] {outputs['html_path']}\n"
        f"📝 [bold]Markdown CV:[/bold] {outputs['md_path']}\n"
        f"🖨️  [bold]Print PDF CV (Single-Page A4):[/bold] {outputs['pdf_path']}\n"
        f"📊 [bold]ATS Match Report (JSON):[/bold] {outputs['ats_report_path']}\n"
        f"✉️  [bold]Cover Letter (TXT):[/bold] {outputs['cover_letter_txt']}\n"
        f"📋 [bold]Cover Letter (MD):[/bold] {outputs['cover_letter_md']}",
        box=box.ROUNDED
    ))


@cli.command("match")
@click.argument("job_id", type=int)
def match_cmd(job_id: int):
    """Resume-Matcher style ATS compatibility check without re-exporting files."""
    app = db.get_job_by_id(job_id)
    if not app:
        console.print(f"[bold red]Error:[/bold red] Job #{job_id} not found.")
        return

    job = ScrapedJob(
        company=app["company"],
        role=app["role"],
        job_url=app["job_url"],
        source=app["source"],
        location=app.get("location", "Mumbai"),
        raw_description=app.get("raw_description", "")
    )

    ctx = profile_engine.get_template_context()
    resume_plain = f"{ctx['name']} {ctx['summary']} {json.dumps(ctx['skills'])} {json.dumps(ctx['work_experience'])}"

    from src.services.ats_scorer import ATSScorer
    scorer = ATSScorer()
    report = scorer.evaluate(
        resume_text=resume_plain,
        resume_context=ctx,
        job_role=job.role,
        job_description=f"{job.role} {job.raw_description}"
    )

    table = Table(title=f"Resume Matcher Card: {job.role} at {job.company}", box=box.ROUNDED)
    table.add_column("ATS Dimension", style="bold cyan")
    table.add_column("Weight", justify="center", style="dim")
    table.add_column("Score", justify="center", style="bold white")

    table.add_row("Keyword Match", "40%", f"{report.sub_scores.get('keyword_match', 0)}%")
    table.add_row("Skills Coverage", "20%", f"{report.sub_scores.get('skills_coverage', 0)}%")
    table.add_row("Title Match", "15%", f"{report.sub_scores.get('title_match', 0)}%")
    table.add_row("Section Completeness", "15%", f"{report.sub_scores.get('section_completeness', 0)}%")
    table.add_row("Date Consistency", "10%", f"{report.sub_scores.get('date_consistency', 0)}%")

    console.print(table)

    matched_sample = ", ".join(report.matched_keywords[:6]) if report.matched_keywords else "None"
    missing_sample = ", ".join(report.missing_keywords[:6]) if report.missing_keywords else "None"

    console.print(Panel(
        f"[bold]Overall Score:[/bold] [bold green]{report.overall_score}/100[/bold green] | [bold]Title Match:[/bold] {report.title_match_type}\n\n"
        f"[bold green]Top Matched Keywords:[/bold green]\n{matched_sample}\n\n"
        f"[bold yellow]Missing Opportunity Keywords:[/bold yellow]\n{missing_sample}\n\n"
        f"[bold]Actionable Recommendations:[/bold]\n" + "\n".join(f"• {s}" for s in report.suggestions),
        title="ATS Scoring Breakdown",
        box=box.ROUNDED
    ))


@cli.command("apply")
@click.argument("job_id", type=int)
@click.option("--notes", default="Applied via JobIt automated pipeline", help="Notes regarding application submission")
def apply_cmd(job_id: int, notes: str):
    """Marks a job as Applied, auto-tailoring CV and drafting recruiter outreach if needed."""
    app = db.get_job_by_id(job_id)
    if not app:
        console.print(f"[bold red]Error:[/bold red] Job #{job_id} not found.")
        return

    job = ScrapedJob(
        company=app["company"],
        role=app["role"],
        job_url=app["job_url"],
        source=app["source"],
        location=app.get("location", "Mumbai"),
        raw_description=app.get("raw_description", ""),
        hr_name=app.get("hr_name"),
        hr_email=app.get("hr_email"),
    )

    pdf_cv = app.get("tailored_cv_path")

    # If CV not yet tailored, tailor it now
    if not pdf_cv or not os.path.exists(pdf_cv):
        console.print(f"[bold cyan]Auto-tailoring CV for {job.role} at {job.company}...[/bold cyan]")
        eval_result = scoring_engine.evaluate(job)
        outputs = tailor_engine.tailor(job, eval_result)
        pdf_cv = outputs["pdf_path"]

    # Generate outreach draft for safety
    outreach = outreach_engine.process_outreach(job, pdf_path=pdf_cv, dry_run=True)
    contact = outreach["draft"]["contact"]

    import datetime
    now_str = datetime.datetime.now().isoformat()

    db.update_status(
        job_id=job_id,
        status="Applied",
        notes=notes,
        tailored_cv_path=pdf_cv,
        applied_date=now_str
    )
    db.update_outreach_contact(
        job_id=job_id,
        hr_name=contact["name"],
        hr_email=contact["primary_email"]
    )

    console.print(Panel(
        f"[bold green]Application Successfully Recorded for Job #[/bold green][bold white]{job_id}[/bold white]\n\n"
        f"🏢 [bold]Company:[/bold] {job.company}\n"
        f"💼 [bold]Role:[/bold] {job.role} ({job.location})\n"
        f"📊 [bold]Fit Score:[/bold] [bold green]{app.get('fit_score')}/100[/bold green] | [bold]Status:[/bold] [bold green]APPLIED[/bold green]\n"
        f"🌐 [bold]Application Portal URL:[/bold] [link={job.job_url}]{job.job_url}[/link]\n\n"
        f"📄 [bold]Tailored A4 PDF Resume:[/bold] {pdf_cv}\n"
        f"👤 [bold]Target Recruiter:[/bold] {contact['name']} <{contact['primary_email']}>\n"
        f"💬 [bold]LinkedIn Note Drafted:[/bold] \"{outreach['draft']['linkedin_note']}\"\n"
        f"💾 [bold]Outreach Draft Path:[/bold] {outreach['draft_txt_path']}",
        title="Application Confirmed",
        box=box.ROUNDED
    ))


@cli.command("outreach")
@click.argument("job_id", type=int)
@click.option("--dry-run/--send", default=True, help="Deterministic safe dry-run (default: true) vs live SMTP dispatch")
def outreach_cmd(job_id: int, dry_run: bool):
    """Drafts or sends recruiter outreach (LinkedIn connection note + Cold Email)."""
    app = db.get_job_by_id(job_id)
    if not app:
        console.print(f"[bold red]Error:[/bold red] Job #{job_id} not found.")
        return

    job = ScrapedJob(
        company=app["company"],
        role=app["role"],
        job_url=app["job_url"],
        source=app["source"],
        location=app.get("location", "Mumbai"),
        hr_name=app.get("hr_name"),
        hr_email=app.get("hr_email"),
        raw_description=app.get("raw_description", "")
    )

    pdf_cv = app.get("tailored_cv_path")

    with console.status("[bold green]Enriching contact, checking DNS MX records, and formulating outreach drafts...[/bold green]"):
        result = outreach_engine.process_outreach(job, pdf_path=pdf_cv, dry_run=dry_run)

    contact = result["draft"]["contact"]
    db.update_outreach_contact(
        job_id=job_id,
        hr_name=contact["name"],
        hr_email=contact["primary_email"],
        status="Emailed" if not dry_run and result["dispatched"] else "Drafted"
    )

    if dry_run:
        console.print(Panel(
            f"[bold yellow]SAFE DRY-RUN ACTIVE: No emails were sent.[/bold yellow]\n\n"
            f"🎯 [bold]Target Recruiter:[/bold] {contact['name']} <{contact['primary_email']}>\n"
            f"🌐 [bold]Domain:[/bold] {contact['domain']} | [bold]MX Valid:[/bold] {contact['mx_valid']}\n"
            f"🔄 [bold]Permutations:[/bold] {', '.join(contact['permutations'][:3])}\n\n"
            f"💬 [bold cyan]LinkedIn Note ({result['draft']['linkedin_note_chars']} chars - strictly under 300):[/bold cyan]\n"
            f"\"{result['draft']['linkedin_note']}\"\n\n"
            f"📧 [bold cyan]Cold Email Subject:[/bold cyan] {result['draft']['email_subject']}\n"
            f"📎 [bold cyan]Attached PDF:[/bold cyan] {pdf_cv or 'None'}\n\n"
            f"💾 [bold green]Draft Saved For Inspection:[/bold green] {result['draft_txt_path']}\n"
            f"[dim]To send live via SMTP, re-run with: jobit outreach {job_id} --send[/dim]",
            title="Outreach Formulation Result",
            box=box.ROUNDED
        ))
    else:
        if result["dispatched"]:
            console.print(f"[bold green]Success![/bold green] Email dispatched to {contact['primary_email']}.")
        else:
            console.print(f"[bold red]Dispatch failed:[/bold red] {result.get('smtp_details', {}).get('error')}")


@cli.command("login")
@click.option("--portal", default="naukri", type=click.Choice(["naukri", "linkedin"], case_sensitive=False), help="Portal to authenticate with")
def login_cmd(portal: str):
    """Opens visible browser to log into Naukri or LinkedIn once; saves persistent session cookies."""
    from src.web_applier import PortalWebApplier
    applier = PortalWebApplier()
    applier.login_interactively(portal=portal)


@cli.command("web-apply")
@click.argument("job_id", type=int)
@click.option("--dry-run/--submit", default=True, help="Stop at preview/modal (default) vs submit final application")
@click.option("--visible/--headless", default=True, help="Launch visible browser window or run headless")
def web_apply_cmd(job_id: int, dry_run: bool, visible: bool):
    """Automates web application submission on Naukri or LinkedIn using Playwright."""
    app = db.get_job_by_id(job_id)
    if not app:
        console.print(f"[bold red]Error:[/bold red] Job #{job_id} not found.")
        return

    job = ScrapedJob(
        company=app["company"],
        role=app["role"],
        job_url=app["job_url"],
        source=app["source"],
        location=app.get("location", "Mumbai"),
        raw_description=app.get("raw_description", ""),
        hr_name=app.get("hr_name"),
        hr_email=app.get("hr_email"),
    )

    pdf_cv = app.get("tailored_cv_path")
    if not pdf_cv or not os.path.exists(pdf_cv):
        console.print(f"[bold cyan]Auto-tailoring CV first for {job.role} at {job.company}...[/bold cyan]")
        eval_result = scoring_engine.evaluate(job)
        outputs = tailor_engine.tailor(job, eval_result)
        pdf_cv = outputs["pdf_path"]
        db.update_status(job_id, status="Tailored", tailored_cv_path=pdf_cv)

    from src.web_applier import PortalWebApplier
    applier = PortalWebApplier()

    with console.status(f"[bold green]Automating web application on {job.source}...[/bold green]"):
        res = applier.apply(job, pdf_path=pdf_cv, dry_run=dry_run, headless=not visible)

    if res.get("status") == "LOGIN_REQUIRED":
        console.print(Panel(
            f"[bold red]Authentication Required[/bold red]\n\n"
            f"You need to log into {job.source} once so Playwright can use your session.\n"
            f"Run: [bold yellow]python3 cli.py login --portal {'naukri' if 'naukri' in job.source.lower() else 'linkedin'}[/bold yellow]\n"
            f"Screenshot captured: {res.get('screenshot_path')}",
            box=box.ROUNDED
        ))
        return

    if res.get("success"):
        if not dry_run and res.get("status") == "SUBMITTED":
            import datetime
            db.update_status(job_id, status="Applied", applied_date=datetime.datetime.now().isoformat())
        console.print(Panel(
            f"[bold green]Web Application Status: {res.get('status')}[/bold green]\n\n"
            f"🏢 [bold]Company:[/bold] {job.company} | [bold]Role:[/bold] {job.role}\n"
            f"🌐 [bold]Portal:[/bold] {job.source} ([link={job.job_url}]{job.job_url}[/link])\n"
            f"📄 [bold]Uploaded PDF Resume:[/bold] {pdf_cv}\n"
            f"📸 [bold]Proof Screenshot:[/bold] {res.get('screenshot_path')}\n\n"
            f"[italic]{res.get('message')}[/italic]",
            title="Browser Automation Result",
            box=box.ROUNDED
        ))
    else:
        console.print(f"[bold red]Web apply notice:[/bold red] {res.get('message')}\nScreenshot: {res.get('screenshot_path')}")


@cli.command("status")
def status_cmd():
    """Renders clean summary table of active pipeline stages and follow-up alerts."""
    stats = db.get_pipeline_stats()
    alerts = db.get_follow_up_alerts(days_threshold=4)

    # Pipeline stats table
    table = Table(title="JobIt Pipeline Overview", box=box.ROUNDED)
    table.add_column("Pipeline Stage", style="bold cyan")
    table.add_column("Count", justify="center", style="bold white")

    for stage, count in stats.items():
        table.add_row(stage, str(count))

    console.print(table)

    # Alerts table if any
    if alerts:
        alert_table = Table(title="⚠️  Follow-up Alerts (Applied/Emailed > 4 Days Ago)", box=box.ROUNDED)
        alert_table.add_column("ID", width=4)
        alert_table.add_column("Company", style="bold white")
        alert_table.add_column("Role", style="cyan")
        alert_table.add_column("Last Action", style="yellow")
        alert_table.add_column("Contact", style="magenta")

        for a in alerts:
            alert_table.add_row(
                str(a["id"]),
                a["company"],
                a["role"],
                a.get("last_action_date", "")[:10],
                f"{a.get('hr_name')} <{a.get('hr_email')}>"
            )
        console.print(alert_table)
    else:
        console.print("[dim]No overdue follow-up alerts pending.[/dim]")


@cli.command("run-all")
@click.option("--limit", default=10, type=int, help="Number of jobs to process")
def run_all_cmd(limit: int):
    """End-to-end automated pipeline: Scrapes, scores, tailors APPLY jobs, and drafts outreach."""
    console.print(Panel(
        f"[bold cyan]Executing Full End-to-End Autonomous Pipeline[/bold cyan]\n"
        f"Candidate: [bold]Manav Mate[/bold] (Product Manager | 0-3 yrs)\n"
        f"Limit: {limit} listings across LinkedIn & Naukri",
        box=box.ROUNDED
    ))

    # 1. Scrape
    with console.status("[bold green]Scraping multi-portal jobs...[/bold green]"):
        jobs = scrape_portals(portal="all", keywords="Product Manager", location="Mumbai", limit=limit)

    console.print(f"Scraped {len(jobs)} postings.")

    # 2. Score & Filter
    apply_jobs = []
    with console.status("[bold green]Filtering domain traps and computing scores...[/bold green]"):
        for job in jobs:
            eval_res = scoring_engine.evaluate(job)
            job_id = db.upsert_job(job, eval_res)
            if eval_res.decision == "APPLY":
                apply_jobs.append((job_id, job, eval_res))

    console.print(f"Found [bold green]{len(apply_jobs)}[/bold green] positions marked [bold green]APPLY[/bold green] (score 75+).")

    # 3. Tailor & Draft Outreach for APPLY jobs
    for job_id, job, eval_res in apply_jobs:
        console.print(f"\n[bold cyan]Processing #{job_id}: {job.role} at {job.company}[/bold cyan]")
        with console.status("Generating tailored CV and Cover Letter..."):
            outputs = tailor_engine.tailor(job, eval_res)
            db.update_status(job_id, status="Tailored", tailored_cv_path=outputs["pdf_path"])

        with console.status("Formulating recruiter outreach and checking MX records..."):
            outreach = outreach_engine.process_outreach(job, pdf_path=outputs["pdf_path"], dry_run=True)
            db.update_outreach_contact(
                job_id=job_id,
                hr_name=outreach["draft"]["contact"]["name"],
                hr_email=outreach["draft"]["contact"]["primary_email"],
                status="Drafted"
            )

        console.print(f"  ✓ Single-page PDF CV: {outputs['pdf_path']}")
        console.print(f"  ✓ Cover letter: {outputs['cover_letter_txt']}")
        console.print(f"  ✓ Outreach draft: {outreach['draft_txt_path']}")

    console.print("\n[bold green]Pipeline execution complete![/bold green] Run [bold yellow]jobit status[/bold yellow] or [bold yellow]jobit rank[/bold yellow] to inspect.")


@cli.command("auto-pilot")
@click.option("--locations", default="Mumbai,Remote Worldwide", help="Comma-separated target locations (e.g. 'Mumbai,Remote Worldwide')")
@click.option("--limit-per-query", default=15, type=int, help="Limit per keyword-location scan")
@click.option("--min-score", default=70, type=int, help="Minimum fit score threshold to trigger auto-tailoring and application (default: 70)")
@click.option("--max-apply", default=30, type=int, help="Maximum number of qualified jobs to auto-tailor and apply")
def auto_pilot_cmd(locations: str, limit_per_query: int, min_score: int, max_apply: int):
    """High-throughput autonomous pipeline: Scrapes Mumbai and Remote jobs worldwide, filters traps, scores fit, auto-tailors CVs, and records applications."""
    target_locations = [loc.strip() for loc in locations.split(",") if loc.strip()]
    target_roles = [
        "Associate Product Manager",
        "Junior Product Manager",
        "AI Product Manager",
        "Product Operations",
        "Product Manager"
    ]

    console.print(Panel(
        f"[bold cyan]⚡ JobIt Autonomous Auto-Pilot Engine[/bold cyan]\n"
        f"Locations: [magenta]{', '.join(target_locations)}[/magenta] | Roles: [green]{len(target_roles)} search vectors[/green]\n"
        f"Target CTC: [yellow]₹11 - ₹16 LPA (or USD remote equivalent)[/yellow] | Min Fit Score: [green]{min_score}+[/green]\n"
        f"Filter: [red]Anti-manufacturing, pharma, NBFC traps active[/red]",
        box=box.ROUNDED
    ))

    total_scraped = 0
    total_evaluated = 0
    total_applied = 0
    filtered_traps = 0

    apply_queue = []

    # 1. First, check existing unapplied jobs in DB meeting the min_score
    existing_unapplied = db.get_all_applications(min_score=min_score)
    for record in existing_unapplied:
        if record.get("status") not in ("Applied", "Emailed", "Filtered"):
            from src.scoring_engine import EvaluationResult
            from src.scrapers.base_scraper import ScrapedJob
            job_obj = ScrapedJob(
                company=record["company"],
                role=record["role"],
                job_url=record["job_url"],
                source=record["source"],
                location=record.get("location", "Mumbai"),
                experience_years=record.get("experience_years", ""),
                salary=record.get("salary", ""),
                raw_description=record.get("raw_description", "")
            )
            eval_res = scoring_engine.evaluate(job_obj)
            if not eval_res.is_filtered_out and (eval_res.fit_score >= min_score or eval_res.decision == "APPLY"):
                apply_queue.append((record["id"], job_obj, eval_res))

    console.print(f"[bold cyan]Checked local pipeline database:[/bold cyan] Found [bold green]{len(apply_queue)}[/bold green] existing unapplied jobs with score >= {min_score}.")

    # 2. Scrape live portals (LinkedIn, Naukri, RemoteOK, Jobicy, Himalayas)
    all_jobs_scraped = []
    for loc in target_locations:
        for role in target_roles:
            console.print(f"[dim]Scanning [cyan]{role}[/cyan] in [magenta]{loc}[/magenta]...[/dim]")
            try:
                batch = scrape_portals(portal="all", keywords=role, location=loc, limit=limit_per_query)
                for j in batch:
                    if not any(existing.job_url == j.job_url for existing in all_jobs_scraped):
                        all_jobs_scraped.append(j)
            except Exception as e:
                console.print(f"[dim yellow]Warning scanning {role} in {loc}: {e}[/dim yellow]")

    total_scraped = len(all_jobs_scraped)
    console.print(f"\n[bold green]Found {total_scraped} postings across sources.[/bold green] Evaluating candidate fit...\n")

    for job in all_jobs_scraped:
        total_evaluated += 1
        eval_res = scoring_engine.evaluate(job)

        if eval_res.is_filtered_out:
            filtered_traps += 1
            db.upsert_job(job, eval_res, status="Filtered")
            continue

        existing_record = db.get_job_by_url(job.job_url)
        # If already applied, don't re-apply
        if existing_record and existing_record.get("status") in ("Applied", "Emailed"):
            continue

        job_id = db.upsert_job(job, eval_res)
        if eval_res.fit_score >= min_score or eval_res.decision == "APPLY":
            if not any(qid == job_id for qid, _, _ in apply_queue):
                apply_queue.append((job_id, job, eval_res))

    console.print(f"Evaluated {total_evaluated} new jobs. [bold red]{filtered_traps}[/bold red] discarded by negative traps. Total queued for application: [bold green]{len(apply_queue)}[/bold green] (score {min_score}+).\n")

    # Apply to top qualified jobs up to max_apply
    for job_id, job, eval_res in apply_queue[:max_apply]:
        console.print(f"[bold cyan]Applying to Job #{job_id}: {job.role} at {job.company} ({job.location})[/bold cyan]")
        
        # 1. Tailor single-page A4 PDF resume
        outputs = tailor_engine.tailor(job, eval_res)
        pdf_path = outputs["pdf_path"]

        # 2. Formulate recruiter outreach & MX check
        outreach = outreach_engine.process_outreach(job, pdf_path=pdf_path, dry_run=True)
        contact = outreach["draft"]["contact"]

        # 3. Record Application
        import datetime
        now_str = datetime.datetime.now().isoformat()
        db.update_status(
            job_id=job_id,
            status="Applied",
            notes=f"Auto-applied via Auto-Pilot on {now_str[:10]}",
            tailored_cv_path=pdf_path,
            applied_date=now_str
        )
        db.update_outreach_contact(
            job_id=job_id,
            hr_name=contact["name"],
            hr_email=contact["primary_email"]
        )

        total_applied += 1
        console.print(f"  ✓ Tailored Single-Page PDF: {pdf_path}")
        console.print(f"  ✓ ATS Compatibility: {outputs['ats_score']}/100")
        console.print(f"  ✓ Recruiter Verified: {contact['name']} <{contact['primary_email']}> (MX: {contact['mx_valid']})")
        console.print(f"  ✓ Status Updated: [bold green]APPLIED[/bold green]\n")

    console.print(Panel(
        f"[bold green]Auto-Pilot Run Complete![/bold green]\n\n"
        f"📊 [bold]Unique Postings Scanned:[/bold] {total_scraped}\n"
        f"🛡️  [bold]Domain Traps Filtered Out:[/bold] {filtered_traps}\n"
        f"🎯 [bold]Newly Tailored & Applied:[/bold] {total_applied}\n"
        f"📈 [bold]Total Applied Pipeline:[/bold] {db.get_pipeline_stats().get('Applied', 0)} jobs",
        title="Execution Summary",
        box=box.ROUNDED
    ))


@cli.command("dashboard")
@click.option("--port", default=5000, type=int, help="Port to run local web dashboard on")
def dashboard_cmd(port: int):
    """Launches the lightweight local-first web dashboard."""
    from src.dashboard import run_dashboard
    run_dashboard(port=port)


if __name__ == "__main__":
    cli()
