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
    显示证据图统计

    Args:
        graph_dict: 证据图的字典表示
    """
    nodes = graph_dict.get("nodes", {})
    by_type = {}
    by_agent = {}

    for n in nodes.values():
        # 按类型统计
        t = n.get("evidence_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
        # 按 Agent 统计
        a = n.get("source_agent", "unknown")
        by_agent[a] = by_agent.get(a, 0) + 1

    mtb_logger.info(f"[EVIDENCE] 总节点: {len(nodes)} | 类型分布: {by_type}")
    if by_agent:
        mtb_logger.info(f"[EVIDENCE] Agent 分布: {by_agent}")


def log_evidence_stats_detailed(graph_dict: dict, title: str = "EVIDENCE"):
    """
    显示证据图详细统计（增强版）

    Args:
        graph_dict: 证据图的字典表示
        title: 日志标签
    """
    if not graph_dict:
        mtb_logger.info(f"[{title}] 证据图为空")
        return

    nodes = graph_dict.get("nodes", {})
    by_type = {}
    by_agent = {}
    by_grade = {}

    for n in nodes.values():
        # 按类型统计
        t = n.get("evidence_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
        # 按 Agent 统计
        a = n.get("source_agent", "unknown")
        by_agent[a] = by_agent.get(a, 0) + 1
        # 按证据等级统计
        g = n.get("grade", "unknown")
        by_grade[g] = by_grade.get(g, 0) + 1

    mtb_logger.info(f"[{title}] ════════════════════════════════════════")
    mtb_logger.info(f"[{title}] 总节点: {len(nodes)}")
    mtb_logger.info(f"[{title}] 类型分布: {by_type}")
    mtb_logger.info(f"[{title}] Agent 分布: {by_agent}")
    mtb_logger.info(f"[{title}] 证据等级分布: {by_grade}")

    # 显示最近添加的证据（按迭代轮次排序）
    recent_nodes = sorted(
        nodes.values(),
        key=lambda n: n.get("iteration", 0),
        reverse=True
    )[:5]

    if recent_nodes:
        mtb_logger.info(f"[{title}] 最近添加:")
        for node in recent_nodes:
            agent = node.get("source_agent", "unknown")
            content = node.get("content", {})
            text = content.get("text", str(content))[:50] if content else ""
            grade = node.get("grade", "?")
            mtb_logger.info(f"[{title}]   - [{agent}][{grade}] {text}...")

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
