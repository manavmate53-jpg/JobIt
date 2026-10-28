"""Warm Introduction Generator & Actionable Output Engine for Happenstance AI.

Generates:
1. Warm Intro Request to the Bridge Contact
2. Forwardable Candidate Blurb (ready for 1-click forwarding)
3. Direct 1st-Degree Re-engagement Notes
4. LinkedIn Quick Messages (< 300 characters)
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from src.happenstance.models import WarmIntroPath


class WarmIntroGenerator:
    """Drafts contextual warm referral requests and forwardable blurbs."""

    def __init__(self, candidate_name: str = "Manav Mate", candidate_email: str = "manavmate53@gmail.com"):
        self.candidate_name = candidate_name
        self.candidate_email = candidate_email

    def generate_referral_package(
        self,
        path: WarmIntroPath,
        target_role: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generates complete warm intro package based on path degree and strength."""
        role_title = target_role or path.target.headline or "Product Manager"
        target_company = path.target_company or path.target.company or "the team"

        if path.degree == 2 and path.bridge:
            bridge_name = path.bridge.name
            target_name = path.target.name
            strength_cat = path.path_strength.category if path.path_strength else "Connection"

            # 1. Warm Intro Request to Bridge Contact
            intro_request_subject = f"Quick question re: {target_company} / intro to {target_name}?"
            intro_request_body = (
                f"Hi {bridge_name.split()[0]},\n\n"
                f"Hope all is well with you! I noticed on your network that you're connected to {target_name} at {target_company}.\n\n"
                f"I am actively applying for the {role_title} opening there and would love to connect with {target_name.split()[0]} "
                f"to learn more about their product priorities and explore if my background is a strong fit.\n\n"
                f"Would you be comfortable facilitating a warm introduction? I've included a short, forwardable blurb below to make "
                f"it frictionless for you if so. Totally understand if you don't know them well enough or if now isn't a good time!\n\n"
                f"Best regards,\n"
                f"{self.candidate_name}\n"
                f"{self.candidate_email}\n\n"
                f"----------------------------------------\n"
                f"FORWARDABLE BLURB FOR {target_name.upper()}:\n\n"
                f"{self._build_forwardable_blurb(target_name, target_company, role_title)}"
            )

            # 2. LinkedIn Quick Note to Bridge Contact (<300 chars)
            clean_bridge_first = bridge_name.split()[0]
            clean_target_first = target_name.split()[0]
            linkedin_bridge_note = (
                f"Hi {clean_bridge_first}, hope you're doing well! Saw you're connected to {clean_target_first} at {target_company}. "
                f"I'm applying for their {role_title} role (cut Llama compute 40% via NVIDIA NIM; bootstrapped 50+ enterprise clients). "
                f"Would you be open to a quick intro? Demos: https://manavmate53-jpg.github.io/pm-product-lab/#hub"
            )
            if len(linkedin_bridge_note) > 298:
                linkedin_bridge_note = (
                    f"Hi {clean_bridge_first}! Saw you know {clean_target_first} at {target_company}. "
                    f"Applying for their {role_title} role (cut Llama compute 40%, 50+ enterprise clients). "
                    f"Open to a quick intro? Demos: https://manavmate53-jpg.github.io/pm-product-lab/#hub"
                )

            return {
                "type": "WARM_MUTUAL_INTRO",
                "target_profile": path.target.to_dict(),
                "bridge_profile": path.bridge.to_dict(),
                "path_visual": f"You ➔ [{bridge_name} ({strength_cat})] ➔ [{target_name} ({target_company})]",
                "intro_request_subject": intro_request_subject,
                "intro_request_body": intro_request_body,
                "forwardable_blurb": self._build_forwardable_blurb(target_name, target_company, role_title),
                "linkedin_bridge_note": linkedin_bridge_note,
                "linkedin_chars": len(linkedin_bridge_note),
                "actionable_next_steps": [
                    f"1. Send intro request email to {bridge_name} ({path.bridge.primary_email or 'via LinkedIn'})",
                    f"2. Or send quick LinkedIn message to {bridge_name}",
                    f"3. When {bridge_name} agrees, they forward the pre-drafted blurb to {target_name}"
                ]
            }

        else:
            # 1st-degree direct connection
            target_first = path.target.name.split()[0]
            reengagement_subject = f"Catching up / {role_title} at {target_company}"
            reengagement_body = (
                f"Hi {target_first},\n\n"
                f"Hope you are having a productive week! I saw that {target_company} is currently expanding the team and hiring for {role_title}.\n\n"
                f"Given our connection, I wanted to reach out directly to hear your perspective on the team's roadmap. "
                f"Most recently at HireFlo, I led AI inference optimization cutting Llama 3.1 compute costs by 40% via NVIDIA NIM, "
                f"and previously bootstrapped NeoManpower to 50+ enterprise clients with zero SLA breaches.\n\n"
                f"I've also published interactive product prototypes in my PM Lab: https://manavmate53-jpg.github.io/pm-product-lab/#hub\n\n"
                f"Would you have 10 minutes for a quick catch-up or be open to referring me internally?\n\n"
                f"Best regards,\n"
                f"{self.candidate_name}\n"
                f"{self.candidate_email}"
            )

            linkedin_direct_note = (
                f"Hi {target_first}, hope you're doing great! Saw the {role_title} opening at {target_company}. "
                f"At HireFlo I cut Llama 3.1 compute costs by 40% via NVIDIA NIM and scaled 50+ enterprise clients at NeoManpower. "
                f"Would love to catch up! Live PM Lab: https://manavmate53-jpg.github.io/pm-product-lab/#hub"
            )
            if len(linkedin_direct_note) > 298:
                linkedin_direct_note = (
                    f"Hi {target_first}! Saw the {role_title} role at {target_company}. "
                    f"Cut Llama 3.1 compute 40% via NVIDIA NIM, scaled 50+ enterprise clients at NeoManpower. "
                    f"Would love to catch up! Live PM Lab: https://manavmate53-jpg.github.io/pm-product-lab/#hub"
                )

            return {
                "type": "DIRECT_REENGAGEMENT",
                "target_profile": path.target.to_dict(),
                "bridge_profile": None,
                "path_visual": f"You ➔ [{path.target.name} ({target_company})]",
                "intro_request_subject": reengagement_subject,
                "intro_request_body": reengagement_body,
                "forwardable_blurb": None,
                "linkedin_bridge_note": linkedin_direct_note,
                "linkedin_chars": len(linkedin_direct_note),
                "actionable_next_steps": [
                    f"1. Send direct re-engagement email to {path.target.name} ({path.target.primary_email or 'via LinkedIn'})",
                    f"2. Connect or send LinkedIn message mentioning mutual background",
                    f"3. Share PM Lab link and single-page ATS CV"
                ]
            }

    def _build_forwardable_blurb(self, target_name: str, target_company: str, role_title: str) -> str:
        """Constructs an authentic 2-paragraph forwardable blurb."""
        target_first = target_name.split()[0]
        return (
            f"Hi {target_first},\n\n"
            f"I wanted to connect you with {self.candidate_name}, an early-career Product Manager who is interested in the "
            f"{role_title} role at {target_company}. {self.candidate_name.split()[0]} brings a rare combination of 0-to-1 founder grit "
            f"and hands-on AI product execution.\n\n"
            f"Key highlights from his track record:\n"
            f"• AI Inference Optimization: At HireFlo, reduced Llama 3.1 model inference compute costs by 40% via NVIDIA NIM containerization "
            f"and architected document parsing pipelines indexing 1,000+ files in under 10 minutes at 98% precision.\n"
            f"• Bootstrapped Execution: Founded NeoManpower from scratch, closing 50+ B2B corporate enterprise clients and managing 200+ field operations "
            f"across Mumbai with zero SLA breaches.\n"
            f"• Interactive Product Prototypes: Built live interactive PM case studies and schema walkthroughs accessible at "
            f"https://manavmate53-jpg.github.io/pm-product-lab/#hub\n"
            f"• Certified Delivery: Certified International Project Manager (CIPM) trained in agile sprint backlogs and technical PRDs.\n\n"
            f"I think {self.candidate_name.split()[0]} would be a high-velocity addition to the team. You can reach him directly at {self.candidate_email}. "
            f"Let me know if you'd like me to introduce you both directly!"
        )
