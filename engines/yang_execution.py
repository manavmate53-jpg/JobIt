"""ENGINE YANG: Autonomous Execution & Outreach Engine (Cycle: Every 3 Hours).

Tasks:
1. Ingest reports/recon_latest.json
2. Vector 2: Shadow Engagement (like and post high-signal comments on HM posts)
3. Connection Flow: Send connection requests with tailored 300-char notes
4. Vector 3 & 4: Dispatch 'Fixed Your Bug' value-drops & direct executive DMs
5. Vibe-Code Cloner: Scaffolds functional MVP prototype repos matching recent hires
6. State Tracking: Enforces daily throttles and updates reports/state.json
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yaml
from core.browser import StealthBrowser
from core.linkedin_client import DailyThrottleExceeded, LinkedInClient
from core.llm_orchestrator import LLMOrchestrator
from portfolio_lab.cloner import PortfolioCloner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (YANG) %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("yang_execution")


class YangExecutionEngine:
    """Orchestrates 3-hour execution loops for outreach, engagement, and vibe-coding."""

    def __init__(self, config_path: Optional[str] = None, dry_run: bool = True):
        self.dry_run = dry_run
        self.config_path = config_path or os.path.join(REPO_ROOT, "config", "settings.yaml")
        self.settings = self._load_settings()

        self.reports_dir = os.path.join(REPO_ROOT, "reports")
        self.recon_file = os.path.join(self.reports_dir, "recon_latest.json")
        self.state_file = os.path.join(self.reports_dir, "state.json")

        self.browser = StealthBrowser(
            headless=self.settings.get("browser", {}).get("headless", True)
        )
        self.linkedin = LinkedInClient(
            browser=self.browser,
            state_file=self.state_file,
            max_connections_per_day=self.settings.get("throttles", {}).get("daily_limits", {}).get("max_connection_requests", 15),
            max_comments_per_day=self.settings.get("throttles", {}).get("daily_limits", {}).get("max_comments", 10),
            max_messages_per_day=self.settings.get("throttles", {}).get("daily_limits", {}).get("max_outreach_messages", 8),
        )
        self.llm = LLMOrchestrator()
        self.cloner = PortfolioCloner()

    def _load_settings(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to load settings from {self.config_path}: {e}")
            return {}

    def _load_recon_data(self) -> Dict[str, Any]:
        if not os.path.exists(self.recon_file):
            logger.warning(f"No recon file found at {self.recon_file}. Running lightweight YING scan first...")
            from engines.ying_recon import YingReconEngine
            engine = YingReconEngine(dry_run=self.dry_run)
            return engine.run()

        try:
            with open(self.recon_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading recon data: {e}")
            return {}

    def run(self, max_actions: int = 10) -> Dict[str, Any]:
        """Executes the full YANG execution and outreach cycle."""
        logger.info("=" * 70)
        logger.info("⚡ STARTING ENGINE YANG: 3-HOUR EXECUTION CYCLE")
        logger.info(f"Mode: {'DRY-RUN (Simulated)' if self.dry_run else 'LIVE PRODUCTION'}")
        logger.info("=" * 70)

        recon_data = self._load_recon_data()
        execution_results = {
            "timestamp": datetime.datetime.now().isoformat(),
            "cycle": "3_hour_execution",
            "actions_taken": {
                "comments_posted": 0,
                "connections_sent": 0,
                "value_drops_sent": 0,
                "projects_scaffolded": 0,
            },
            "scaffolded_blueprints": [],
        }

        # ----------------------------------------------------------------------
        # 1. VECTOR 2: SHADOW ENGAGEMENT (COMMENTS & LIKES)
        # ----------------------------------------------------------------------
        posts = recon_data.get("active_posts", [])
        logger.info(f"Evaluating {len(posts)} harvested posts for shadow engagement...")
        for post in posts:
            post_url = post["post_url"]
            comment = post.get("suggested_comment", "")
            try:
                success = self.linkedin.shadow_engage(
                    post_url=post_url, comment_text=comment, dry_run=self.dry_run
                )
                if success:
                    execution_results["actions_taken"]["comments_posted"] += 1
            except DailyThrottleExceeded as e:
                logger.warning(f"Daily throttle reached: {e}")
                break

        # ----------------------------------------------------------------------
        # 2. CONNECTION FLOW & DIRECT OUTREACH (VECTOR 4)
        # ----------------------------------------------------------------------
        leads = recon_data.get("leads", [])
        logger.info(f"Evaluating {len(leads)} decision makers for connection requests...")
        for lead in leads:
            linkedin_url = lead.get("linkedin_url")
            if not linkedin_url:
                continue

            note = self.llm.generate_connection_note(
                recipient_name=lead["name"],
                company=lead["company"],
                role=lead.get("title", "Product"),
            )

            try:
                success = self.linkedin.send_connection_request(
                    profile_url=linkedin_url, note=note, dry_run=self.dry_run
                )
                if success:
                    execution_results["actions_taken"]["connections_sent"] += 1
            except DailyThrottleExceeded as e:
                logger.warning(f"Daily throttle reached: {e}")
                break

        # ----------------------------------------------------------------------
        # 3. VECTOR 3: 'FIXED YOUR BUG' VALUE-DROPS
        # ----------------------------------------------------------------------
        teardowns = recon_data.get("teardown_vectors", [])
        logger.info(f"Dispatching {len(teardowns)} 'Fixed Your Bug' value-drop payloads...")
        for td in teardowns:
            pitch = td.get("outreach_pitch", {})
            dm_text = f"Subject: {pitch.get('subject')}\n\n{pitch.get('body')}"
            try:
                success = self.linkedin.send_direct_message(
                    profile_url=f"https://www.linkedin.com/in/{td['company'].lower()}-lead",
                    message=dm_text,
                    dry_run=self.dry_run,
                )
                if success:
                    execution_results["actions_taken"]["value_drops_sent"] += 1
            except DailyThrottleExceeded as e:
                logger.warning(f"Daily throttle reached: {e}")
                break

        # ----------------------------------------------------------------------
        # 4. VIBE-CODE PROJECT CLONER (REPLICATING RECENT HIRES)
        # ----------------------------------------------------------------------
        hires = recon_data.get("reverse_engineered_profiles", [])
        logger.info(f"Scaffolding vibe-coded repositories for {len(hires)} reverse-engineered profiles...")
        seen_companies = set()
        for hire in hires:
            comp = hire["company"]
            if comp in seen_companies:
                continue
            seen_companies.add(comp)

            tech_stack = hire.get("tech_stack", ["Python", "FastAPI", "Redis"])
            arch = hire.get("project_architectures", ["Distributed async event ingestion pipeline"])[0]

            blueprint = self.cloner.scaffold_project(
                project_title=f"{comp} Telemetry & Scale Engine",
                target_company=comp,
                target_role=hire.get("role", "Product Manager"),
                tech_stack=tech_stack,
                architecture_theme=arch,
            )
            execution_results["scaffolded_blueprints"].append(blueprint)
            execution_results["actions_taken"]["projects_scaffolded"] += 1

        # Persist execution state
        if hasattr(self, "state_file") and self.state_file:
            self.linkedin.state_file = self.state_file
        self.linkedin._save_state()

        logger.info("=" * 70)
        logger.info("✅ ENGINE YANG COMPLETED EXECUTION CYCLE SUCCESSFULLY")
        logger.info(f"Summary of Actions: {execution_results['actions_taken']}")
        logger.info("=" * 70)
        return execution_results


def main():
    parser = argparse.ArgumentParser(description="Run YANG Execution Cycle")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Run in dry-run mode")
    parser.add_argument("--live", action="store_true", help="Run in live mode with network actions")
    args = parser.parse_args()

    engine = YangExecutionEngine(dry_run=not args.live)
    engine.run()


if __name__ == "__main__":
    main()

