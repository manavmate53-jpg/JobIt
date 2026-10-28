"""Proprietary Relationship Strength & Scoring Engine for Happenstance AI.

Evaluates frequency, recency, directionality, and channel diversity
to calculate a calibrated relationship strength score (0-100) and category.
"""

from __future__ import annotations

import datetime
import math
from typing import List, Optional

from src.happenstance.models import Direction, InteractionEdge, InteractionType, RelationshipStrength


class RelationshipScorer:
    """Computes relationship strength between two nodes based on communication metadata."""

    HALF_LIFE_DAYS = 90.0  # Relationship freshness half-life

    def __init__(self, half_life_days: float = 90.0):
        self.half_life_days = half_life_days

    def evaluate(
        self,
        interactions: List[InteractionEdge],
        now: Optional[datetime.datetime] = None
    ) -> RelationshipStrength:
        """Calculates multi-dimensional relationship strength."""
        ref_time = now or datetime.datetime.now(datetime.timezone.utc)

        if not interactions:
            return RelationshipStrength(
                score=0.0,
                category="Unknown",
                frequency_score=0.0,
                recency_score=0.0,
                direction_score=0.0,
                channel_diversity_score=0.0,
                last_interaction_date=None,
                days_since_interaction=9999,
                total_touchpoints=0
            )

        # 1. Frequency calculation
        total_touchpoints = sum(max(1, edge.thread_count) for edge in interactions)
        # 1 touchpoint = 25, 4 touchpoints = 65, 8+ = 100
        frequency_score = min(100.0, 15.0 + (total_touchpoints * 11.0))

        # 2. Recency calculation (exponential half-life decay)
        # Ensure timestamps are timezone-aware for comparison
        def normalize_dt(dt: datetime.datetime) -> datetime.datetime:
            if dt.tzinfo is None:
                return dt.replace(tzinfo=datetime.timezone.utc)
            return dt

        latest_edge = max(interactions, key=lambda e: normalize_dt(e.timestamp))
        latest_dt = normalize_dt(latest_edge.timestamp)
        days_since = max(0, (ref_time - latest_dt).total_seconds() / 86400.0)

        # Formula: 100 * (0.5 ^ (days / half_life))
        recency_score = 100.0 * math.pow(0.5, days_since / self.half_life_days)
        recency_score = max(0.0, min(100.0, recency_score))

        # 3. Directionality
        has_bidirectional = any(e.direction == Direction.BIDIRECTIONAL for e in interactions)
        has_inbound = any(e.direction == Direction.INBOUND for e in interactions)
        has_outbound = any(e.direction == Direction.OUTBOUND for e in interactions)

        if has_bidirectional or (has_inbound and has_outbound):
            direction_score = 100.0
        elif has_inbound:
            direction_score = 75.0
        elif has_outbound:
            # Unanswered outbound email or outreach
            direction_score = 25.0
        else:
            direction_score = 50.0

        # 4. Channel Diversity
        channels = set(e.interaction_type for e in interactions)
        if len(channels) >= 3:
            channel_score = 100.0
        elif len(channels) == 2:
            channel_score = 80.0
        else:
            channel_score = 55.0

        # Weighted aggregate
        # Frequency (35%), Recency (30%), Directionality (25%), Channel (10%)
        composite_score = (
            0.35 * frequency_score +
            0.30 * recency_score +
            0.25 * direction_score +
            0.10 * channel_score
        )

        # Categorization
        if composite_score >= 75.0:
            category = "Strong Connection"
        elif composite_score >= 45.0:
            category = "Moderate"
        elif days_since > 180.0:
            category = "Dormant"
        else:
            category = "Weak"

        return RelationshipStrength(
            score=round(composite_score, 1),
            category=category,
            frequency_score=round(frequency_score, 1),
            recency_score=round(recency_score, 1),
            direction_score=round(direction_score, 1),
            channel_diversity_score=round(channel_score, 1),
            last_interaction_date=latest_edge.timestamp,
            days_since_interaction=int(days_since),
            total_touchpoints=total_touchpoints
        )
