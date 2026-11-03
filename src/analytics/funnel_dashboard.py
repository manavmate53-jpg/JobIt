"""
JobIt v2.0 - Rich Funnel Telemetry Dashboard
Visual CLI reporting, conversion rates, and automated bottleneck diagnostics.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.analytics.telemetry_db import TelemetryDB

logger = logging.getLogger(__name__)


class FunnelDashboard:
    """Renders a rich terminal analytics dashboard and diagnostic report."""

    def __init__(self, db: Optional[TelemetryDB] = None):
        self.db = db or TelemetryDB()
        self.console = Console()

    def render(self) -> None:
        summary = self.db.get_funnel_summary()
        pillar_metrics = self.db.get_pillar_metrics()
        top_opps = self.db.get_top_opportunities(limit=5)

        self.console.print("\n")
        self.console.print(
            Panel.fit(
                "[bold cyan]JobIt v2.0: Signal-Driven Startup Outbound & Funnel Telemetry[/bold cyan]\n"
                "[dim]Bypassing Enterprise ATS Degree Gates &bull; 3-Pillar High-Intent Outbound Engine[/dim]",
                border_style="cyan"
            )
        )

        # 1. Main Conversion Funnel Table
        table = Table(title="[bold yellow]Targeting & Conversion Funnel[/bold yellow]", expand=True)
        table.add_column("Funnel Stage", style="bold white", justify="left")
        table.add_column("Count", justify="center", style="bold green")
        table.add_column("Stage Conversion", justify="center", style="cyan")
        table.add_column("Status Benchmark", justify="left", style="dim")

        sig = summary["signals_captured"]
        opp = summary["opportunities_identified"]
        qual = summary["qualified_opportunities"]
        sent = summary["outreach_sent"]
        replies = summary["responses_received"]
        screens = summary["screening_calls"]
        offers = summary["offers_received"]

        table.add_row("1. Fresh Funding Signals Captured", str(sig), "-", "Inc42, Entrackr, YourStory feeds")
        table.add_row("2. Opportunities Identified", str(opp), f"{round(opp/sig*100, 1)}%" if sig else "0%", "3-Pillar role cross-checks")
        table.add_row("3. Qualified Startups (Score >= 70)", str(qual), f"{round(qual/opp*100, 1)}%" if opp else "0%", "Filtered via Gatekeeper matrix")
        table.add_row("4. Outbound DMs & Notes Sent", str(sent), f"{round(sent/qual*100, 1)}%" if qual else "0%", "Goal: 10 Founder DMs / day")
        table.add_row("5. Founder / TA Replies", str(replies), f"{summary['response_rate_pct']}%", "Benchmark: 15% - 25% target")
        table.add_row("6. Screening Calls Scheduled", str(screens), f"{round(screens/sent*100, 1)}%" if sent else "0%", "Benchmark: 4 - 6 per sprint")
        table.add_row("7. Full-Time Offers", str(offers), f"{round(offers/screens*100, 1)}%" if screens else "0%", "Target: 1 - 2 offers")

        self.console.print(table)
        self.console.print("\n")

        # 2. Pillar Distribution Table
        p_table = Table(title="[bold magenta]3-Pillar Distribution & Health[/bold magenta]", expand=True)
        p_table.add_column("Strategic Pillar", style="bold white")
        p_table.add_column("Active Opportunities", justify="center", style="cyan")
        p_table.add_column("Average Rubric Score", justify="center", style="green")
        p_table.add_column("Core Value Proposition", style="dim")

        pillar_descs = {
            "PILLAR_1_FOUNDERS_OFFICE": "NeoManpower 0-50+ clients, P&L ownership, HireFlo 5-tier monetization",
            "PILLAR_2_PRODUCT_OPERATIONS": "133 field personnel, 0 SLA breaches, 12 days to 48 hrs reconciliation",
            "PILLAR_3_AI_APM": "HireFlo 1,000-doc parsing, 40% Llama 3.1 compute cost reduction, 14+ PRDs"
        }

        for p in pillar_metrics:
            p_id = p.get("pillar", "UNKNOWN")
            p_table.add_row(
                p_id.replace("PILLAR_", "Pillar ").replace("_", " "),
                str(p.get("count", 0)),
                f"{round(p.get('avg_score', 0), 1)}/100",
                pillar_descs.get(p_id, "Targeted proof-of-work pitches")
            )

        self.console.print(p_table)
        self.console.print("\n")

        # 3. Bottleneck Diagnostic Engine
        self.console.print("[bold red]Bottleneck Diagnostics & Action Items:[/bold red]")
        if sent == 0:
            self.console.print("  [yellow]&bull; Zero outbound sent yet.[/yellow] Run `python3 cli.py pack` to generate today's Action Pack and dispatch top 10 founder notes.")
        elif summary["response_rate_pct"] < 10.0 and sent >= 15:
            self.console.print("  [red]&bull; Low response rate (<10%).[/red] Recommendation: Increase proof-of-work link prominence and tighten connection note character count.")
        elif screens == 0 and replies >= 3:
            self.console.print("  [yellow]&bull; Replies received but no screening calls yet.[/yellow] Recommendation: Push for immediate 15-minute sync with dynamic salary quote alignment.")
        else:
            self.console.print("  [green]&bull; Funnel telemetry healthy.[/green] Continue executing 10 Founder DMs + 5 Wellfound applications daily.")

        self.console.print("\n")

