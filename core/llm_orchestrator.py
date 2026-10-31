"""LLM Orchestration Layer for Intelligent Tailoring & Vibe-Coding.

Interfaces with Gemini API and local heuristic fallback engines:
- Vector 1: Profile skill & architecture deconstruction
- Vector 2: Shadow Engagement comment generation (matching tone & vocabulary)
- Vector 3: "Fixed Your Bug" value-drop teardowns
- Vector 4: Executive InMail / DM drafting
- Dynamic Project Vibe-Code blueprints
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
import requests
import yaml

logger = logging.getLogger("ying_yang.llm")


class LLMOrchestrator:
    """Manages prompt rendering and inference via Gemini API or heuristic fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        prompts_path: Optional[str] = None,
        model_name: str = "gemini-2.5-flash",
    ):
        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("LLM_API_KEY")
            or ""
        )
        self.model_name = model_name
        self.prompts = self._load_prompts(prompts_path)

    def _load_prompts(self, path: Optional[str]) -> Dict[str, Any]:
        target_path = path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "config", "prompts.yaml"
        )
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Could not load prompts.yaml from {target_path}: {e}")
            return {}

    def _call_gemini(self, system_instruction: str, user_content: str) -> Optional[str]:
        """Calls Google Gemini Generative Language REST API."""
        if not self.api_key:
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_instruction}\n\nTask:\n{user_content}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 1024,
            },
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
            else:
                logger.debug(f"Gemini API returned status {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            logger.debug(f"Gemini API invocation failed: {e}")

        return None

    def generate_comment(
        self, author_name: str, author_title: str, company: str, post_content: str
    ) -> str:
        """Generates a high-signal, context-aware comment matching the HM's tone (Vector 2)."""
        prompt_cfg = self.prompts.get("shadow_engagement", {})
        sys_prompt = prompt_cfg.get("system", "Write a high-signal technical observation.")
        user_prompt = (
            f"Author: {author_name} ({author_title} at {company})\n"
            f"Post Content: \"{post_content}\"\n"
            "Draft a high-signal comment matching tone and vocabulary (max 2-3 sentences):"
        )

        res = self._call_gemini(sys_prompt, user_prompt)
        if res:
            return res

        # Heuristic Fallback matching high-signal PM tone
        post_lower = post_content.lower()
        if "scale" in post_lower or "latency" in post_lower or "architecture" in post_lower:
            return (
                f"Spot-on on the trade-offs around throughput versus data consistency here. "
                f"Balancing asynchronous queue workloads against synchronous SLA boundaries is where "
                f"most edge cases emerge in production. Curious how your team handles consumer backpressure?"
            )
        elif "ai" in post_lower or "llm" in post_lower or "agent" in post_lower:
            return (
                f"Strong perspective. The real bottleneck in production AI workflows is rarely model reasoning "
                f"— it's telemetry fidelity, token latency sizing, and deterministic output schema validation. "
                f"Evaluating compute boundaries early saves immense operational overhead."
            )
        else:
            return (
                f"Strong breakdown of this operational dynamic. Aligning cross-functional priorities "
                f"against measurable north-star telemetry is where sustainable execution happens. "
                f"Appreciate you sharing this perspective."
            )

    def generate_fixed_your_bug(
        self,
        decision_maker: str,
        role: str,
        company: str,
        flaw_description: str,
        solution_details: str,
        prototype_link: str,
    ) -> Dict[str, str]:
        """Generates a Vector 3 'Fixed Your Bug' value-drop outreach pitch."""
        subject = f"I fixed your {flaw_description[:30]} for free — Future {role}"

        body = (
            f"Hi {decision_maker.split()[0]},\n\n"
            f"Was diving deep into {company}'s product flow this week and noticed a critical friction point: "
            f"{flaw_description}.\n\n"
            f"Rather than just sending a standard resume, I engineered a concrete architectural fix: "
            f"{solution_details}.\n\n"
            f"Here is the interactive spec & blueprint: {prototype_link}\n\n"
            f"Would love to share 2 quick ideas on your product telemetry whenever you have 5 minutes. "
            f"No pitch, just builder to builder.\n\n"
            f"Best,\nManav Mate\nProduct Manager | System Design"
        )
        return {"subject": subject, "body": body}

    def generate_connection_note(self, recipient_name: str, company: str, role: str) -> str:
        """Drafts a high-converting 300-char LinkedIn connection note."""
        first = recipient_name.split()[0]
        note = (
            f"Hi {first}, saw {company}'s builds in {role}. At HireFlo I cut Llama 3.1 compute costs "
            f"by 40% and led 200+ ops deployments. Would love to follow your team's work and connect!"
        )
        return note[:300]

    def generate_executive_dm(
        self, recipient_name: str, company: str, role: str, highlights: str
    ) -> str:
        """Drafts a direct high-priority DM for decision-makers (Vector 4)."""
        first = recipient_name.split()[0]
        dm = (
            f"Hi {first},\n\n"
            f"Quick note — tracking {company}'s growth across {role}. "
            f"Recently completed Scaler's System Design certification, focusing on latency/cost "
            f"trade-offs, API schemas, and distributed scaling. {highlights}\n\n"
            f"If you are exploring early-career PM builders who speak engineering fluently, "
            f"here is my portfolio hub: https://manavmate53-jpg.github.io/pm-product-lab/#hub\n\n"
            f"Best,\nManav"
        )
        return dm

