"""In-memory and SQLite-backed professional relationship graph for Happenstance AI."""

from __future__ import annotations

import datetime
import json
import sqlite3
from typing import Any, Dict, List, Optional, Set, Tuple

from src.happenstance.models import (
    Direction,
    InteractionEdge,
    InteractionType,
    PersonNode,
    RelationshipStrength,
    WarmIntroPath,
)


class RelationshipGraph:
    """Manages the professional relationship graph."""

    def __init__(self, root_id: str = "me"):
        self.root_id = root_id
        self.nodes: Dict[str, PersonNode] = {}
        # Adjacency: node_id -> list of outgoing edges
        self.edges: Dict[str, List[InteractionEdge]] = {}
        # Undirected link index for rapid mutual connection lookups: (nodeA, nodeB) -> list of edges
        self._pair_edges: Dict[Tuple[str, str], List[InteractionEdge]] = {}

        # Ensure root user exists
        if self.root_id not in self.nodes:
            self.nodes[self.root_id] = PersonNode(
                id=self.root_id,
                name="You",
                headline="Candidate / Product Leader",
                tags=["User"]
            )
            self.edges[self.root_id] = []

    def add_person(self, person: PersonNode) -> PersonNode:
        """Adds or updates a person node in the graph."""
        if person.id in self.nodes:
            # Update fields if new data present
            existing = self.nodes[person.id]
            if person.headline:
                existing.headline = person.headline
            if person.company:
                existing.company = person.company
            if person.location:
                existing.location = person.location
            if person.domain:
                existing.domain = person.domain
            if person.tags:
                for t in person.tags:
                    if t not in existing.tags:
                        existing.tags.append(t)
            if person.primary_email and not existing.primary_email:
                existing.primary_email = person.primary_email
            return existing
        else:
            self.nodes[person.id] = person
            if person.id not in self.edges:
                self.edges[person.id] = []
            return person

    def add_interaction(self, edge: InteractionEdge) -> None:
        """Records an interaction between two nodes."""
        # Ensure endpoints exist
        if edge.source_id not in self.nodes:
            self.nodes[edge.source_id] = PersonNode(id=edge.source_id, name=edge.source_id)
            self.edges[edge.source_id] = []
        if edge.target_id not in self.nodes:
            self.nodes[edge.target_id] = PersonNode(id=edge.target_id, name=edge.target_id)
            self.edges[edge.target_id] = []

        self.edges[edge.source_id].append(edge)

        # Index undirected pair
        pair_key = tuple(sorted([edge.source_id, edge.target_id]))
        if pair_key not in self._pair_edges:
            self._pair_edges[pair_key] = []
        self._pair_edges[pair_key].append(edge)

    def get_person(self, person_id: str) -> Optional[PersonNode]:
        return self.nodes.get(person_id)

    def get_interactions(self, id_a: str, id_b: str) -> List[InteractionEdge]:
        """Returns all interaction touchpoints between two people regardless of direction."""
        pair_key = tuple(sorted([id_a, id_b]))
        return self._pair_edges.get(pair_key, [])

    def get_1st_degree_connections(self, root_id: Optional[str] = None) -> List[PersonNode]:
        """Returns all individuals with a direct connection to root."""
        root = root_id or self.root_id
        connected: Set[str] = set()

        for (u, v) in self._pair_edges.keys():
            if u == root and v != root:
                connected.add(v)
            elif v == root and u != root:
                connected.add(u)

        return [self.nodes[pid] for pid in connected if pid in self.nodes]

    def get_mutual_connections(self, id_a: str, id_b: str) -> List[PersonNode]:
        """Finds contacts who are connected to both Person A and Person B."""
        neighbors_a = set()
        for (u, v) in self._pair_edges.keys():
            if u == id_a and v != id_a:
                neighbors_a.add(v)
            elif v == id_a and u != id_a:
                neighbors_a.add(u)

        neighbors_b = set()
        for (u, v) in self._pair_edges.keys():
            if u == id_b and v != id_b:
                neighbors_b.add(v)
            elif v == id_b and u != id_b:
                neighbors_b.add(u)

        mutual_ids = neighbors_a.intersection(neighbors_b)
        mutual_ids.discard(self.root_id)
        mutual_ids.discard(id_a)
        mutual_ids.discard(id_b)

        return [self.nodes[mid] for mid in mutual_ids if mid in self.nodes]

    def to_json(self) -> str:
        """Serializes the graph to JSON."""
        data = {
            "root_id": self.root_id,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [
                edge.to_dict()
                for edge_list in self.edges.values()
                for edge in edge_list
            ]
        }
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> RelationshipGraph:
        """Reconstructs the relationship graph from JSON."""
        data = json.loads(json_str)
        graph = cls(root_id=data.get("root_id", "me"))
        for nd in data.get("nodes", []):
            graph.add_person(PersonNode.from_dict(nd))
        for ed in data.get("edges", []):
            graph.add_interaction(InteractionEdge(
                source_id=ed["source_id"],
                target_id=ed["target_id"],
                interaction_type=InteractionType(ed["interaction_type"]),
                timestamp=datetime.datetime.fromisoformat(ed["timestamp"]),
                direction=Direction(ed["direction"]),
                thread_count=ed.get("thread_count", 1),
                subject_summary=ed.get("subject_summary"),
                metadata=ed.get("metadata", {})
            ))
        return graph
