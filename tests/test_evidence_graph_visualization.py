"""
Evidence Graph 可视化和序列化测试

测试覆盖:
- to_cytoscape_json() 节点/边转换
- to_persistence_dict() 元数据信封
- observations 按 grade 排序
- HTML 报告中 Cytoscape 集成
- 无图数据时 HTML 不含 graph section
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.evidence_graph import (
    EvidenceGraph, Entity, Edge, Observation,
    EntityType, Predicate, EvidenceGrade, CivicEvidenceType,
)
from src.renderers.html_generator import HtmlReportGenerator


# ==================== Fixtures ====================

@pytest.fixture
def gen():
    """HtmlReportGenerator instance."""
    return HtmlReportGenerator()


@pytest.fixture
def evidence_graph():
    """包含多种实体类型、边和不同等级观察的 EvidenceGraph"""
    g = EvidenceGraph()

    # 实体
    g.get_or_create_entity("GENE:EGFR", EntityType.GENE, "EGFR", "Geneticist")
    g.get_or_create_entity("EGFR_L858R", EntityType.VARIANT, "L858R", "Geneticist")
    g.get_or_create_entity("DRUG:OSIMERTINIB", EntityType.DRUG, "Osimertinib", "Oncologist")
    g.get_or_create_entity("DISEASE:NSCLC", EntityType.DISEASE, "NSCLC", "Pathologist")
    g.get_or_create_entity("NCT:NCT04487080", EntityType.TRIAL, "NCT04487080", "Recruiter")

    # 多等级观察（用于排序测试）
    obs_c = Observation(
        id="obs_viz_001",
        statement="Case report: L858R responded to osimertinib",
        source_agent="Geneticist",
        source_tool="PubMed",
        provenance="PMID:30000001",
        evidence_grade=EvidenceGrade.C,
        iteration=1,
    )
    obs_a = Observation(
        id="obs_viz_002",
        statement="Meta-analysis confirms L858R sensitivity to osimertinib",
        source_agent="Geneticist",
        source_tool="CIViC",
        provenance="PMID:28854312",
        source_url="https://pubmed.ncbi.nlm.nih.gov/28854312/",
        evidence_grade=EvidenceGrade.A,
        civic_type=CivicEvidenceType.PREDICTIVE,
        iteration=2,
    )
    obs_e = Observation(
        id="obs_viz_003",
        statement="Theoretical mechanism: L858R activates kinase domain",
        source_agent="Geneticist",
        source_tool="PubMed",
        evidence_grade=EvidenceGrade.E,
        iteration=1,
    )
    g.add_observation_to_entity("EGFR_L858R", obs_c)
    g.add_observation_to_entity("EGFR_L858R", obs_a)
    g.add_observation_to_entity("EGFR_L858R", obs_e)

    # Drug 观察
    obs_b = Observation(
        id="obs_viz_004",
        statement="Osimertinib PFS 18.9 months in FLAURA trial",
        source_agent="Oncologist",
        source_tool="PubMed",
        provenance="PMID:29151359",
        source_url="https://pubmed.ncbi.nlm.nih.gov/29151359/",
        evidence_grade=EvidenceGrade.B,
        civic_type=CivicEvidenceType.PREDICTIVE,
        iteration=2,
    )
    g.add_observation_to_entity("DRUG:OSIMERTINIB", obs_b)

    # 边 + 观察
    edge_obs = Observation(
        id="obs_viz_005",
        statement="EGFR L858R sensitizes to osimertinib",
        source_agent="Geneticist",
        source_tool="CIViC",
        provenance="PMID:28854312",
        source_url="https://pubmed.ncbi.nlm.nih.gov/28854312/",
        evidence_grade=EvidenceGrade.A,
        iteration=1,
    )
    g.add_edge("EGFR_L858R", "DRUG:OSIMERTINIB", Predicate.SENSITIZES,
               observation=edge_obs, confidence=0.95)

    # TREATS 边
    treats_obs = Observation(
        id="obs_viz_006",
        statement="Osimertinib is standard of care for EGFR+ NSCLC",
        source_agent="Oncologist",
        source_tool="NCCN",
        evidence_grade=EvidenceGrade.A,
        iteration=2,
    )
    g.add_edge("DRUG:OSIMERTINIB", "DISEASE:NSCLC", Predicate.TREATS,
               observation=treats_obs, confidence=0.9)

    return g


@pytest.fixture
def empty_graph():
    """空的 EvidenceGraph"""
    return EvidenceGraph()


# ==================== Class 1: to_cytoscape_json() 节点 ====================

class TestCytoscapeJsonNodes:
    """Cytoscape.js JSON 节点转换测试"""

    def test_entity_to_node_basic_fields(self, evidence_graph):
        """实体应转换为包含基本字段的 Cytoscape 节点"""
        result = evidence_graph.to_cytoscape_json()

        nodes = result["elements"]["nodes"]
        assert len(nodes) == 5

        # 找到 EGFR 节点
        egfr_node = next(n for n in nodes if n["data"]["id"] == "GENE:EGFR")
        data = egfr_node["data"]

        assert data["label"] == "EGFR"
        assert data["entity_type"] == "gene"
        assert "id" in data

    def test_node_obs_count(self, evidence_graph):
        """节点应包含正确的 obs_count"""
        result = evidence_graph.to_cytoscape_json()
        nodes = result["elements"]["nodes"]

        l858r = next(n for n in nodes if n["data"]["id"] == "EGFR_L858R")
        assert l858r["data"]["obs_count"] == 3

        osimertinib = next(n for n in nodes if n["data"]["id"] == "DRUG:OSIMERTINIB")
        assert osimertinib["data"]["obs_count"] == 1

    def test_node_best_grade(self, evidence_graph):
        """节点应显示最佳证据等级"""
        result = evidence_graph.to_cytoscape_json()
        nodes = result["elements"]["nodes"]

        # L858R 有 A, C, E 级观察 → best_grade = A
        l858r = next(n for n in nodes if n["data"]["id"] == "EGFR_L858R")
        assert l858r["data"]["best_grade"] == "A"

        # Osimertinib 有 B 级观察
        osi = next(n for n in nodes if n["data"]["id"] == "DRUG:OSIMERTINIB")
        assert osi["data"]["best_grade"] == "B"

    def test_node_grade_distribution(self, evidence_graph):
        """节点应包含等级分布"""
        result = evidence_graph.to_cytoscape_json()
        nodes = result["elements"]["nodes"]

        l858r = next(n for n in nodes if n["data"]["id"] == "EGFR_L858R")
        dist = l858r["data"]["grade_distribution"]
        assert dist.get("A") == 1
        assert dist.get("C") == 1
        assert dist.get("E") == 1

    def test_node_source_agents(self, evidence_graph):
        """节点应列出来源 agents"""
        result = evidence_graph.to_cytoscape_json()
        nodes = result["elements"]["nodes"]

        l858r = next(n for n in nodes if n["data"]["id"] == "EGFR_L858R")
        assert "Geneticist" in l858r["data"]["source_agents"]

    def test_node_observations_detail(self, evidence_graph):
        """节点应包含完整的 observation 详情"""
        result = evidence_graph.to_cytoscape_json()
        nodes = result["elements"]["nodes"]

        l858r = next(n for n in nodes if n["data"]["id"] == "EGFR_L858R")
        obs_list = l858r["data"]["observations"]
        assert len(obs_list) == 3

        # 检查第一个 observation 的字段
        first_obs = obs_list[0]
        assert "id" in first_obs
        assert "statement" in first_obs
        assert "grade" in first_obs
        assert "source_agent" in first_obs

    def test_empty_graph_returns_empty_nodes(self, empty_graph):
        """空图应返回空节点列表"""
        result = empty_graph.to_cytoscape_json()
        assert result["elements"]["nodes"] == []

    def test_entity_types_in_nodes(self, evidence_graph):
        """所有实体类型应正确反映在节点中"""
        result = evidence_graph.to_cytoscape_json()
        nodes = result["elements"]["nodes"]

        types = {n["data"]["entity_type"] for n in nodes}
        assert "gene" in types
        assert "variant" in types
        assert "drug" in types
        assert "disease" in types
        assert "trial" in types


# ==================== Class 2: to_cytoscape_json() 边 ====================

class TestCytoscapeJsonEdges:
    """Cytoscape.js JSON 边转换测试"""

    def test_edge_basic_fields(self, evidence_graph):
        """边应包含 source, target, predicate 等字段"""
        result = evidence_graph.to_cytoscape_json()
        edges = result["elements"]["edges"]

        assert len(edges) == 2

        # 找到 sensitizes 边（Predicate enum values are lowercase）
        sens_edge = next(e for e in edges if e["data"]["predicate"] == "sensitizes")
        data = sens_edge["data"]

        assert data["source"] == "EGFR_L858R"
        assert data["target"] == "DRUG:OSIMERTINIB"
        assert data["confidence"] == 0.95

    def test_edge_best_grade(self, evidence_graph):
        """边应包含最佳等级"""
        result = evidence_graph.to_cytoscape_json()
        edges = result["elements"]["edges"]

        sens_edge = next(e for e in edges if e["data"]["predicate"] == "sensitizes")
        assert sens_edge["data"]["best_grade"] == "A"

    def test_edge_obs_count(self, evidence_graph):
        """边应包含 observation 数量"""
        result = evidence_graph.to_cytoscape_json()
        edges = result["elements"]["edges"]

        sens_edge = next(e for e in edges if e["data"]["predicate"] == "sensitizes")
        assert sens_edge["data"]["obs_count"] == 1

    def test_edge_observations_detail(self, evidence_graph):
        """边应包含完整 observation 详情"""
        result = evidence_graph.to_cytoscape_json()
        edges = result["elements"]["edges"]

        sens_edge = next(e for e in edges if e["data"]["predicate"] == "sensitizes")
        obs_list = sens_edge["data"]["observations"]
        assert len(obs_list) == 1
        assert obs_list[0]["grade"] == "A"
        assert obs_list[0]["source_agent"] == "Geneticist"

    def test_empty_graph_returns_empty_edges(self, empty_graph):
        """空图应返回空边列表"""
        result = empty_graph.to_cytoscape_json()
        assert result["elements"]["edges"] == []


# ==================== Class 3: Observation 排序 ====================

class TestObservationSorting:
    """observations 应按 grade A→E 排序"""

    def test_node_observations_sorted_by_grade(self, evidence_graph):
        """节点的 observations 应按 A > B > C > D > E 排序"""
        result = evidence_graph.to_cytoscape_json()
        nodes = result["elements"]["nodes"]

        l858r = next(n for n in nodes if n["data"]["id"] == "EGFR_L858R")
        obs_grades = [o["grade"] for o in l858r["data"]["observations"]]

        # 应为 A, C, E（按升序排列 = 按优先级降序）
        assert obs_grades == ["A", "C", "E"]

    def test_observation_none_grade_at_end(self):
        """没有 grade 的 observation 应排在最后"""
        g = EvidenceGraph()
        g.get_or_create_entity("GENE:TEST", EntityType.GENE, "TEST", "Agent")

        obs_none = Observation(
            id="obs_sort_001", statement="No grade", source_agent="Agent",
            evidence_grade=None, iteration=1,
        )
        obs_b = Observation(
            id="obs_sort_002", statement="Grade B", source_agent="Agent",
            evidence_grade=EvidenceGrade.B, iteration=1,
        )
        g.add_observation_to_entity("GENE:TEST", obs_none)
        g.add_observation_to_entity("GENE:TEST", obs_b)

        result = g.to_cytoscape_json()
        nodes = result["elements"]["nodes"]
        test_node = next(n for n in nodes if n["data"]["id"] == "GENE:TEST")
        grades = [o["grade"] for o in test_node["data"]["observations"]]

        assert grades == ["B", None]


# ==================== Class 4: to_cytoscape_json() 统计 ====================

class TestCytoscapeJsonStats:
    """Cytoscape JSON 统计信息测试"""

    def test_stats_counts(self, evidence_graph):
        """stats 应包含正确的计数"""
        result = evidence_graph.to_cytoscape_json()
        stats = result["stats"]

        assert stats["entity_count"] == 5
        assert stats["edge_count"] == 2
        assert stats["observation_count"] > 0

    def test_stats_entities_by_type(self, evidence_graph):
        """stats 应包含 entities_by_type 分布"""
        result = evidence_graph.to_cytoscape_json()
        by_type = result["stats"]["entities_by_type"]

        assert by_type.get("gene") == 1
        assert by_type.get("variant") == 1
        assert by_type.get("drug") == 1
        assert by_type.get("disease") == 1
        assert by_type.get("trial") == 1

    def test_empty_graph_stats(self, empty_graph):
        """空图的统计应全部为 0"""
        result = empty_graph.to_cytoscape_json()
        stats = result["stats"]

        assert stats["entity_count"] == 0
        assert stats["edge_count"] == 0


# ==================== Class 5: to_persistence_dict() ====================

class TestPersistenceDict:
    """to_persistence_dict() 元数据信封测试"""

    def test_persistence_dict_structure(self, evidence_graph):
        """应包含 metadata 和 graph 顶层字段"""
        result = evidence_graph.to_persistence_dict("phase1", 3, "checkpoint")

        assert "metadata" in result
        assert "graph" in result

    def test_persistence_dict_metadata_fields(self, evidence_graph):
        """metadata 应包含所有必要字段"""
        result = evidence_graph.to_persistence_dict("phase2", 5, "phase_complete")

        meta = result["metadata"]
        assert meta["version"] == "1.0"
        assert meta["phase"] == "phase2"
        assert meta["iteration"] == 5
        assert meta["checkpoint_type"] == "phase_complete"
        assert "timestamp" in meta
        assert "stats" in meta

    def test_persistence_dict_stats(self, evidence_graph):
        """metadata.stats 应包含正确的计数"""
        result = evidence_graph.to_persistence_dict("final", 0, "final")

        stats = result["metadata"]["stats"]
        assert stats["entity_count"] == 5
        assert stats["edge_count"] == 2
        assert "entities_by_type" in stats
        assert "edges_by_predicate" in stats

    def test_persistence_dict_graph_roundtrip(self, evidence_graph):
        """graph 数据应能被 from_dict 重新加载"""
        from src.models.evidence_graph import load_evidence_graph

        result = evidence_graph.to_persistence_dict("phase1", 1, "checkpoint")
        reloaded = load_evidence_graph(result["graph"])

        assert len(reloaded.entities) == len(evidence_graph.entities)
        assert len(reloaded.edges) == len(evidence_graph.edges)


# ==================== Class 6: HTML 集成 ====================

class TestHtmlCytoscapeIntegration:
    """HTML 报告中的 Cytoscape.js 集成测试"""

    def test_html_with_cytoscape_data(self, gen, evidence_graph, tmp_path):
        """有图数据时 HTML 应包含 Cytoscape 脚本和数据"""
        html = gen.generate(
            raw_pdf_text="患者ID：TEST001\n诊断：NSCLC",
            chair_synthesis="# 1. 概要\n\n测试报告内容",
            run_folder=str(tmp_path),
            evidence_graph_data=evidence_graph.to_dict(),
        )

        # 读取生成的 HTML
        html_path = tmp_path / "6_final_report.html"
        assert html_path.exists()
        html_content = html_path.read_text(encoding="utf-8")

        # 应包含 Cytoscape 相关内容
        assert "cytoscape" in html_content.lower()
        assert "GRAPH_DATA" in html_content
        assert "evidence-graph-section" in html_content
        assert "eg-cytoscape" in html_content

    def test_html_without_cytoscape_data(self, gen, tmp_path):
        """无图数据时 HTML 不应包含 graph data 变量和 graph section div"""
        html = gen.generate(
            raw_pdf_text="患者ID：TEST002\n诊断：NSCLC",
            chair_synthesis="# 1. 概要\n\n测试报告内容",
            run_folder=str(tmp_path),
            evidence_graph_data=None,
        )

        html_path = tmp_path / "6_final_report.html"
        html_content = html_path.read_text(encoding="utf-8")

        # 不应包含 graph 数据变量（CSS 中的类名可能始终存在）
        assert "GRAPH_DATA" not in html_content
        # 不应有实际的 graph section div（区别于 CSS 样式定义）
        assert '<div class="evidence-graph-section">' not in html_content

    def test_html_with_empty_graph(self, gen, empty_graph, tmp_path):
        """空图（无实体）时不应渲染 graph section"""
        html = gen.generate(
            raw_pdf_text="患者ID：TEST003\n诊断：NSCLC",
            chair_synthesis="# 1. 概要\n\n测试报告内容",
            run_folder=str(tmp_path),
            evidence_graph_data=empty_graph.to_dict(),
        )

        html_path = tmp_path / "6_final_report.html"
        html_content = html_path.read_text(encoding="utf-8")

        # 空图不应有 graph section
        assert "GRAPH_DATA" not in html_content

    def test_cytoscape_data_is_valid_json(self, evidence_graph):
        """传递给模板的 cytoscape_data 应是有效 JSON"""
        cytoscape_json = evidence_graph.to_cytoscape_json()
        json_str = json.dumps(cytoscape_json, ensure_ascii=False)

        # 应能解析回来
        parsed = json.loads(json_str)
        assert "elements" in parsed
        assert "stats" in parsed
        assert "nodes" in parsed["elements"]
        assert "edges" in parsed["elements"]

    def test_cytoscape_cdn_url_in_html(self, gen, evidence_graph, tmp_path):
        """HTML 应包含 Cytoscape.js CDN URL"""
        gen.generate(
            raw_pdf_text="患者ID：TEST004\n诊断：NSCLC",
            chair_synthesis="# 1. 概要\n\n测试内容",
            run_folder=str(tmp_path),
            evidence_graph_data=evidence_graph.to_dict(),
        )

        html_path = tmp_path / "6_final_report.html"
        html_content = html_path.read_text(encoding="utf-8")

        assert "cytoscape" in html_content.lower()
        # CDN URL 或内联脚本
        assert "cdnjs.cloudflare.com/ajax/libs/cytoscape" in html_content or "cytoscape.min.js" in html_content
