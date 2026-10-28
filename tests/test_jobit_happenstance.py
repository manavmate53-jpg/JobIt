import datetime
import pytest
from src.scrapers.base_scraper import ScrapedJob
from src.happenstance.manager import HappenstanceManager
from src.happenstance.models import Direction, InteractionEdge, InteractionType, PersonNode


def test_happenstance_manager_initialization(tmp_path):
    graph_file = str(tmp_path / "test_graph.json")
    mgr = HappenstanceManager(graph_path=graph_file)

    assert "me" in mgr.graph.nodes
    assert len(mgr.graph.nodes) >= 4  # Includes seeded nodes


def test_warm_intro_for_job(tmp_path):
    graph_file = str(tmp_path / "test_graph.json")
    mgr = HappenstanceManager(graph_path=graph_file)

    job = ScrapedJob(
        company="Perplexity AI",
        role="AI Product Manager - LLM Evaluation & Search Quality",
        job_url="https://wellfound.com/jobs/perplexity-ai-pm-llm-eval-search-948101",
        source="Wellfound"
    )

    paths = mgr.find_warm_paths_for_job(job)
    assert len(paths) >= 1

    best_path = paths[0]
    assert best_path.degree == 2
    assert best_path.target.name == "Aravind Srinivas"
    assert best_path.bridge.name == "Rohan Deshmukh"

    pkg = mgr.generate_referral_package(best_path, job)
    assert pkg["type"] == "WARM_MUTUAL_INTRO"
    assert "Perplexity AI" in pkg["intro_request_subject"]
    assert "NVIDIA NIM" in pkg["forwardable_blurb"]
    assert pkg["linkedin_chars"] <= 300


def test_network_natural_language_query(tmp_path):
    graph_file = str(tmp_path / "test_graph.json")
    mgr = HappenstanceManager(graph_path=graph_file)

    results = mgr.query("Find founders at Dukaan or Perplexity AI")
    assert len(results) >= 1
    companies = [p.target.company for p in results]
    assert any("Perplexity" in c or "Dukaan" in c for c in companies)

