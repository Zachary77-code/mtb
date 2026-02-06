"""
Neo4j 同步层：将内存 EvidenceGraph 同步到 Neo4j 图数据库

Schema:
  (:Run {run_id, patient_id, timestamp, status, phase})
  (:Entity {canonical_id, entity_type, name, aliases})
  (:Evidence {edge_id, predicate, confidence, conflict_group})  ← reified edge
  (:Observation {obs_id, statement, grade, civic_type, source_agent, source_tool, provenance, source_url, iteration, created_at})

Relationships:
  (:Run)-[:CONTAINS]->(:Entity)
  (:Run)-[:CONTAINS]->(:Evidence)
  (:Entity)-[:HAS_OBS]->(:Observation)
  (:Evidence)-[:HAS_OBS]->(:Observation)
  (:Entity)-[:FROM]->(:Evidence)-[:TO]->(:Entity)
"""
from neo4j import GraphDatabase
from datetime import datetime
from typing import Dict, Any, Optional, List
from src.models.evidence_graph import EvidenceGraph, Entity, Edge, Observation
from src.utils.logger import mtb_logger as logger


class Neo4jSync:
    """Neo4j 同步层"""

    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        """
        初始化 Neo4j 连接

        Args:
            uri: Neo4j URI (neo4j://127.0.0.1:7687)
            user: Neo4j 用户名
            password: Neo4j 密码
            database: 数据库名（默认 neo4j）
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database
        self.ensure_schema()
        logger.info(f"[NEO4J] Connected to {uri}, database={database}")

    def close(self):
        """关闭驱动连接"""
        if self.driver:
            self.driver.close()
            logger.info("[NEO4J] Connection closed")

    def ensure_schema(self):
        """
        创建约束和索引（幂等操作）

        创建以下约束和索引：
        - entity_unique on Entity.canonical_id
        - obs_unique on Observation.obs_id
        - evidence_unique on Evidence.edge_id
        - run_unique on Run.run_id
        - Indexes on entity_type, grade, source_agent
        """
        with self.driver.session(database=self.database) as session:
            # 约束（唯一性）
            constraints = [
                "CREATE CONSTRAINT entity_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.canonical_id IS UNIQUE",
                "CREATE CONSTRAINT obs_unique IF NOT EXISTS FOR (o:Observation) REQUIRE o.obs_id IS UNIQUE",
                "CREATE CONSTRAINT evidence_unique IF NOT EXISTS FOR (ev:Evidence) REQUIRE ev.edge_id IS UNIQUE",
                "CREATE CONSTRAINT run_unique IF NOT EXISTS FOR (r:Run) REQUIRE r.run_id IS UNIQUE",
            ]

            # 索引（查询优化）
            indexes = [
                "CREATE INDEX entity_type_idx IF NOT EXISTS FOR (e:Entity) ON (e.entity_type)",
                "CREATE INDEX obs_grade_idx IF NOT EXISTS FOR (o:Observation) ON (o.grade)",
                "CREATE INDEX obs_agent_idx IF NOT EXISTS FOR (o:Observation) ON (o.source_agent)",
            ]

            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    # 约束可能已存在，忽略错误
                    logger.debug(f"[NEO4J] Constraint already exists or error: {e}")

            for index in indexes:
                try:
                    session.run(index)
                except Exception as e:
                    logger.debug(f"[NEO4J] Index already exists or error: {e}")

            logger.info("[NEO4J] Schema ensured (constraints + indexes)")

    def sync_graph(
        self,
        evidence_graph: EvidenceGraph,
        run_id: str,
        patient_id: str,
        phase: str = "unknown"
    ):
        """
        全量同步证据图到 Neo4j

        Args:
            evidence_graph: 内存证据图
            run_id: 运行 ID
            patient_id: 患者 ID
            phase: 阶段标识 (phase1/phase2/final)
        """
        start_time = datetime.now()
        logger.info(f"[NEO4J] Syncing graph for run_id={run_id}, patient_id={patient_id}, phase={phase}")

        with self.driver.session(database=self.database) as session:
            # 1. MERGE Run 节点
            session.execute_write(self._sync_run, run_id, patient_id, phase)

            # 2. 同步所有实体
            entity_count = 0
            for canonical_id, entity in evidence_graph.entities.items():
                session.execute_write(self._sync_entity, entity, run_id)
                entity_count += 1

            # 3. 同步所有边
            edge_count = 0
            for edge_id, edge in evidence_graph.edges.items():
                session.execute_write(self._sync_edge, edge, run_id)
                edge_count += 1

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"[NEO4J] Sync complete: {entity_count} entities, {edge_count} edges in {elapsed:.2f}s")

    @staticmethod
    def _sync_run(tx, run_id: str, patient_id: str, phase: str):
        """同步 Run 节点"""
        query = """
        MERGE (r:Run {run_id: $run_id})
        SET r.patient_id = $patient_id,
            r.phase = $phase,
            r.timestamp = datetime(),
            r.status = 'active'
        RETURN r
        """
        tx.run(query, run_id=run_id, patient_id=patient_id, phase=phase)

    @staticmethod
    def _sync_entity(tx, entity: Entity, run_id: str):
        """
        同步实体及其观察

        Args:
            tx: Neo4j 事务
            entity: Entity 对象
            run_id: 运行 ID
        """
        # 将 observations 序列化为 dict 列表
        observations = []
        for obs in entity.observations:
            observations.append({
                "obs_id": obs.id,
                "statement": obs.statement,
                "grade": obs.evidence_grade.value if obs.evidence_grade else None,
                "civic_type": obs.civic_type.value if obs.civic_type else None,
                "source_agent": obs.source_agent,
                "source_tool": obs.source_tool,
                "provenance": obs.provenance,
                "source_url": obs.source_url,
                "iteration": obs.iteration,
                "created_at": obs.created_at.isoformat(),
            })

        query = """
        MERGE (e:Entity {canonical_id: $canonical_id})
        SET e.name = $name,
            e.entity_type = $entity_type,
            e.aliases = $aliases,
            e.updated_at = $updated_at
        WITH e
        MATCH (r:Run {run_id: $run_id})
        MERGE (r)-[:CONTAINS]->(e)
        WITH e
        UNWIND $observations AS obs
        MERGE (o:Observation {obs_id: obs.obs_id})
        SET o.statement = obs.statement,
            o.grade = obs.grade,
            o.civic_type = obs.civic_type,
            o.source_agent = obs.source_agent,
            o.source_tool = obs.source_tool,
            o.provenance = obs.provenance,
            o.source_url = obs.source_url,
            o.iteration = obs.iteration,
            o.created_at = obs.created_at
        MERGE (e)-[:HAS_OBS]->(o)
        """

        tx.run(
            query,
            canonical_id=entity.canonical_id,
            name=entity.name,
            entity_type=entity.entity_type.value,
            aliases=entity.aliases,
            updated_at=entity.updated_at.isoformat(),
            run_id=run_id,
            observations=observations,
        )

    @staticmethod
    def _sync_edge(tx, edge: Edge, run_id: str):
        """
        同步边及其观察

        Args:
            tx: Neo4j 事务
            edge: Edge 对象
            run_id: 运行 ID
        """
        # 将 observations 序列化为 dict 列表
        observations = []
        for obs in edge.observations:
            observations.append({
                "obs_id": obs.id,
                "statement": obs.statement,
                "grade": obs.evidence_grade.value if obs.evidence_grade else None,
                "civic_type": obs.civic_type.value if obs.civic_type else None,
                "source_agent": obs.source_agent,
                "source_tool": obs.source_tool,
                "provenance": obs.provenance,
                "source_url": obs.source_url,
                "iteration": obs.iteration,
                "created_at": obs.created_at.isoformat(),
            })

        query = """
        MATCH (src:Entity {canonical_id: $source_id})
        MATCH (tgt:Entity {canonical_id: $target_id})
        MERGE (ev:Evidence {edge_id: $edge_id})
        SET ev.predicate = $predicate,
            ev.confidence = $confidence,
            ev.conflict_group = $conflict_group
        MERGE (src)-[:FROM]->(ev)
        MERGE (ev)-[:TO]->(tgt)
        WITH ev
        MATCH (r:Run {run_id: $run_id})
        MERGE (r)-[:CONTAINS]->(ev)
        WITH ev
        UNWIND $observations AS obs
        MERGE (o:Observation {obs_id: obs.obs_id})
        SET o.statement = obs.statement,
            o.grade = obs.grade,
            o.civic_type = obs.civic_type,
            o.source_agent = obs.source_agent,
            o.source_tool = obs.source_tool,
            o.provenance = obs.provenance,
            o.source_url = obs.source_url,
            o.iteration = obs.iteration,
            o.created_at = obs.created_at
        MERGE (ev)-[:HAS_OBS]->(o)
        """

        tx.run(
            query,
            source_id=edge.source_id,
            target_id=edge.target_id,
            edge_id=edge.id,
            predicate=edge.predicate.value,
            confidence=edge.confidence,
            conflict_group=edge.conflict_group,
            run_id=run_id,
            observations=observations,
        )

    def query_entity_across_runs(self, canonical_id: str) -> Optional[Dict[str, Any]]:
        """
        查询实体在所有运行中的信息

        Args:
            canonical_id: 实体规范 ID

        Returns:
            实体信息及其跨运行的所有观察
        """
        with self.driver.session(database=self.database) as session:
            query = """
            MATCH (e:Entity {canonical_id: $canonical_id})
            OPTIONAL MATCH (e)-[:HAS_OBS]->(o:Observation)
            OPTIONAL MATCH (r:Run)-[:CONTAINS]->(e)
            RETURN e, collect(DISTINCT o) as observations, collect(DISTINCT r.run_id) as runs
            """
            result = session.run(query, canonical_id=canonical_id)
            record = result.single()

            if not record:
                return None

            entity_node = record["e"]
            observations = record["observations"]
            runs = record["runs"]

            return {
                "canonical_id": entity_node["canonical_id"],
                "name": entity_node["name"],
                "entity_type": entity_node["entity_type"],
                "aliases": entity_node["aliases"],
                "observations": [dict(obs) for obs in observations if obs],
                "runs": runs,
            }

    def query_patient_graph(self, run_id: str) -> Dict[str, Any]:
        """
        查询指定运行的完整图

        Args:
            run_id: 运行 ID

        Returns:
            完整图数据（entities, edges, observations）
        """
        with self.driver.session(database=self.database) as session:
            query = """
            MATCH (r:Run {run_id: $run_id})-[:CONTAINS]->(e:Entity)
            OPTIONAL MATCH (e)-[:HAS_OBS]->(o:Observation)
            RETURN collect(DISTINCT e) as entities, collect(DISTINCT o) as observations
            """
            result = session.run(query, run_id=run_id)
            record = result.single()

            entities = [dict(e) for e in record["entities"]] if record["entities"] else []
            observations = [dict(o) for o in record["observations"] if o] if record["observations"] else []

            # 查询边
            edge_query = """
            MATCH (r:Run {run_id: $run_id})-[:CONTAINS]->(ev:Evidence)
            OPTIONAL MATCH (ev)-[:HAS_OBS]->(o:Observation)
            OPTIONAL MATCH (src:Entity)-[:FROM]->(ev)-[:TO]->(tgt:Entity)
            RETURN collect(DISTINCT ev) as edges, collect(DISTINCT o) as edge_observations,
                   collect(DISTINCT src.canonical_id) as sources, collect(DISTINCT tgt.canonical_id) as targets
            """
            edge_result = session.run(edge_query, run_id=run_id)
            edge_record = edge_result.single()

            edges = [dict(e) for e in edge_record["edges"]] if edge_record["edges"] else []
            edge_observations = [dict(o) for o in edge_record["edge_observations"] if o] if edge_record["edge_observations"] else []

            return {
                "run_id": run_id,
                "entities": entities,
                "edges": edges,
                "observations": observations + edge_observations,
            }

    def get_stats(self) -> Dict[str, int]:
        """
        获取图数据库统计信息

        Returns:
            节点和关系数量统计
        """
        with self.driver.session(database=self.database) as session:
            query = """
            MATCH (r:Run) WITH count(r) as runs
            MATCH (e:Entity) WITH runs, count(e) as entities
            MATCH (ev:Evidence) WITH runs, entities, count(ev) as edges
            MATCH (o:Observation) WITH runs, entities, edges, count(o) as observations
            RETURN runs, entities, edges, observations
            """
            result = session.run(query)
            record = result.single()

            if not record:
                return {"runs": 0, "entities": 0, "edges": 0, "observations": 0}

            return {
                "runs": record["runs"],
                "entities": record["entities"],
                "edges": record["edges"],
                "observations": record["observations"],
            }
