"""
日志配置
"""
import sys
from pathlib import Path

from loguru import logger

from config.settings import LOGS_DIR


def setup_logger(
    log_level: str = "INFO",
    log_file: str = "mtb.log",
    console: bool = True
) -> logger:
    """
    配置日志

    Args:
        log_level: 日志级别
        log_file: 日志文件名
        console: 是否输出到控制台

    Returns:
        配置后的 logger
    """
    # 移除默认处理器
    logger.remove()

    # 日志格式
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    simple_format = (
        "{time:HH:mm:ss} | {level: <8} | {message}"
    )

    # 控制台输出
    if console:
        logger.add(
            sys.stdout,
            format=simple_format,
            level=log_level,
            colorize=True
        )

    # 文件输出
    log_path = LOGS_DIR / log_file
    logger.add(
        str(log_path),
        format=log_format,
        level=log_level,
        rotation="10 MB",  # 文件大小达到 10MB 时轮转
        retention="7 days",  # 保留 7 天
        compression="zip",  # 压缩旧日志
        encoding="utf-8"
    )

    return logger


# 默认配置
mtb_logger = setup_logger()


# ==================== 进度显示辅助函数 ====================

def log_phase_progress(phase: str, iteration: int, max_iter: int, mode: str):
    """
    显示阶段进度条

    Args:
        phase: 阶段名称 (PHASE1/PHASE2)
        iteration: 当前迭代次数
        max_iter: 最大迭代次数
        mode: 研究模式 (breadth_first/depth_first)
    """
    bar = "█" * iteration + "░" * (max_iter - iteration)
    mtb_logger.info(f"[{phase}] 进度 [{bar}] {iteration}/{max_iter} | 模式: {mode}")


def log_evidence_stats(graph_dict: dict):
    """
    显示证据图统计（Entity-Edge-Observation 架构）

    Args:
        graph_dict: 证据图的字典表示 (entities, edges)
    """
    entities = graph_dict.get("entities", {})
    edges = graph_dict.get("edges", {})
    by_type = {}
    by_agent = {}
    total_observations = 0

    for entity in entities.values():
        # 按实体类型统计
        t = entity.get("entity_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
        # 统计观察数和 Agent 分布
        observations = entity.get("observations", [])
        total_observations += len(observations)
        for obs in observations:
            a = obs.get("source_agent", "unknown")
            by_agent[a] = by_agent.get(a, 0) + 1

    mtb_logger.info(f"[EVIDENCE] 实体: {len(entities)}, 边: {len(edges)}, 观察: {total_observations} | 类型: {by_type}")
    if by_agent:
        mtb_logger.info(f"[EVIDENCE] Agent 分布: {by_agent}")

    # 边统计
    if edges:
        edge_types = {}
        for e in edges.values():
            et = e.get("predicate", "unknown")
            edge_types[et] = edge_types.get(et, 0) + 1
        mtb_logger.info(f"[EVIDENCE] 关系分布: {edge_types}")

        # 冲突检测
        conflicts = [e for e in edges.values() if e.get("conflict_group")]
        if conflicts:
            mtb_logger.warning(f"[EVIDENCE] 检测到 {len(conflicts)} 个证据冲突")


def log_evidence_stats_detailed(graph_dict: dict, title: str = "EVIDENCE"):
    """
    显示证据图详细统计（Entity-Edge-Observation 架构，增强版）

    Args:
        graph_dict: 证据图的字典表示 (entities, edges)
        title: 日志标签
    """
    if not graph_dict:
        mtb_logger.info(f"[{title}] 证据图为空")
        return

    entities = graph_dict.get("entities", {})
    edges = graph_dict.get("edges", {})
    by_type = {}
    by_agent = {}
    by_grade = {}
    total_observations = 0

    for entity in entities.values():
        # 按实体类型统计
        t = entity.get("entity_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

        # 统计观察和 Agent/Grade 分布
        observations = entity.get("observations", [])
        total_observations += len(observations)
        for obs in observations:
            a = obs.get("source_agent", "unknown")
            by_agent[a] = by_agent.get(a, 0) + 1
            g = obs.get("evidence_grade", "unknown")
            by_grade[g] = by_grade.get(g, 0) + 1

    mtb_logger.info(f"[{title}] ════════════════════════════════════════")
    mtb_logger.info(f"[{title}] 总实体: {len(entities)}, 总边: {len(edges)}, 总观察: {total_observations}")
    mtb_logger.info(f"[{title}] 实体类型分布: {by_type}")
    mtb_logger.info(f"[{title}] Agent 分布: {by_agent}")
    mtb_logger.info(f"[{title}] 证据等级分布: {by_grade}")

    # 边统计
    if edges:
        predicate_types = {}
        total_confidence = 0.0

        for e in edges.values():
            pred = e.get("predicate", "unknown")
            predicate_types[pred] = predicate_types.get(pred, 0) + 1
            total_confidence += e.get("confidence", 0.0)

        avg_confidence = total_confidence / len(edges) if edges else 0.0
        mtb_logger.info(f"[{title}] 谓词分布: {predicate_types}")
        mtb_logger.info(f"[{title}] 平均边置信度: {avg_confidence:.2f}")

        # 冲突检测（通过 conflict_group 字段）
        conflicts = [e for e in edges.values() if e.get("conflict_group")]
        if conflicts:
            conflict_groups = {}
            for c in conflicts:
                group = c.get("conflict_group")
                conflict_groups[group] = conflict_groups.get(group, 0) + 1
            mtb_logger.warning(f"[{title}] ⚠ 检测到 {len(conflict_groups)} 组证据冲突 ({len(conflicts)} 条边)")
            for conflict in conflicts[:3]:  # 只显示前3个
                src = conflict.get("source_id", "?")
                tgt = conflict.get("target_id", "?")
                pred = conflict.get("predicate", "?")
                mtb_logger.warning(f"[{title}]   - {src} --[{pred}]--> {tgt}")

    # 显示最近添加的实体（按最新观察的迭代轮次排序）
    def get_latest_iteration(entity):
        observations = entity.get("observations", [])
        if not observations:
            return 0
        return max(obs.get("iteration", 0) for obs in observations)

    recent_entities = sorted(
        entities.values(),
        key=get_latest_iteration,
        reverse=True
    )[:5]

    if recent_entities:
        mtb_logger.info(f"[{title}] 最近添加的实体:")
        for entity in recent_entities:
            name = entity.get("name", "unknown")
            entity_type = entity.get("entity_type", "?")
            obs_list = entity.get("observations", [])
            obs_count = len(obs_list)
            # 获取最高证据等级
            grades = [o.get("evidence_grade") for o in obs_list if o.get("evidence_grade")]
            best_grade = min(grades) if grades else "?"  # A < B < C < D < E
            mtb_logger.info(f"[{title}]   - [{entity_type}] {name} ({obs_count} obs, best: {best_grade})")

    mtb_logger.info(f"[{title}] ════════════════════════════════════════")


def log_tool_call(agent: str, tool: str, query: str, success: bool, result_len: int = 0):
    """
    显示工具调用日志

    Args:
        agent: Agent 名称
        tool: 工具名称
        query: 查询内容
        success: 是否成功
        result_len: 结果长度
    """
    status = "✓" if success else "✗"
    query_short = query[:60] + "..." if len(query) > 60 else query
    mtb_logger.info(f"[{agent}] {status} {tool}: {query_short}")
    if result_len > 0:
        mtb_logger.info(f"[{agent}]   返回 {result_len} 字符")


def log_separator(title: str = "", char: str = "═"):
    """
    显示分隔线

    Args:
        title: 标题文字
        char: 分隔符字符
    """
    if title:
        mtb_logger.info(f"[{title}] {char * 40}")
    else:
        mtb_logger.info(char * 50)


def log_edge_stats(graph_dict: dict, title: str = "EDGE"):
    """
    显示边统计（Entity-Edge-Observation 架构）

    Args:
        graph_dict: 证据图的字典表示 (entities, edges)
        title: 日志标签
    """
    edges = graph_dict.get("edges", {})

    if not edges:
        mtb_logger.info(f"[{title}] 尚无边")
        return

    predicate_counts = {}
    total_confidence = 0.0
    total_observations = 0

    for e in edges.values():
        pred = e.get("predicate", "unknown")
        predicate_counts[pred] = predicate_counts.get(pred, 0) + 1
        total_confidence += e.get("confidence", 0.0)
        # 统计边上的观察数
        edge_observations = e.get("observations", [])
        total_observations += len(edge_observations)

    avg_confidence = total_confidence / len(edges) if edges else 0.0

    mtb_logger.info(f"[{title}] 总边数: {len(edges)}, 总观察: {total_observations}")
    mtb_logger.info(f"[{title}] 谓词分布: {predicate_counts}")
    mtb_logger.info(f"[{title}] 平均置信度: {avg_confidence:.2f}")

    # 显示关键谓词（使用新架构的谓词名称）
    key_predicates = ["SENSITIZES", "CAUSES_RESISTANCE", "CONTRADICTS", "SUPPORTS", "TREATS", "INHIBITS"]
    for pred in key_predicates:
        count = predicate_counts.get(pred, 0)
        if count > 0:
            mtb_logger.info(f"[{title}]   {pred}: {count} 条")

    # 显示冲突组
    conflict_groups = {}
    for e in edges.values():
        group = e.get("conflict_group")
        if group:
            conflict_groups[group] = conflict_groups.get(group, 0) + 1
    if conflict_groups:
        mtb_logger.warning(f"[{title}] ⚠ 冲突组: {len(conflict_groups)} 组")


def log_convergence_status(phase: str, iteration: int, max_iter: int,
                           pending_dirs: int, evidence_count: int,
                           new_findings: int, coverage: float, result: str):
    """
    显示收敛检查状态

    Args:
        phase: 阶段名称
        iteration: 当前迭代
        max_iter: 最大迭代
        pending_dirs: 待完成方向数
        evidence_count: 证据节点数
        new_findings: 本轮新发现数
        coverage: 问题覆盖率
        result: 检查结果 (continue/converged)
    """
    mtb_logger.info(f"[{phase}_CONVERGENCE] 检查收敛条件...")
    mtb_logger.info(f"[{phase}_CONVERGENCE]   迭代: {iteration}/{max_iter}")
    mtb_logger.info(f"[{phase}_CONVERGENCE]   待完成方向: {pending_dirs}")
    mtb_logger.info(f"[{phase}_CONVERGENCE]   证据节点: {evidence_count}")
    mtb_logger.info(f"[{phase}_CONVERGENCE]   本轮新发现: {new_findings}")
    mtb_logger.info(f"[{phase}_CONVERGENCE]   问题覆盖率: {coverage:.1%}")
    result_icon = "→ 收敛" if result == "converged" else "→ 继续"
    mtb_logger.info(f"[{phase}_CONVERGENCE] {result_icon}")


if __name__ == "__main__":
    # 测试日志
    mtb_logger.info("日志模块测试")
    mtb_logger.debug("调试信息")
    mtb_logger.warning("警告信息")
    mtb_logger.error("错误信息")
    print(f"日志文件位置: {LOGS_DIR}")
