# JobIt ⚡

**Production-grade, local-first automated job hunting, ATS resume tailoring, recruiter outreach, and application tracking system.**

Built specifically for early-career tech product managers and founder-operators transitioning from commercial operations to product execution.

---

## 🎯 Core Design Philosophy

1. **Local-First & Modular**: Runs entirely on your local machine with SQLite, Playwright, and BeautifulSoup. No mandatory cloud vendor dependencies or monthly recurring SaaS subscription lock-ins.
2. **Grounded Candidate Truth**: Strictly represents the candidate as an early-career builder and bootstrapped founder who transitioned from on-ground operations to tech product management, **never** a tenured corporate executive.
3. **Zero Corporate Jargon**: Resumes, cover letters, and outreach emails use a concise, human builder tone. Strictly eliminates em dashes (`—`), double hyphens (`--`), and empty corporate buzzwords (no "spearheaded cross-functional synergies").
4. **Deterministic Fail-Safe Outreach**: All email and messaging features default to `--dry-run` mode. Outreach drafts and verified recruiter permutations are saved locally for inspection before anything can be dispatched.

---

## 🏗️ Architecture & Modules

```
JobIt/
├── config/
│   ├── candidate_profile.json   # Candidate ground truth, achievements, interactive builds, CTC
│   └── search_queries.json      # Search queries, portals, locations, and negative traps
├── src/
│   ├── scrapers/
│   │   ├── base_scraper.py      # Abstract scraper interface & ScrapedJob model
│   │   ├── filter_rules.py      # Negative domain trap detector (factory ops, pharma, NBFC, 5+ yrs)
│   │   ├── linkedin_scraper.py  # LinkedIn public job search adapter (Playwright + BeautifulSoup)
│   │   ├── naukri_scraper.py    # Naukri job search adapter
│   │   └── __init__.py          # Unified scraper coordinator
│   ├── profile_engine.py        # Candidate profile parser, pydantic schemas, and prompt injection
│   ├── scoring_engine.py        # 2-stage fit evaluator (Deterministic 0-40 + Semantic 0-60)
│   ├── tailor_engine.py         # ATS single-page HTML/MD/PDF generator and builder cover letter
│   ├── outreach_engine.py       # MX verification, email permutations, and dry-run dispatcher
│   ├── tracker_db.py            # SQLite application database & pipeline tracker
│   └── dashboard.py             # Lightweight local web dashboard (Flask)
├── templates/
│   ├── resume_template.html     # Single-page A4 print-optimized ATS resume template
│   ├── resume_template.md       # Clean Markdown resume template
│   └── cover_letter_template.txt# Crisp, human builder outreach note (under 130 words)
├── exports/
│   ├── resumes/                 # Generated HTML, Markdown, and single-page PDF resumes
│   ├── cover_letters/           # Generated human cover letter notes (.txt and .md)
│   └── outreach_drafts/         # Safe dry-run outreach inspection files (.txt and .json)
├── data/
│   ├── .gitkeep
│   └── jobit.db                 # SQLite local database
├── tests/                       # Complete pytest automated test suite
├── cli.py                       # Interactive CLI entrypoint (Rich + Click)
├── requirements.txt             # Production dependencies
└── .env.example                 # Environment configuration template
```

---

## 🚀 Quickstart & Setup

### 1. Clone & Enter Directory
```bash
git clone https://github.com/manavmate53-jpg/JobIt.git
cd JobIt
```

### 2. Install Dependencies
```bash
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and populate any optional keys:
```bash
cp .env.example .env
```
> **Note**: JobIt works 100% out-of-the-box in local heuristic mode without requiring any paid API keys. If `GEMINI_API_KEY` or `OPENAI_API_KEY` is set, semantic scoring will automatically leverage LLM inference.

---

## 💻 CLI Usage

JobIt provides an interactive CLI built with `click` and `rich`:

### 1. Scrape Job Portals
Scrape Mumbai and Remote postings across LinkedIn and Naukri, filter out domain traps, and compute fit scores:
```bash
python3 cli.py scrape --portal all --keywords "Product Manager" --limit 20
```

Options:
- `--portal`: `linkedin`, `naukri`, or `all` (default: `all`)
- `--keywords`: Target job keywords (default: `"Product Manager"`)
- `--location`: Search location (default: `"Mumbai"`)
- `--limit`: Maximum postings to fetch (default: `20`)

### 2. View Ranked Applications
Display all stored applications ordered by fit score:
```bash
python3 cli.py rank
```
Filter by decision:
```bash
python3 cli.py rank --decision APPLY
```

### 3. Application Deep Dive
Inspect gap analysis, matching competencies, recruiter info, and recommended pitch angle:
```bash
python3 cli.py view <job_id>
```

### 4. Tailor Resume & Cover Letter
Automatically tailor an ATS-compliant resume and a human under-130-word cover letter:
```bash
python3 cli.py tailor <job_id>
```
Outputs:
- Single-page A4 PDF resume rendered via headless Chromium (`exports/resumes/Manav_Mate_[Company]_CV.pdf`)
- ATS HTML file (`exports/resumes/Manav_Mate_[Company]_CV.html`)
- Markdown CV (`exports/resumes/Manav_Mate_[Company]_CV.md`)
- Builder Cover Letter (`exports/cover_letters/Manav_Mate_[Company]_CoverLetter.txt`)

### 5. Recruiter Outreach & Permutations
Verify domain DNS MX records, formulate enterprise email permutations, and draft a LinkedIn note:
```bash
# Safe dry-run (default: logs to exports/outreach_drafts/ without sending)
python3 cli.py outreach <job_id> --dry-run

# Live dispatch (requires SMTP credentials in .env)
python3 cli.py outreach <job_id> --send
```

### 6. Pipeline Status & Follow-Up Alerts
View active pipeline stages and alerts for applications awaiting follow-up:
```bash
python3 cli.py status
```

### 7. End-to-End Autonomous Pipeline
Run the entire workflow (scrape -> filter -> evaluate -> tailor top APPLY jobs -> generate outreach drafts):
```bash
python3 cli.py run-all --limit 10
```

### 8. Local Web Dashboard
Launch the visual pipeline dashboard:
```bash
python3 cli.py dashboard --port 5000
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) to view your active application funnel.

---

## 🛡️ Negative Filtering & Domain Trap Detector

JobIt automatically filters out irrelevant or mislabeled postings before scoring:
- **Physical Manufacturing / Factory Operations**: Discards mattress production, foam manufacturing, plant engineering, injection molding, and factory operations.
- **Pharmaceutical Brand Marketing**: Discards HCP marketing, clinical detailing, medical vaccines, and pharma sales.
- **Offline Vehicle / Equipment NBFC Financing**: Discards construction equipment loans, commercial vehicle branch credit, tractor loan underwriting, and repossession.
- **Seniority Traps**: Discards roles mandating 5+ years of corporate enterprise product management or VP/Director titles.

---

## 📊 Two-Stage Scoring Engine

Each job is evaluated against `config/candidate_profile.json`:
1. **Deterministic Rule Score (0 to 40 pts)**:
   - Location match (Mumbai / Navi Mumbai / Remote): **+15 pts**
   - Experience band match (0-3 years / entry / APM): **+15 pts**
   - Domain match (Software, AI, Fintech, SaaS, Logistics, Fleet, Operations): **+10 pts**
2. **Semantic Strengths Evaluation (0 to 60 pts)**:
   - Matches role needs against candidate's demonstrated background (HireFlo India NVIDIA NIM optimization, 1,000-doc parsing pipeline, NeoManpower 50+ B2B clients & 133 personnel, EvalGuard AI, VeriShield, AutoMatch IQ).
   - Total Score:
     * **75 - 100**: `APPLY` (auto-tailoring candidate)
     * **55 - 74**: `CONSIDER`
     * **< 55**: `SKIP`

---

## 🧪 Running Automated Tests

Run the full pytest test suite:
```bash
python3 -m pytest tests/ -v
```
All 15 unit and integration tests validate profile parsing, filter traps, deterministic scoring, PDF compilation, MX lookups, and SQLite database operations.

---

## 🔒 Safety & Privacy Policy

- JobIt runs strictly on your local machine.
- Your personal candidate details and application histories remain in your local `data/jobit.db` SQLite database.
- `--dry-run` is active by default on outreach to prevent unintentional emails. Live sending requires explicit `--send` and valid SMTP environment variables.

---

## 👤 Candidate Ground Truth

- **Candidate**: Manav Mate
- **Location**: Jogeshwari East, Mumbai, Maharashtra, India
- **Phone**: +91 85915 95889 | **Email**: manavmate53@gmail.com
- **Main Portfolio**: [https://manavmate53-jpg.github.io/portfolio/#hero](https://manavmate53-jpg.github.io/portfolio/#hero)
- **Interactive PM Product Lab**: [https://manavmate53-jpg.github.io/pm-product-lab/#hub](https://manavmate53-jpg.github.io/pm-product-lab/#hub)
- **GitHub**: [https://github.com/manavmate53-jpg](https://github.com/manavmate53-jpg)
- **LinkedIn**: [https://linkedin.com/in/manavmate](https://linkedin.com/in/manavmate)
- **Compensation Baseline**: Current CTC: ₹8 LPA | Target Expected: ₹11 - ₹16 LPA
