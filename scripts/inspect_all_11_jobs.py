import sys
import os
import json
import re
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path("/Users/manav/.gemini/antigravity-ide/scratch/JobIt")
sys.path.insert(0, str(BASE_DIR))

urls = [
    {"id": 1, "url": "https://signpostindia.com/career/event-management-2026/", "platform": "direct"},
    {"id": 2, "url": "https://www.naukri.com/job-listings-event-and-operations-manager-craftworld-events-mumbai-suburban-3-to-8-years-021126013957?src=simJobDeskACP&sid=17940788985165759&xp=1&px=1", "platform": "naukri"},
    {"id": 3, "url": "https://www.naukri.com/job-listings-corporate-event-planner-sarvysampanna-system-solutions-mumbai-all-areas-2-to-6-years-231026033513?src=simJobDeskACP&sid=17940788985165759&xp=2&px=1", "platform": "naukri"},
    {"id": 4, "url": "https://www.mercurytravels.co.in/about-us/careers", "platform": "direct"},
    {"id": 5, "url": "https://www.naukri.com/job-listings-events-lead-torqwars-mumbai-3-to-7-years-071026029016?src=jobsearchDesk&sid=17940788904325118&xp=19&px=1&nignbevent_src=jobsearchDeskGNB", "platform": "naukri"},
    {"id": 6, "url": "https://www.linkedin.com/jobs/view/4485438603/", "platform": "linkedin"},
    {"id": 7, "url": "https://www.linkedin.com/jobs/view/4429659549/", "platform": "linkedin"},
    {"id": 8, "url": "https://www.linkedin.com/jobs/view/4479999036/", "platform": "linkedin"},
    {"id": 9, "url": "https://www.linkedin.com/jobs/view/4486940469/", "platform": "linkedin"},
    {"id": 10, "url": "https://www.linkedin.com/jobs/view/4479837751/", "platform": "linkedin"},
    {"id": 11, "url": "https://www.linkedin.com/jobs/view/4484646116/", "platform": "linkedin"},
]

results = []

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars"
        ]
    )
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800}
    )
    page = context.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    for item in urls:
        print(f"\n--- Checking #{item['id']}: {item['url']} ---")
        job_info = {"id": item["id"], "url": item["url"], "platform": item["platform"]}
        try:
            page.goto(item["url"], wait_until="domcontentloaded", timeout=25000)
            time.sleep(2)
            title = page.title()
            job_info["title"] = title
            print(f"Title: {title}")

            # Extract body text sample
            body_text = page.inner_text("body")[:3000]
            job_info["text_preview"] = body_text[:500]

            # Find emails
            emails = list(set(re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", page.content())))
            clean_emails = [e for e in emails if not any(x in e.lower() for x in ["example", "sentry", "w3.org", "webpack", "format", "schema"])]
            job_info["emails"] = clean_emails
            print(f"Emails found: {clean_emails}")

            # Check for buttons
            buttons = page.locator("button, a.apply-button, a[href*='apply'], a[href*='mailto']").all_inner_texts()
            btn_sample = [b.strip() for b in buttons if b.strip() and len(b.strip()) < 50][:10]
            job_info["buttons"] = btn_sample
            print(f"Buttons: {btn_sample}")

            # Take screenshot
            ss_path = BASE_DIR / "exports" / "applications" / f"inspect_job_{item['id']}.png"
            page.screenshot(path=str(ss_path))
            job_info["screenshot"] = str(ss_path)

        except Exception as e:
            print(f"Error inspecting {item['url']}: {e}")
            job_info["error"] = str(e)

        results.append(job_info)

    browser.close()

with open(BASE_DIR / "data" / "target_jobs_inspection.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\nDone inspection! Saved to data/target_jobs_inspection.json")
