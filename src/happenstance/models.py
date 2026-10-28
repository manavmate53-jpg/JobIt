"""Core graph data models for Happenstance AI Relationship Intelligence."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class InteractionType(str, Enum):
    EMAIL = "email"
    CALENDAR = "calendar"
    LINKEDIN = "linkedin"
    MANUAL = "manual"


class Direction(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BIDIRECTIONAL = "bidirectional"


@dataclass
class PersonNode:
    """Represents an individual in the professional network."""
    id: str
    name: str
    primary_email: Optional[str] = None
    headline: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    domain: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    linkedin_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "primary_email": self.primary_email,
            "headline": self.headline,
            "company": self.company,
            "location": self.location,
            "domain": self.domain,
            "tags": self.tags,
            "notes": self.notes,
            "linkedin_url": self.linkedin_url,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PersonNode:
        return cls(
            id=data["id"],
            name=data["name"],
            primary_email=data.get("primary_email"),
            headline=data.get("headline"),
            company=data.get("company"),
            location=data.get("location"),
            domain=data.get("domain"),
            tags=data.get("tags", []),
            notes=data.get("notes"),
            linkedin_url=data.get("linkedin_url"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class InteractionEdge:
    """Represents a communication or connection touchpoint between two nodes."""
    source_id: str
    target_id: str
    interaction_type: InteractionType
    timestamp: datetime.datetime
    direction: Direction = Direction.BIDIRECTIONAL
    thread_count: int = 1
    subject_summary: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "interaction_type": self.interaction_type.value,
            "timestamp": self.timestamp.isoformat(),
            "direction": self.direction.value,
            "thread_count": self.thread_count,
            "subject_summary": self.subject_summary,
            "metadata": self.metadata,
        }


@dataclass
class RelationshipStrength:
    """Multi-factor relationship strength evaluation."""
    score: float  # 0.0 - 100.0
    category: str  # 'Strong Connection', 'Moderate', 'Weak', 'Dormant'
    frequency_score: float
    recency_score: float
    direction_score: float
    channel_diversity_score: float
    last_interaction_date: Optional[datetime.datetime]
    days_since_interaction: int
    total_touchpoints: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 1),
            "category": self.category,
            "frequency_score": round(self.frequency_score, 1),
            "recency_score": round(self.recency_score, 1),
            "direction_score": round(self.direction_score, 1),
            "channel_diversity_score": round(self.channel_diversity_score, 1),
            "last_interaction_date": self.last_interaction_date.isoformat() if self.last_interaction_date else None,
            "days_since_interaction": self.days_since_interaction,
            "total_touchpoints": self.total_touchpoints,
        }


@dataclass
class WarmIntroPath:
    """A pathway to reach a target profile via direct contact or mutual bridge."""
    target: PersonNode
    bridge: Optional[PersonNode] = None  # None for 1st-degree
    degree: int = 1  # 1 for direct, 2 for mutual friend
    path_strength: Optional[RelationshipStrength] = None
    target_company: Optional[str] = None
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "degree": self.degree,
            "target": self.target.to_dict(),
            "bridge": self.bridge.to_dict() if self.bridge else None,
            "path_strength": self.path_strength.to_dict() if self.path_strength else None,
            "target_company": self.target_company,
            "reasoning": self.reasoning,
        }
