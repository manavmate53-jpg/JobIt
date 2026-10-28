"""Happenstance AI Relationship Intelligence & Warm Referral Engine for JobIt.

Acts as a "Google Search for your professional relationships", mapping warm introduction
paths to founders, hiring managers, and teams for open job listings.
"""

from src.happenstance.models import (
    PersonNode,
    InteractionEdge,
    InteractionType,
    Direction,
    RelationshipStrength,
    WarmIntroPath
)
from src.happenstance.relationship_graph import RelationshipGraph
from src.happenstance.strength_engine import RelationshipScorer
from src.happenstance.intent_parser import IntentParser, StructuredQuery
from src.happenstance.path_finder import PathFinder
from src.happenstance.intro_generator import WarmIntroGenerator
from src.happenstance.linkedin_ingester import LinkedInIngester
from src.happenstance.email_header_ingester import EmailHeaderIngester
from src.happenstance.calendar_ingester import CalendarIngester

__all__ = [
    "PersonNode",
    "InteractionEdge",
    "InteractionType",
    "Direction",
    "RelationshipStrength",
    "WarmIntroPath",
    "RelationshipGraph",
    "RelationshipScorer",
    "IntentParser",
    "StructuredQuery",
    "PathFinder",
    "WarmIntroGenerator",
    "LinkedInIngester",
    "EmailHeaderIngester",
    "CalendarIngester"
]
