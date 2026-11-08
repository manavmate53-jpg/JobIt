#!/usr/bin/env python3
"""
JobIt - Dispatch Verified Official Job Applications for Event Management & MICE.
Applies directly to verified corporate HR / careers inboxes with Manav_Mate_Event_Management_CV.pdf.
Candidate inboxes are CC'd to provide 100% visible proof.
"""

import os
import sys
import time
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path("/Users/manav/.gemini/antigravity-ide/scratch/JobIt")
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")

PDF_PATH = BASE_DIR / "exports" / "resumes" / "Manav_Mate_Event_Management_CV.pdf"
CANDIDATE_EMAILS = ["manavmate53@gmail.com", "manavstore666@gmail.com"]

# Verified official corporate inboxes with active MX records
OFFICIAL_TARGETS = [
    {
        "company": "Craftworld Events Pvt Ltd",
        "role": "Event and Operations Manager",
        "location": "Andheri West, Mumbai",
        "recipients": ["hr@craftworldevents.com", "hr@cwe.in"],
        "pitch_focus": "Vendor management, stage and production coordination, crowd control, and on-ground floor operations across 150+ corporate events in Mumbai."
    },
    {
        "company": "TorqWars (Zenovia Apparel Pvt Ltd)",
        "role": "Events Lead & Arena Operations",
        "location": "Bandra West / Worli, Mumbai",
        "recipients": ["crew@torqwars.com"],
        "pitch_focus": "High-energy experiential sports entertainment, arena floor mapping, spectator crowd flow, crew rostering, and interactive event operations."
    },
    {
        "company": "Sarvysampanna System Solutions",
        "role": "Corporate Event Planner & Operations Manager",
        "location": "Mumbai",
        "recipients": ["sarvyasampanna@gmail.com"],
        "pitch_focus": "Corporate conferences, dealer meets, procurement negotiation, venue setup, and VIP delegate hospitality."
    },
    {
        "company": "BookMyShow (Bigtree Entertainment)",
        "role": "Assistant Project Management (Live Events)",
        "location": "Mumbai",
        "recipients": ["jobs@bookmyshow.com"],
        "pitch_focus": "Large-scale public entertainment, ticketing crowd queues, VIP guest hospitality, venue production, and live stage show-time coordination."
    },
    {
        "company": "Sunburn Festival (Spacebound Web Labs)",
        "role": "Events Specialist (Festival Operations)",
        "location": "Andheri East / Vile Parle, Mumbai",
        "recipients": ["sunburn.spacebound@gmail.com"],
        "pitch_focus": "Large-scale festival production, multi-zone security flow, stage AV time management, vendor procurement, and crisis mitigation."
    },
    {
        "company": "Encompass Events (Geometry Encompass)",
        "role": "Events Specialist & Operations Lead",
        "location": "Andheri East, Mumbai",
        "recipients": ["careers@encompass.co.in"],
        "pitch_focus": "High-touch brand experiential evenings, corporate MICE summits, delegate logistics, and Canva pitch deck creation."
    },
    {
        "company": "Wizcraft Entertainment Agency",
        "role": "Client Servicing & Event Operations Lead",
        "location": "Andheri West, Mumbai",
        "recipients": ["careers@wizcraft.co"],
        "pitch_focus": "Mega-event productions, high-profile awards, technical AV scheduling, venue booking, and cross-functional team coordination."
    },
    {
        "company": "70 EMG (Seventy Event Media Group)",
        "role": "Event Operations Manager",
        "location": "Lower Parel, Mumbai",
        "recipients": ["hr@seventyemg.com"],
        "pitch_focus": "Luxury weddings, high-net-worth brand activations, bespoke decor procurement, and flawless on-ground execution."
    },
    {
        "company": "Laqshya Live Experiences",
        "role": "Event Operations Manager",
        "location": "Jogeshwari East, Mumbai",
        "recipients": ["info@laqshyaliveex.com", "corporate@laqshyagroup.com"],
        "pitch_focus": "Local Jogeshwari presence, experiential live platforms, high-velocity on-ground manpower deployment (133+ personnel), and procurement."
    },
    {
        "company": "Procam International",
        "role": "Event Operations Manager (Mass Participation)",
        "location": "Lower Parel / Marine Drive, Mumbai",
        "recipients": ["info@procam.in"],
        "pitch_focus": "Tata Mumbai Marathon 2026 venue operations and production execution across Mumbai University; runner crowd flow, stage and zone mapping."
    },
    {
        "company": "NESCO Events (Bombay Exhibition Centre)",
        "role": "Venue Operations Manager",
        "location": "Goregaon East, Mumbai",
        "recipients": ["contact@nescoevents.in"],
        "pitch_focus": "Exhibition hall management, exhibitor stall logistics, crowd queue optimization, AV time management, and venue floor mapping."
    },
    {
        "company": "Messe Frankfurt Trade Fairs India",
        "role": "Event Operations Manager",
        "location": "Andheri East, Mumbai",
        "recipients": ["hr.india@india.messefrankfurt.com"],
        "pitch_focus": "International trade fairs, delegate registration systems, conference hall setups, and technical vendor management."
    },
    {
        "company": "Informa Markets India",
        "role": "Event Production & Procurement Executive",
        "location": "Andheri East, Mumbai",
        "recipients": ["informamarkets@informa.com"],
        "pitch_focus": "Exhibition production, vendor cost negotiation, custom goodies procurement, and end-to-end logistics."
    },
    {
        "company": "BCD Meetings & Events India",
        "role": "MICE Project Manager / Coordinator",
        "location": "Andheri East, Mumbai",
        "recipients": ["sayhello@bcdme.com"],
        "pitch_focus": "Global corporate MICE, international delegate travel and ground logistics, hotel banquet setups, and PMI CIPM certified execution."
    },
    {
        "company": "BI WORLDWIDE India",
        "role": "MICE Project Manager / Coordinator",
        "location": "Mumbai / Bangalore",
        "recipients": ["careers.in@biworldwide.com"],
        "pitch_focus": "Corporate incentive travel, dealer conferences, delegate registration flows, and VIP hospitality operations."
    },
    {
        "company": "Fountainhead MKTG (Dentsu India)",
        "role": "MICE & Corporate Event Project Executive",
        "location": "Worli, Mumbai",
        "recipients": ["Connect.India@dentsu.com"],
        "pitch_focus": "Brand experiences, MICE project timelines, technical AV management, and Canva/AI workflow velocity."
    }
]


def send_application(target: dict) -> bool:
    smtp_user = os.getenv("SMTP_USER", "manavmate53@gmail.com")
    raw_pw = os.getenv("SMTP_PASSWORD", "")
    smtp_password = raw_pw.replace(" ", "")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    company = target["company"]
    role = target["role"]
    loc = target["location"]
    recipients = target["recipients"]
    pitch_focus = target["pitch_focus"]

    subject = f"Application: {role} (4+ Yrs Event Ops, 150+ Events, {loc}) - Manav Mate"

    body = f"""Dear {company} Recruitment Team,

I am writing to formally submit my application for the {role} position in {loc}.

I bring 4+ years of hands-on event operations and production experience, having executed 150 to 200+ events across Mumbai in partnership with 15+ event management agencies. My background spans corporate MICE, public sporting mega-events, international summits, live concerts, and brand activations.

Key 2026 Marquee Event Executions:
1. Tata Mumbai Marathon 2026: Directed entire venue operations and on-ground production at Mumbai University (zone mapping, production setup, crowd flow control, and real-time crisis management).
2. ICANN 2026 (Global MICE): Managed high-volume international delegate registration and end-to-end on-ground logistics.
3. Neurology Summit Mumbai 2026 (Medical MICE): Owned all 4 execution pillars: Delegate Registration, Stage Production, Floor Operations, and VIP Hospitality.

Operational & Procurement Capabilities Relevant to {company}:
- {pitch_focus}
- End-to-End Procurement: Custom event supplies, merchandise, and collateral sourcing with cost negotiation and zero stockouts.
- Venue Booking & Floor Mapping: Layout design and on-ground coordination at premier venues (Jio World Centre, NESCO, Mumbai University, 5-star hotel banquets).
- Catering & AV Production: F&B menu suggestions, dining crowd flow, and technical AV operation with strict show-time management.
- Canva & AI Workflow Speed: Rapid turnaround on client pitch presentations, signage, and collateral; AI tools for budgeting drafts and scheduling.
- Credentials: PMI CIPM certified (Aug 2026), Saylor Operations Management, Scaler System Design, upGrad Business Analytics, B.Com (University of Mumbai).

Proof of Work Simulation:
https://manavmate53-jpg.github.io/pm-product-lab/#crewrostering

Screening Parameters:
- Total Experience: 4+ Years in Event Operations & Production
- Current Location: Jogeshwari East, Mumbai (Available on-site immediately)
- Notice Period: Immediate / 0 Days
- Current CTC: ₹6,00,000 (6.0 LPA)
- Expected CTC: ₹6,50,000 - ₹7,20,000 (₹45,000 - ₹50,000/mo in-hand)
- Flexible with live event dates & travel: Yes

My single-page A4 CV is attached for your review. I would welcome the opportunity to discuss how my execution velocity and vendor network can support {company}'s live calendar.

Warm regards,

Manav Mate
Jogeshwari East, Mumbai 400060
Phone: +91 93246 80491
Email: manavmate53@gmail.com
LinkedIn: https://www.linkedin.com/in/manav-mate-4a0090226/
Portfolio: https://manavmate53-jpg.github.io/pm-product-lab/#crewrostering
"""

    all_recipients = list(set(recipients + CANDIDATE_EMAILS))

    msg = MIMEMultipart()
    msg["From"] = f"Manav Mate <{smtp_user}>"
    msg["To"] = ", ".join(recipients)
    msg["Cc"] = ", ".join(CANDIDATE_EMAILS)
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
        server.sendmail(smtp_user, all_recipients, msg.as_string())
        server.quit()
        print(f"[SUCCESS] Dispatched to {company} ({', '.join(recipients)}) | CC: {', '.join(CANDIDATE_EMAILS)}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send to {company} ({recipients}): {e}")
        return False


def main():
    print("=" * 70)
    print("JOBIT: DISPATCHING REAL VERIFIED OFFICIAL EVENT APPLICATIONS")
    print("=" * 70)

    success_count = 0
    for target in OFFICIAL_TARGETS:
        print(f"\nProcessing: {target['company']}...")
        if send_application(target):
            success_count += 1
        time.sleep(1)

    print("\n" + "=" * 70)
    print(f"DISPATCH COMPLETED: {success_count}/{len(OFFICIAL_TARGETS)} OFFICIAL APPLICATIONS SENT SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    main()

