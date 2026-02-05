"""
Evidence Graph 持久化工具

JSON 文件备份 + Neo4j 同步的统一入口
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from src.utils.logger import mtb_logger as logger


def save_evidence_graph_json(
    evidence_graph_data: Dict[str, Any],
    run_folder: str,
    phase: str,
    iteration: Optional[int] = None,
    checkpoint_type: str = "final"
) -> Optional[str]:
    """
    保存证据图为 JSON 文件

    Args:
        evidence_graph_data: 证据图字典数据
        run_folder: 运行文件夹路径
        phase: 阶段标识 (phase1/phase2/final)
        iteration: 迭代轮次（checkpoint 时提供）
        checkpoint_type: 检查点类型 (final/phase_complete/checkpoint)

    Returns:
        保存的文件路径，失败返回 None
    """
    try:
        from src.models.evidence_graph import load_evidence_graph

        # 加载为 EvidenceGraph 对象
        graph = load_evidence_graph(evidence_graph_data)

        # 序列化为持久化格式（添加元数据）
        persistence_dict = {
            "metadata": {
                "saved_at": datetime.now().isoformat(),
                "phase": phase,
                "iteration": iteration,
                "checkpoint_type": checkpoint_type,
                "entity_count": len(graph.entities),
                "edge_count": len(graph.edges),
            },
            "graph": graph.to_dict()
        }

        # 确定文件名
        run_folder_path = Path(run_folder)
        if checkpoint_type == "final":
            filename = "evidence_graph.json"
        elif checkpoint_type == "phase_complete":
            filename = f"evidence_graph_{phase}_complete.json"
        else:  # checkpoint
            filename = f"evidence_graph_{phase}_iter{iteration}.json"

        filepath = run_folder_path / filename

        # 保存 JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(persistence_dict, f, ensure_ascii=False, indent=2)

        logger.info(f"[GRAPH_PERSIST] Saved {checkpoint_type} graph to {filepath}")
        logger.info(f"[GRAPH_PERSIST] Stats: {len(graph.entities)} entities, {len(graph.edges)} edges")

        return str(filepath)

    except Exception as e:
        logger.error(f"[GRAPH_PERSIST] Failed to save graph: {e}")
        return None


def load_evidence_graph_json(filepath: str) -> Optional[Dict[str, Any]]:
    """
    从 JSON 文件加载证据图

    Args:
        filepath: JSON 文件路径

    Returns:
        证据图字典，失败返回 None
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 检查是否有元数据信封
        if "graph" in data and "metadata" in data:
            logger.info(f"[GRAPH_PERSIST] Loaded graph from {filepath}")
            logger.info(f"[GRAPH_PERSIST] Metadata: {data['metadata']}")
            return data["graph"]
        else:
            # 直接返回数据（兼容旧格式）
            logger.info(f"[GRAPH_PERSIST] Loaded graph from {filepath} (legacy format)")
            return data

    except Exception as e:
        logger.error(f"[GRAPH_PERSIST] Failed to load graph from {filepath}: {e}")
        return None


def checkpoint_evidence_graph(
    state: Dict[str, Any],
    phase: str,
    iteration: Optional[int] = None,
    checkpoint_type: str = "checkpoint"
) -> bool:
    """
    统一的证据图检查点入口

    同时执行：
    1. JSON 文件备份（总是执行）
    2. Neo4j 同步（如果启用）

    Args:
        state: MtbState 状态对象
        phase: 阶段标识 (phase1/phase2/final)
        iteration: 迭代轮次（可选）
        checkpoint_type: 检查点类型 (final/phase_complete/checkpoint)

    Returns:
        是否成功
    """
    from config.settings import NEO4J_ENABLED, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

    # 获取必要字段
    evidence_graph_data = state.get("evidence_graph")
    run_folder = state.get("run_folder")
    run_id = state.get("run_id", "unknown")

    if not evidence_graph_data or not run_folder:
        logger.warning("[GRAPH_PERSIST] Missing evidence_graph or run_folder in state, skipping checkpoint")
        return False

    success = True

    # 1. 总是保存 JSON 备份
    json_path = save_evidence_graph_json(
        evidence_graph_data=evidence_graph_data,
        run_folder=run_folder,
        phase=phase,
        iteration=iteration,
        checkpoint_type=checkpoint_type
    )

    if not json_path:
        logger.error("[GRAPH_PERSIST] JSON backup failed")
        success = False

    # 2. 如果启用 Neo4j，执行同步
    if NEO4J_ENABLED:
        try:
            from src.utils.neo4j_sync import Neo4jSync
            from src.models.evidence_graph import load_evidence_graph

            # 加载图对象
            graph = load_evidence_graph(evidence_graph_data)

            # 提取患者 ID（从 run_folder 或 state 中）
            patient_id = state.get("patient_id", "unknown")
            if patient_id == "unknown":
                # 从 run_folder 路径中提取
                folder_name = Path(run_folder).name
                parts = folder_name.split("_")
                if len(parts) > 1:
                    patient_id = "_".join(parts[1:])

            # 同步到 Neo4j
            neo4j = Neo4jSync(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
            try:
                neo4j.sync_graph(
                    evidence_graph=graph,
                    run_id=run_id,
                    patient_id=patient_id,
                    phase=phase
                )
                logger.info(f"[GRAPH_PERSIST] Neo4j sync complete for run_id={run_id}, phase={phase}")
            finally:
                neo4j.close()

        except Exception as e:
            logger.warning(f"[GRAPH_PERSIST] Neo4j sync failed (non-critical): {e}")
            # Neo4j 失败不影响整体流程，只记录警告

    return success
