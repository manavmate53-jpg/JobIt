#!/usr/bin/env python3
"""Interactive Co-Pilot Sprint Runner for Top 5 Priority Roles.

Sequentially launches visible interactive Chrome sessions for:
1. Job 647: Euro Panel Products Ltd (Indeed | Events Executive)
2. Job 616: WebMD (Jobvite | Associate Product Marketing Manager)
3. Job 643: Red Bull (LinkedIn | On Premise Festival & Events Manager)
4. Job 638: Torqwars (Naukri | Events Lead)
5. Job 179: Dukaan (Wellfound | APM B2B Commerce)
"""

import os
import sys
import time
import subprocess
from pathlib import Path

BASE_DIR = Path("/Users/manav/.gemini/antigravity-ide/scratch/JobIt")
sys.path.insert(0, str(BASE_DIR))

from src.tracker_db import TrackerDB
from src.analytics.telemetry_db import TelemetryDB
from src.ats_applier import BrowserCoPilot, verify_confirmation_screen

TARGET_SPRINT_JOBS = [
    {
        "id": 647,
        "company": "Euro Panel Products Ltd",
        "role": "Events Executive (Display & Events)",
        "track": "event_mice",
        "portal": "Indeed",
        "url": "https://in.indeed.com/viewjob?jk=2051dab3e8356d40",
        "resume": "Manav_Mate_Event_Management_CV.pdf"
    },
    {
        "id": 616,
        "company": "WebMD",
        "role": "Associate Product Marketing Manager",
        "track": "apm",
        "portal": "Jobvite",
        "url": "https://jobs.jobvite.com/webmd/job/oH8YAfw7?isComingFromApp=true",
        "resume": "Manav_Mate_APM_CV.pdf"
    },
    {
        "id": 643,
        "company": "Red Bull",
        "role": "On Premise Festival & Events Manager",
        "track": "event_mice",
        "portal": "LinkedIn",
        "url": "https://www.linkedin.com/jobs/view/4479837751/",
        "resume": "Manav_Mate_Event_Management_CV.pdf"
    },
    {
        "id": 638,
        "company": "Torqwars",
        "role": "Events Lead",
        "track": "event_mice",
        "portal": "Naukri",
        "url": "https://www.naukri.com/job-listings-events-lead-torqwars-mumbai-3-to-7-years-071026029016?src=jobsearchDesk&sid=17940788904325118&xp=19&px=1&nignbevent_src=jobsearchDeskGNB",
        "resume": "Manav_Mate_Event_Management_CV.pdf"
    },
    {
        "id": 179,
        "company": "Dukaan",
        "role": "Associate Product Manager - B2B Commerce & Catalog AI",
        "track": "apm",
        "portal": "Wellfound",
        "url": "https://wellfound.com/jobs/dukaan-apm-b2b-commerce-catalog-849306",
        "resume": "Manav_Mate_APM_CV.pdf"
    }
]


def run_sprint():
    tracker_db = TrackerDB()
    telemetry_db = TelemetryDB()
    copilot = BrowserCoPilot(tracker_db=tracker_db, telemetry_db=telemetry_db)

    print("\n" + "=" * 80)
    print("STARTING INTERACTIVE CO-PILOT SPRINT (5 TARGET ROLES)")
    print("Proof-of-Submission (PoS) Firewall Enforcement: ACTIVE")
    print("=" * 80)

    results = []

    for idx, target in enumerate(TARGET_SPRINT_JOBS, 1):
        job_id = target["id"]
        company = target["company"]
        role = target["role"]
        track = target["track"]
        url = target["url"]

        print(f"\n[{idx}/5] Processing Sprint Job #{job_id}: {company} ({role})")
        print(f"Track: {track.upper()} | Tailored CV: {target['resume']}")
        print(f"URL: {url}")

        res = copilot.launch_copilot(
            job_id=job_id,
            job_url=url,
            company=company,
            role=role,
            track=track
        )

        results.append({
            "job_id": job_id,
            "company": company,
            "role": role,
            "track": track,
            "status": res.get("status"),
            "proof": res.get("proof_screenshot_path") or res.get("screenshot"),
            "reason": res.get("reason")
        })

        # Brief pause between targets
        time.sleep(2)

    # Print summary table
    print("\n" + "=" * 80)
    print("SPRINT EXECUTION RESULTS SUMMARY")
    print("=" * 80)
    for r in results:
        status_color = "\033[92m" if r["status"] == "APPLIED_VERIFIED" else "\033[93m"
        print(f"Job #{r['job_id']:<3} | {r['company']:<25} | {status_color}{r['status']:<18}\033[0m | Proof: {r['proof']}")

    return results


if __name__ == "__main__":
    run_sprint()

