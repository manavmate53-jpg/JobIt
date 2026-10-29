import pytest
from src.profile_engine import ProfileEngine, sanitize_builder_text


def test_profile_loading():
    pe = ProfileEngine()
    profile = pe.profile
    assert profile.personal.name == "Manav Mate"
    assert "Mumbai" in profile.personal.location
    assert profile.personal.email == "manavmate53@gmail.com"
    assert "pm-product-lab" in profile.personal.links.pm_product_lab
    assert len(profile.work_experience) >= 2
    assert any(exp.company == "HireFlo India" for exp in profile.work_experience)
    assert any(exp.company == "NeoManpower" for exp in profile.work_experience)


def test_sanitize_builder_text():
    raw = "He spearheaded—cross-functional synergies -- to scale."
    cleaned = sanitize_builder_text(raw)
    assert "—" not in cleaned
    assert "--" not in cleaned
    assert "synergies" not in cleaned.lower()
    assert "spearheaded" not in cleaned.lower()


def test_grounding_prompt_context():
    pe = ProfileEngine()
    prompt = pe.get_grounding_prompt_context()
    assert "CANDIDATE GROUND TRUTH" in prompt
    assert "Manav Mate" in prompt
    assert "HireFlo India" in prompt
    assert "NeoManpower" in prompt
    assert "EvalGuard AI" in prompt


def test_scaler_system_design_certification():
    pe = ProfileEngine()
    profile = pe.profile
    scaler_cert = next((c for c in profile.certifications if "Scaler" in c.issuer), None)
    assert scaler_cert is not None
    assert "Quora System Design" in scaler_cert.name
    assert "System Architecture" in scaler_cert.core_competencies
    assert profile.skills.system_architecture is not None
    assert "CAP Theorem Trade-Offs" in profile.skills.system_architecture
    assert "system_architecture" in profile.skills.technical
