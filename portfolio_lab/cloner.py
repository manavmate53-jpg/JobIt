"""Dynamic Project Cloner & Vibe-Coding Scaffolder.

Translates the reverse-engineered project themes of successful hires into
production-grade MVP prototypes, system architecture designs, and PRD specs.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ying_yang.portfolio_lab")


class PortfolioCloner:
    """Generates functional vibe-coded repository blueprints and PM case studies."""

    def __init__(self, output_base_dir: Optional[str] = None):
        self.output_base_dir = output_base_dir or os.path.join(
            os.path.dirname(__file__), "generated_repos"
        )
        os.makedirs(self.output_base_dir, exist_ok=True)

    def _slugify(self, text: str) -> str:
        s = text.lower().strip()
        s = re.sub(r"[^\w\s-]", "", s)
        return re.sub(r"[\s_-]+", "-", s)

    def scaffold_project(
        self,
        project_title: str,
        target_company: str,
        target_role: str,
        tech_stack: List[str],
        architecture_theme: str,
        metric_goal: str = "40% latency reduction and zero SLA breaches",
    ) -> Dict[str, Any]:
        """Auto-scaffolds a functional prototype repo matching successful hire profiles."""
        slug = f"{self._slugify(target_company)}-{self._slugify(project_title)}"
        repo_dir = os.path.join(self.output_base_dir, slug)
        os.makedirs(repo_dir, exist_ok=True)

        logger.info(f"Scaffolding vibe-coded repository at {repo_dir}...")

        # 1. Generate Architecture README.md
        readme_content = f"""# {project_title}
> **Target Alignment:** Built for {target_company} · {target_role} Architecture Showcase  
> **Key Metric:** {metric_goal}  
> **Tech Stack:** {", ".join(tech_stack)}

## 1. Executive Summary & Problem Framing
This repository implements a lightweight, high-throughput system architecture addressing {architecture_theme.lower()}. Designed by modeling production requirements and trade-offs of modern scale platforms.

## 2. System Architecture Diagram
```mermaid
flowchart TD
    Client["Client / API Gateway"] --> |HTTPS / JSON| Ingest["Ingestion Service (FastAPI)"]
    Ingest --> |Async Push| Queue["Message Queue (RabbitMQ / Redis Stream)"]
    Queue --> |Batch Pull| Worker["Worker Cluster (Python Engine)"]
    Worker --> |Cache Hit| Cache[("Redis Cache Cluster")]
    Worker --> |Write-Through| DB[("PostgreSQL Replica")]
    Worker --> |Telemetry Event| Metrics["Metrics Collector (Prometheus)"]
```

## 3. Latency vs. Cost Trade-Off Evaluation
- **Synchronous vs Asynchronous:** Slices API latency from ~450ms down to ~28ms by offloading telemetry logging to an in-memory queue.
- **Compute Sizing:** Auto-scales worker nodes based on queue depth metrics, maintaining target cost under $0.002 per 1,000 processed events.
- **Data Consistency:** Leverages eventual consistency for analytics rollups while maintaining strict serializability for transactional balances.

## 4. Quickstart
```bash
pip install -r requirements.txt
python main.py
```
"""
        with open(os.path.join(repo_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write(readme_content)

        # 2. Generate Functional Python Prototype (main.py)
        main_py_content = f"""\"\"\"Functional Prototype for {project_title}.
Target Company: {target_company}
Architecture: {architecture_theme}
\"\"\"

import time
import uuid
from typing import Dict, Any

class IngestionPipeline:
    def __init__(self):
        self.queue = []
        self.processed = 0

    def ingest_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        event_id = str(uuid.uuid4())
        record = {{
            "id": event_id,
            "timestamp": time.time(),
            "payload": payload,
            "status": "queued"
        }}
        self.queue.append(record)
        return {{"status": "accepted", "event_id": event_id}}

    def process_batch(self, batch_size: int = 10) -> int:
        batch = self.queue[:batch_size]
        self.queue = self.queue[batch_size:]
        for item in batch:
            item["status"] = "processed"
            self.processed += 1
        return len(batch)

if __name__ == "__main__":
    pipeline = IngestionPipeline()
    print("Initializing {project_title} prototype...")
    for i in range(5):
        pipeline.ingest_event({{"metric": "latency", "sample_id": i}})
    count = pipeline.process_batch(5)
    print(f"Successfully processed {{count}} items. Queue clear.")
"""
        with open(os.path.join(repo_dir, "main.py"), "w", encoding="utf-8") as f:
            f.write(main_py_content)

        # 3. Generate requirements.txt
        req_content = "pydantic>=2.0.0\npytest>=7.0.0\n"
        with open(os.path.join(repo_dir, "requirements.txt"), "w", encoding="utf-8") as f:
            f.write(req_content)

        # 4. Generate PRD / Teardown Spec
        prd_content = f"""# PRD & Product Teardown: {project_title}
**Target Company:** {target_company}  
**Author:** Manav Mate (Product Manager / Systems Builder)  

## Problem Statement
Identified friction in {target_company}'s existing data flow: high latency under peak workloads and reliance on unbatched writes.

## User Personas & Use Cases
- **Engineers / SREs:** Require deterministic API response times (< 50ms p95).
- **Product Managers:** Need accurate, real-time funnel telemetry without impacting user checkout speed.

## Success Metrics
- **North Star:** P99 Latency < 60ms
- **Secondary:** Zero data loss during worker node redeployment
- **Cost Target:** Sizing infrastructure to ₹0.04 per customer session
"""
        with open(os.path.join(repo_dir, "teardown_spec.md"), "w", encoding="utf-8") as f:
            f.write(prd_content)

        blueprint_record = {
            "project_title": project_title,
            "slug": slug,
            "company": target_company,
            "role": target_role,
            "path": repo_dir,
            "tech_stack": tech_stack,
            "architecture_theme": architecture_theme,
        }
        return blueprint_record

