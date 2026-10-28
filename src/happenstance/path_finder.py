"""Multi-source sub-graph traversal and warm introduction pathfinder."""

from __future__ import annotations

import datetime
from typing import List, Optional, Set

from src.happenstance.models import PersonNode, RelationshipStrength, WarmIntroPath
from src.happenstance.relationship_graph import RelationshipGraph
from src.happenstance.intent_parser import StructuredQuery
from src.happenstance.strength_engine import RelationshipScorer


class PathFinder:
    """Traverses relationship graph to discover candidate matches and warm intro paths."""

    def __init__(self, graph: RelationshipGraph, scorer: Optional[RelationshipScorer] = None):
        self.graph = graph
        self.scorer = scorer or RelationshipScorer()

    def search(
        self,
        query: StructuredQuery,
        now: Optional[datetime.datetime] = None
    ) -> List[WarmIntroPath]:
        """Executes sub-graph traversal based on structured query constraints."""
        ref_time = now or datetime.datetime.now(datetime.timezone.utc)
        results: List[WarmIntroPath] = []
        root_id = self.graph.root_id

        # Candidate pool: all nodes except root
        candidates = [node for nid, node in self.graph.nodes.items() if nid != root_id]

        for person in candidates:
            if not self._matches_profile(person, query):
                continue

            # Determine degree to root
            direct_interactions = self.graph.get_interactions(root_id, person.id)
            is_1st_degree = len(direct_interactions) > 0 or person in self.graph.get_1st_degree_connections(root_id)

            # Evaluate direct relationship strength if 1st degree
            direct_strength: Optional[RelationshipStrength] = None
            if is_1st_degree:
                direct_strength = self.scorer.evaluate(direct_interactions, now=ref_time)

                # Check temporal constraints on 1st degree
                if query.min_days_since_interaction is not None:
                    if direct_strength.days_since_interaction < query.min_days_since_interaction:
                        # Exclude: spoken to too recently
                        continue

                if query.max_days_since_interaction is not None:
                    if direct_strength.days_since_interaction > query.max_days_since_interaction:
                        # Exclude: too long ago
                        continue

                if not query.require_mutual:
                    results.append(WarmIntroPath(
                        target=person,
                        bridge=None,
                        degree=1,
                        path_strength=direct_strength,
                        target_company=person.company,
                        reasoning=f"Direct 1st-degree connection ({direct_strength.category}, score {direct_strength.score}/100)"
                    ))
                    # If query only wanted 1st degree, continue
                    if query.max_degree == 1:
                        continue

            # Check 2nd-degree boundary (mutual connections via bridge)
            if query.max_degree >= 2:
                mutual_bridges = self.graph.get_mutual_connections(root_id, person.id)
                for bridge in mutual_bridges:
                    bridge_interactions = self.graph.get_interactions(root_id, bridge.id)
                    bridge_strength = self.scorer.evaluate(bridge_interactions, now=ref_time)

                    # Filter by minimum bridge strength if requested
                    if query.min_strength_category == "Strong Connection" and bridge_strength.category != "Strong Connection":
                        continue

                    reasoning = (
                        f"Warm intro path: You → {bridge.name} ({bridge_strength.category}, "
                        f"score {bridge_strength.score}/100) → {person.name} ({person.headline or person.company})"
                    )

                    results.append(WarmIntroPath(
                        target=person,
                        bridge=bridge,
                        degree=2,
                        path_strength=bridge_strength,
                        target_company=person.company,
                        reasoning=reasoning
                    ))

        # Rank results:
        # 1. Direct high-strength first
        # 2. 2nd-degree via strongest bridge next
        def sort_key(p: WarmIntroPath) -> float:
            base = 100.0 if p.degree == 1 else 50.0
            score = p.path_strength.score if p.path_strength else 0.0
            return base + score

        results.sort(key=sort_key, reverse=True)
        return results

    def find_paths_to_company(
        self,
        company_name: str,
        target_role_keywords: Optional[List[str]] = None,
        now: Optional[datetime.datetime] = None
    ) -> List[WarmIntroPath]:
        """Convenience method to find warm paths targeting a specific hiring company."""
        q = StructuredQuery(
            raw_query=f"Find contacts or mutual connections at {company_name}",
            target_companies=[company_name],
            target_roles=target_role_keywords or [],
            max_degree=2
        )
        return self.search(q, now=now)

    def _matches_profile(self, person: PersonNode, query: StructuredQuery) -> bool:
        """Checks if a person matches the entity constraints in the query."""
        # 1. Company match
        if query.target_companies:
            comp_match = False
            p_comp = (person.company or "").lower()
            p_domain = (person.domain or "").lower()
            for tc in query.target_companies:
                tc_lower = tc.lower()
                if tc_lower in p_comp or tc_lower in p_domain:
                    comp_match = True
                    break
            if not comp_match:
                return False

        # 2. Role match
        if query.target_roles:
            role_match = False
            p_headline = (person.headline or "").lower()
            p_tags = [t.lower() for t in person.tags]
            for tr in query.target_roles:
                tr_lower = tr.lower()
                if tr_lower in p_headline or any(tr_lower in t for t in p_tags):
                    role_match = True
                    break
            if not role_match:
                return False

        # 3. Location match
        if query.target_locations:
            loc_match = False
            p_loc = (person.location or "").lower()
            for tl in query.target_locations:
                tl_lower = tl.lower()
                if tl_lower in p_loc:
                    loc_match = True
                    break
            if not loc_match:
                return False

        # 4. Sector / Tag match
        if query.target_sectors:
            sec_match = False
            p_text = f"{person.headline or ''} {' '.join(person.tags)} {person.notes or ''}".lower()
            for ts in query.target_sectors:
                ts_lower = ts.lower()
                if ts_lower in p_text:
                    sec_match = True
                    break
            if not sec_match:
                return False

        # 5. General keyword match
        if query.keywords and not (query.target_companies or query.target_roles or query.target_sectors):
            kw_match = False
            p_full = f"{person.name} {person.headline or ''} {person.company or ''} {' '.join(person.tags)}".lower()
            for kw in query.keywords:
                if kw.lower() in p_full:
                    kw_match = True
                    break
            if not kw_match:
                return False

        return True
