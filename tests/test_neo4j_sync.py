"""
Neo4j 同步层单元测试

测试覆盖:
- Neo4jSync 类的构造和 schema 设置
- entity / edge / observation 同步（使用 mock）
- MERGE 幂等性（重复同步不产生重复）
- 跨 run entity 共享
- NEO4J_ENABLED=false 时的行为
- checkpoint_evidence_graph 统一入口
"""
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, call

import pytest

# 项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.evidence_graph import (
    EvidenceGraph, Entity, Edge, Observation,
    EntityType, Predicate, EvidenceGrade, CivicEvidenceType,
)


# ==================== Fixtures ====================

@pytest.fixture
def evidence_graph():
    """构建一个包含实体、边和观察的完整 EvidenceGraph"""
    g = EvidenceGraph()

    # 实体
    g.get_or_create_entity("GENE:EGFR", EntityType.GENE, "EGFR", "Geneticist")
    g.get_or_create_entity("EGFR_L858R", EntityType.VARIANT, "L858R", "Geneticist")
    g.get_or_create_entity("DRUG:OSIMERTINIB", EntityType.DRUG, "Osimertinib", "Oncologist")
    g.get_or_create_entity("DISEASE:NSCLC", EntityType.DISEASE, "NSCLC", "Pathologist")

    # 实体上的观察
    obs1 = Observation(
        id="obs_neo4j_001",
        statement="EGFR L858R is a common activating mutation in NSCLC",
        source_agent="Geneticist",
        source_tool="CIViC",
        provenance="PMID:28854312",
        source_url="https://pubmed.ncbi.nlm.nih.gov/28854312/",
        evidence_grade=EvidenceGrade.A,
        civic_type=CivicEvidenceType.PREDICTIVE,
        iteration=1,
    )
    g.add_observation_to_entity("EGFR_L858R", obs1)

    obs2 = Observation(
        id="obs_neo4j_002",
        statement="Osimertinib is first-line treatment for EGFR+ NSCLC",
        source_agent="Oncologist",
        source_tool="PubMed",
        provenance="PMID:29151359",
        source_url="https://pubmed.ncbi.nlm.nih.gov/29151359/",
        evidence_grade=EvidenceGrade.B,
        civic_type=CivicEvidenceType.PREDICTIVE,
        iteration=2,
    )
    g.add_observation_to_entity("DRUG:OSIMERTINIB", obs2)

    # 边 + 边上的观察
    edge_obs = Observation(
        id="obs_neo4j_003",
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

    return g


@pytest.fixture
def mock_neo4j_driver():
    """模拟 Neo4j driver + session + transaction"""
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__ = MagicMock(return_value=session)
    driver.session.return_value.__exit__ = MagicMock(return_value=False)
    return driver, session


# ==================== Class 1: Neo4jSync 构造和 Schema ====================

class TestNeo4jSyncConstruction:
    """Neo4jSync 初始化和 schema 管理测试"""

    @patch("src.utils.neo4j_sync.GraphDatabase")
    def test_constructor_connects(self, mock_gdb):
        """构造函数应调用 GraphDatabase.driver"""
        mock_driver = MagicMock()
        mock_gdb.driver.return_value = mock_driver

        from src.utils.neo4j_sync import Neo4jSync
        sync = Neo4jSync("bolt://localhost:7687", "neo4j", "password")

        mock_gdb.driver.assert_called_once_with(
            "bolt://localhost:7687", auth=("neo4j", "password")
        )
        assert sync.driver == mock_driver

    @patch("src.utils.neo4j_sync.GraphDatabase")
    def test_ensure_schema_creates_constraints_and_indexes(self, mock_gdb):
        """ensure_schema 应创建 4 个约束 + 3 个索引"""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_gdb.driver.return_value = mock_driver

        from src.utils.neo4j_sync import Neo4jSync
        sync = Neo4jSync("bolt://test:7687", "neo4j", "pass")

        # ensure_schema 在构造函数中调用
        # 应有 4 constraints + 3 indexes = 7 calls to session.run
        assert mock_session.run.call_count == 7

        # 检查约束关键字
        calls_str = str(mock_session.run.call_args_list)
        assert "entity_unique" in calls_str
        assert "obs_unique" in calls_str
        assert "evidence_unique" in calls_str
        assert "run_unique" in calls_str
        assert "entity_type_idx" in calls_str
        assert "obs_grade_idx" in calls_str
        assert "obs_agent_idx" in calls_str

    @patch("src.utils.neo4j_sync.GraphDatabase")
    def test_close_calls_driver_close(self, mock_gdb):
        """close() 应调用 driver.close()"""
        mock_driver = MagicMock()
        mock_gdb.driver.return_value = mock_driver

        from src.utils.neo4j_sync import Neo4jSync
        sync = Neo4jSync("bolt://test:7687", "neo4j", "pass")
        sync.close()

        mock_driver.close.assert_called_once()


# ==================== Class 2: Entity/Edge 同步 ====================

class TestNeo4jSyncOperations:
    """entity 和 edge 同步操作测试"""

    @patch("src.utils.neo4j_sync.GraphDatabase")
    def test_sync_graph_calls_sync_methods(self, mock_gdb, evidence_graph):
        """sync_graph 应同步 run + 所有 entities + 所有 edges"""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_gdb.driver.return_value = mock_driver

        from src.utils.neo4j_sync import Neo4jSync
        sync = Neo4jSync("bolt://test:7687", "neo4j", "pass")

        # 重置 mock 计数（ensure_schema 已经调用过）
        mock_session.execute_write.reset_mock()

        sync.sync_graph(evidence_graph, "run_001", "patient_001", "phase1")

        # 1 run + 4 entities + 1 edge = 6 execute_write 调用
        assert mock_session.execute_write.call_count == 6

    @patch("src.utils.neo4j_sync.GraphDatabase")
    def test_sync_entity_formats_observations(self, mock_gdb, evidence_graph):
        """_sync_entity 应正确格式化 observation 数据"""
        from src.utils.neo4j_sync import Neo4jSync

        # 直接测试 _sync_entity 静态方法
        tx = MagicMock()

        entity = evidence_graph.entities["EGFR_L858R"]
        Neo4jSync._sync_entity(tx, entity, "run_001")

        # 验证 tx.run 被调用
        tx.run.assert_called_once()

        # 检查参数
        call_kwargs = tx.run.call_args
        assert call_kwargs.kwargs["canonical_id"] == "EGFR_L858R"
        assert call_kwargs.kwargs["name"] == "L858R"
        assert call_kwargs.kwargs["entity_type"] == "variant"
        assert call_kwargs.kwargs["run_id"] == "run_001"

        # 验证 observations 参数
        observations = call_kwargs.kwargs["observations"]
        assert len(observations) == 1
        assert observations[0]["obs_id"] == "obs_neo4j_001"
        assert observations[0]["grade"] == "A"
        assert observations[0]["source_agent"] == "Geneticist"

    @patch("src.utils.neo4j_sync.GraphDatabase")
    def test_sync_edge_formats_reified_evidence(self, mock_gdb, evidence_graph):
        """_sync_edge 应创建 reified Evidence 节点 + FROM/TO 关系"""
        from src.utils.neo4j_sync import Neo4jSync

        tx = MagicMock()

        # 获取第一条边
        edge = list(evidence_graph.edges.values())[0]
        Neo4jSync._sync_edge(tx, edge, "run_001")

        # 验证 tx.run 被调用
        tx.run.assert_called_once()

        # 检查 Cypher 查询包含关键模式
        call_args = tx.run.call_args
        cypher = call_args.args[0] if call_args.args else call_args.kwargs.get("query", "")
        # Cypher 应包含 MERGE Evidence, FROM, TO
        assert "MERGE" in cypher
        assert "Evidence" in cypher
        assert "FROM" in cypher
        assert "TO" in cypher

        # 检查参数
        kwargs = call_args.kwargs
        assert kwargs["source_id"] == "EGFR_L858R"
        assert kwargs["target_id"] == "DRUG:OSIMERTINIB"
        assert kwargs["predicate"] == "sensitizes"
        assert kwargs["confidence"] == 0.95

    @patch("src.utils.neo4j_sync.GraphDatabase")
    def test_sync_entity_without_observations(self, mock_gdb):
        """没有观察的实体也应该能同步"""
        from src.utils.neo4j_sync import Neo4jSync

        tx = MagicMock()

        g = EvidenceGraph()
        g.get_or_create_entity("GENE:TP53", EntityType.GENE, "TP53", "Geneticist")
        entity = g.entities["GENE:TP53"]

        Neo4jSync._sync_entity(tx, entity, "run_001")

        call_kwargs = tx.run.call_args.kwargs
        assert call_kwargs["canonical_id"] == "GENE:TP53"
        assert call_kwargs["observations"] == []

    @patch("src.utils.neo4j_sync.GraphDatabase")
    def test_sync_run_sets_metadata(self, mock_gdb):
        """_sync_run 应设置 patient_id, phase, status"""
        from src.utils.neo4j_sync import Neo4jSync

        tx = MagicMock()

        Neo4jSync._sync_run(tx, "run_20260205_test", "patient_XYZ", "phase2")

        tx.run.assert_called_once()
        call_kwargs = tx.run.call_args.kwargs
        assert call_kwargs["run_id"] == "run_20260205_test"
        assert call_kwargs["patient_id"] == "patient_XYZ"
        assert call_kwargs["phase"] == "phase2"


# ==================== Class 3: MERGE 幂等性 ====================

class TestMergeIdempotency:
    """验证 MERGE 操作的幂等性（重复同步不产生重复数据）"""

    @patch("src.utils.neo4j_sync.GraphDatabase")
    def test_double_sync_same_entity(self, mock_gdb, evidence_graph):
        """同一 entity 同步两次，_sync_entity 应使用 MERGE"""
        from src.utils.neo4j_sync import Neo4jSync

        tx = MagicMock()
        entity = evidence_graph.entities["GENE:EGFR"]

        # 同步两次
        Neo4jSync._sync_entity(tx, entity, "run_001")
        Neo4jSync._sync_entity(tx, entity, "run_001")

        # 两次调用都应该使用 MERGE（不是 CREATE）
        for call_obj in tx.run.call_args_list:
            cypher = call_obj.args[0] if call_obj.args else ""
            assert "MERGE" in cypher
            assert "CREATE" not in cypher or "CREATE CONSTRAINT" in cypher or "CREATE INDEX" in cypher

    @patch("src.utils.neo4j_sync.GraphDatabase")
    def test_entity_shared_across_runs(self, mock_gdb, evidence_graph):
        """同一 canonical_id 在不同 run 中应共享同一 Entity 节点"""
        from src.utils.neo4j_sync import Neo4jSync

        tx = MagicMock()
        entity = evidence_graph.entities["GENE:EGFR"]

        # 在两个不同的 run 中同步
        Neo4jSync._sync_entity(tx, entity, "run_001")
        Neo4jSync._sync_entity(tx, entity, "run_002")

        # 两次调用应使用相同的 canonical_id
        for call_obj in tx.run.call_args_list:
            assert call_obj.kwargs["canonical_id"] == "GENE:EGFR"

        # 但 run_id 不同
        run_ids = [c.kwargs["run_id"] for c in tx.run.call_args_list]
        assert "run_001" in run_ids
        assert "run_002" in run_ids


# ==================== Class 4: checkpoint_evidence_graph 统一入口 ====================

class TestCheckpointEvidenceGraph:
    """checkpoint_evidence_graph() 统一入口测试"""

    def test_checkpoint_with_missing_data_returns_false(self):
        """缺少 evidence_graph 或 run_folder 时返回 False"""
        from src.utils.graph_persistence import checkpoint_evidence_graph

        # 缺少 evidence_graph
        result = checkpoint_evidence_graph(
            {"run_folder": "/tmp/test"},
            phase="phase1",
            iteration=1,
        )
        assert result is False

        # 缺少 run_folder
        result = checkpoint_evidence_graph(
            {"evidence_graph": {"entities": {}}},
            phase="phase1",
            iteration=1,
        )
        assert result is False

    @patch("config.settings.NEO4J_ENABLED", False)
    def test_checkpoint_saves_json_when_neo4j_disabled(self, tmp_path, evidence_graph):
        """NEO4J_ENABLED=false 时仍保存 JSON"""
        from src.utils.graph_persistence import checkpoint_evidence_graph

        state = {
            "evidence_graph": evidence_graph.to_dict(),
            "run_folder": str(tmp_path),
            "run_id": "run_test_001",
        }

        result = checkpoint_evidence_graph(state, phase="phase1", iteration=1, checkpoint_type="checkpoint")
        assert result is True

        # 验证 JSON 文件创建
        json_files = list(tmp_path.glob("evidence_graph_*.json"))
        assert len(json_files) >= 1

    @patch("config.settings.NEO4J_ENABLED", False)
    def test_checkpoint_filenames_by_type(self, tmp_path, evidence_graph):
        """不同 checkpoint_type 应产生不同文件名"""
        from src.utils.graph_persistence import checkpoint_evidence_graph

        state = {
            "evidence_graph": evidence_graph.to_dict(),
            "run_folder": str(tmp_path),
            "run_id": "run_test_002",
        }

        # checkpoint
        checkpoint_evidence_graph(state, phase="phase1", iteration=2, checkpoint_type="checkpoint")
        assert (tmp_path / "evidence_graph_phase1_iter2.json").exists()

        # phase_complete
        checkpoint_evidence_graph(state, phase="phase1", iteration=2, checkpoint_type="phase_complete")
        assert (tmp_path / "evidence_graph_phase1_complete.json").exists()

        # final
        checkpoint_evidence_graph(state, phase="final", iteration=0, checkpoint_type="final")
        assert (tmp_path / "evidence_graph.json").exists()

    @patch("config.settings.NEO4J_ENABLED", True)
    @patch("src.utils.neo4j_sync.Neo4jSync")
    def test_checkpoint_calls_neo4j_when_enabled(self, mock_sync_class, tmp_path, evidence_graph):
        """NEO4J_ENABLED=true 时应调用 Neo4jSync.sync_graph"""
        from src.utils.graph_persistence import checkpoint_evidence_graph

        mock_instance = MagicMock()
        mock_sync_class.return_value = mock_instance

        state = {
            "evidence_graph": evidence_graph.to_dict(),
            "run_folder": str(tmp_path),
            "run_id": "run_test_003",
            "patient_id": "patient_XYZ",
        }

        result = checkpoint_evidence_graph(state, phase="phase2", iteration=3, checkpoint_type="checkpoint")

        # 应调用 sync_graph
        mock_instance.sync_graph.assert_called_once()
        # 应调用 close
        mock_instance.close.assert_called_once()

    @patch("config.settings.NEO4J_ENABLED", True)
    @patch("src.utils.neo4j_sync.Neo4jSync")
    def test_checkpoint_survives_neo4j_failure(self, mock_sync_class, tmp_path, evidence_graph):
        """Neo4j 同步失败不影响 JSON 备份和整体流程"""
        from src.utils.graph_persistence import checkpoint_evidence_graph

        mock_sync_class.side_effect = Exception("Neo4j connection refused")

        state = {
            "evidence_graph": evidence_graph.to_dict(),
            "run_folder": str(tmp_path),
            "run_id": "run_test_004",
        }

        # 不应抛出异常
        result = checkpoint_evidence_graph(state, phase="phase1", iteration=1, checkpoint_type="checkpoint")

        # JSON 备份仍然应该创建
        json_files = list(tmp_path.glob("evidence_graph_*.json"))
        assert len(json_files) >= 1


# ==================== Class 5: JSON 持久化 ====================

class TestJsonPersistence:
    """JSON 文件备份和加载测试"""

    def test_save_and_load_roundtrip(self, tmp_path, evidence_graph):
        """JSON 保存后可以正确加载"""
        from src.utils.graph_persistence import save_evidence_graph_json, load_evidence_graph_json

        filepath = save_evidence_graph_json(
            evidence_graph.to_dict(), str(tmp_path), "phase1", 1, "checkpoint"
        )
        assert filepath is not None
        assert Path(filepath).exists()

        # 加载
        loaded = load_evidence_graph_json(filepath)
        assert loaded is not None
        assert "entities" in loaded
        assert "edges" in loaded

    def test_load_legacy_format(self, tmp_path):
        """兼容旧格式（无 metadata 信封）的 JSON"""
        import json
        from src.utils.graph_persistence import load_evidence_graph_json

        legacy_data = {"entities": {}, "edges": {}}
        filepath = tmp_path / "legacy.json"
        with open(filepath, 'w') as f:
            json.dump(legacy_data, f)

        loaded = load_evidence_graph_json(str(filepath))
        assert loaded is not None
        assert loaded["entities"] == {}

    def test_load_nonexistent_file_returns_none(self):
        """加载不存在的文件返回 None"""
        from src.utils.graph_persistence import load_evidence_graph_json

        result = load_evidence_graph_json("/nonexistent/path/graph.json")
        assert result is None

    def test_save_final_filename(self, tmp_path, evidence_graph):
        """final checkpoint 使用 evidence_graph.json 文件名"""
        from src.utils.graph_persistence import save_evidence_graph_json

        filepath = save_evidence_graph_json(
            evidence_graph.to_dict(), str(tmp_path), "final", 0, "final"
        )

        assert filepath is not None
        assert Path(filepath).name == "evidence_graph.json"

    def test_saved_json_contains_metadata(self, tmp_path, evidence_graph):
        """保存的 JSON 包含 metadata 信封"""
        import json
        from src.utils.graph_persistence import save_evidence_graph_json

        filepath = save_evidence_graph_json(
            evidence_graph.to_dict(), str(tmp_path), "phase2", 3, "checkpoint"
        )

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert "metadata" in data
        assert "graph" in data
        assert data["metadata"]["phase"] == "phase2"
        assert data["metadata"]["iteration"] == 3
        assert data["metadata"]["checkpoint_type"] == "checkpoint"
        assert data["metadata"]["entity_count"] == 4
        assert data["metadata"]["edge_count"] == 1
