"""Direct ATS Form Applier and Browser Co-Pilot Engine.

Provides two execution modes:
MODE A: Direct ATS Form Applier (Jobvite, Lever, Greenhouse, Trakstar, Gem, Ashby, Workable, Zoho)
MODE B: Persistent Logged-In Browser Co-Pilot Mode (Naukri, LinkedIn, Indeed, Wellfound, Custom Portals)
Enforces Proof-of-Submission (PoS) Firewall, Multi-Step DOM Form Filling, and Mandatory 3-Stage Screenshots.
"""

from __future__ import annotations

import datetime
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from patchright.sync_api import sync_playwright, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError
except ImportError:
    from playwright.sync_api import sync_playwright, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

from src.tracker_db import TrackerDB
from src.analytics.telemetry_db import TelemetryDB

logger = logging.getLogger(__name__)

BASE_DIR = Path("/Users/manav/.gemini/antigravity-ide/scratch/JobIt")
PROOFS_DIR = BASE_DIR / "exports" / "proofs"
PROOFS_DIR.mkdir(parents=True, exist_ok=True)

CANDIDATE_DATA = {
    "full_name": "Manav Mate",
    "first_name": "Manav",
    "last_name": "Mate",
    "email": "manavmate53@gmail.com",
    "phone": "+91 85915 95889",
    "phone_clean": "8591595889",
    "location": "Jogeshwari East, Mumbai, Maharashtra, India",
    "address": "Jogeshwari East, Mumbai, Maharashtra, India",
    "city": "Mumbai",
    "state": "Maharashtra",
    "country": "India",
    "zip": "400060",
    "linkedin": "https://www.linkedin.com/in/manav-mate-9448b1341/",
    "portfolio": "https://manavmate53-jpg.github.io/portfolio/#hero",
    "product_lab": "https://manavmate53-jpg.github.io/pm-product-lab/#crewrostering",
    "current_company": "NeoManpower / HireFlo",
    "current_title": "Product & Operations Lead",
    "experience_years": "4",
    "notice_period": "Immediate / 0 Days",
    "notice_period_days": "0",
    "notice_period_dropdown": "0-15",
    "current_ctc": "6.0 LPA",
    "current_ctc_numeric": "600000",
    "expected_ctc": "6.5 - 7.2 LPA (₹45,000 - ₹50,000 in-hand)",
    "expected_ctc_numeric": "650000",
}

TRACK_RESUMES = {
    "event_mice": BASE_DIR / "exports" / "resumes" / "Manav_Mate_Event_Management_CV.pdf",
    "founders_office": BASE_DIR / "exports" / "resumes" / "Manav_Mate_Founders_Office_CV.pdf",
    "prod_ops": BASE_DIR / "exports" / "resumes" / "Manav_Mate_ProdOps_CV.pdf",
    "apm": BASE_DIR / "exports" / "resumes" / "Manav_Mate_APM_CV.pdf",
}


class SubmissionIncompleteError(Exception):
    """Raised when an application is claimed to be submitted but pre-apply or unsubmitted elements remain visible."""
    pass


class ZeroFieldsFilledError(Exception):
    """Raised when an application form is loaded but 0 input fields could be identified and filled."""
    pass


UNSUBMITTED_BLACKLIST_MARKERS = [
    "apply now",
    "apply on company site",
    "apply with your resume",
    "job details",
    "full job description",
    "review your application",
    "submit your application",
]

SUBMIT_BUTTON_SELECTORS = [
    "button:has-text('Apply now')",
    "button:has-text('Apply on company site')",
    "button:has-text('Apply')",
    "button:has-text('Submit your application')",
    "button:has-text('Submit application')",
    "button:has-text('Submit Application')",
    "button:has-text('Send Application')",
    "button:has-text('Submit')",
    "button#submit_app",
    "input[type='submit']",
    "a:has-text('Apply now')",
    "a:has-text('Apply on company site')",
]

BOT_WALL_PHRASES = [
    "attention required! | cloudflare",
    "access denied",
    "403 forbidden",
    "verify you are human",
    "please verify you are human",
    "cloudflare ray id",
    "please enable cookies",
    "security check to continue",
]


def detect_login_wall(page: Any, job_id: Optional[int] = None) -> Tuple[bool, str, str]:
    """Detects whether the current page is blocked by an authentication wall.

    Returns (is_gated: bool, platform: str, reason: str).
    If gated, captures exports/proofs/step0_login_wall_<job_id>.png.
    """
    url = getattr(page, "url", "")
    if callable(url):
        url = url()
    url_lower = str(url).lower()

    content = ""
    if hasattr(page, "content"):
        content = page.content() if callable(page.content) else page.content
    content_lower = str(content).lower()

    platform = "generic"
    is_gated = False
    reason = ""

    if "linkedin.com" in url_lower:
        platform = "LinkedIn"
        if any(p in url_lower for p in ["/login", "/checkpoint", "authwall"]):
            is_gated = True
            reason = f"LinkedIn auth gate in URL: {url}"
        elif any(t in content_lower for t in ["sign in to linkedin", "join linkedin to apply", "sign in with google"]):
            is_gated = True
            reason = "LinkedIn sign-in form visible in DOM"

    elif "naukri.com" in url_lower:
        platform = "Naukri"
        if any(p in url_lower for p in ["/nlogin", "/login"]):
            is_gated = True
            reason = f"Naukri login URL detected: {url}"
        elif any(t in content_lower for t in ["login to apply", "register to apply", "login / register"]):
            is_gated = True
            reason = "Naukri login required banner in DOM"

    elif "indeed.com" in url_lower:
        platform = "Indeed"
        if any(p in url_lower for p in ["/account/login", "secure.indeed.com"]):
            is_gated = True
            reason = f"Indeed sign-in URL detected: {url}"
        elif any(t in content_lower for t in ["sign in to your account", "create an account to continue"]):
            is_gated = True
            reason = "Indeed sign-in modal in DOM"

    elif "wellfound.com" in url_lower or "angel.co" in url_lower:
        platform = "Wellfound"
        if "/login" in url_lower:
            is_gated = True
            reason = f"Wellfound login URL detected: {url}"
        elif "log in" in content_lower and "sign up to apply" in content_lower:
            is_gated = True
            reason = "Wellfound auth wall in DOM"

    else:
        if any(p in url_lower for p in ["/login", "/signin", "/sign-in", "/auth"]):
            is_gated = True
            platform = "Generic"
            reason = f"Generic login URL detected: {url}"

    if is_gated:
        jid_str = str(job_id) if job_id is not None else "unknown"
        wall_shot = PROOFS_DIR / f"step0_login_wall_{jid_str}.png"
        try:
            if hasattr(page, "screenshot") and callable(page.screenshot):
                page.screenshot(path=str(wall_shot))
        except Exception:
            pass
        print(f"\n[AUTH REQUIRED] Logged out on {platform}. Reason: {reason}")
        print(f"Auth wall screenshot: {wall_shot}")

    return is_gated, platform, reason


def normalize_ats_url(url: str) -> str:
    """Normalizes job posting URLs directly to application endpoints where applicable."""
    u = url.strip()
    u_lower = u.lower()

    if "jobs.jobvite.com" in u_lower and "/apply" not in u_lower:
        parts = u.split("?")
        base = parts[0].rstrip("/")
        query = f"?{parts[1]}" if len(parts) > 1 else ""
        return f"{base}/apply{query}"

    if "lever.co" in u_lower and not u_lower.endswith("/apply") and "/apply" not in u_lower:
        parts = u.split("?")
        base = parts[0].rstrip("/")
        query = f"?{parts[1]}" if len(parts) > 1 else ""
        return f"{base}/apply{query}"

    return u


def fill_all_visible_inputs(
    page: Page,
    profile: Dict[str, Any] = CANDIDATE_DATA,
    cv_path: Optional[Path] = None,
    job_id: Optional[int] = None,
) -> List[Tuple[str, str]]:
    """Smart Label-Matched DOM Form Filler.

    Iterates over all visible inputs, selects, and textareas across the page and child iframes.
    Matches candidate attributes by inspecting label[for], parent labels, placeholder, name, id,
    aria-label, and autocomplete.
    Handles file upload inputs (even when hidden).
    Highlights filled inputs in green (#10b981).
    Logs [FILLED] <name> = <val>.
    Raises ZeroFieldsFilledError if no fields could be filled.
    """
    filled_fields: List[Tuple[str, str]] = []

    # 1. Handle Country / Language Select dropdowns (e.g. Jobvite country selector)
    try:
        country_selectors = ["#jv-country-select", "select[name*='country']", "select[id*='country']"]
        for c_sel in country_selectors:
            loc = page.locator(c_sel).first
            if loc.count() > 0 and loc.is_visible():
                options = loc.locator("option").all_inner_texts()
                target_val = None
                for opt in options:
                    if any(target in opt.lower() for target in ["united states & other", "india", "united states", "other"]):
                        target_val = opt
                        break
                if target_val:
                    loc.select_option(label=target_val)
                else:
                    # Select first non-empty option
                    opts = loc.locator("option").all()
                    if len(opts) > 1:
                        val = opts[1].get_attribute("value")
                        if val:
                            loc.select_option(value=val)
                time.sleep(2)
                print(f"[FILLED] Country/Language Selector = '{target_val or 'Default'}'")
                filled_fields.append(("Country/Language Selector", target_val or "Selected"))
                break
    except Exception as e:
        logger.debug(f"Country select handling: {e}")

    # 2. File Upload handling across main page and child iframes
    if cv_path and cv_path.exists():
        all_frames = [page.main_frame] + [f for f in page.frames if f != page.main_frame]
        resume_uploaded = False

        # If a portal has a trigger button to open attachment chooser (e.g. Jobvite "Select")
        try:
            select_btns = page.locator(
                "button:has-text('Select'), button[jv-add-attachment], button:has-text('Add Resume'), button:has-text('Upload Resume')"
            ).all()
            for sbtn in select_btns:
                if sbtn.is_visible():
                    sbtn.click()
                    time.sleep(1)
                    break
        except Exception:
            pass

        for frame in all_frames:
            try:
                file_inputs = frame.locator("input[type='file']").all()
                for finp in file_inputs:
                    finp.set_input_files(str(cv_path))
                    time.sleep(2)
                    resume_uploaded = True
                    fname = cv_path.name
                    print(f"[FILLED] Resume / CV File Upload = '{fname}'")
                    filled_fields.append(("Resume File", fname))
                    break
                if resume_uploaded:
                    break
            except Exception as e:
                logger.debug(f"File upload error in frame: {e}")

    # 3. Handle Mandatory Checkboxes (Consent, Privacy, Terms, Declarations)
    for frame in all_frames:
        try:
            checkboxes = frame.locator("input[type='checkbox']").all()
        except Exception:
            continue
        for cb in checkboxes:
            try:
                if not cb.is_visible():
                    continue
                cid = cb.get_attribute("id") or ""
                cname = cb.get_attribute("name") or ""
                clbl = ""
                if cid:
                    lbl = frame.locator(f"label[for='{cid}']").first
                    if lbl.count() > 0:
                        clbl = lbl.inner_text().strip()
                if not clbl:
                    try:
                        clbl = cb.evaluate("e => e.closest('label') ? e.closest('label').innerText : ''").strip()
                    except Exception:
                        pass
                cdesc = f"{clbl} {cname} {cid}".lower()
                if any(
                    term in cdesc
                    for term in [
                        "consent",
                        "privacy",
                        "agree",
                        "acknowledge",
                        "certify",
                        "declare",
                        "terms",
                        "policy",
                        "authorized",
                        "confirm",
                        "understand",
                    ]
                ):
                    if not cb.is_checked():
                        cb.check(force=True)
                        try:
                            cb.dispatch_event("change")
                        except Exception:
                            pass
                        cb_name = clbl or cname or cid or "Consent Checkbox"
                        print(f"[FILLED] Checkbox '{cb_name}' = Checked")
                        filled_fields.append((cb_name, "Checked"))
            except Exception:
                pass

    # 4. Label-Matched Input / Select / Textarea Filling
    all_frames = [page.main_frame] + [f for f in page.frames if f != page.main_frame]

    for frame in all_frames:
        try:
            elements = frame.locator("input:not([type='file']):not([type='hidden']), textarea, select").all()
        except Exception:
            continue

        for el in elements:
            try:
                if not el.is_visible():
                    continue

                tag = el.evaluate("e => e.tagName").upper()
                itype = (el.get_attribute("type") or "text").lower()
                iid = el.get_attribute("id") or ""
                name = el.get_attribute("name") or ""
                ph = el.get_attribute("placeholder") or ""
                aria = el.get_attribute("aria-label") or ""
                auto = el.get_attribute("autocomplete") or ""

                # Find associated label text
                lbl_text = ""
                if iid:
                    lbl = frame.locator(f"label[for='{iid}']").first
                    if lbl.count() > 0:
                        lbl_text = lbl.inner_text().strip()
                if not lbl_text:
                    try:
                        lbl_text = el.evaluate("e => e.closest('label') ? e.closest('label').innerText : ''").strip()
                    except Exception:
                        pass

                desc = f"{lbl_text} {name} {iid} {ph} {aria} {auto}".lower()
                display_name = lbl_text or name or iid or ph or "Unknown Field"

                val_to_fill = None

                # Matching logic
                if any(k in desc for k in ["first name", "firstname", "first_name", "given-name", "given name"]) or (
                    desc.strip() == "first" or ("first" in desc and "name" in desc)
                ):
                    val_to_fill = profile.get("first_name", "Manav")

                elif any(k in desc for k in ["last name", "lastname", "last_name", "family-name", "family name", "surname"]) or (
                    desc.strip() == "last" or ("last" in desc and "name" in desc)
                ):
                    val_to_fill = profile.get("last_name", "Mate")

                elif any(k in desc for k in ["full name", "fullname", "your name", "candidate name"]) or desc.strip() in ["name", "name *"]:
                    val_to_fill = profile.get("full_name", "Manav Mate")

                elif any(k in desc for k in ["email", "e-mail"]):
                    val_to_fill = profile.get("email", "manavmate53@gmail.com")

                elif any(k in desc for k in ["phone", "mobile", "cell", "telephone", "tel"]):
                    if itype in ["tel", "number"] or "10" in desc or "cellphone" in desc:
                        val_to_fill = profile.get("phone_clean", "8591595889")
                    else:
                        val_to_fill = profile.get("phone", "+91 85915 95889")

                elif ("current" in desc and any(k in desc for k in ["salary", "ctc", "compensation", "earning"])) or desc.strip() in [
                    "current salary*",
                    "current ctc",
                ]:
                    val_to_fill = profile.get("current_ctc_numeric", "600000")

                elif any(k in desc for k in ["desired", "expected", "target"]) and any(k in desc for k in ["salary", "ctc", "compensation"]):
                    val_to_fill = profile.get("expected_ctc_numeric", "650000")

                elif "notice" in desc:
                    if tag == "SELECT":
                        opts = el.locator("option").all_inner_texts()
                        selected_opt = None
                        for opt in opts:
                            if any(target in opt.lower() for target in ["0-15", "immediate", "0", "15", "1 month"]):
                                selected_opt = opt
                                break
                        if selected_opt:
                            el.select_option(label=selected_opt)
                            val_to_fill = selected_opt
                        else:
                            val_to_fill = profile.get("notice_period", "0-15")
                    else:
                        val_to_fill = profile.get("notice_period", "Immediate / 0 Days")

                elif "city" in desc or "address-level2" in desc:
                    val_to_fill = profile.get("city", "Mumbai")

                elif any(k in desc for k in ["zip", "postal", "pincode", "pin code", "postal-code"]):
                    val_to_fill = profile.get("zip", "400060")

                elif any(k in desc for k in ["location", "address"]) and not any(k in desc for k in ["email", "ip"]):
                    val_to_fill = profile.get("location", "Mumbai, Maharashtra, India")

                elif "linkedin" in desc:
                    val_to_fill = profile.get("linkedin", "https://www.linkedin.com/in/manav-mate-9448b1341/")

                elif any(k in desc for k in ["portfolio", "website", "personal website", "github", "url"]):
                    val_to_fill = profile.get("portfolio", "https://manavmate53-jpg.github.io/portfolio/#hero")

                elif any(k in desc for k in ["company", "employer", "organization", "current org"]):
                    val_to_fill = profile.get("current_company", "NeoManpower")

                elif any(k in desc for k in ["title", "current title", "designation"]):
                    val_to_fill = profile.get("current_title", "Product & Operations Lead")

                elif any(k in desc for k in ["experience", "years of exp"]):
                    val_to_fill = profile.get("experience_years", "4")

                elif any(
                    k in desc
                    for k in [
                        "authorized to work",
                        "legally entitled",
                        "work authorization",
                        "eligible to work",
                        "right to work",
                    ]
                ):
                    if tag == "SELECT":
                        opts = el.locator("option").all_inner_texts()
                        for opt in opts:
                            if "yes" in opt.lower():
                                val_to_fill = opt
                                break
                    else:
                        val_to_fill = "Yes"

                elif any(k in desc for k in ["sponsorship", "require visa", "visa sponsorship", "need sponsorship"]):
                    if tag == "SELECT":
                        opts = el.locator("option").all_inner_texts()
                        for opt in opts:
                            if "no" in opt.lower():
                                val_to_fill = opt
                                break
                    else:
                        val_to_fill = "No"

                elif any(k in desc for k in ["relocate", "relocation", "willing to commute", "commute to"]):
                    if tag == "SELECT":
                        opts = el.locator("option").all_inner_texts()
                        for opt in opts:
                            if "yes" in opt.lower():
                                val_to_fill = opt
                                break
                    else:
                        val_to_fill = "Yes"

                elif any(k in desc for k in ["how did you hear", "source", "hear about us", "referral source"]):
                    if tag == "SELECT":
                        opts = el.locator("option").all_inner_texts()
                        for opt in opts:
                            if any(s in opt.lower() for s in ["linkedin", "job board", "online", "internet"]):
                                val_to_fill = opt
                                break
                        if not val_to_fill and len(opts) > 1:
                            val_to_fill = opts[1]
                    else:
                        val_to_fill = "LinkedIn"

                elif any(k in desc for k in ["gender", "sex"]):
                    if tag == "SELECT":
                        opts = el.locator("option").all_inner_texts()
                        for opt in opts:
                            if "male" in opt.lower() and "female" not in opt.lower():
                                val_to_fill = opt
                                break
                    else:
                        val_to_fill = "Male"

                if val_to_fill:
                    if tag == "SELECT":
                        try:
                            el.select_option(label=str(val_to_fill))
                        except Exception:
                            try:
                                el.select_option(value=str(val_to_fill))
                            except Exception:
                                pass
                    else:
                        el.fill(str(val_to_fill))
                        try:
                            el.dispatch_event("input")
                            el.dispatch_event("change")
                            el.dispatch_event("blur")
                        except Exception:
                            pass

                    print(f"[FILLED] {display_name} = '{val_to_fill}'")
                    filled_fields.append((display_name, str(val_to_fill)))

            except Exception as e:
                logger.debug(f"Input fill loop element error: {e}")

    # 4. Highlight filled inputs in green
    try:
        page.evaluate("""() => {
            document.querySelectorAll('input, select, textarea').forEach(el => {
                if (el.value && el.value.length > 0 && el.type !== 'hidden' && el.type !== 'file') {
                    el.style.border = '2px solid #10b981';
                    el.style.backgroundColor = '#ecfdf5';
                    el.style.boxShadow = '0 0 8px #10b981';
                }
            });
        }""")
    except Exception:
        pass

    # 5. Enforce Non-Zero Filled Fields
    if len(filled_fields) == 0:
        raise ZeroFieldsFilledError(
            f"0 fields filled on {page.url}. Smart DOM agent could not match any inputs to candidate profile."
        )

    return filled_fields


def step_through_wizard(
    page: Page,
    profile: Dict[str, Any] = CANDIDATE_DATA,
    cv_path: Optional[Path] = None,
    max_steps: int = 5,
) -> Tuple[bool, str]:
    """Iterates through multi-step application wizards until final Submit is reached.

    Returns (submitted: bool, notes: str).
    """
    for step_num in range(1, max_steps + 1):
        print(f"[WIZARD STEP {step_num}] Filling visible step inputs...")
        try:
            fill_all_visible_inputs(page, profile=profile, cv_path=cv_path)
        except ZeroFieldsFilledError:
            pass

        # Check for final submit button
        submit_btn = None
        for sel in SUBMIT_BUTTON_SELECTORS:
            btn = page.locator(sel).first
            if btn.count() > 0 and btn.is_visible() and btn.is_enabled():
                submit_btn = btn
                break

        # Check for intermediate wizard progression button
        wizard_btn = None
        wizard_selectors = [
            "button:has-text('Next')",
            "button:has-text('Continue')",
            "button:has-text('Save & Continue')",
            "button:has-text('Review')",
            "a:has-text('Next')",
            "a:has-text('Continue')",
        ]
        for w_sel in wizard_selectors:
            w_btn = page.locator(w_sel).first
            if w_btn.count() > 0 and w_btn.is_visible() and w_btn.is_enabled():
                wizard_btn = w_btn
                break

        # If a next button is visible and not final submit, advance
        if wizard_btn and (not submit_btn or wizard_btn != submit_btn):
            print(f"[WIZARD STEP {step_num}] Clicking progression button: '{wizard_btn.inner_text().strip()}'")
            wizard_btn.click()
            time.sleep(2)
            continue

        # If final submit is visible, click it
        if submit_btn:
            print(f"[WIZARD FINAL] Clicking submit button: '{submit_btn.inner_text().strip()}'")
            submit_btn.scroll_into_view_if_needed()
            submit_btn.click()
            time.sleep(4)
            return True, f"Submit button clicked on step {step_num}"

        time.sleep(1)

    return False, f"Completed {max_steps} wizard steps without finding final submit button"


def verify_confirmation_screen(page: Any, ats_type: str = "generic", raise_on_failure: bool = False) -> Tuple[bool, str]:
    """Strictly validates that the page is genuinely a post-submission confirmation screen.

    Returns (is_verified: bool, reason: str).
    Rules:
    1. Blacklist check: If any pre-apply or in-progress marker is visible, strictly forbid verification.
    2. Button check: If an apply or submit button is still visible and clickable, reject.
    3. Mandatory Positive Confirmation: Requires explicit post-submission tokens per portal.
    """
    url = getattr(page, "url", "")
    if callable(url):
        url = url()
    url_lower = str(url).lower()

    content = ""
    if hasattr(page, "content"):
        content = page.content() if callable(page.content) else page.content
    content_lower = str(content).lower()

    # Rule 1: Blacklist False Confirmation Markers
    for marker in UNSUBMITTED_BLACKLIST_MARKERS:
        marker_found = False
        if hasattr(page, "locator") and callable(page.locator):
            try:
                loc = page.locator(f"text='{marker}'").first
                if loc.is_visible(timeout=300):
                    marker_found = True
            except Exception:
                pass
        if not marker_found and marker in content_lower:
            if not hasattr(page, "locator") or not callable(page.locator):
                marker_found = True

        if marker_found:
            reason = f"Pre-apply blacklist marker visible: '{marker}' (application not submitted)"
            if raise_on_failure:
                raise SubmissionIncompleteError(reason)
            return False, reason

    # Rule 2: Two-Step Check for Visible Submit/Apply Buttons
    for sel in SUBMIT_BUTTON_SELECTORS:
        btn_txt = None
        if hasattr(page, "locator") and callable(page.locator):
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=300) and btn.is_enabled(timeout=300):
                    txt = btn.inner_text().strip().lower()
                    if any(w in txt for w in ["apply", "submit"]):
                        btn_txt = txt
            except Exception:
                pass

        if btn_txt:
            reason = f"Submit/Apply button still visible and clickable: '{btn_txt}'"
            if raise_on_failure:
                raise SubmissionIncompleteError(reason)
            return False, reason

    # Rule 3: Mandatory Platform-Specific Positive Confirmation Markers
    if "indeed.com" in url_lower:
        indeed_tokens = [
            "your application has been submitted",
            "your application was sent to",
            "your application has been sent",
            "application submitted",
        ]
        has_positive = any(t in content_lower for t in indeed_tokens) or "/post-apply" in url_lower
        if not has_positive:
            reason = "Indeed submission incomplete: Missing 'Your application has been submitted / sent' or '/post-apply' URL"
            if raise_on_failure:
                raise SubmissionIncompleteError(reason)
            return False, reason
        return True, "Indeed post-submission confirmation verified"

    elif "lever.co" in url_lower:
        has_positive = "/thanks" in url_lower or "thank you for applying" in content_lower
        if not has_positive:
            reason = "Lever submission incomplete: Missing '/thanks' URL or 'Thank you for applying' confirmation text"
            if raise_on_failure:
                raise SubmissionIncompleteError(reason)
            return False, reason
        return True, "Lever post-submission confirmation verified"

    elif "greenhouse.io" in url_lower:
        has_positive = (
            "/confirmation" in url_lower
            or "application submitted!" in content_lower
            or "thank you for applying" in content_lower
        )
        if not has_positive:
            reason = "Greenhouse submission incomplete: Missing '/confirmation' URL or 'Application submitted!' text"
            if raise_on_failure:
                raise SubmissionIncompleteError(reason)
            return False, reason
        return True, "Greenhouse post-submission confirmation verified"

    elif "jobvite.com" in url_lower:
        has_positive = (
            "thank you for your interest" in content_lower
            or "your application has been successfully submitted" in content_lower
            or "application submitted" in content_lower
            or "thank you for applying" in content_lower
        )
        if not has_positive:
            reason = "Jobvite submission incomplete: Missing 'successfully submitted' or 'Thank you for your interest' confirmation text"
            if raise_on_failure:
                raise SubmissionIncompleteError(reason)
            return False, reason
        return True, "Jobvite post-submission confirmation verified"

    elif "linkedin.com" in url_lower:
        has_positive = "application sent" in content_lower or "your application was sent" in content_lower
        if not has_positive:
            reason = "LinkedIn submission incomplete: Missing 'Application sent' confirmation modal"
            if raise_on_failure:
                raise SubmissionIncompleteError(reason)
            return False, reason
        return True, "LinkedIn post-submission confirmation verified"

    elif "naukri.com" in url_lower:
        has_positive = "successfully applied" in content_lower or "you have successfully applied" in content_lower
        if not has_positive:
            reason = "Naukri submission incomplete: Missing 'Successfully applied' confirmation banner"
            if raise_on_failure:
                raise SubmissionIncompleteError(reason)
            return False, reason
        return True, "Naukri post-submission confirmation verified"

    elif "wellfound.com" in url_lower or "angel.co" in url_lower:
        has_positive = "application sent" in content_lower or "applied" in url_lower
        if not has_positive:
            reason = "Wellfound submission incomplete: Missing application confirmation"
            if raise_on_failure:
                raise SubmissionIncompleteError(reason)
            return False, reason
        return True, "Wellfound post-submission confirmation verified"

    else:
        generic_confirm_tokens = [
            "your application has been submitted",
            "thank you for applying",
            "application submitted successfully",
            "we have received your application",
            "application complete",
        ]
        has_positive = any(t in content_lower for t in generic_confirm_tokens) or any(
            u in url_lower for u in ["/thanks", "/thank-you", "/thankyou", "/confirmation", "/submitted"]
        )
        if not has_positive:
            reason = "Generic ATS submission incomplete: No explicit confirmation header or success URL detected"
            if raise_on_failure:
                raise SubmissionIncompleteError(reason)
            return False, reason
        return True, "Generic ATS post-submission confirmation verified"


def assert_confirmation_screen(page: Any, ats_type: str = "generic") -> Tuple[bool, str]:
    """Strictly asserts confirmation screen. Raises SubmissionIncompleteError on any failure."""
    return verify_confirmation_screen(page, ats_type=ats_type, raise_on_failure=True)


class DirectATSApplier:
    """Automates form submission directly on ATS portals without bot walls."""

    def __init__(self, tracker_db: Optional[TrackerDB] = None, telemetry_db: Optional[TelemetryDB] = None):
        self.tracker_db = tracker_db or TrackerDB()
        self.telemetry_db = telemetry_db or TelemetryDB()

    def get_resume_path(self, track: str) -> Path:
        res = TRACK_RESUMES.get(track.lower())
        if res and res.exists():
            return res
        fallback = BASE_DIR / "exports" / "resumes" / "Manav_Mate_Master_CV.pdf"
        if fallback.exists():
            return fallback
        return TRACK_RESUMES["event_mice"]

    def detect_ats_type(self, url: str) -> str:
        u = url.lower()
        if "lever.co" in u:
            return "lever"
        elif "greenhouse.io" in u:
            return "greenhouse"
        elif "jobvite.com" in u:
            return "jobvite"
        elif "trakstar.com" in u:
            return "trakstar"
        elif "gem.com" in u:
            return "gem"
        elif "ashbyhq.com" in u:
            return "ashby"
        elif "workable.com" in u:
            return "workable"
        elif "zohorecruit" in u:
            return "zoho"
        elif "darwinbox" in u:
            return "darwinbox"
        return "generic_ats"

    def apply_job(
        self,
        job_id: int,
        job_url: str,
        company: str,
        role: str,
        track: str = "event_mice",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Applies to an ATS posting with Proof-of-Submission (PoS) verification and mandatory 3-stage screenshots."""
        normalized_url = normalize_ats_url(job_url)
        ats_type = self.detect_ats_type(normalized_url)
        safe_comp = re.sub(r"[^\w-]", "_", company)
        resume_pdf = self.get_resume_path(track)

        # Mandatory 3-Stage Screenshots Paths
        step1_path = PROOFS_DIR / f"job_{job_id}_step1_loaded.png"
        step2_path = PROOFS_DIR / f"job_{job_id}_step2_filled.png"
        step3_path = PROOFS_DIR / f"job_{job_id}_step3_result.png"

        logger.info(f"Applying to {company} ({role}) via {ats_type.upper()} | URL: {normalized_url}")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            )
            page = context.new_page()

            try:
                page.goto(normalized_url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(2)

                # Mandatory Stage 1: Loaded Screenshot
                page.screenshot(path=str(step1_path))
                logger.info(f"Step 1 loaded screenshot captured: {step1_path}")

                # Check for login walls
                is_gated, platform, gate_reason = detect_login_wall(page, job_id=job_id)
                if is_gated:
                    browser.close()
                    self.tracker_db.mark_needs_human_click(job_id, f"Auth wall detected: {gate_reason}", str(step1_path))
                    return {
                        "status": "NEEDS_HUMAN_CLICK",
                        "reason": f"Login wall detected on {platform}: {gate_reason}",
                        "step1_screenshot": str(step1_path),
                    }

                # Check for bot walls on visible page text
                try:
                    page_text_lower = page.inner_text("body").lower()
                except Exception:
                    page_text_lower = page.content().lower()
                for bw in BOT_WALL_PHRASES:
                    if bw in page_text_lower:
                        shot_path = PROOFS_DIR / f"blocked_{track}_{safe_comp}_{job_id}.png"
                        page.screenshot(path=str(shot_path))
                        browser.close()
                        self.tracker_db.mark_needs_human_click(job_id, f"Bot wall encountered ({bw})", str(shot_path))
                        return {
                            "status": "NEEDS_HUMAN_CLICK",
                            "reason": f"Bot wall detected: {bw}",
                            "screenshot": str(shot_path),
                        }

                # Dismiss cookie banners if present
                for cookie_btn in page.locator(
                    "button:has-text('Accept'), button:has-text('Agree'), button:has-text('Allow all')"
                ).all():
                    if cookie_btn.is_visible():
                        try:
                            cookie_btn.click()
                            time.sleep(1)
                            break
                        except Exception:
                            pass

                # Smart DOM Form Filling
                filled = fill_all_visible_inputs(page, profile=CANDIDATE_DATA, cv_path=resume_pdf, job_id=job_id)
                logger.info(f"Filled {len(filled)} fields for {company}")

                # Mandatory Stage 2: Filled Screenshot
                page.screenshot(path=str(step2_path))
                logger.info(f"Step 2 filled screenshot captured: {step2_path}")

                if dry_run:
                    browser.close()
                    return {
                        "status": "READY_TO_SUBMIT",
                        "step1_screenshot": str(step1_path),
                        "step2_screenshot": str(step2_path),
                        "fields_filled_count": len(filled),
                        "message": f"Form filled successfully in dry-run mode for {company}.",
                    }

                # Multi-Step Wizard Progression or Submit
                submitted, submit_notes = step_through_wizard(page, profile=CANDIDATE_DATA, cv_path=resume_pdf)

                # Mandatory Stage 3: Result Screenshot
                page.screenshot(path=str(step3_path))
                logger.info(f"Step 3 result screenshot captured: {step3_path}")

                time.sleep(4)
                is_verified, reason = verify_confirmation_screen(page, ats_type=ats_type)

                if is_verified:
                    proof_path = PROOFS_DIR / f"{track}_{safe_comp}_{job_id}_SUCCESS.png"
                    page.screenshot(path=str(proof_path))
                    submission_url = page.url
                    browser.close()

                    self.tracker_db.mark_applied_verified(
                        job_id=job_id,
                        proof_screenshot_path=str(proof_path),
                        submission_url=submission_url,
                        notes=f"Submitted via Direct ATS Applier ({ats_type}): {reason}",
                    )
                    return {
                        "status": "APPLIED_VERIFIED",
                        "proof_screenshot_path": str(proof_path),
                        "submission_url": submission_url,
                        "company": company,
                        "role": role,
                        "reason": reason,
                        "step1_screenshot": str(step1_path),
                        "step2_screenshot": str(step2_path),
                        "step3_screenshot": str(step3_path),
                    }
                else:
                    browser.close()
                    self.tracker_db.mark_needs_human_click(
                        job_id,
                        f"Post-submission confirmation unconfirmed: {reason}",
                        str(step3_path),
                    )
                    return {
                        "status": "NEEDS_HUMAN_CLICK",
                        "reason": f"Post-submission confirmation unconfirmed: {reason}",
                        "step1_screenshot": str(step1_path),
                        "step2_screenshot": str(step2_path),
                        "step3_screenshot": str(step3_path),
                    }

            except Exception as e:
                try:
                    page.screenshot(path=str(step3_path))
                except Exception:
                    pass
                browser.close()
                self.tracker_db.mark_needs_human_click(job_id, f"Automation exception: {e}", str(step3_path))
                return {
                    "status": "NEEDS_HUMAN_CLICK",
                    "reason": f"Exception: {e}",
                    "step1_screenshot": str(step1_path),
                    "step2_screenshot": str(step2_path),
                    "step3_screenshot": str(step3_path),
                }


class BrowserCoPilot:
    """Persistent Browser Co-Pilot Mode for Naukri, LinkedIn, Indeed, Wellfound, and Custom Portals."""

    def __init__(
        self,
        profile_dir: Optional[Path] = None,
        tracker_db: Optional[TrackerDB] = None,
        telemetry_db: Optional[TelemetryDB] = None,
    ):
        self.profile_dir = profile_dir or (BASE_DIR / "data" / "browser_profile")
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.tracker_db = tracker_db or TrackerDB()
        self.telemetry_db = telemetry_db or TelemetryDB()

    def launch_copilot(
        self,
        job_id: int,
        job_url: str,
        company: str,
        role: str,
        track: str = "event_mice",
    ) -> Dict[str, Any]:
        """Launches a persistent browser session with auto-filled fields and terminal prompt."""
        import select
        import sys

        safe_comp = re.sub(r"[^\w-]", "_", company)
        resume_pdf = DirectATSApplier().get_resume_path(track)
        normalized_url = normalize_ats_url(job_url)

        # Mandatory 3-Stage Screenshots Paths
        step1_path = PROOFS_DIR / f"job_{job_id}_step1_loaded.png"
        step2_path = PROOFS_DIR / f"job_{job_id}_step2_filled.png"
        step3_path = PROOFS_DIR / f"job_{job_id}_step3_result.png"

        print("\n" + "=" * 80)
        print(f"[CO-PILOT MODE] Launching interactive browser for: {company} - {role}")
        print(f"Target URL: {normalized_url}")
        print(f"Tailored CV: {resume_pdf.name}")
        print("=" * 80)

        headless_mode = os.getenv("COPILOT_HEADLESS", "false").lower() in ("true", "1")

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                headless=headless_mode,
                viewport={"width": 1280, "height": 900},
                args=["--disable-blink-features=AutomationControlled"],
            )
            page = context.pages[0] if context.pages else context.new_page()

            try:
                page.goto(normalized_url, timeout=30000)
                time.sleep(2)

                # Step 1: Loaded Screenshot
                page.screenshot(path=str(step1_path))

                # Check for login walls
                is_gated, platform, gate_reason = detect_login_wall(page, job_id=job_id)
                if is_gated:
                    print(f"\n[AUTH REQUIRED] Please log into your {platform} account in the opened browser window.")

                # Auto-open application modal/form if on job posting page
                try:
                    if "indeed.com" in page.url.lower():
                        indeed_apply = page.locator(
                            "#indeedApplyButton, button:has-text('Apply now'), a:has-text('Apply now')"
                        ).first
                        if indeed_apply.is_visible(timeout=3000):
                            indeed_apply.click()
                            time.sleep(2)
                    elif "linkedin.com" in page.url.lower():
                        li_apply = page.locator("button.jobs-apply-button, button:has-text('Easy Apply')").first
                        if li_apply.is_visible(timeout=3000):
                            li_apply.click()
                            time.sleep(2)
                    elif "naukri.com" in page.url.lower():
                        naukri_apply = page.locator("button:has-text('Apply'), a:has-text('Apply')").first
                        if naukri_apply.is_visible(timeout=3000):
                            naukri_apply.click()
                            time.sleep(2)
                except Exception:
                    pass

                # Fill all visible inputs
                try:
                    fill_all_visible_inputs(page, profile=CANDIDATE_DATA, cv_path=resume_pdf, job_id=job_id)
                except ZeroFieldsFilledError as ze:
                    print(f"[NOTE] Form filling notice: {ze}")

                # Step 2: Filled Screenshot
                page.screenshot(path=str(step2_path))

                # Activate window on macOS if interactive
                try:
                    import subprocess
                    subprocess.run(["osascript", "-e", 'tell application "Chromium" to activate'], capture_output=True)
                except Exception:
                    pass

                box_msg = (
                    f"\n" + "=" * 70 + "\n"
                    f"CO-PILOT READY: {company} - {role}\n"
                    f"1. Check the opened browser window.\n"
                    f"2. Answer any company-specific questions or complete CAPTCHA if prompted.\n"
                    f"3. Click the final 'Submit Application' button on the website.\n"
                    f"4. Once the confirmation screen ('Thank you / Application Sent') loads, press ENTER here.\n"
                    + "=" * 70 + "\n"
                )
                print(box_msg)

                # Wait for user submission or confirmation screen detection
                max_wait = int(os.getenv("COPILOT_WAIT_TIMEOUT", "45"))
                start_time = time.time()
                is_verified = False
                reason = "Timed out waiting for submission confirmation"

                while time.time() - start_time < max_wait:
                    ver, r = verify_confirmation_screen(page)
                    if ver:
                        is_verified = True
                        reason = r
                        break

                    try:
                        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                            sys.stdin.readline()
                            time.sleep(1.5)
                            is_verified, reason = verify_confirmation_screen(page)
                            break
                    except Exception:
                        pass

                    time.sleep(1.5)

                if not is_verified and time.time() - start_time >= max_wait:
                    is_verified, reason = verify_confirmation_screen(page)

                # Step 3: Result Screenshot
                page.screenshot(path=str(step3_path))

                if is_verified:
                    proof_path = PROOFS_DIR / f"{track}_{safe_comp}_{job_id}_SUCCESS.png"
                    page.screenshot(path=str(proof_path))
                    submission_url = page.url
                    context.close()

                    self.tracker_db.mark_applied_verified(
                        job_id=job_id,
                        proof_screenshot_path=str(proof_path),
                        submission_url=submission_url,
                        notes=f"Submitted via Co-Pilot interactive browser: {reason}",
                    )

                    try:
                        with self.telemetry_db._get_connection() as conn:
                            cur = conn.cursor()
                            cur.execute("SELECT id FROM opportunities WHERE company_name LIKE ?", (f"%{company}%",))
                            row = cur.fetchone()
                            if row:
                                self.telemetry_db.mark_applied_verified(
                                    opportunity_id=row["id"],
                                    proof_screenshot_path=str(proof_path),
                                    submission_url=submission_url,
                                    notes=f"Submitted via Co-Pilot interactive browser: {reason}",
                                )
                    except Exception as e:
                        logger.warning(f"Failed to update telemetry_db for {company}: {e}")

                    print(f"\n[SUCCESS] Verified submission captured for {company}.")
                    print(f"Proof screenshot captured: {proof_path}")
                    return {
                        "status": "APPLIED_VERIFIED",
                        "proof_screenshot_path": str(proof_path),
                        "submission_url": submission_url,
                        "reason": reason,
                        "step1_screenshot": str(step1_path),
                        "step2_screenshot": str(step2_path),
                        "step3_screenshot": str(step3_path),
                    }
                else:
                    context.close()
                    self.tracker_db.mark_needs_human_click(
                        job_id,
                        f"Co-Pilot confirmation check failed: {reason}",
                        str(step3_path),
                    )
                    print(f"\n\033[91m[REJECTED] Confirmation check failed. Screen still shows unsubmitted state.\033[0m")
                    print(f"Details: {reason}")
                    print(f"State screenshot captured: {step3_path}")
                    return {
                        "status": "NEEDS_HUMAN_CLICK",
                        "reason": f"Confirmation check failed: {reason}",
                        "step1_screenshot": str(step1_path),
                        "step2_screenshot": str(step2_path),
                        "step3_screenshot": str(step3_path),
                    }

            except Exception as e:
                context.close()
                self.tracker_db.mark_needs_human_click(job_id, f"Co-Pilot browser error: {e}")
                return {
                    "status": "NEEDS_HUMAN_CLICK",
                    "reason": str(e),
                }
