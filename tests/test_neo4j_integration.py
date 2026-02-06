"""
Neo4j 集成测试 - 验证真实连接和数据存储

运行方式：
    python tests/test_neo4j_integration.py

注意：需要 Neo4j Desktop 运行中，且 patient 数据库已启动
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE, NEO4J_ENABLED
from src.models.evidence_graph import (
    EvidenceGraph, Observation,
    EntityType, Predicate, EvidenceGrade, CivicEvidenceType,
)
from src.utils.neo4j_sync import Neo4jSync


def create_test_graph() -> EvidenceGraph:
    """创建测试用的 EvidenceGraph"""
    g = EvidenceGraph()

    # 实体
    g.get_or_create_entity("GENE:EGFR", EntityType.GENE, "EGFR", "TestAgent")
    g.get_or_create_entity("EGFR_L858R", EntityType.VARIANT, "L858R", "TestAgent")
    g.get_or_create_entity("DRUG:OSIMERTINIB", EntityType.DRUG, "Osimertinib", "TestAgent")
    g.get_or_create_entity("DISEASE:NSCLC", EntityType.DISEASE, "NSCLC", "TestAgent")

    # 观察
    obs1 = Observation(
        id=f"obs_integration_test_{datetime.now().strftime('%H%M%S')}_001",
        statement="EGFR L858R 是 NSCLC 中最常见的激活突变",
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
        id=f"obs_integration_test_{datetime.now().strftime('%H%M%S')}_002",
        statement="奥希替尼是 EGFR+ NSCLC 的一线治疗",
        source_agent="Oncologist",
        source_tool="NCCN",
        provenance="NCCN Guidelines 2024",
        evidence_grade=EvidenceGrade.A,
        iteration=2,
    )
    g.add_observation_to_entity("DRUG:OSIMERTINIB", obs2)

    # 边 + 观察
    edge_obs = Observation(
        id=f"obs_integration_test_{datetime.now().strftime('%H%M%S')}_003",
        statement="EGFR L858R 对奥希替尼敏感",
        source_agent="Geneticist",
        source_tool="CIViC",
        provenance="PMID:28854312",
        evidence_grade=EvidenceGrade.A,
        iteration=1,
    )
    g.add_edge("EGFR_L858R", "DRUG:OSIMERTINIB", Predicate.SENSITIZES,
               observation=edge_obs, confidence=0.95)

    return g


def test_connection():
    """测试 1: 基本连接"""
    print("\n" + "=" * 60)
    print("测试 1: Neo4j 连接")
    print("=" * 60)

    print(f"URI: {NEO4J_URI}")
    print(f"Database: {NEO4J_DATABASE}")
    print(f"Enabled: {NEO4J_ENABLED}")

    try:
        sync = Neo4jSync(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE)
        stats = sync.get_stats()
        sync.close()

        print(f"[OK] 连接成功!")
        print(f"  当前数据库统计: {stats}")
        return True
    except Exception as e:
        print(f"[FAIL] 连接失败: {e}")
        return False


def test_sync_graph():
    """测试 2: 同步 EvidenceGraph"""
    print("\n" + "=" * 60)
    print("测试 2: 同步 EvidenceGraph 到 Neo4j")
    print("=" * 60)

    # 创建测试图
    graph = create_test_graph()
    run_id = f"test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    patient_id = "test_patient_001"

    print(f"测试图: {len(graph.entities)} entities, {len(graph.edges)} edges")
    print(f"Run ID: {run_id}")
    print(f"Patient ID: {patient_id}")

    try:
        sync = Neo4jSync(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE)

        # 同步前统计
        stats_before = sync.get_stats()
        print(f"\n同步前: {stats_before}")

        # 执行同步
        sync.sync_graph(graph, run_id, patient_id, "test_phase")

        # 同步后统计
        stats_after = sync.get_stats()
        print(f"同步后: {stats_after}")

        # 验证增量
        new_entities = stats_after["entities"] - stats_before["entities"]
        new_edges = stats_after["edges"] - stats_before["edges"]
        new_obs = stats_after["observations"] - stats_before["observations"]

        print(f"\n新增: +{new_entities} entities, +{new_edges} edges, +{new_obs} observations")

        sync.close()

        if new_entities >= 0 and new_obs >= 0:
            print("[OK] 同步成功!")
            return run_id
        else:
            print("[FAIL] 同步异常")
            return None

    except Exception as e:
        print(f"[FAIL] 同步失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_query_entity():
    """测试 3: 查询实体"""
    print("\n" + "=" * 60)
    print("测试 3: 查询跨 Run 实体")
    print("=" * 60)

    try:
        sync = Neo4jSync(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE)

        # 查询 EGFR 实体
        result = sync.query_entity_across_runs("GENE:EGFR")

        if result:
            print(f"[OK] 找到实体: {result['name']} ({result['entity_type']})")
            print(f"  出现在 {len(result['runs'])} 个 run 中: {result['runs'][:5]}...")
            print(f"  共 {len(result['observations'])} 条观察")
        else:
            print("[FAIL] 未找到 GENE:EGFR 实体")

        sync.close()
        return result is not None

    except Exception as e:
        print(f"[FAIL] 查询失败: {e}")
        return False


def test_query_patient_graph(run_id: str):
    """测试 4: 查询患者完整图"""
    print("\n" + "=" * 60)
    print("测试 4: 查询患者完整图")
    print("=" * 60)

    if not run_id:
        print("[SKIP] 跳过（无有效 run_id）")
        return False

    try:
        sync = Neo4jSync(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE)

        result = sync.query_patient_graph(run_id)

        print(f"Run ID: {run_id}")
        print(f"  Entities: {len(result['entities'])}")
        print(f"  Edges: {len(result['edges'])}")
        print(f"  Observations: {len(result['observations'])}")

        if result['entities']:
            print(f"\n  实体列表:")
            for e in result['entities'][:5]:
                print(f"    - {e.get('canonical_id')}: {e.get('name')} ({e.get('entity_type')})")

        sync.close()

        print("[OK] 查询成功!")
        return True

    except Exception as e:
        print(f"[FAIL] 查询失败: {e}")
        return False


def test_cypher_query():
    """测试 5: 直接 Cypher 查询"""
    print("\n" + "=" * 60)
    print("测试 5: Cypher 查询示例")
    print("=" * 60)

    try:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

        with driver.session(database=NEO4J_DATABASE) as session:
            # 查询 SENSITIZES 关系
            result = session.run("""
                MATCH (src:Entity)-[:FROM]->(ev:Evidence)-[:TO]->(tgt:Entity)
                WHERE ev.predicate = 'sensitizes'
                RETURN src.name as source, ev.predicate as predicate, tgt.name as target
                LIMIT 5
            """)

            records = list(result)
            print(f"找到 {len(records)} 条 SENSITIZES 关系:")
            for r in records:
                print(f"  {r['source']} --[{r['predicate']}]--> {r['target']}")

        driver.close()
        print("[OK] Cypher 查询成功!")
        return True

    except Exception as e:
        print(f"[FAIL] Cypher 查询失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("  Neo4j 集成测试")
    print("=" * 60)

    if not NEO4J_ENABLED:
        print("\n[WARN] NEO4J_ENABLED=false, 跳过测试")
        print("请在 .env 中设置 NEO4J_ENABLED=true")
        return

    results = {}

    # 测试 1: 连接
    results["connection"] = test_connection()
    if not results["connection"]:
        print("\n[ERROR] 连接失败，终止后续测试")
        return

    # 测试 2: 同步
    run_id = test_sync_graph()
    results["sync"] = run_id is not None

    # 测试 3: 查询实体
    results["query_entity"] = test_query_entity()

    # 测试 4: 查询患者图
    results["query_patient"] = test_query_patient_graph(run_id)

    # 测试 5: Cypher
    results["cypher"] = test_cypher_query()

    # 汇总
    print("\n" + "=" * 60)
    print("  测试结果汇总")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, passed_test in results.items():
        status = "PASS" if passed_test else "FAIL"
        print(f"  {name}: {status}")

    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n[SUCCESS] 所有测试通过! Neo4j 集成正常工作。")
    else:
        print("\n[WARN] 部分测试失败，请检查配置和 Neo4j 状态。")


if __name__ == "__main__":
    main()
