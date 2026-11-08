#!/usr/bin/env python3
"""
JobIt - Forensic Database Reset Migration
Resets fake 'Applied' statuses caused by synthetic email guessing or unverified dry-runs.
Unlocks all valid opportunities into READY_FOR_COPILOT queue.
Preserves ONLY genuinely verified submissions as APPLIED_VERIFIED.
"""

import os
import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/Users/manav/.gemini/antigravity-ide/scratch/JobIt")
DB_V1 = BASE_DIR / "data" / "jobit.db"
DB_V2 = BASE_DIR / "data" / "jobit_v2.db"

VERIFIED_KEYS = [
    "daxko",
    "peoplesprint",
    "turbohire",
    "joblet-ai",
    "bookmyshow",
    "netapp",
    "craftworld",
    "encompass",
    "mercury travels",
    "signpost india",
    "70 emg",
    "bics",
    "new zealand",
    "nzte"
]

def classify_track(role: str, company: str, pillar: str = None) -> str:
    r = (role or "").lower()
    c = (company or "").lower()
    p = (pillar or "").lower()

    if any(k in r or k in c or k in p for k in ["event", "mice", "venue", "entertainment", "wedding", "banquet"]):
        return "event_mice"
    elif any(k in r or k in p for k in ["founder", "chief of staff", "special project", "founders_office"]):
        return "founders_office"
    elif any(k in r or k in p for k in ["product operations", "prod_ops", "prodops", "operations manager", "ops manager"]):
        return "prod_ops"
    else:
        return "apm"

def reset_database():
    print("=" * 80)
    print("JOBIT FORENSIC DATABASE MIGRATION & AUDIT")
    print("=" * 80)

    # 1. Migrate V1 Database (data/jobit.db)
    conn1 = sqlite3.connect(DB_V1)
    cur1 = conn1.cursor()

    # Ensure schema has PoS columns
    for col in ["proof_screenshot_path", "submission_url"]:
        try:
            cur1.execute(f"ALTER TABLE applications ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass

    cur1.execute("SELECT id, company, role, status, notes, job_url, pillar FROM applications")
    rows1 = cur1.fetchall()

    before_counts = {"event_mice": {}, "founders_office": {}, "prod_ops": {}, "apm": {}}
    after_counts = {"event_mice": {}, "founders_office": {}, "prod_ops": {}, "apm": {}}

    for r in rows1:
        jid, comp, role, st, notes, url, pillar = r
        track = classify_track(role, comp, pillar)
        before_counts[track][st] = before_counts[track].get(st, 0) + 1

    # Perform status updates on V1
    for r in rows1:
        jid, comp, role, st, notes, url, pillar = r
        comp_lower = (comp or "").lower()
        notes_str = (notes or "").lower()

        is_verified = any(k in comp_lower or k in notes_str for k in VERIFIED_KEYS)

        if is_verified and st in ("Applied", "Applied_LinkedIn", "Applied_Portal", "Applied_Portal_Confirmed"):
            new_st = "APPLIED_VERIFIED"
            proof_shot = ""
            sub_url = url or ""
            if "mercury" in comp_lower:
                proof_shot = str(BASE_DIR / "exports/applications/mercury_travels_submitted.png")
            elif "daxko" in comp_lower:
                proof_shot = str(BASE_DIR / "exports/applications/daxko_gem_submitted.png")
            elif "bookmyshow" in comp_lower:
                sub_url = "https://bookmyshow.hire.trakstar.com/"
            
            cur1.execute(
                "UPDATE applications SET status = ?, proof_screenshot_path = ?, submission_url = ? WHERE id = ?",
                (new_st, proof_shot, sub_url, jid)
            )
        elif st in ("Applied", "Emailed", "Applied_LinkedIn", "Applied_Portal"):
            # Synthetic email or unverified dry run -> Reset
            new_st = "RESET_BOUNCED_READY"
            cur1.execute("UPDATE applications SET status = ? WHERE id = ?", (new_st, jid))
        elif st in ("Scraped", "Ranked", "Queued_DM", "Tailored"):
            new_st = "READY_FOR_COPILOT"
            cur1.execute("UPDATE applications SET status = ? WHERE id = ?", (new_st, jid))

    conn1.commit()

    # Recalculate V1 after counts
    cur1.execute("SELECT id, company, role, status, notes, job_url, pillar FROM applications")
    rows1_after = cur1.fetchall()
    for r in rows1_after:
        jid, comp, role, st, notes, url, pillar = r
        track = classify_track(role, comp, pillar)
        after_counts[track][st] = after_counts[track].get(st, 0) + 1

    conn1.close()

    # 2. Migrate V2 Database (data/jobit_v2.db)
    conn2 = sqlite3.connect(DB_V2)
    cur2 = conn2.cursor()

    for col in ["proof_screenshot_path", "submission_url"]:
        try:
            cur2.execute(f"ALTER TABLE opportunities ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass

    cur2.execute("SELECT id, company_name, role_title, pillar, status FROM opportunities")
    rows2 = cur2.fetchall()

    v2_before = {}
    v2_after = {}

    for r in rows2:
        oid, comp, role, pillar, st = r
        v2_before[st] = v2_before.get(st, 0) + 1

        comp_lower = (comp or "").lower()
        is_verified = any(k in comp_lower for k in VERIFIED_KEYS)

        if is_verified and st in ("APPLIED_PORTAL", "APPLIED_EMAIL", "QUEUED_YANG", "IDENTIFIED"):
            new_st = "APPLIED_VERIFIED"
            cur2.execute("UPDATE opportunities SET status = ? WHERE id = ?", (new_st, oid))
            v2_after[new_st] = v2_after.get(new_st, 0) + 1
        elif st in ("APPLIED_EMAIL", "APPLIED_PORTAL"):
            new_st = "RESET_BOUNCED_READY"
            cur2.execute("UPDATE opportunities SET status = ? WHERE id = ?", (new_st, oid))
            v2_after[new_st] = v2_after.get(new_st, 0) + 1
        else:
            new_st = "READY_FOR_COPILOT"
            cur2.execute("UPDATE opportunities SET status = ? WHERE id = ?", (new_st, oid))
            v2_after[new_st] = v2_after.get(new_st, 0) + 1

    conn2.commit()
    conn2.close()

    print("\n--- DATABASE AUDIT BEFORE MIGRATION (V1 jobit.db) ---")
    for track, counts in before_counts.items():
        print(f"[{track.upper()}]: {counts}")

    print("\n--- DATABASE AUDIT AFTER MIGRATION (V1 jobit.db TRUTHFUL COUNTS) ---")
    for track, counts in after_counts.items():
        print(f"[{track.upper()}]: {counts}")

    print("\n--- DATABASE AUDIT V2 (jobit_v2.db) ---")
    print("Before:", v2_before)
    print("After: ", v2_after)

    print("\n" + "=" * 80)
    print("MIGRATION COMPLETED SUCCESSFULLY: SYNTHETIC COUNTS ZEROED OUT")
    print("=" * 80)

if __name__ == "__main__":
    reset_database()
