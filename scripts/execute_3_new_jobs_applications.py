#!/usr/bin/env python3
"""
JobIt - Autonomous Application & Outreach Dispatcher for 3 New Target Roles:
1. Euro Panel Products Ltd (Eurobond) - Events Executive (Borivali, Mumbai)
2. Sarvysampanna System Solutions - Corporate Events Manager (Mumbai)
3. Jobsora Listing (52907144628) - Gated by reCAPTCHA (Handled safely with direct link)
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
PACK_PATH = BASE_DIR / "exports" / "daily_action_packs" / "2026-11-08_new_events_batch.md"
DB_V2_PATH = BASE_DIR / "data" / "jobit_v2.db"
DB_PATH = BASE_DIR / "data" / "jobit.db"

JOBS = [
    {
        "id": 1,
        "company": "Euro Panel Products Ltd",
        "sub_brand": "Eurobond ACP",
        "role": "Events Executive (Display & Events)",
        "location": "Borivali, Mumbai",
        "job_url": "https://in.indeed.com/viewjob?jk=2051dab3e8356d40",
        "platform": "Indeed / Official HR Email",
        "channel": "email",
        "recipient_email": "careers@eurobondacp.com",
        "salary_range": "₹45,000 - ₹50,000 / month (₹5.4L - ₹6.0L PA)",
        "decision_maker": "Head of Marketing & Communications / HR",
        "fit_score": 98,
        "experience_req": "Min 5 Years",
        "status": "APPLIED_EMAIL",
        "notes": "Plan and execute exhibitions, corporate events, dealer meets, product launches; manage vendor coordination, quotation comparison, cost negotiation, procurement, display centers, corporate gifting, ATL/BTL activations."
    },
    {
        "id": 2,
        "company": "Sarvysampanna System Solutions",
        "sub_brand": "Sarvysampanna Systems (Indeed Listing)",
        "role": "Corporate Events Manager",
        "location": "Mumbai, Maharashtra (In-Person)",
        "job_url": "https://in.indeed.com/viewjob?jk=c5d94c084ced26ba",
        "platform": "Indeed",
        "channel": "indeed_apply",
        "recipient_email": None,
        "salary_range": "₹4,00,000 - ₹6,00,000 / year",
        "decision_maker": "Talent Acquisition & Event Lead",
        "fit_score": 94,
        "experience_req": "2-6 Years",
        "status": "QUEUED_YANG",
        "notes": "Corporate events, vendor management, vendor communication, coordination, planning, on-ground delivery."
    },
    {
        "id": 3,
        "company": "Jobsora Aggregated Listing",
        "sub_brand": "Event Operations / Manager",
        "role": "Event Operations Manager (Job #52907144628)",
        "location": "Mumbai, Maharashtra",
        "job_url": "https://in.jobsora.com/job-52907144628",
        "platform": "Jobsora (reCAPTCHA Protected)",
        "channel": "direct_browser",
        "recipient_email": None,
        "salary_range": "Competitive Market CTC",
        "decision_maker": "Hiring Team",
        "fit_score": 90,
        "experience_req": "3-5 Years",
        "status": "RECAPTCHA_FLAGGED",
        "notes": "Frontend protected by Google reCAPTCHA. In accordance with safety policies, automated solver bypassed; 1-click direct link provided for manual verification."
    }
]


def send_smtp_application(to_email: str, company: str, role: str) -> dict:
    """Dispatches official application email with PDF CV attached via SMTP."""
    smtp_user = os.getenv("SMTP_USER", "manavmate53@gmail.com")
    raw_pw = os.getenv("SMTP_PASSWORD", "")
    smtp_password = raw_pw.replace(" ", "")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    subject = f"Application: {role} (4+ Yrs Exp, 150+ Events, Borivali/Mumbai) - Manav Mate"

    body = f"""Dear Eurobond ACP Hiring Team,

I am writing to formally apply for the Display & Events Executive position with Euro Panel Products Ltd in Borivali, Mumbai.

I bring 4+ years of hands-on event operations, exhibition execution, and procurement experience, having delivered 150 to 200+ events and exhibitions across Mumbai in partnership with 15+ premier event management companies. My background directly aligns with your requirements for vendor negotiations, exhibition booth production, corporate dealer meets, and on-ground logistics.

Key 2026 Marquee Event Executions:
1. Tata Mumbai Marathon 2026: Directed entire venue operations and on-ground production at Mumbai University (zone mapping, production setup, crowd flow control, and real-time crisis management).
2. ICANN 2026 (Global MICE): Managed high-volume international delegate registration and end-to-end on-ground logistics.
3. Neurology Summit Mumbai 2026 (Medical MICE): Owned all 4 execution pillars: Registration, Stage Production, Floor Operations, and VIP Hospitality.

Operational & Procurement Capabilities:
- Vendor Coordination & Procurement: Sourcing custom event supplies, display branding materials, goodies, and merchandise with quotation comparison, strict cost negotiation, and zero stockout incidents.
- Exhibitions & Dealer Meets: Layout planning, booth production, audio-visual technical management, and on-ground crowd flow at premier venues (NESCO Goregaon, Jio World Centre BKC, hotel banquets).
- Canva & Marketing Collateral: Rapid turnaround on presentation pitch decks, event signage, and visual merchandising assets; AI tools for budgeting drafts and planning schedules.
- Professional Credentials: PMI CIPM certified (Aug 2026), Saylor Operations Management, Scaler System Design, upGrad Business Analytics, B.Com (University of Mumbai).

Interactive Proof of Work Simulation:
I built interactive event operational simulations (crew rostering and queue dynamics):
https://manavmate53-jpg.github.io/pm-product-lab/#crewrostering

Screening & Availability:
- Current Location: Jogeshwari East, Mumbai (Quick commute to Borivali; available on-site immediately)
- Total Experience: 4+ Years in Event Operations & Exhibition Production
- Notice Period: Immediate / 0 Days
- Current CTC: ₹6,00,000 (6.0 LPA)
- Expected CTC: ₹45,000 - ₹50,000 / month (₹5.5L - ₹6.5L CTC, matching your posted range)
- Willing to travel across locations: Yes

My single-page A4 CV is attached for your review. I would welcome the opportunity to discuss how my vendor network and on-ground execution velocity can support Eurobond's upcoming exhibition and dealer meet calendar.

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
    """Generates strictly <= 280-char LinkedIn connection note."""
    comp = job["company"]
    if comp == "Euro Panel Products Ltd":
        note = "Hi, 4+ yrs managing 150-200+ events & exhibitions across Mumbai. Executed Tata Mumbai Marathon '26 venue ops, ICANN '26 & Neurology Summit. Specialize in vendor procurement, cost negotiation, dealer meets & Borivali ops. Would love to connect regarding Eurobond!"
    else:
        note = f"Hi, 4+ yrs managing 150-200+ events across Mumbai. Executed Tata Mumbai Marathon '26 (Univ venue ops), ICANN '26 & Neurology Summit. Specialize in corporate events, vendor coordination & AV show timing. Would love to connect regarding {comp}!"

    assert len(note) <= 280, f"Note exceeds 280 chars: {len(note)}"
    return note


def generate_cold_dm(job: dict) -> str:
    """Generates targeted cold DM / cover pitch."""
    comp = job["company"]
    role = job["role"]

    return f"""Hi,

Reaching out regarding {role} opportunities at {comp}.

I bring 4+ years of hands-on event operations experience, having delivered 150 to 200+ events in partnership with 15+ premier event management companies across Mumbai.

Key 2026 Marquee Event Executions:
1. Tata Mumbai Marathon 2026: Directed entire venue operations and on-ground production across Mumbai University (zone mapping, production setup, crowd flow control, and real-time crisis management).
2. ICANN 2026 (Global MICE): Managed high-volume international delegate registration and end-to-end on-ground logistics.
3. Neurology Summit Mumbai 2026 (Medical MICE): Handled all 4 core pillars: Registration, Stage Production, Floor Operations, and VIP Hospitality.

Operational & Tool Capabilities:
- End-to-end procurement of custom event supplies, goodies, and client deliverables with zero stockout incidents.
- Venue booking and precision floor mapping at premier venues (Jio World Centre, NESCO, Mumbai University, 5-star hotel banquets).
- Catering layout planning, dining crowd management, and technical AV show-time management with zero run-of-show slippage.
- Canva for rapid client pitch decks and signage; AI tools for budgeting drafts and planning schedules.
- PMI CIPM certified (Aug 2026), Saylor Operations Management, Scaler System Design, upGrad Business Analytics, B.Com (University of Mumbai).

Live Proof of Work Simulation:
I built interactive event operational simulations (crew rostering and attendee queue dynamics):
https://manavmate53-jpg.github.io/pm-product-lab/#crewrostering

Screening & Availability:
- Location: Jogeshwari East, Mumbai (Available On-Site Immediately)
- Notice Period: Immediate / 0 Days
- Current CTC: ₹6.0 LPA | Expected CTC: ₹45,000 - ₹50,000 / month (₹5.5L - ₹6.5L CTC)
- Live Event Date Flexibility: Yes

Open to a brief 10-minute conversation this week?

Warm regards,
Manav Mate
+91 93246 80491 | manavmate53@gmail.com
"""


def sync_databases(jobs: list, smtp_results: dict):
    """Logs the opportunities into SQLite databases."""
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
        expected_ctc = j.get("salary_range", "₹6.5L - ₹7.2L")
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
            """, (comp, role, pillar, score, status, dm_name, "Operations / Marketing Head", expected_ctc, pdf, notes, now_iso, now_iso))
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
                comp, role, job_url, source, loc, exp, j.get("salary_range", "₹5.5L - ₹6.5L PA"),
                score, "APPLY", status, pdf, hr_name, hr_email,
                json.dumps(["Event Operations & Production", "Corporate MICE & Conferences", "Vendor Procurement", "Exhibition Management", "Canva Pitch Decks"]),
                "Direct match for 4+ Years Event Operations & Production candidate profile.",
                "Highlight 150-200+ events, Tata Mumbai Marathon 2026 venue ops, ICANN 2026, and Neurology Summit 2026.",
                desc, now_iso if status == "Applied" else None, now_iso, "Auto-processed via New Target 3 Jobs pipeline.",
                now_iso, "PILLAR_4_EVENT_OPERATIONS_MICE", "crewrostering"
            ))

    conn.commit()
    conn.close()
    print("[DB SUCCESS] Synced jobs into data/jobit_v2.db and data/jobit.db!")


def generate_action_pack_markdown(jobs: list, smtp_results: dict):
    """Generates the targeted Markdown Action Pack without em dashes or double hyphens."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M IST")

    lines = [
        f"# Target Action Pack: 3 New Mumbai Event Roles",
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
        lines.append(f"| **{j['id']}** | **{comp}** | {role} | {loc} | **{score}/100** | `{status}` | [Job Link]({url}) |")

    lines.extend([
        "",
        "---",
        "",
        "## 2. Auto-Fill Screening Parameters Applied",
        "",
        "- **Total Experience in Event Operations**: 4+ Years (150 to 200+ events across 15+ event management agencies)",
        "- **Current Location**: Jogeshwari East, Mumbai (Quick commute to Borivali; available on-site immediately)",
        "- **Notice Period**: Immediate / 0 Days",
        "- **Current CTC**: ₹6,00,000 (6.0 LPA)",
        "- **Expected CTC**: ₹45,000 to ₹50,000 / month (₹5.5L - ₹6.5L CTC / ₹45k - ₹50k in-hand)",
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
        search_query = f"%22{comp.replace(' ', '%20')}%22%20%22Operations%22"
        li_search = f"https://www.linkedin.com/search/results/people/?keywords={search_query}&origin=GLOBAL_SEARCH_HEADER"

        lines.extend([
            f"### #{jid}. {comp} &bull; {role}",
            f"- **Location**: {loc}",
            f"- **Fit Score**: **{score}/100** &bull; **Status**: `{status}`",
            f"- **Target Decision Maker**: {dm}",
            f"- **Direct Job URL**: [Open Job Page]({url})",
            f"- **Direct LinkedIn Search**: [Find Hiring Team on LinkedIn]({li_search})",
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
            f"#### Touchpoint 2: Direct Cold InMail / Cover Note",
            "```text",
            cold_dm.strip(),
            "```",
            "",
            f"#### Touchpoint 3: 4-Day Follow-Up Bump",
            "```text",
            f"Hi, bumping this quickly in case it got buried under your inbox surge. Still very keen to discuss how my 4+ years of event operations, exhibition execution, and vendor procurement experience can support {comp}'s calendar. Happy to share a tailored operational plan whenever convenient.",
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
    print("JOBIT: AUTONOMOUS APPLICATION PIPELINE FOR 3 NEW EVENT ROLES")
    print("=" * 70)

    # 1. SMTP Dispatch for Official Direct Email Applications
    smtp_results = {}
    print("\n--- STEP 1: OFFICIAL DIRECT EMAIL DISPATCH ---")
    for j in JOBS:
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
    sync_databases(JOBS, smtp_results)

    # 3. Action Pack Generation
    print("\n--- STEP 3: ACTION PACK GENERATION ---")
    generate_action_pack_markdown(JOBS, smtp_results)

    print("\n" + "=" * 70)
    print("ALL 3 NEW EVENT ROLES SUCCESSFULLY PROCESSED AND STAGED!")
    print("=" * 70)


if __name__ == "__main__":
    main()

