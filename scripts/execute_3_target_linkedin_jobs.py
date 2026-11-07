#!/usr/bin/env python3
"""
JobIt - Autonomous Application & Outreach Dispatcher for 3 Specific Target LinkedIn Roles:
1. BICS - Manager Events (Reports to: Alwin Chettiar)
2. Encompass - Events Specialist
3. BookMyShow - Executive Project Management (Sunburn)
"""

import sys
import os
import re
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path("/Users/manav/.gemini/antigravity-ide/scratch/JobIt")
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")

PDF_PATH = BASE_DIR / "exports" / "resumes" / "Manav_Mate_Event_Management_CV.pdf"
PACK_PATH = BASE_DIR / "exports" / "daily_action_packs" / "2026-11-08_linkedin_target_jobs.md"
DB_V2_PATH = BASE_DIR / "data" / "jobit_v2.db"
DB_PATH = BASE_DIR / "data" / "jobit.db"

JOBS = [
    {
        "id": 1,
        "company": "BICS",
        "sub_brand": "Proximus Global",
        "role": "Events Manager",
        "location": "Mumbai Metropolitan Region",
        "job_url": "https://www.linkedin.com/jobs/view/4482200554/",
        "platform": "LinkedIn",
        "decision_maker": "Alwin Chettiar (Reporting Hiring Manager / CMO Dept)",
        "fit_score": 98,
        "experience_req": "4–5+ Years",
        "status": "QUEUED_YANG",
        "notes": "Regional marketing events, trade shows, conferences, exhibitions, registrations, logistics, travel, vendor SLAs, POs/budget tracking, branded merchandise. Reports directly to Alwin Chettiar."
    },
    {
        "id": 2,
        "company": "Encompass",
        "sub_brand": "House of Brands (Stoa Paris, SmallBatch) / Geometry Encompass",
        "role": "Events Specialist",
        "location": "Mumbai Metropolitan Region",
        "job_url": "https://www.linkedin.com/jobs/view/4479999036/",
        "platform": "LinkedIn",
        "decision_maker": "Head of Experiential & Brand Events",
        "fit_score": 96,
        "experience_req": "2–4 Years",
        "status": "QUEUED_YANG",
        "notes": "Intimate & high-touch brand events, launches, community evenings, founder dinners, pop-ups, partner showcases, venue, vendors, run of show across cities."
    },
    {
        "id": 3,
        "company": "BookMyShow",
        "sub_brand": "Big Tree Entertainment / Sunburn Festival",
        "role": "Executive - Project Management (Sunburn)",
        "location": "Mumbai, Maharashtra, India",
        "job_url": "https://www.linkedin.com/jobs/view/4478100584/",
        "platform": "LinkedIn",
        "decision_maker": "Sunburn Festival Operations & Live Events Head",
        "fit_score": 97,
        "experience_req": "2–5 Years",
        "status": "QUEUED_YANG",
        "notes": "Sunburn Campus, Arena & Festival project management across India. Venue production, artist logistics, college partnerships, crowd flow, vendor SLAs, and budget closure."
    }
]


def generate_linkedin_note(job: dict) -> str:
    """Generates strictly <= 280-char LinkedIn connection note tailored to each role."""
    comp = job["company"]
    if comp == "BICS":
        note = "Hi Alwin, 4+ yrs managing 150-200+ events across Mumbai. Directed ICANN '26 delegate registration & logistics, Tata Mumbai Marathon '26 venue ops & Neurology Summit. Specialize in regional conferences, vendor SLAs, budget tracking & Canva/AI planning. Would love to connect!"
    elif comp == "Encompass":
        note = "Hi, 4+ yrs managing 150-200+ events across 15+ agencies. Executed VIP hospitality at Neurology Summit '26 & Tata Mumbai Marathon '26 venue ops. Specialize in high-touch brand launches, pop-ups, venue mapping & run of show. Would love to connect regarding Encompass!"
    else:  # BookMyShow - Sunburn
        note = "Hi, 4+ yrs managing 150-200+ events across Mumbai. Directed full venue ops & crowd flow for Tata Mumbai Marathon '26 at Mumbai Univ, plus live concerts & festivals. Specialize in on-ground staging, artist logistics & vendor SLAs. Would love to connect for Sunburn PM!"

    assert len(note) <= 280, f"Note exceeds 280 chars: {len(note)} ({note})"
    return note


def generate_cold_dm(job: dict) -> str:
    """Generates targeted cold DM / cover pitch."""
    comp = job["company"]
    role = job["role"]
    dm = job["decision_maker"]

    if comp == "BICS":
        salutation = "Hi Alwin,"
        hook = "Reaching out regarding the Events Manager role at BICS reporting directly to your team."
        context_para = "Having managed 150 to 200+ corporate and high-stakes events in partnership with 15+ premier event agencies across Mumbai, I bring direct end-to-end operational capabilities aligning with BICS's regional trade shows, customer engagement, and conference roadmap."
    elif comp == "Encompass":
        salutation = "Hi,"
        hook = f"Reaching out regarding the Events Specialist role for Encompass's House of Brands."
        context_para = "Having delivered 150 to 200+ events across Mumbai with 15+ agencies, I specialize in translating brand briefs into immaculate, memorable live rooms: founder dinners, product launches, community pop-ups, and partner showcases."
    else:  # BookMyShow - Sunburn
        salutation = "Hi,"
        hook = f"Reaching out regarding the Executive - Project Management role for Sunburn at BookMyShow."
        context_para = "Having executed 150 to 200+ events across Mumbai—ranging from mega-sporting events and live concert venues to high-volume youth activations—I bring battle-tested on-ground production and venue management ready for Sunburn Campus and Arena tours."

    body = f"""{salutation}

{hook}

{context_para}

Key 2026 Marquee Event Executions:
1. Tata Mumbai Marathon 2026: Directed entire venue operations and on-ground production across Mumbai University (zone mapping, production setup, crowd flow control, and real-time crisis management).
2. ICANN 2026 (Global MICE): Managed high-volume international delegate registration and end-to-end on-ground logistics.
3. Neurology Summit Mumbai 2026 (Medical MICE): Handled all 4 core pillars: Registration, Stage Production, Floor Operations, and VIP Hospitality.

Operational & Tool Capabilities:
- End-to-end procurement of custom event supplies, goodies, and merchandise with zero stockout incidents.
- Venue booking and precision floor mapping at premier venues (Jio World Centre, NESCO, Mumbai University, 5-star hotel banquets).
- Catering layout planning, dining crowd management, and technical AV show-time management with zero run-of-show slippage.
- Canva for rapid client pitch decks and signage; AI tools for budgeting drafts and planning schedules.
- PMI CIPM certified (Aug 2026), Saylor Operations Management, Scaler System Design, upGrad Business Analytics, B.Com (University of Mumbai).

Live Proof of Work Simulation:
I built interactive event operational simulations (crew rostering and attendee queue dynamics):
https://manavmate53-jpg.github.io/pm-product-lab/#crewrostering

Screening & Availability:
- Total Experience: 4+ Years in Event Operations & Production
- Current Location: Jogeshwari East, Mumbai (Available On-Site Immediately)
- Notice Period: Immediate / 0 Days
- Current CTC: ₹6,00,000 (6.0 LPA)
- Expected CTC: ₹6,50,000 to ₹7,20,000 (6.5 - 7.2 LPA CTC / ₹45k-₹50k in-hand)
- Flexible with live event dates & travel: Yes

My single-page A4 CV is ready to share. Would love to connect for a 10-minute chat this week.

Warm regards,
Manav Mate
Jogeshwari East, Mumbai 400060
Phone: +91 93246 80491 | Email: manavmate53@gmail.com
LinkedIn: https://www.linkedin.com/in/manav-mate-4a0090226/
"""
    return body


def sync_databases(jobs: list):
    """Logs the 3 target opportunities into SQLite databases."""
    now_iso = datetime.now().isoformat()

    # 1. JobIt v2 DB
    conn_v2 = sqlite3.connect(DB_V2_PATH)
    c_v2 = conn_v2.cursor()

    for j in jobs:
        comp = j["company"]
        role = j["role"]
        pillar = "PILLAR_4_EVENT_OPERATIONS_MICE"
        score = j["fit_score"]
        status = j["status"]
        dm_name = j["decision_maker"]
        notes = f"Platform: {j['platform']} | Req: {j['experience_req']} | URL: {j['job_url']} | {j['notes']}"
        expected_ctc = "₹6.5L - ₹7.2L"
        pdf = str(PDF_PATH)

        c_v2.execute("SELECT id FROM opportunities WHERE company_name = ? AND role_title = ?", (comp, role))
        row = c_v2.fetchone()
        if row:
            opp_id = row[0]
            c_v2.execute("""
                UPDATE opportunities
                SET pillar = ?, score = ?, status = ?, target_dm_name = ?, expected_ctc_quote = ?,
                    tailored_pdf_path = ?, notes = ?, updated_at = ?
                WHERE id = ?
            """, (pillar, score, status, dm_name, expected_ctc, pdf, notes, now_iso, opp_id))
        else:
            c_v2.execute("""
                INSERT INTO opportunities (
                    company_name, role_title, pillar, score, status, target_dm_name,
                    target_dm_title, expected_ctc_quote, tailored_pdf_path, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (comp, role, pillar, score, status, dm_name, "Hiring Manager / Operations", expected_ctc, pdf, notes, now_iso, now_iso))
            opp_id = c_v2.lastrowid

        # Outreach note
        li_note = generate_linkedin_note(j)
        c_v2.execute("""
            INSERT INTO outreach_logs (
                opportunity_id, company_name, channel, touchpoint_type, message_text,
                status, sent_at, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (opp_id, comp, "linkedin", "CONNECT_NOTE", li_note, "QUEUED", now_iso, f"Char count: {len(li_note)}"))

        cold_dm = generate_cold_dm(j)
        c_v2.execute("""
            INSERT INTO outreach_logs (
                opportunity_id, company_name, channel, touchpoint_type, message_text,
                status, sent_at, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (opp_id, comp, "linkedin", "COLD_DM", cold_dm, "QUEUED", now_iso, f"DM Target: {dm_name}"))

    conn_v2.commit()
    conn_v2.close()

    # 2. Legacy JobIt DB
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for j in jobs:
        comp = j["company"]
        role = j["role"]
        job_url = j["job_url"]
        source = j["platform"]
        loc = j["location"]
        exp = j["experience_req"]
        score = j["fit_score"]
        status = "Ranked"
        hr_name = j["decision_maker"]
        pdf = str(PDF_PATH)
        desc = j["notes"]

        c.execute("SELECT id FROM applications WHERE company = ? AND role = ?", (comp, role))
        row = c.fetchone()
        if row:
            c.execute("""
                UPDATE applications
                SET job_url = ?, source = ?, location = ?, experience_years = ?, fit_score = ?,
                    status = ?, tailored_cv_path = ?, hr_name = ?, last_action_date = ?, notes = ?
                WHERE id = ?
            """, (job_url, source, loc, exp, score, status, pdf, hr_name, now_iso, desc, row[0]))
        else:
            c.execute("""
                INSERT INTO applications (
                    company, role, job_url, source, location, experience_years, salary,
                    fit_score, decision, status, tailored_cv_path, hr_name, hr_email,
                    matching_skills, gap_analysis, recommended_angle, raw_description,
                    applied_date, last_action_date, notes, created_at, pillar, lab_builds
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                comp, role, job_url, source, loc, exp, "₹6,50,000 - ₹7,20,000 PA",
                score, "APPLY", status, pdf, hr_name, None,
                json.dumps(["Event Operations & Production", "Corporate MICE & Conferences", "Live Concert & Festival PM", "Canva Pitch Decks", "AI Planning Workflows"]),
                "Direct match for 4+ Years Event Operations & Production candidate profile.",
                "Highlight 150-200+ events, Tata Mumbai Marathon 2026 venue ops, ICANN 2026, and Neurology Summit 2026.",
                desc, None, now_iso, "Auto-processed via Target LinkedIn 3 Jobs pipeline.",
                now_iso, "PILLAR_4_EVENT_OPERATIONS_MICE", "crewrostering"
            ))

    conn.commit()
    conn.close()
    print("[DB SUCCESS] Synced 3 LinkedIn roles into data/jobit_v2.db and data/jobit.db!")


def generate_action_pack_markdown(jobs: list):
    """Generates the targeted Markdown Action Pack."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M IST")

    lines = [
        f"# Target Action Pack: 3 Priority LinkedIn Event Roles",
        f"**Generated**: {now_str} &bull; **Strategic Pillar**: `PILLAR_4_EVENT_OPERATIONS_MICE`",
        f"**Candidate**: Manav Mate &bull; **Tailored CV**: `exports/resumes/Manav_Mate_Event_Management_CV.pdf`",
        f"**Interactive Proof of Work**: [CrewRoster Simulation Engine](https://manavmate53-jpg.github.io/pm-product-lab/#crewrostering)",
        "",
        "---",
        "",
        "## 1. Priority Execution Table",
        "",
        "| # | Target Company | Target Role Title | Location | Fit Score | Status | Quick Links |",
        "| :-: | :--- | :--- | :--- | :-: | :-: | :--- |"
    ]

    for j in jobs:
        comp = j["company"]
        role = j["role"]
        loc = j["location"]
        score = j["fit_score"]
        status = j["status"]
        url = j["job_url"]
        lines.append(f"| **{j['id']}** | **{comp}** | {role} | {loc} | **{score}/100** | `{status}` | [LinkedIn Post]({url}) |")

    lines.extend([
        "",
        "---",
        "",
        "## 2. Auto-Fill Screening Parameters Applied",
        "",
        "- **Total Experience in Event Operations**: 4+ Years (150 to 200+ events across 15+ event management agencies)",
        "- **Current Location**: Jogeshwari East, Mumbai (Available On-Site Immediately)",
        "- **Notice Period**: Immediate / 0 Days",
        "- **Current CTC**: ₹6,00,000 (6.0 LPA)",
        "- **Expected CTC**: ₹6,50,000 to ₹7,20,000 (6.5 - 7.2 LPA CTC / ₹45k - ₹50k in-hand)",
        "- **Flexible with live event dates & travel**: Yes",
        "",
        "---",
        "",
        "## 3. Targeted Decision Maker Packages",
        ""
    ])

    for j in jobs:
        jid = j["id"]
        comp = j["company"]
        role = j["role"]
        score = j["fit_score"]
        loc = j["location"]
        url = j["job_url"]
        dm = j["decision_maker"]
        status = j["status"]
        li_note = generate_linkedin_note(j)
        cold_dm = generate_cold_dm(j)

        if comp == "BICS":
            search_query = "%22Alwin%20Chettiar%22%20%22BICS%22"
        elif comp == "Encompass":
            search_query = "%22Encompass%22%20%22Experiential%22%20OR%20%22Events%22"
        else:
            search_query = "%22BookMyShow%22%20%22Sunburn%22%20OR%20%22Live%20Events%22"

        li_search = f"https://www.linkedin.com/search/results/people/?keywords={search_query}&origin=GLOBAL_SEARCH_HEADER"

        lines.extend([
            f"### #{jid}. {comp} &bull; {role}",
            f"- **Location**: {loc}",
            f"- **Fit Score**: **{score}/100** &bull; **Status**: `{status}`",
            f"- **Target Decision Maker**: {dm}",
            f"- **Direct LinkedIn Job Link**: [View Job Listing]({url})",
            f"- **Direct LinkedIn Search**: [Find {dm} on LinkedIn]({li_search})",
            "",
            f"#### Touchpoint 1: LinkedIn Connection Note ({len(li_note)}/280 chars)",
            "```text",
            li_note,
            "```",
            "",
            f"#### Touchpoint 2: Direct Cold InMail / Cover Note",
            "```text",
            cold_dm.strip(),
            "```",
            "",
            f"#### Touchpoint 3: 4-Day Follow-Up Bump",
            "```text",
            f"Hi, bumping this quickly in case it got buried under your inbox surge. Still very keen to discuss how my 4+ years of on-ground production experience (150-200+ events in Mumbai, Tata Mumbai Marathon '26 venue ops, ICANN '26 logistics) can support {comp}'s event execution calendar. Happy to share a tailored operational plan whenever convenient.",
            "```",
            "",
            "---",
            ""
        ])

    PACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PACK_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[PACK SUCCESS] Generated action pack at {PACK_PATH}")


def main():
    print("=" * 70)
    print("JOBIT: 3 TARGET LINKEDIN EVENT ROLES PIPELINE")
    print("=" * 70)

    sync_databases(JOBS)
    generate_action_pack_markdown(JOBS)

    print("\n" + "=" * 70)
    print("ALL 3 LINKEDIN ROLES SUCCESSFULLY STAGED AND SYNCED!")
    print("=" * 70)


if __name__ == "__main__":
    main()
