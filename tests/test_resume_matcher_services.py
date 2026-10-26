import pytest
from src.services.ats_scorer import ATSScorer
from src.services.bullet_selector import BulletSelector
from src.services.keyword_aligner import KeywordAligner
from src.services.writing_quality import WritingQualityAudit
from src.services.page_fit import PageFitValidator


def test_ats_scorer_dimensions():
    scorer = ATSScorer()
    context = {
        "name": "Manav Mate",
        "email": "manavmate53@gmail.com",
        "phone": "+91 85915 95889",
        "headline": "Associate Product Manager",
        "summary": "Early-career Associate Product Manager with hands-on background in PRDs, SQL, and AI workflows.",
        "skills": {
            "technical": ["Python", "SQL", "PRDs", "Jira", "Llama 3.1", "NVIDIA NIM"],
            "operations": ["SLA Management", "Client Discovery"]
        },
        "work_experience": [
            {"company": "HireFlo", "duration": "2026 - Aug 2026", "achievements": ["Cut Llama 3.1 inference compute costs by 40%"]}
        ],
        "featured_projects": [
            {"name": "EvalGuard AI", "summary": "Schema guardrails"}
        ],
        "education": [{"degree": "B.Com"}],
        "certifications": [{"name": "CIPM"}]
    }

    report = scorer.evaluate(
        resume_text=f"{context['name']} {context['summary']} Python SQL PRDs Jira Llama 3.1 NVIDIA NIM",
        resume_context=context,
        job_role="Associate Product Manager",
        job_description="Looking for an Associate Product Manager skilled in PRDs, SQL analytics, Jira, and Python."
    )

    assert report.overall_score >= 70.0
    assert "keyword_match" in report.sub_scores
    assert "skills_coverage" in report.sub_scores
    assert "title_match" in report.sub_scores
    assert "section_completeness" in report.sub_scores
    assert "date_consistency" in report.sub_scores
    assert report.sub_scores["title_match"] >= 80.0


def test_bullet_selector_relevance():
    selector = BulletSelector()
    bullets = [
        "Cut model inference compute costs by 40% on Llama 3.1 via NVIDIA NIM.",
        "Managed field teams of 133 personnel across 200+ commercial projects.",
        "Authored 14+ technical PRDs and user journey maps."
    ]
    exps = [{"company": "Test", "achievements": bullets}]

    # When JD is heavily AI-focused
    ranked_ai = selector.rank_experience_bullets(exps, jd_text="Need experience in AI LLM Llama inference and compute")
    assert "Llama" in ranked_ai[0]["achievements"][0]

    # When JD is heavily operations/team focused
    ranked_ops = selector.rank_experience_bullets(exps, jd_text="Commercial operations team field management logistics")
    assert "133 personnel" in ranked_ops[0]["achievements"][0]


def test_writing_quality_rules():
    # Em dash scrubbing
    dirty_text = "Experienced PM—built AI models -- with high efficiency."
    cleaned = WritingQualityAudit.clean_text(dirty_text)
    assert "—" not in cleaned
    assert "--" not in cleaned

    # Weak opener correction
    weak_bullet = "Responsible for building 1,000-doc parsing pipeline."
    cleaned_bullet = WritingQualityAudit.clean_text(weak_bullet)
    assert not cleaned_bullet.lower().startswith("responsible for")
    assert cleaned_bullet.lower().startswith("led")

    # Anti-hallucination check
    is_valid, issues = WritingQualityAudit.audit_bullet("Cut costs by 40% using NVIDIA NIM.")
    assert is_valid

    # Novel hallucinated number test
    is_valid_fake, issues_fake = WritingQualityAudit.audit_bullet("Scaled revenue to 894371 dollars.")
    assert any("unauthorized metric" in i for i in issues_fake)


def test_page_fit_single_page_enforcement():
    context = {
        "summary": "Short 20 word summary for A4 page fit test.",
        "work_experience": [
            {"company": "Comp A", "achievements": ["Bullet 1", "Bullet 2", "Bullet 3", "Bullet 4", "Bullet 5", "Bullet 6"]}
        ],
        "featured_projects": [{"name": f"P{i}", "summary": f"S{i}"} for i in range(5)]
    }

    # Should enforce max 5 bullets and max 3 projects
    enforced = PageFitValidator.enforce_single_page(context)
    assert len(enforced["work_experience"][0]["achievements"]) == 5
    assert len(enforced["featured_projects"]) == 3

    is_fit, total_words, warnings = PageFitValidator.audit_context(enforced)
    assert is_fit is True
    assert total_words < 540
