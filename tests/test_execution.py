"""Unit & Schema Validation Tests for Engine YANG (Execution & Vibe-Coding)."""

import json
import os
import pytest
from core.linkedin_client import DailyThrottleExceeded, LinkedInClient
from engines.yang_execution import YangExecutionEngine
from portfolio_lab.cloner import PortfolioCloner


def test_portfolio_cloner_scaffold(tmp_path):
    cloner = PortfolioCloner(output_base_dir=str(tmp_path))
    blueprint = cloner.scaffold_project(
        project_title="Event Stream Ingestion Service",
        target_company="PostHog",
        target_role="Product Manager - Telemetry",
        tech_stack=["Python", "FastAPI", "Redis", "Kafka"],
        architecture_theme="High-throughput asynchronous telemetry buffer",
    )

    repo_dir = blueprint["path"]
    assert os.path.isdir(repo_dir)

    # Check generated files
    readme_path = os.path.join(repo_dir, "README.md")
    main_py_path = os.path.join(repo_dir, "main.py")
    req_path = os.path.join(repo_dir, "requirements.txt")
    spec_path = os.path.join(repo_dir, "teardown_spec.md")

    assert os.path.exists(readme_path)
    assert os.path.exists(main_py_path)
    assert os.path.exists(req_path)
    assert os.path.exists(spec_path)

    # Verify Mermaid architecture block
    with open(readme_path, "r", encoding="utf-8") as f:
        readme_text = f.read()
        assert "```mermaid" in readme_text
        assert "flowchart TD" in readme_text
        assert "PostHog" in readme_text

    # Verify functional Python prototype
    with open(main_py_path, "r", encoding="utf-8") as f:
        code_text = f.read()
        assert "class IngestionPipeline:" in code_text
        assert "def ingest_event" in code_text


def test_daily_throttle_enforcement(tmp_path):
    state_file = os.path.join(str(tmp_path), "state.json")
    client = LinkedInClient(
        state_file=state_file,
        max_connections_per_day=2,
        max_comments_per_day=1,
        max_messages_per_day=1,
    )

    # Action 1: First connection succeeds
    assert client.send_connection_request("https://linkedin.com/in/user1", "Note 1", dry_run=True) is True
    # Action 2: Second connection succeeds
    assert client.send_connection_request("https://linkedin.com/in/user2", "Note 2", dry_run=True) is True

    # Action 3: Third connection exceeds daily quota and raises DailyThrottleExceeded
    with pytest.raises(DailyThrottleExceeded):
        client.send_connection_request("https://linkedin.com/in/user3", "Note 3", dry_run=True)


def test_yang_execution_dry_run_and_state_schema(tmp_path):
    engine = YangExecutionEngine(dry_run=True)
    engine.reports_dir = str(tmp_path)
    engine.recon_file = os.path.join(str(tmp_path), "recon_latest.json")
    engine.state_file = os.path.join(str(tmp_path), "state.json")
    engine.cloner = PortfolioCloner(output_base_dir=os.path.join(str(tmp_path), "repos"))
    engine.linkedin.state_file = engine.state_file
    engine.linkedin._load_state()

    results = engine.run(max_actions=5)

    assert "timestamp" in results
    assert "cycle" in results
    assert "actions_taken" in results
    assert results["actions_taken"]["projects_scaffolded"] >= 1

    # Verify state.json schema
    assert os.path.exists(engine.state_file)
    with open(engine.state_file, "r", encoding="utf-8") as f:
        state = json.load(f)
        assert "date" in state
        assert "counts" in state
        assert "connections" in state["counts"]
        assert "comments" in state["counts"]
        assert "messages" in state["counts"]
        assert "last_run" in state

