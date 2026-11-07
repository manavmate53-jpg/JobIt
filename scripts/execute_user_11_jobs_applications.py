#!/usr/bin/env python3
"""
JobIt - Autonomous Application & Outreach Dispatcher for User Target 11 Jobs.
Executes live application dispatch, database persistence, and action pack generation.
"""

import sys
import os
import re
import json
import sqlite3
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path("/Users/manav/.gemini/antigravity-ide/scratch/JobIt")
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")

PDF_PATH = BASE_DIR / "exports" / "resumes" / "Manav_Mate_Event_Management_CV.pdf"
PACK_PATH = BASE_DIR / "exports" / "daily_action_packs" / "2026-11-08_target_events_applications.md"
DB_V2_PATH = BASE_DIR / "data" / "jobit_v2.db"
DB_PATH = BASE_DIR / "data" / "jobit.db"

JOBS_DATA = [
    {
        "id": 1,
        "company": "Signpost India Limited",
        "sub_brand": "E-Flag Corp",
        "role": "Event Management (2026)",
        "location": "Mumbai",
        "job_url": "https://signpostindia.com/career/event-management-2026/",
        "platform": "Direct Career / Official Email",
        "channel": "email",
        "recipient_email": "career@signpostindia.com",
        "decision_maker": "Shripad Ashtekar (Founder & MD)",
        "fit_score": 98,
        "experience_req": "2-3 Years",
        "status": "APPLIED_EMAIL",
        "notes": "Large-scale public events, phygital IPs, venue management, stage setup, audio-visual, procurement, budgeting, government protocols."
    },
    {
        "id": 2,
        "company": "Craftworld Events Pvt Ltd",
        "sub_brand": "Craftworld Events",
        "role": "Event and Operations Manager",
        "location": "Mumbai Suburban",
        "job_url": "https://www.naukri.com/job-listings-event-and-operations-manager-craftworld-events-mumbai-suburban-3-to-8-years-021126013957?src=simJobDeskACP&sid=17940788985165759&xp=1&px=1",
        "platform": "Naukri",
        "channel": "naukri_apply",
        "recipient_email": None,
        "decision_maker": "Manoj Gopalani / Neha Seth (Leadership & Operations)",
        "fit_score": 96,
        "experience_req": "3-8 Years",
        "status": "APPLIED_PORTAL",
        "notes": "On-ground execution, production, logistics, vendor coordination, manpower management, budget control across experiential/corporate events."
    },
    {
        "id": 3,
        "company": "Sarvysampanna System Solutions",
        "sub_brand": "Sarvysampanna Systems",
        "role": "Corporate Event Planner",
        "location": "Mumbai (All Areas)",
        "job_url": "https://www.naukri.com/job-listings-corporate-event-planner-sarvysampanna-system-solutions-mumbai-all-areas-2-to-6-years-231026033513?src=simJobDeskACP&sid=17940788985165759&xp=2&px=1",
        "platform": "Naukri",
        "channel": "naukri_apply",
        "recipient_email": None,
        "decision_maker": "Talent Acquisition Lead",
        "fit_score": 92,
        "experience_req": "2-6 Years",
        "status": "APPLIED_PORTAL",
        "notes": "Corporate events, conferences, venue coordination, delegate logistics, hospitality management."
    },
    {
        "id": 4,
        "company": "Mercury Travels",
        "sub_brand": "EbixCash Travel & MICE",
        "role": "MICE & Corporate Event Project Executive",
        "location": "Mumbai (Lower Parel / Fort)",
        "job_url": "https://www.mercurytravels.co.in/about-us/careers",
        "platform": "Direct Career / Official Email",
        "channel": "email",
        "recipient_email": "hr@mercurytravels.in",
        "decision_maker": "Head of MICE & Corporate Operations",
        "fit_score": 96,
        "experience_req": "2-5 Years",
        "status": "APPLIED_EMAIL",
        "notes": "Corporate MICE travel, conferences, summits, delegate logistics, venue booking, ground handling."
    },
    {
        "id": 5,
        "company": "Torqwars",
        "sub_brand": "Torqwars Experiential",
        "role": "Events Lead",
        "location": "Mumbai",
        "job_url": "https://www.naukri.com/job-listings-events-lead-torqwars-mumbai-3-to-7-years-071026029016?src=jobsearchDesk&sid=17940788904325118&xp=19&px=1&nignbevent_src=jobsearchDeskGNB",
        "platform": "Naukri",
        "channel": "naukri_apply",
        "recipient_email": None,
        "decision_maker": "Founder & Managing Director",
        "fit_score": 94,
        "experience_req": "3-7 Years",
        "status": "APPLIED_PORTAL",
        "notes": "High-adrenaline motorsport and experiential event production, crowd flow, track/venue ops, vendor SLAs."
    },
    {
        "id": 6,
        "company": "NetApp",
        "sub_brand": "NetApp India",
        "role": "Jr. Corporate Event Manager",
        "location": "Mumbai, Maharashtra",
        "job_url": "https://www.linkedin.com/jobs/view/4485438603/",
        "platform": "LinkedIn",
        "channel": "linkedin_apply",
        "recipient_email": None,
        "decision_maker": "APAC Corporate Events Lead",
        "fit_score": 95,
        "experience_req": "2-5 Years",
        "status": "APPLIED_PORTAL",
        "notes": "High-impact B2B events across APAC/India, tradeshows, NetApp-led experiences, virtual events, hybrid execution."
    },
    {
        "id": 7,
        "company": "BookMyShow",
        "sub_brand": "Big Tree Entertainment Pvt Ltd",
        "role": "Assistant Project Management (Events)",
        "location": "Mumbai Metropolitan Region",
        "job_url": "https://www.linkedin.com/jobs/view/4429659549/",
        "platform": "LinkedIn",
        "channel": "linkedin_apply",
        "recipient_email": None,
        "decision_maker": "Head of Live Events & Special Projects",
        "fit_score": 95,
        "experience_req": "2-5 Years",
        "status": "APPLIED_PORTAL",
        "notes": "End-to-end management of live entertainment events, festival operations, concert production, venue logistics."
    },
    {
        "id": 8,
        "company": "Encompass",
        "sub_brand": "Encompass House of Brands / Geometry Encompass",
        "role": "Events Specialist",
        "location": "Mumbai Metropolitan Region",
        "job_url": "https://www.linkedin.com/jobs/view/4479999036/",
        "platform": "LinkedIn",
        "channel": "linkedin_apply",
        "recipient_email": None,
        "decision_maker": "Head of Experiential & Brand Events",
        "fit_score": 96,
        "experience_req": "2-4 Years",
        "status": "APPLIED_PORTAL",
        "notes": "Intimate & high-touch brand events, launches, community evenings, pop-ups, partner showcases, venue, run of show."
    },
    {
        "id": 9,
        "company": "New Zealand Trade and Enterprise",
        "sub_brand": "Te Taurapa Tūhono (NZTE)",
        "role": "Events Manager - India",
        "location": "Mumbai Metropolitan Region",
        "job_url": "https://www.linkedin.com/jobs/view/4486940469/",
        "platform": "LinkedIn",
        "channel": "linkedin_apply",
        "recipient_email": None,
        "decision_maker": "India Trade Commissioner & Regional Marketing Director",
        "fit_score": 95,
        "experience_req": "3-6 Years",
        "status": "APPLIED_PORTAL",
        "notes": "High-level bilateral trade delegations, ministerial summits, VIP hospitality, multi-city trade showcases."
    },
    {
        "id": 10,
        "company": "Red Bull",
        "sub_brand": "Red Bull India",
        "role": "On Premise Festival & Events Manager",
        "location": "Mumbai Metropolitan Region",
        "job_url": "https://www.linkedin.com/jobs/view/4479837751/",
        "platform": "LinkedIn",
        "channel": "linkedin_apply",
        "recipient_email": None,
        "decision_maker": "Head of Culture & Brand Marketing Events",
        "fit_score": 94,
        "experience_req": "3-6 Years",
        "status": "APPLIED_PORTAL",
        "notes": "Music festivals, open airs, warehouse parties, Red Bull brand activations, venue partnerships, on-ground crowd execution."
    },
    {
        "id": 11,
        "company": "Craftworld Events Pvt Ltd",
        "sub_brand": "Craftworld Events (LinkedIn Listing)",
        "role": "Manager - Events Operation Manager",
        "location": "Mumbai, Maharashtra",
        "job_url": "https://www.linkedin.com/jobs/view/4484646116/",
        "platform": "LinkedIn",
        "channel": "linkedin_apply",
        "recipient_email": None,
        "decision_maker": "Director of Operations",
        "fit_score": 96,
        "experience_req": "5-8 Years",
        "status": "APPLIED_PORTAL",
        "notes": "Event operations, production, logistics, vendor coordination, manpower management, on-ground delivery."
    }
]


def send_smtp_application(to_email: str, company: str, role: str) -> dict:
    """Dispatches official application email with PDF CV attached via SMTP."""
    smtp_user = os.getenv("SMTP_USER", "manavmate53@gmail.com")
    raw_pw = os.getenv("SMTP_PASSWORD", "")
    smtp_password = raw_pw.replace(" ", "")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    subject = f"Application: {role} (4+ Yrs Exp, 150+ Events Executed) - Manav Mate"
    
    body = f"""Dear {company} Hiring Team,

I am writing to formally submit my application for the {role} position in Mumbai.

I bring 4+ years of hands-on event operations and production experience, having executed 150 to 200+ events across Mumbai in partnership with 15+ premier event management companies. My background spans corporate MICE, large-scale public sporting events, international summits, live concerts, and high-stakes corporate brand activations.

Key 2026 Marquee Event Executions:
1. Tata Mumbai Marathon 2026: Directed entire venue operations and on-ground production at Mumbai University (zone mapping, production setup, crowd flow control, and real-time crisis management).
2. ICANN 2026 (Global MICE): Managed high-volume international delegate registration and end-to-end on-ground logistics.
3. Neurology Summit Mumbai 2026 (Medical MICE): Owned all 4 execution pillars: Delegate Registration, Stage Production, Floor Operations, and VIP Hospitality.

Operational & Tool Capabilities:
- End-to-End Procurement: Sourcing custom event supplies, goodies, and merchandise with zero stockout incidents.
- Venue Booking & Floor Mapping: Precision layout planning and on-site coordination at premier venues (Jio World Centre, NESCO, Mumbai University, 5-star hotel banquets).
- Catering & AV Production: F&B menu curation, catering layout planning, dining crowd management, and AV show-time management with zero run-of-show slippage.
- Canva & AI Speed: Rapid turnaround on client pitch presentations, event signage, and collateral; AI tools for budgeting drafts and planning schedules.
- Professional Credentials: PMI CIPM certified (Aug 2026), Saylor Operations Management, Scaler System Design, upGrad Business Analytics, B.Com (University of Mumbai).

Proof of Work Simulation:
I have built interactive operational tools and simulations demonstrating roster and queue algorithms:
https://manavmate53-jpg.github.io/pm-product-lab/#crewrostering

Screening Parameters:
- Total Experience: 4+ Years in Event Operations & Production
- Current Location: Jogeshwari East, Mumbai (Available on-site immediately)
- Notice Period: Immediate / 0 Days
- Current CTC: ₹6,00,000 (6.0 LPA)
- Expected CTC: ₹6,50,000 to ₹7,20,000 (6.5 - 7.2 LPA CTC / ₹45k - ₹50k in-hand)
- Flexible with live event dates: Yes

My single-page A4 CV is attached for your review. I would welcome the opportunity to discuss how my on-ground execution velocity and vendor network can support {company}'s upcoming calendar.

Warm regards,

Manav Mate
Jogeshwari East, Mumbai 400060
Phone: +91 93246 80491
Email: manavmate53@gmail.com
LinkedIn: https://www.linkedin.com/in/manav-mate-4a0090226/
Portfolio: https://manavmate53-jpg.github.io/pm-product-lab/#crewrostering
"""

    msg = MIMEMultipart()
    msg["From"] = f"Manav Mate <{smtp_user}>"
    msg["To"] = to_email
    msg["Bcc"] = "manavmate53@gmail.com"
    msg["Subject"] = subject
    msg["Reply-To"] = "manavmate53@gmail.com"
    msg.attach(MIMEText(body, "plain", "utf-8"))

    if PDF_PATH.exists():
        with open(PDF_PATH, "rb") as f:
            pdf_data = f.read()
        part = MIMEApplication(pdf_data, _subtype="pdf")
        part.add_header("Content-Disposition", "attachment", filename="Manav_Mate_Event_Management_CV.pdf")
        msg.attach(part)

    try:
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
        server.starttls()
        server.login(smtp_user, smtp_password)
        recipients = [to_email, "manavmate53@gmail.com"]
        server.sendmail(smtp_user, recipients, msg.as_string())
        server.quit()
        print(f"[SMTP SUCCESS] Dispatched application to {to_email} (BCC: {smtp_user})")
        return {"success": True, "recipient": to_email, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        print(f"[SMTP ERROR] Failed to send email to {to_email}: {e}")
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}


def generate_linkedin_note(job: dict) -> str:
    """Generates character-counted LinkedIn connection note (strictly <= 280 chars)."""
    comp = job["company"]
    note = f"Hi, 4+ yrs managing 150-200+ events across Mumbai. Executed Tata Mumbai Marathon '26 (Mumbai Univ venue ops), ICANN '26 & Neurology Summit. Specialize in procurement, venue mapping, AV timing & Canva/AI planning. Would love to connect regarding {comp}!"
    if len(note) > 280:
        note = f"Hi, 4+ yrs managing 150-200+ events in Mumbai. Executed Tata Mumbai Marathon '26 (Univ venue ops), ICANN '26 & Neurology Summit. Specialize in procurement, venue mapping & AV timing. Would love to connect regarding {comp}!"
    assert len(note) <= 280, f"Note exceeds 280 chars: {len(note)}"
    return note


def generate_cold_dm(job: dict) -> str:
    """Generates direct cold DM / InMail / Cover Note."""
    comp = job["company"]
    role = job["role"]
    dm = f"""Hi,

Reaching out regarding {role} opportunities at {comp}.

I bring 4+ years of hands-on event operations experience, having delivered 150 to 200+ events in partnership with 15+ premier event management companies across Mumbai.

Key 2026 Marquee Event Executions:
1. Tata Mumbai Marathon 2026: Directed entire venue operations and on-ground production across Mumbai University (zone mapping, production setup, crowd flow, and real-time crisis management).
2. ICANN 2026 (Global MICE): Managed high-volume international delegate registration and end-to-end on-ground logistics.
3. Neurology Summit Mumbai 2026 (Medical MICE): Handled all 4 core pillars: Registration, Stage Production, Floor Operations, and VIP Hospitality.

Operational & Tool Capabilities:
- End-to-end procurement of custom event supplies, goodies, and client deliverables with zero stockout incidents.
- Venue booking and precision floor mapping at premier venues (Jio World Centre, NESCO, Mumbai University, 5-star hotel banquets).
- Catering layout planning, dining crowd management, and technical AV show-time management with zero run-of-show slippage.
- Canva for rapid client pitch decks and signage; AI tools for budgeting drafts and planning schedules.
- PMI CIPM certified (Aug 2026), Saylor Operations Management, Scaler System Design, upGrad Business Analytics, B.Com (University of Mumbai).

Live Proof of Work:
I built interactive event operational simulations (roster allocation and attendee queue flow): https://manavmate53-jpg.github.io/pm-product-lab/#crewrostering

Screening & Availability:
- Location: Jogeshwari East, Mumbai (Available On-Site Immediately)
- Notice Period: Immediate / 0 Days
- Current CTC: ₹6.0 LPA | Expected CTC: ₹6.5L - ₹7.2L CTC (₹45k-₹50k in-hand)
- Live Event Date Flexibility: Yes

Open to a brief 10-minute conversation this week?

Warm regards,
Manav Mate
+91 93246 80491 | manavmate53@gmail.com
"""
    return dm


def sync_to_databases(jobs: list, smtp_results: dict):
    """Logs all 11 target opportunities and outreach touchpoints to SQLite DBs."""
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
        notes = f"Platform: {j['platform']} | Req: {j['experience_req']} | URL: {j['job_url']}"
        expected_ctc = "₹6.5L - ₹7.2L"
        pdf = str(PDF_PATH)

        # Check if exists
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
            """, (comp, role, pillar, score, status, dm_name, "Operations / Talent Acquisition", expected_ctc, pdf, notes, now_iso, now_iso))
            opp_id = c_v2.lastrowid

        # Log outreach
        li_note = generate_linkedin_note(j)
        c_v2.execute("""
            INSERT INTO outreach_logs (
                opportunity_id, company_name, channel, touchpoint_type, message_text,
                status, sent_at, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (opp_id, comp, "linkedin", "CONNECT_NOTE", li_note, "QUEUED", now_iso, f"Char count: {len(li_note)}"))

        cold_dm = generate_cold_dm(j)
        channel_type = "email" if j["channel"] == "email" else "dm"
        dm_status = "SENT" if j["channel"] == "email" and smtp_results.get(comp, {}).get("success") else "QUEUED"
        c_v2.execute("""
            INSERT INTO outreach_logs (
                opportunity_id, company_name, channel, touchpoint_type, message_text,
                status, sent_at, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (opp_id, comp, channel_type, "COLD_DM", cold_dm, dm_status, now_iso, f"Recipient: {j.get('recipient_email') or dm_name}"))

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
        status = "Applied" if j["status"] == "APPLIED_EMAIL" else "Ranked"
        hr_name = j["decision_maker"]
        hr_email = j.get("recipient_email")
        pdf = str(PDF_PATH)
        desc = j["notes"]

        c.execute("SELECT id FROM applications WHERE company = ? AND role = ?", (comp, role))
        row = c.fetchone()
        if row:
            c.execute("""
                UPDATE applications
                SET job_url = ?, source = ?, location = ?, experience_years = ?, fit_score = ?,
                    status = ?, tailored_cv_path = ?, hr_name = ?, hr_email = ?, last_action_date = ?, notes = ?
                WHERE id = ?
            """, (job_url, source, loc, exp, score, status, pdf, hr_name, hr_email, now_iso, desc, row[0]))
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
                score, "APPLY", status, pdf, hr_name, hr_email,
                json.dumps(["Event Operations & Production", "Corporate MICE & Conferences", "Event Procurement", "Canva Pitch Decks", "AI Planning Workflows"]),
                "Role matched against 4+ Years Event Operations & Production candidate profile.",
                "Highlight 150-200+ events, Tata Mumbai Marathon 2026 venue ops, ICANN 2026, and Neurology Summit 2026.",
                desc, now_iso if status == "Applied" else None, now_iso, "Auto-processed via Target 11 Jobs pipeline.",
                now_iso, "PILLAR_4_EVENT_OPERATIONS_MICE", "crewrostering"
            ))

    conn.commit()
    conn.close()
    print("[DB SUCCESS] Synced all 11 jobs into data/jobit_v2.db and data/jobit.db!")


def generate_action_pack_markdown(jobs: list, smtp_results: dict):
    """Generates complete action pack with execution table and copy-paste touchpoints."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M IST")

    lines = [
        f"# Daily Action Pack: Target 11 Mumbai Event & MICE Jobs Launch",
        f"**Generated**: {now_str} &bull; **Strategic Pillar**: `PILLAR_4_EVENT_OPERATIONS_MICE`",
        f"**Candidate**: Manav Mate &bull; **Tailored CV**: `exports/resumes/Manav_Mate_Event_Management_CV.pdf`",
        f"**Interactive Proof of Work**: [CrewRoster Simulation Engine](https://manavmate53-jpg.github.io/pm-product-lab/#crewrostering)",
        "",
        "---",
        "",
        "## 1. Execution & Application Dispatch Summary",
        "",
        "| # | Company | Role | Platform / Channel | Fit Score | Status | Direct Apply / Search |",
        "| :-: | :--- | :--- | :--- | :-: | :-: | :--- |"
    ]

    for j in jobs:
        comp = j["company"]
        role = j["role"]
        platform = j["platform"]
        score = j["fit_score"]
        status = j["status"]
        url = j["job_url"]
        lines.append(f"| **{j['id']}** | **{comp}** | {role} | {platform} | **{score}/100** | `{status}` | [Job Link]({url}) |")

    lines.extend([
        "",
        "---",
        "",
        "## 2. Auto-Fill Screening Parameters Applied",
        "",
        "- **Total Experience in Event Operations**: 4 Years (150 to 200+ events with 15+ event management agencies)",
        "- **Current Location**: Jogeshwari East, Mumbai (Available On-Site Immediately)",
        "- **Notice Period**: Immediate / 0 Days",
        "- **Current CTC**: ₹6,00,000 (6.0 LPA)",
        "- **Expected CTC**: ₹6,50,000 to ₹7,20,000 (6.5 - 7.2 LPA CTC / ₹45k - ₹50k in-hand)",
        "- **Flexible with live event dates**: Yes",
        "",
        "---",
        "",
        "## 3. Detailed Company Touchpoint Packages",
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
        search_query = f"%22{comp.replace(' ', '%20')}%22%20%22Operations%22"
        li_search = f"https://www.linkedin.com/search/results/people/?keywords={search_query}&origin=GLOBAL_SEARCH_HEADER"

        lines.extend([
            f"### #{jid}. {comp} &bull; {role}",
            f"- **Location**: {loc}",
            f"- **Fit Score**: **{score}/100** &bull; **Status**: `{status}`",
            f"- **Target Decision Maker**: {dm}",
            f"- **Direct Job URL**: [Open Job Page]({url})",
            f"- **LinkedIn Decision Maker Search**: [Find Hiring Team on LinkedIn]({li_search})",
        ])

        if j.get("recipient_email"):
            smtp_status = "SENT" if smtp_results.get(comp, {}).get("success") else "QUEUED"
            lines.append(f"- **Official Email Application**: `{j['recipient_email']}` (Status: `{smtp_status}` via SMTP with A4 PDF CV attached)")

        lines.extend([
            "",
            f"#### Touchpoint 1: LinkedIn Connection Note ({len(li_note)}/280 chars)",
            "```text",
            li_note,
            "```",
            "",
            "#### Touchpoint 2: Direct Cold Message / Email Pitch",
            "```text",
            cold_dm.strip(),
            "```",
            "",
            "#### Touchpoint 3: 4-Day Follow-Up Bump",
            "```text",
            f"Hi, bumping this quickly in case it got buried under your inbox surge. Still keen to explore how I can support event operations, procurement, and on-ground production at {comp}. Happy to share a quick operational plan whenever convenient.",
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
    print("JOBIT: AUTONOMOUS APPLICATION & DISPATCH PIPELINE FOR 11 TARGET JOBS")
    print("=" * 70)

    # 1. SMTP Dispatch for Official Email Applications
    smtp_results = {}
    print("\n--- STEP 1: OFFICIAL DIRECT EMAIL DISPATCH ---")
    for j in JOBS_DATA:
        if j["channel"] == "email" and j.get("recipient_email"):
            print(f"Dispatching application to {j['company']} ({j['recipient_email']})...")
            res = send_smtp_application(
                to_email=j["recipient_email"],
                company=j["company"],
                role=j["role"]
            )
            smtp_results[j["company"]] = res

    # 2. Database Sync
    print("\n--- STEP 2: DATABASE PERSISTENCE & TELEMETRY ---")
    sync_to_databases(JOBS_DATA, smtp_results)

    # 3. Action Pack Generation
    print("\n--- STEP 3: ACTION PACK GENERATION ---")
    generate_action_pack_markdown(JOBS_DATA, smtp_results)

    print("\n" + "=" * 70)
    print("ALL 11 TARGET JOBS SUCCESSFULLY PROCESSED AND STAGED!")
    print("=" * 70)


if __name__ == "__main__":
    main()
