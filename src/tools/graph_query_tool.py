"""
GraphQueryTool - 证据图查询工具 (retrieve_from_graph)

有状态工具：持有当前 EvidenceGraph 的引用。
与外部 API 工具不同，此工具在内存中操作证据图。

使用模式:
    graph_tool = GraphQueryTool()
    graph_tool.set_graph(evidence_graph)  # 绑定图引用
    # 注入到 Agent 工具列表后，LLM 可通过 tool_call 查询图

设计原则:
    - 只读：不提供 add_to_graph 操作（图写入通过 entity_extractors 管道）
    - "Not found" 引导外部搜索：空结果明确提示使用 PubMed/CIViC 等外部工具
    - 单工具多动作：通过 action 参数路由到不同查询方法
"""
import json
from typing import Dict, Any, Optional, List

from src.tools.base_tool import BaseTool
from src.models.evidence_graph import (
    EvidenceGraph,
    EntityType,
    Predicate,
    EvidenceGrade,
    CivicEvidenceType,
)
from src.utils.logger import mtb_logger as logger


class GraphQueryTool(BaseTool):
    """
    有状态的证据图查询工具。

    通过 set_graph() 绑定 EvidenceGraph 引用后，
    Agent 可在 tool_call 中查询图的局部结构。
    """

    def __init__(self):
        super().__init__(
            name="query_evidence_graph",
            description=(
                "Query the evidence graph to explore known entities, relationships, "
                "and observations. Use this BEFORE calling external tools to check "
                "what is already known. Actions: search_entities, get_entity_detail, "
                "get_neighborhood, retrieve_subgraph, get_node_observations, "
                "get_edge_observations, get_drug_sensitivity, get_treatment_evidence, "
                "get_conflicts, get_stats."
            ),
        )
        self._graph: Optional[EvidenceGraph] = None

    def set_graph(self, graph: EvidenceGraph):
        """
        绑定证据图引用。每次 research_iterate() 前调用。

        Args:
            graph: 当前 EvidenceGraph 实例（同一 Python 对象，
                   entity extraction 后 tool 自动看到更新）
        """
        self._graph = graph

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "search_entities",
                        "get_entity_detail",
                        "get_neighborhood",
                        "retrieve_subgraph",
                        "get_node_observations",
                        "get_edge_observations",
                        "get_drug_sensitivity",
                        "get_treatment_evidence",
                        "get_conflicts",
                        "get_stats",
                    ],
                    "description": (
                        "The query action to perform on the evidence graph. "
                        "Use search_entities to find entities by name; "
                        "get_entity_detail for full info on one entity; "
                        "get_neighborhood for BFS exploration from an anchor; "
                        "retrieve_subgraph for multi-anchor subgraph extraction; "
                        "get_node_observations for all observations of an entity; "
                        "get_edge_observations for all observations of an edge."
                    ),
                },
                "entity_id": {
                    "type": "string",
                    "description": "Entity canonical_id (e.g. GENE:EGFR, DRUG:OSIMERTINIB, EGFR_L858R)",
                },
                "anchor_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of anchor entity canonical_ids for subgraph retrieval",
                },
                "query": {
                    "type": "string",
                    "description": "Search query string for entity search (e.g. 'EGFR', 'T790M', 'osimertinib')",
                },
                "entity_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by entity types: gene, variant, drug, disease, pathway, biomarker, trial, guideline, regimen, finding",
                },
                "predicate_filter": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter edges by predicate: sensitizes, treats, causes_resistance, recommends, etc.",
                },
                "max_hops": {
                    "type": "integer",
                    "description": "Maximum BFS hops for neighborhood/subgraph (default 2)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return (default 20)",
                },
                "min_grade": {
                    "type": "string",
                    "description": "Minimum evidence grade filter: A, B, C, D, or E",
                },
                "source_id": {
                    "type": "string",
                    "description": "Source entity canonical_id for edge observations query",
                },
                "target_id": {
                    "type": "string",
                    "description": "Target entity canonical_id for edge observations query",
                },
                "predicate": {
                    "type": "string",
                    "description": "Edge predicate for edge observations query (e.g. sensitizes, treats, causes_resistance)",
                },
            },
            "required": ["action"],
        }

    def _call_real_api(self, **kwargs) -> Optional[str]:
        """Route action to the appropriate graph query handler."""
        if not self._graph:
            return (
                "Evidence graph is empty — no evidence collected yet. "
                "Use external tools (search_pubmed, search_civic, etc.) to search for evidence."
            )

        action = kwargs.get("action", "")
        logger.debug(f"[GraphQueryTool] action={action}, kwargs={kwargs}")

        handlers = {
            "search_entities": self._handle_search_entities,
            "get_entity_detail": self._handle_get_entity_detail,
            "get_neighborhood": self._handle_get_neighborhood,
            "retrieve_subgraph": self._handle_retrieve_subgraph,
            "get_node_observations": self._handle_get_node_observations,
            "get_edge_observations": self._handle_get_edge_observations,
            "get_drug_sensitivity": self._handle_get_drug_sensitivity,
            "get_treatment_evidence": self._handle_get_treatment_evidence,
            "get_conflicts": self._handle_get_conflicts,
            "get_stats": self._handle_get_stats,
        }

        handler = handlers.get(action)
        if not handler:
            return f"Unknown action: '{action}'. Valid actions: {', '.join(handlers.keys())}"

        try:
            return handler(kwargs)
        except Exception as e:
            logger.error(f"[GraphQueryTool] {action} failed: {e}")
            return f"Error executing {action}: {str(e)}"

    # ==================== Action Handlers ====================

    def _parse_entity_types(self, kwargs: Dict) -> Optional[List[EntityType]]:
        """Parse entity_types from kwargs."""
        raw = kwargs.get("entity_types")
        if not raw:
            return None
        result = []
        for t in raw:
            try:
                result.append(EntityType(t.lower()))
            except ValueError:
                pass
        return result or None

    def _parse_predicates(self, kwargs: Dict) -> Optional[List[Predicate]]:
        """Parse predicate_filter from kwargs."""
        raw = kwargs.get("predicate_filter")
        if not raw:
            return None
        result = []
        for p in raw:
            try:
                result.append(Predicate(p.lower()))
            except ValueError:
                pass
        return result or None

    def _parse_grade(self, kwargs: Dict) -> Optional[EvidenceGrade]:
        """Parse min_grade from kwargs."""
        raw = kwargs.get("min_grade")
        if not raw:
            return None
        try:
            return EvidenceGrade(raw.upper())
        except ValueError:
            return None

    def _not_found_hint(self, what: str) -> str:
        """Standard hint when information is not found in graph."""
        return (
            f"Not found in evidence graph: {what}. "
            "This information may not have been collected yet. "
            "Consider using external tools (search_pubmed, search_civic, "
            "search_clinical_trials, etc.) to search for this information."
        )

    def _handle_search_entities(self, kwargs: Dict) -> str:
        query = kwargs.get("query", "")
        if not query:
            return "Error: 'query' parameter is required for search_entities."

        entity_types = self._parse_entity_types(kwargs)
        limit = kwargs.get("max_results", 20)

        results = self._graph.search_entities(
            query=query,
            entity_types=entity_types,
            limit=limit,
        )

        if not results:
            return self._not_found_hint(f"entities matching '{query}'")

        lines = [f"Found {len(results)} entities matching '{query}':"]
        lines.append("")
        for r in results:
            grade = f" [Best: {r['best_grade']}]" if r.get("best_grade") else ""
            aliases = f" (aliases: {', '.join(r['aliases'])})" if r.get("aliases") else ""
            lines.append(
                f"- **{r['canonical_id']}** ({r['type']}){grade} "
                f"— {r['observation_count']} observations{aliases}"
            )
        lines.append("")
        lines.append("Use `get_entity_detail` for full observations, or `get_neighborhood` to explore connections.")
        return "\n".join(lines)

    def _handle_get_entity_detail(self, kwargs: Dict) -> str:
        entity_id = kwargs.get("entity_id", "")
        if not entity_id:
            return "Error: 'entity_id' parameter is required for get_entity_detail."

        detail = self._graph.get_entity_detail(entity_id)
        if not detail:
            return self._not_found_hint(f"entity '{entity_id}'")

        entity = detail["entity"]
        lines = [
            f"## {entity['name']} ({entity['canonical_id']})",
            f"**Type**: {entity['type']}",
        ]
        if entity.get("aliases"):
            lines.append(f"**Aliases**: {', '.join(entity['aliases'])}")
        lines.append("")

        # Observations
        observations = entity.get("observations", [])
        if observations:
            lines.append(f"### Observations ({len(observations)}):")
            for obs in observations:
                grade = f"[{obs['evidence_grade']}]" if obs.get("evidence_grade") else "[?]"
                prov = f" ({obs['provenance']})" if obs.get("provenance") else ""
                agent = f" [{obs['source_agent']}]" if obs.get("source_agent") else ""
                lines.append(f"- {grade}{agent} {obs['statement']}{prov}")
        else:
            lines.append("No observations recorded yet.")
        lines.append("")

        # Connected edges
        edges = detail.get("edges", [])
        if edges:
            lines.append(f"### Relationships ({len(edges)}):")
            for edge in edges:
                src_name = edge["source_id"]
                tgt_name = edge["target_id"]
                pred = edge["predicate"]
                conf = f" (conf={edge['confidence']:.2f})" if edge.get("confidence") else ""
                lines.append(f"- {src_name} → **{pred}** → {tgt_name}{conf}")
        lines.append("")

        # Connected entities
        connected = detail.get("connected_entities", [])
        if connected:
            lines.append(f"### Connected entities ({len(connected)}):")
            for c in connected:
                lines.append(f"- {c['canonical_id']} ({c['type']})")

        return "\n".join(lines)

    def _handle_get_neighborhood(self, kwargs: Dict) -> str:
        entity_id = kwargs.get("entity_id", "")
        if not entity_id:
            return "Error: 'entity_id' parameter is required for get_neighborhood."

        max_hops = kwargs.get("max_hops", 2)
        max_results = kwargs.get("max_results", 30)
        predicate_filter = self._parse_predicates(kwargs)
        entity_type_filter = self._parse_entity_types(kwargs)

        neighborhood = self._graph.get_neighborhood(
            entity_id=entity_id,
            max_hops=max_hops,
            max_entities=max_results,
            predicate_filter=predicate_filter,
            entity_type_filter=entity_type_filter,
        )

        entities = neighborhood["entities"]
        edges = neighborhood["edges"]
        hop_map = neighborhood["hop_map"]

        if not entities:
            return self._not_found_hint(f"entity '{entity_id}'")

        lines = [
            f"Neighborhood of **{entity_id}** (max {max_hops} hops, {len(entities)} entities, {len(edges)} edges):",
            "",
        ]

        # Group by hop distance
        by_hop: Dict[int, List] = {}
        for e in entities:
            h = hop_map.get(e.canonical_id, -1)
            by_hop.setdefault(h, []).append(e)

        for hop in sorted(by_hop.keys()):
            hop_label = "Anchor" if hop == 0 else f"Hop {hop}"
            lines.append(f"### {hop_label}:")
            for e in by_hop[hop]:
                best_grade = e.get_best_grade()
                grade_str = f" [{best_grade.value}]" if best_grade else ""
                obs_count = len(e.observations)
                lines.append(f"- {e.canonical_id} ({e.entity_type.value}){grade_str} — {obs_count} obs")
            lines.append("")

        # Key edges
        if edges:
            lines.append("### Key relationships:")
            for edge in edges:
                pred = edge.predicate.value
                conf = f" (conf={edge.confidence:.2f})" if edge.confidence else ""
                lines.append(f"- {edge.source_id} → **{pred}** → {edge.target_id}{conf}")

        return "\n".join(lines)

    def _handle_retrieve_subgraph(self, kwargs: Dict) -> str:
        anchor_ids = kwargs.get("anchor_ids", [])
        if not anchor_ids:
            return "Error: 'anchor_ids' parameter (list of entity IDs) is required for retrieve_subgraph."

        max_hops = kwargs.get("max_hops", 2)
        max_results = kwargs.get("max_results", 50)
        predicate_filter = self._parse_predicates(kwargs)
        entity_type_filter = self._parse_entity_types(kwargs)

        subgraph = self._graph.retrieve_subgraph(
            anchor_ids=anchor_ids,
            max_hops=max_hops,
            max_entities=max_results,
            predicate_filter=predicate_filter,
            entity_type_filter=entity_type_filter,
            include_observations=True,
        )

        stats = subgraph["stats"]
        entities = subgraph["entities"]
        edges = subgraph["edges"]

        if not entities:
            return self._not_found_hint(f"entities for anchors {anchor_ids}")

        lines = [
            f"Subgraph around {len(anchor_ids)} anchors: "
            f"{stats['total_entities']} entities, {stats['total_edges']} edges, "
            f"{stats['total_observations']} observations",
            "",
        ]

        # Entities sorted by observation count
        for e in sorted(entities, key=lambda x: -x.get("observation_count", 0)):
            grade = f" [{e['best_grade']}]" if e.get("best_grade") else ""
            hop = f" (hop {e['hop_distance']})" if e.get("hop_distance", 0) > 0 else " (anchor)"
            lines.append(
                f"- **{e['canonical_id']}** ({e['type']}){grade} "
                f"— {e['observation_count']} obs{hop}"
            )
        lines.append("")

        # Key edges
        if edges:
            lines.append("### Relationships:")
            for edge in edges:
                pred = edge["predicate"]
                conf = f" (conf={edge['confidence']:.2f})" if edge.get("confidence") else ""
                lines.append(f"- {edge['source_id']} → **{pred}** → {edge['target_id']}{conf}")

        return "\n".join(lines)

    def _handle_get_node_observations(self, kwargs: Dict) -> str:
        """返回指定实体的所有 observation（含完整 statement、grade、source）"""
        entity_id = kwargs.get("entity_id", "")
        if not entity_id:
            return "Error: 'entity_id' parameter is required for get_node_observations."

        entity = self._graph.get_entity(entity_id)
        if not entity:
            return self._not_found_hint(f"entity '{entity_id}'")

        observations = entity.observations
        if not observations:
            return f"Entity '{entity_id}' has no observations recorded."

        lines = [f"## Observations for **{entity_id}** ({len(observations)} total)", ""]

        # 按证据等级排序 (A > B > C > D > E)
        grade_order = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}
        sorted_obs = sorted(
            observations,
            key=lambda o: grade_order.get(o.evidence_grade.value if o.evidence_grade else "E", 5)
        )

        for obs in sorted_obs:
            grade = f"[{obs.evidence_grade.value}]" if obs.evidence_grade else "[ungraded]"
            source = f" ({obs.source_tool})" if obs.source_tool else ""
            agent = f" [{obs.source_agent}]" if obs.source_agent else ""
            prov = f" — {obs.provenance}" if obs.provenance else ""
            url = f" <{obs.source_url}>" if obs.source_url else ""
            lines.append(f"- {grade}{agent}{source} {obs.statement}{prov}{url}")

        return "\n".join(lines)

    def _handle_get_edge_observations(self, kwargs: Dict) -> str:
        """返回指定边的所有 observation"""
        source_id = kwargs.get("source_id", "")
        target_id = kwargs.get("target_id", "")
        predicate_str = kwargs.get("predicate", "")

        if not source_id or not target_id:
            return "Error: 'source_id' and 'target_id' parameters are required for get_edge_observations."

        # 查找匹配的边
        matching_edges = []
        for edge in self._graph.edges.values():
            if edge.source_id == source_id and edge.target_id == target_id:
                if predicate_str:
                    try:
                        pred = Predicate(predicate_str.lower())
                        if edge.predicate == pred:
                            matching_edges.append(edge)
                    except ValueError:
                        pass
                else:
                    matching_edges.append(edge)

        if not matching_edges:
            # 尝试反向查找
            for edge in self._graph.edges.values():
                if edge.source_id == target_id and edge.target_id == source_id:
                    if predicate_str:
                        try:
                            pred = Predicate(predicate_str.lower())
                            if edge.predicate == pred:
                                matching_edges.append(edge)
                        except ValueError:
                            pass
                    else:
                        matching_edges.append(edge)

        if not matching_edges:
            return self._not_found_hint(
                f"edge between '{source_id}' and '{target_id}'"
                + (f" with predicate '{predicate_str}'" if predicate_str else "")
            )

        lines = [f"## Edge Observations ({len(matching_edges)} edges found)", ""]

        for edge in matching_edges:
            pred = edge.predicate.value
            conf = f" (confidence={edge.confidence:.2f})" if edge.confidence else ""
            lines.append(f"### {edge.source_id} → **{pred}** → {edge.target_id}{conf}")

            if edge.observations:
                for obs in edge.observations:
                    grade = f"[{obs.evidence_grade.value}]" if obs.evidence_grade else "[ungraded]"
                    source = f" ({obs.source_tool})" if obs.source_tool else ""
                    prov = f" — {obs.provenance}" if obs.provenance else ""
                    lines.append(f"- {grade}{source} {obs.statement}{prov}")
            else:
                lines.append("- No observations on this edge.")
            lines.append("")

        return "\n".join(lines)

    def _handle_get_drug_sensitivity(self, kwargs: Dict) -> str:
        sensitivity_map = self._graph.get_drug_sensitivity_map()

        if not sensitivity_map:
            return self._not_found_hint("drug sensitivity relationships")

        lines = ["## Drug Sensitivity Map", ""]

        for variant_id, entries in sensitivity_map.items():
            variant = self._graph.get_entity(variant_id)
            variant_name = variant.name if variant else variant_id
            lines.append(f"### {variant_name} ({variant_id})")

            for entry in entries:
                drug = entry.get("drug_entity")
                edge = entry.get("edge")
                if drug and edge:
                    pred = edge.predicate.value
                    conf = f" (conf={edge.confidence:.2f})" if edge.confidence else ""
                    grade = f" [{entry.get('grade', '?')}]" if entry.get("grade") else ""
                    lines.append(f"- {pred} → **{drug.name}**{grade}{conf}")

                    # Show edge observations
                    for obs in edge.observations:
                        prov = f" ({obs.provenance})" if obs.provenance else ""
                        lines.append(f"  - {obs.statement}{prov}")
            lines.append("")

        return "\n".join(lines)

    def _handle_get_treatment_evidence(self, kwargs: Dict) -> str:
        entity_id = kwargs.get("entity_id", "")

        treatment_predicates = [
            Predicate.TREATS,
            Predicate.RECOMMENDS,
            Predicate.SENSITIZES,
            Predicate.CAUSES_RESISTANCE,
            Predicate.CONTRAINDICATED_FOR,
            Predicate.INTERACTS_WITH,
        ]

        if entity_id:
            # Treatment evidence for a specific entity
            entity = self._graph.get_entity(entity_id)
            if not entity:
                return self._not_found_hint(f"entity '{entity_id}' for treatment evidence")

            edges = self._graph.get_entity_edges(entity_id, direction="both")
            treatment_edges = [e for e in edges if e.predicate in treatment_predicates]

            if not treatment_edges:
                return f"No treatment-related evidence found for {entity_id}."

            lines = [f"## Treatment evidence for {entity.name} ({entity_id})", ""]
            for edge in treatment_edges:
                src = self._graph.get_entity(edge.source_id)
                tgt = self._graph.get_entity(edge.target_id)
                src_name = src.name if src else edge.source_id
                tgt_name = tgt.name if tgt else edge.target_id
                pred = edge.predicate.value
                conf = f" (conf={edge.confidence:.2f})" if edge.confidence else ""

                lines.append(f"### {src_name} → {pred} → {tgt_name}{conf}")
                for obs in edge.observations:
                    grade = f"[{obs.evidence_grade.value}]" if obs.evidence_grade else "[?]"
                    prov = f" ({obs.provenance})" if obs.provenance else ""
                    lines.append(f"- {grade} {obs.statement}{prov}")
                lines.append("")

            return "\n".join(lines)
        else:
            # All treatment evidence
            all_treatment_edges = []
            for edge in self._graph.edges.values():
                if edge.predicate in treatment_predicates:
                    all_treatment_edges.append(edge)

            if not all_treatment_edges:
                return self._not_found_hint("treatment evidence")

            lines = [f"## All treatment evidence ({len(all_treatment_edges)} relationships)", ""]
            for edge in all_treatment_edges:
                src = self._graph.get_entity(edge.source_id)
                tgt = self._graph.get_entity(edge.target_id)
                src_name = src.name if src else edge.source_id
                tgt_name = tgt.name if tgt else edge.target_id
                pred = edge.predicate.value
                best_obs = edge.observations[0] if edge.observations else None
                grade = f" [{best_obs.evidence_grade.value}]" if best_obs and best_obs.evidence_grade else ""
                lines.append(f"- {src_name} → **{pred}** → {tgt_name}{grade}")

            return "\n".join(lines)

    def _handle_get_conflicts(self, kwargs: Dict) -> str:
        conflicts = self._graph.get_conflicts()

        if not conflicts:
            return "No conflicting evidence detected in the graph."

        lines = [f"## Evidence Conflicts ({len(conflicts)} groups)", ""]

        for conflict in conflicts:
            group_id = conflict.get("conflict_group", "unknown")
            edges = conflict.get("edges", [])
            entities = conflict.get("entities", [])

            entity_names = [e.name for e in entities if e]
            lines.append(f"### Conflict group: {group_id}")
            lines.append(f"Entities involved: {', '.join(entity_names)}")

            for edge in edges:
                pred = edge.predicate.value
                lines.append(f"- {edge.source_id} → {pred} → {edge.target_id}")
                for obs in edge.observations:
                    grade = f"[{obs.evidence_grade.value}]" if obs.evidence_grade else ""
                    prov = f" ({obs.provenance})" if obs.provenance else ""
                    lines.append(f"  - {grade} {obs.statement}{prov}")
            lines.append("")

        return "\n".join(lines)

    def _handle_get_stats(self, kwargs: Dict) -> str:
        summary = self._graph.summary()
        agent_summary = self._graph.summary_by_agent()

        entity_type_str = ", ".join(
            f"{k}({v})" for k, v in summary.get("entities_by_type", {}).items()
        )
        agent_str = ", ".join(
            f"{k}({v['observation_count']})" for k, v in agent_summary.items()
        )
        grade_str = ", ".join(
            f"{k}({v})" for k, v in sorted(summary.get("best_grades", {}).items())
        )

        lines = [
            "## Evidence Graph Statistics",
            "",
            f"- **Total entities**: {summary.get('total_entities', 0)}",
            f"- **Total edges**: {summary.get('total_edges', 0)}",
            f"- **Total observations**: {summary.get('total_observations', 0)}",
            f"- **By entity type**: {entity_type_str}",
            f"- **By agent (observations)**: {agent_str}",
            f"- **By evidence grade**: {grade_str}",
        ]

        return "\n".join(lines)
