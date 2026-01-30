"""
Research Subgraph - 两阶段研究循环子图

实现 DeepEvidence 风格的研究循环：
- Phase 1: Pathologist + Geneticist + Recruiter 并行 BFRS/DFRS 循环
- Phase 2: Oncologist 独立 BFRS/DFRS 循环
"""
import json
from typing import List, Literal, Dict, Any, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.types import Send

from src.models.state import MtbState
from src.models.evidence_graph import (
    load_evidence_graph,
    Entity,
    Edge,
)
from src.models.research_plan import (
    load_research_plan,
    ResearchMode
)
from src.agents.base_agent import SUBGRAPH_MODEL, ORCHESTRATOR_MODEL
from src.agents.pathologist import PathologistAgent
from src.agents.geneticist import GeneticistAgent
from src.agents.recruiter import RecruiterAgent
from src.agents.oncologist import OncologistAgent
from src.agents.research_mixin import ResearchMixin
from src.agents.plan_agent import PlanAgent
from src.utils.logger import (
    mtb_logger as logger,
    log_separator,
    log_evidence_stats,
    log_edge_stats
)
from config.settings import (
    MAX_PHASE1_ITERATIONS,
    MAX_PHASE2_ITERATIONS,
    MIN_EVIDENCE_NODES,
    MIN_EVIDENCE_PER_DIRECTION,
    COVERAGE_REQUIRED_MODULES
)
# ConvergenceJudge 已废弃，收敛判断移入 PlanAgent
# from src.agents.convergence_judge import ConvergenceJudgeAgent


# ==================== 研究增强型 Agent ====================

class ResearchPathologist(PathologistAgent, ResearchMixin):
    """具有研究能力的病理学家"""
    def __init__(self):
        super().__init__()
        self.model = SUBGRAPH_MODEL  # 使用 flash 模型


class ResearchGeneticist(GeneticistAgent, ResearchMixin):
    """具有研究能力的遗传学家"""
    def __init__(self):
        super().__init__()
        self.model = SUBGRAPH_MODEL


class ResearchRecruiter(RecruiterAgent, ResearchMixin):
    """具有研究能力的临床试验专员"""
    def __init__(self):
        super().__init__()
        self.model = SUBGRAPH_MODEL


class ResearchOncologist(OncologistAgent, ResearchMixin):
    """具有研究能力的肿瘤学家"""
    def __init__(self):
        super().__init__()
        self.model = SUBGRAPH_MODEL


# ==================== 报告生成型 Agent（Pro 模型）====================

class ReportPathologist(PathologistAgent):
    """使用 Pro 模型生成领域报告的病理学家"""
    def __init__(self):
        super().__init__()
        self.model = ORCHESTRATOR_MODEL
        self.tools = []


class ReportGeneticist(GeneticistAgent):
    """使用 Pro 模型生成领域报告的遗传学家"""
    def __init__(self):
        super().__init__()
        self.model = ORCHESTRATOR_MODEL
        self.tools = []


class ReportRecruiter(RecruiterAgent):
    """使用 Pro 模型生成领域报告的临床试验专员"""
    def __init__(self):
        super().__init__()
        self.model = ORCHESTRATOR_MODEL
        self.tools = []


class ReportOncologist(OncologistAgent):
    """使用 Pro 模型生成领域报告的肿瘤学家"""
    def __init__(self):
        super().__init__()
        self.model = ORCHESTRATOR_MODEL
        self.tools = []


# ==================== 模块覆盖检查 ====================

def check_direction_evidence_sufficiency(state: MtbState, agent_names: list[str] = None) -> tuple[bool, list[str]]:
    """
    检查每个研究方向是否有足够证据

    Args:
        state: MtbState 状态
        agent_names: 要检查的 Agent 列表，None 表示检查所有

    Returns:
        (是否通过, 证据不足的方向描述列表)
    """
    plan = load_research_plan(state.get("research_plan", {}))
    if not plan:
        return True, []

    insufficient = []
    directions_to_check = plan.directions
    if agent_names:
        directions_to_check = [d for d in plan.directions if d.target_agent in agent_names]

    for direction in directions_to_check:
        evidence_count = len(direction.evidence_ids)
        if evidence_count < MIN_EVIDENCE_PER_DIRECTION:
            insufficient.append(f"{direction.id}:{direction.topic[:20]}({evidence_count}/{MIN_EVIDENCE_PER_DIRECTION})")

    if insufficient:
        logger.warning(f"[DIRECTION_EVIDENCE] 证据不足的方向: {insufficient}")
        return False, insufficient

    logger.info(f"[DIRECTION_EVIDENCE] 所有方向证据充分 (>= {MIN_EVIDENCE_PER_DIRECTION})")
    return True, []


def check_module_coverage(state: MtbState) -> tuple[bool, list[str]]:
    """
    检查模块覆盖率

    Args:
        state: MtbState 状态

    Returns:
        (是否通过, 未覆盖模块列表)
    """
    plan = load_research_plan(state.get("research_plan", {}))
    if not plan:
        logger.info("[MODULE_COVERAGE] 无研究计划，跳过检查")
        return True, []

    covered_modules = plan.get_module_coverage()
    uncovered = [m for m in COVERAGE_REQUIRED_MODULES if m not in covered_modules]

    if uncovered:
        logger.warning(f"[MODULE_COVERAGE] 未覆盖模块: {uncovered}")
        return False, uncovered

    logger.info(f"[MODULE_COVERAGE] 所有 {len(COVERAGE_REQUIRED_MODULES)} 个模块已覆盖")
    return True, []


def check_agent_module_coverage(state: MtbState, agent_names: list[str]) -> tuple[bool, list[str]]:
    """
    检查指定Agent是否覆盖了各自被分配的target_modules

    每个Phase只检查该阶段Agent被分配的模块，而不是全局9个模块。

    Args:
        state: MtbState 状态
        agent_names: 要检查的Agent列表

    Returns:
        (是否通过, 未覆盖模块列表)
    """
    plan = load_research_plan(state.get("research_plan", {}))
    if not plan:
        logger.info("[AGENT_MODULE_COVERAGE] 无研究计划，跳过检查")
        return True, []

    uncovered = []
    for direction in plan.directions:
        if direction.target_agent not in agent_names:
            continue
        # 检查该方向的target_modules是否有证据
        if len(direction.evidence_ids) == 0:
            uncovered.extend(direction.target_modules)

    uncovered = list(set(uncovered))  # 去重

    if uncovered:
        logger.warning(f"[AGENT_MODULE_COVERAGE] Agent {agent_names} 未覆盖模块: {uncovered}")
        return False, uncovered

    logger.info(f"[AGENT_MODULE_COVERAGE] Agent {agent_names} 所有分配模块已覆盖")
    return True, []


# ==================== 证据等级辅助函数 ====================

def _grade_description(grade) -> str:
    """证据等级描述"""
    if not grade:
        return "未知"
    descs = {
        "A": "Validated",
        "B": "Clinical",
        "C": "Case Study",
        "D": "Preclinical",
        "E": "Inferential"
    }
    return descs.get(grade.value if hasattr(grade, 'value') else grade, "")


# ==================== Agent 报告保存 ====================

def _save_agent_report(state: MtbState, filename: str, content: str):
    """
    保存 Agent 报告到 run_folder

    Args:
        state: MtbState 包含 run_folder
        filename: 文件名（如 "1_pathologist_report.md"）
        content: 报告内容
    """
    from pathlib import Path
    run_folder = state.get("run_folder")
    if not run_folder:
        logger.warning(f"[SAVE_REPORT] run_folder 未设置，无法保存 {filename}")
        return
    filepath = Path(run_folder) / filename
    filepath.write_text(content, encoding="utf-8")
    logger.info(f"[SAVE_REPORT] 已保存: {filepath}")


# ==================== 迭代报告输出 ====================

def _save_iteration_report(
    state: MtbState,
    phase: str,
    iteration: int,
    agent_findings: Dict[str, Any],
    convergence_details: Dict[str, Any],
    final_decision: str
):
    """
    保存每次迭代的中间报告（包含 ConvergenceJudge 结果）

    Args:
        state: MtbState 状态
        phase: 阶段名称 "PHASE1" 或 "PHASE2"
        iteration: 迭代轮次
        agent_findings: Agent 发现详情 {Agent名: {count: N, evidence_ids: [...]}}
        convergence_details: 收敛检查详情
        final_decision: 最终决策 "continue" 或 "converged"
    """
    import os

    run_folder = state.get("run_folder", "")
    if not run_folder:
        logger.warning(f"[ITERATION_REPORT] run_folder 未设置，跳过保存")
        return

    evidence_graph = state.get("evidence_graph", {})
    graph = load_evidence_graph(evidence_graph)

    # 生成报告内容
    lines = [
        f"# {phase} 迭代 {iteration} 报告",
        "",
        f"**时间**: {datetime.now().isoformat()}",
        f"**决策**: {final_decision}",
        "",
    ]

    # === 本轮新增证据 ===
    lines.append("## 本轮新增证据")
    lines.append("")
    for agent_name, findings in agent_findings.items():
        count = findings.get("count", 0)
        evidence_ids = findings.get("evidence_ids", [])
        lines.append(f"### {agent_name}: {count} 条")
        if graph and evidence_ids:
            for eid in evidence_ids:
                # 新模型：evidence_ids 是 entity canonical_id
                entity = graph.get_entity(eid)
                if entity:
                    best_grade = entity.get_best_grade()
                    grade = f"[{best_grade.value}]" if best_grade else ""
                    etype = entity.entity_type.value if entity.entity_type else "unknown"
                    # 获取最新观察的摘要
                    obs_text = ""
                    if entity.observations:
                        latest_obs = entity.observations[-1]
                        obs_text = latest_obs.statement or ""
                    lines.append(f"- {grade} [{etype}] {entity.name}: {obs_text}...")
        lines.append("")

    # === Evidence Graph 当前状态 ===
    lines.append("## Evidence Graph 当前状态")
    lines.append("")
    if graph:
        summary = graph.summary()
        agent_summary = graph.summary_by_agent()
        lines.append(f"- **总实体数**: {summary.get('total_entities', 0)}")
        lines.append(f"- **总边数**: {summary.get('total_edges', 0)}")
        lines.append(f"- **总观察数**: {summary.get('total_observations', 0)}")
        lines.append(f"- **实体类型分布**: {summary.get('entities_by_type', {})}")
        # Agent 分布从 agent_summary 获取
        agent_dist = {a: s.get('observation_count', 0) for a, s in agent_summary.items()}
        lines.append(f"- **Agent 观察分布**: {agent_dist}")
        lines.append(f"- **证据等级分布**: {summary.get('best_grades', {})}")
    else:
        lines.append("- 证据图为空")
    lines.append("")

    # === 收敛检查详情 ===
    lines.append("## 收敛检查 (Convergence Check)")
    lines.append("")

    # 处理 Phase 1 多 Agent 的情况
    if phase == "PHASE1" and isinstance(convergence_details, dict):
        # Phase 1: convergence_details 可能是 {Agent名: {step1..., step2..., step3...}}
        for agent_name, agent_details in convergence_details.items():
            if isinstance(agent_details, dict) and "step1_direction_evidence" in agent_details:
                lines.append(f"### {agent_name} 收敛检查")
                lines.append("")
                _append_convergence_steps(lines, agent_details)
                lines.append("")
        # 如果是单独的 step1/step2/step3 结构（Phase 2 或 Phase 1 全局）
        if "step1_metrics" in convergence_details or "step2_module" in convergence_details:
            _append_convergence_steps(lines, convergence_details)
    else:
        # Phase 2 或简单结构
        _append_convergence_steps(lines, convergence_details)

    # === 最终决策 ===
    lines.append("## 最终决策")
    lines.append("")
    decision_text = "继续下一轮迭代" if final_decision == "continue" else "研究已收敛，进入下一阶段"
    lines.append(f"**{final_decision.upper()}** - {decision_text}")

    # 保存文件
    filename = f"{phase.lower()}_iter{iteration}_report.md"
    filepath = os.path.join(run_folder, filename)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logger.info(f"[ITERATION_REPORT] 已保存: {filename}")
    except Exception as e:
        logger.error(f"[ITERATION_REPORT] 保存失败: {e}")


def _append_convergence_steps(lines: list, details: Dict[str, Any]):
    """向报告添加收敛检查步骤详情"""
    # Step 1: Metric-based / Direction Evidence
    step1 = details.get("step1_metrics", details.get("step1_direction_evidence", {}))
    if step1:
        step1_status = "✓ 通过" if step1.get("passed") else "✗ 未通过"
        lines.append(f"#### Step 1: Metric-based 检查 {step1_status}")
        if step1.get("reason"):
            lines.append(f"- 原因: {step1['reason']}")
        if step1.get("insufficient"):
            lines.append(f"- 证据不足: {step1['insufficient']}")
        lines.append("")

    # Step 2: Module Coverage
    step2 = details.get("step2_module", details.get("step2_module_coverage", {}))
    if step2:
        step2_status = "✓ 通过" if step2.get("passed") else "✗ 未通过"
        lines.append(f"#### Step 2: Module Coverage 检查 {step2_status}")
        if step2.get("uncovered"):
            lines.append(f"- 未覆盖模块: {', '.join(step2['uncovered'])}")
        lines.append("")

    # Step 3: ConvergenceJudge
    step3 = details.get("step3_judge")
    if step3:
        judge_decision = step3.get("decision", "N/A")
        judge_confidence = step3.get("confidence", 0)
        judge_reasoning = step3.get("reasoning", "")
        judge_gaps = step3.get("gaps", [])
        judge_strengths = step3.get("strengths", [])

        judge_status = "✓ 收敛" if judge_decision == "converged" else "○ 继续"
        lines.append(f"#### Step 3: ConvergenceJudge Agent {judge_status}")
        lines.append(f"- **决策**: {judge_decision}")
        lines.append(f"- **置信度**: {judge_confidence:.2f}" if isinstance(judge_confidence, (int, float)) else f"- **置信度**: {judge_confidence}")
        lines.append(f"- **理由**: {judge_reasoning}")
        if judge_gaps:
            lines.append("- **研究空白 (Gaps)**:")
            for gap in judge_gaps:
                lines.append(f"  - {gap}")
        if judge_strengths:
            lines.append("- **已覆盖优势 (Strengths)**:")
            for strength in judge_strengths:
                lines.append(f"  - {strength}")
        lines.append("")
    else:
        lines.append("#### Step 3: ConvergenceJudge Agent")
        lines.append("- 未触发（前置检查未通过或达到迭代上限）")
        lines.append("")


def _save_detailed_iteration_report(
    state: MtbState,
    phase: str,
    iteration: int,
    eval_result: Dict[str, Any],
    agent_names: List[str],
    pre_eval_plan: Optional[Dict[str, Any]] = None
):
    """
    保存 PlanAgent 评估后的详细迭代报告

    报告包含：
    0. 本轮迭代执行详情（各方向执行概览表）
    1. 下一轮各方向研究模式
    2. PlanAgent 决策和理由
    3. 本轮新增证据的完整明细（不截断）
    4. Evidence Graph 完整统计

    Args:
        state: MtbState 状态
        phase: 阶段名称 "PHASE1" 或 "PHASE2"
        iteration: 迭代轮次
        eval_result: PlanAgent 评估结果
        agent_names: 参与的 Agent 列表
        pre_eval_plan: 评估前的研究计划（用于对比变化）
    """
    import os

    run_folder = state.get("run_folder", "")
    if not run_folder:
        logger.warning("[DETAILED_REPORT] run_folder 未设置，跳过保存")
        return

    evidence_graph = state.get("evidence_graph", {})
    graph = load_evidence_graph(evidence_graph)

    lines = [
        f"# {phase} 迭代 {iteration} 详细报告",
        "",
        f"**时间**: {datetime.now().isoformat()}",
        f"**PlanAgent 决策**: {eval_result.get('decision', 'unknown')}",
        f"**下一轮模式**: {eval_result.get('research_mode', 'N/A')}",
        "",
    ]

    # === 本轮迭代执行详情 ===
    if pre_eval_plan:
        pre_plan = load_research_plan(pre_eval_plan)
        post_plan = load_research_plan(eval_result.get("research_plan", {}))

        if pre_plan:
            lines.append("## 本轮迭代执行详情")
            lines.append("")

            # 合并表格：本轮各方向执行概览
            lines.append("| 方向 ID | 主题 | Agent | 模式 | Obs数(实体+边) | Entity数 | 状态变化 |")
            lines.append("|---------|------|-------|------|----------------|----------|----------|")
            for d in pre_plan.directions:
                if d.target_agent in agent_names:
                    mode_disp = {"breadth_first": "BFRS", "depth_first": "DFRS", "skip": "Skip"}.get(
                        d.preferred_mode, d.preferred_mode
                    )
                    topic_short = d.topic
                    # 计算 observation 数和 entity 数（只计算本 agent 的观察，含实体+边）
                    target_agent = d.target_agent
                    entity_count = len(d.evidence_ids)
                    evidence_id_set = set(d.evidence_ids)
                    # 实体观察数（仅本 agent）
                    entity_obs_count = sum(
                        sum(1 for obs in graph.get_entity(eid).observations
                            if obs.source_agent == target_agent)
                        for eid in d.evidence_ids
                        if graph and graph.get_entity(eid)
                    )
                    # 边观察数（仅本 agent，且边的端点在该方向的 evidence_ids 中）
                    edge_obs_count = 0
                    if graph:
                        for edge in graph.edges.values():
                            if edge.source_id in evidence_id_set or edge.target_id in evidence_id_set:
                                edge_obs_count += sum(
                                    1 for obs in edge.observations
                                    if obs.source_agent == target_agent
                                )
                    obs_count = entity_obs_count + edge_obs_count
                    # 状态变化
                    post_d = post_plan.get_direction_by_id(d.id) if post_plan else None
                    pre_status = d.status.value
                    post_status = post_d.status.value if post_d else pre_status
                    status_change = f"{pre_status} → {post_status}" if pre_status != post_status else pre_status
                    lines.append(f"| {d.id} | {topic_short} | {d.target_agent} | {mode_disp} | {obs_count} | {entity_count} | {status_change} |")
            lines.append("")

    # === 0. 下一轮各方向研究模式 ===
    research_plan = eval_result.get("research_plan", state.get("research_plan", {}))
    plan = load_research_plan(research_plan)
    if plan and plan.directions:
        # 构建 pre_plan 方向索引，用于检测新增/更新
        pre_plan_obj = load_research_plan(pre_eval_plan) if pre_eval_plan else None
        pre_direction_map = {}
        if pre_plan_obj:
            for d in pre_plan_obj.directions:
                pre_direction_map[d.id] = d

        lines.append("## 0. 下一轮各方向研究模式")
        lines.append("")
        lines.append("| 方向 ID | 主题 | Agent | 模式 | 变动 | 理由 |")
        lines.append("|---------|------|-------|------|------|------|")
        for d in plan.directions:
            if d.target_agent in agent_names:
                mode_display = {"breadth_first": "BFRS", "depth_first": "DFRS", "skip": "Skip"}.get(d.preferred_mode, d.preferred_mode)
                topic_short = d.topic
                # 判断变动类型
                if d.id not in pre_direction_map:
                    change_tag = "新增"
                else:
                    pre_d = pre_direction_map[d.id]
                    pre_status = pre_d.status.value if hasattr(pre_d.status, 'value') else str(pre_d.status)
                    post_status = d.status.value if hasattr(d.status, 'value') else str(d.status)
                    pre_mode = pre_d.preferred_mode
                    post_mode = d.preferred_mode
                    if pre_status != post_status or pre_mode != post_mode:
                        change_tag = "更新"
                    else:
                        change_tag = "—"
                lines.append(f"| {d.id} | {topic_short} | {d.target_agent} | {mode_display} | {change_tag} | {d.mode_reason} |")
        lines.append("")

    # === 1. PlanAgent 评估结果 ===
    lines.append("## 1. PlanAgent 评估结果")
    lines.append("")
    lines.append("### 决策理由")
    lines.append(eval_result.get("reasoning", "无"))
    lines.append("")

    qa = eval_result.get("quality_assessment", {})
    lines.append("### 质量评估")
    high_quality = qa.get('high_quality_coverage', [])
    low_quality = qa.get('low_quality_only', [])
    conflicts = qa.get('conflicts', [])
    lines.append(f"- **有高质量证据的模块**: {', '.join(high_quality) if high_quality else '无'}")
    lines.append(f"- **只有低质量证据的模块**: {', '.join(low_quality) if low_quality else '无'}")
    lines.append(f"- **证据冲突**: {', '.join(conflicts) if conflicts else '无'}")
    lines.append("")

    # 各方向完成情况评估（始终显示）
    direction_assessments = eval_result.get("direction_assessments", {})
    direction_stats = eval_result.get("direction_stats", {})
    needs_deep_items = eval_result.get("needs_deep_research", [])
    research_plan_data = eval_result.get("research_plan", state.get("research_plan", {}))
    assessed_plan = load_research_plan(research_plan_data)

    # 按方向分组 needs_deep_research
    deep_by_dir = {}
    for item in needs_deep_items:
        d_id = item.get("direction_id", "") if isinstance(item, dict) else ""
        if d_id not in deep_by_dir:
            deep_by_dir[d_id] = []
        deep_by_dir[d_id].append(item)

    # 收集未收敛方向信息（用于全局收敛判断段落）
    unconverged_directions = []

    if assessed_plan:
        lines.append("### 各方向完成情况")
        lines.append("")
        for d in assessed_plan.directions:
            if d.target_agent not in agent_names:
                continue
            status_display = d.status.value if hasattr(d.status, 'value') else str(d.status)
            mode_display = {"breadth_first": "BFRS", "depth_first": "DFRS", "skip": "Skip"}.get(d.preferred_mode, d.preferred_mode)
            lines.append(f"#### {d.id}: {d.topic}")

            # 显示 direction_stats（完成度、证据等级分布）
            stats = direction_stats.get(d.id, {})
            if stats:
                gd = stats.get("grade_distribution", {})
                grade_parts = []
                for g in ["A", "B", "C", "D", "E"]:
                    if gd.get(g, 0) > 0:
                        grade_parts.append(f"{g}={gd[g]}")
                grade_str = " ".join(grade_parts) if grade_parts else "无"
                lines.append(f"**状态**: {status_display} | **模式**: {mode_display} | **完成度**: {stats.get('completeness', 0):.0f}% | **证据数**: {stats.get('evidence_count', 0)} | **等级分布**: {grade_str}")
            else:
                lines.append(f"**状态**: {status_display} | **模式**: {mode_display}")
            lines.append("")

            # ① 证据充分性评估
            assessment_data = direction_assessments.get(d.id, {})
            # 兼容旧格式（字符串）和新格式（dict）
            if isinstance(assessment_data, str):
                evidence_text = assessment_data
                deep_assessments = []
            else:
                evidence_text = assessment_data.get("evidence_assessment", "")
                deep_assessments = assessment_data.get("deep_research_assessment", [])

            lines.append(f"**① 证据充分性评估**:")
            if evidence_text:
                lines.append(evidence_text)
            else:
                lines.append("（无评估信息）")
            lines.append("")

            # ② 待深入研究项评估
            dir_deep = deep_by_dir.get(d.id, [])
            if dir_deep or deep_assessments:
                lines.append("**② 待深入研究项评估**:")
                if deep_assessments:
                    # 使用 LLM 的结构化评估
                    lines.append("| 项目 | 覆盖 | 影响 | 说明 |")
                    lines.append("|------|------|------|------|")
                    coverage_map = {"covered": "已覆盖", "partial": "部分覆盖", "uncovered": "未覆盖"}
                    impact_map = {"critical": "关键", "important": "重要", "minor": "次要"}
                    for da in deep_assessments:
                        item_name = da.get("item", "")
                        coverage = coverage_map.get(da.get("coverage", ""), da.get("coverage", ""))
                        impact = impact_map.get(da.get("impact", ""), da.get("impact", ""))
                        justification = da.get("justification", "")
                        lines.append(f"| {item_name} | {coverage} | {impact} | {justification} |")
                else:
                    # 无结构化评估，仅列出原始 needs_deep_research
                    for item in dir_deep:
                        if isinstance(item, dict):
                            agent = item.get("agent", "")
                            finding = item.get("finding", "")
                            reason = item.get("reason", "")
                            reason_str = f" — {reason}" if reason else ""
                            lines.append(f"- [{agent}] {finding}{reason_str}")
                        else:
                            lines.append(f"- {item}")
                lines.append("")
            else:
                lines.append("**② 待深入研究项评估**: 无待深入研究项")
                lines.append("")

            # ③ 方向收敛判定
            is_converged = (status_display == "completed" and d.preferred_mode == "skip")
            if is_converged:
                lines.append(f"**③ 方向收敛判定**: 已收敛")
            else:
                # 构建未收敛原因
                unconverge_reasons = []
                if deep_assessments:
                    blocking_items = [
                        da for da in deep_assessments
                        if da.get("coverage") != "covered" and da.get("impact") in ("critical", "important")
                    ]
                    if blocking_items:
                        impact_counts = {}
                        for bi in blocking_items:
                            imp = {"critical": "关键", "important": "重要"}.get(bi.get("impact", ""), bi.get("impact", ""))
                            impact_counts[imp] = impact_counts.get(imp, 0) + 1
                        impact_str = "、".join(f"{k}×{v}" for k, v in impact_counts.items())
                        unconverge_reasons.append(f"存在{impact_str}级别未覆盖项")
                        unconverged_directions.append(f"{d.id} ({impact_str})")
                elif dir_deep:
                    unconverge_reasons.append(f"有{len(dir_deep)}项待深入研究")
                    unconverged_directions.append(f"{d.id} (待深入×{len(dir_deep)})")
                if status_display != "completed":
                    unconverge_reasons.append(f"完成度不足")
                    if d.id not in [ud.split(" ")[0] for ud in unconverged_directions]:
                        unconverged_directions.append(f"{d.id} (完成度不足)")
                reason_text = " — " + "；".join(unconverge_reasons) if unconverge_reasons else ""
                lines.append(f"**③ 方向收敛判定**: 未收敛{reason_text}")
            lines.append("")

            # ④ 下一轮模式
            lines.append(f"**④ 下一轮模式**: {mode_display} — {d.mode_reason}")

            lines.append("")
            lines.append("---")
            lines.append("")
        lines.append("")

    # 全局收敛判断
    decision = eval_result.get("decision", "unknown")
    reasoning = eval_result.get("reasoning", "")
    lines.append("### 全局收敛判断")
    lines.append("")
    lines.append(f"**决策**: {decision}")
    lines.append(f"**理由**: {reasoning}")
    if unconverged_directions:
        lines.append(f"**未收敛方向**: {', '.join(unconverged_directions)}")
    lines.append("")

    gaps = eval_result.get("gaps", [])
    lines.append("### 待填补空白")
    if gaps:
        for gap in gaps:
            lines.append(f"- {gap}")
    else:
        lines.append("- 无")
    lines.append("")

    priorities = eval_result.get("next_priorities", [])
    lines.append("### 下一轮优先事项")
    if priorities:
        for i, p in enumerate(priorities, 1):
            lines.append(f"{i}. {p}")
    else:
        lines.append("- 无")
    lines.append("")

    # === 2. 工具执行详情（含实体提取） ===
    lines.append("## 2. 工具执行详情")
    lines.append("")

    for agent_name in agent_names:
        result_key = f"{agent_name.lower()}_research_result"
        agent_result = state.get(result_key, {})
        tool_records = agent_result.get("tool_call_records", [])
        ext_details = agent_result.get("extraction_details", [])

        lines.append(f"### {agent_name}")
        lines.append("")

        if not tool_records:
            # 回退到旧的 tool_call_report 字符串（兼容）
            tool_report = agent_result.get("tool_call_report", "")
            if tool_report:
                lines.append(tool_report)
            else:
                lines.append("本轮无工具调用记录")
            lines.append("")
            continue

        # 按 source_tool 分组 extraction_details，用于按顺序匹配
        ext_by_tool = {}
        for detail in ext_details:
            tool_key = detail.get("source_tool", "")
            if tool_key not in ext_by_tool:
                ext_by_tool[tool_key] = []
            ext_by_tool[tool_key].append(detail)
        # 跟踪每个 tool 已消费的 extraction index
        ext_consumed = {k: 0 for k in ext_by_tool}

        seen_reasoning = set()  # 去重 Gemini thinking tokens（同一 API response 共享 reasoning）
        for i, record in enumerate(tool_records, 1):
            tool_name = record.get("tool_name", "")
            phase_tag = record.get("phase", "")
            lines.append(f"#### Tool Call {i}: `{tool_name}` [{phase_tag}]")
            lines.append(f"**Timestamp:** {record.get('timestamp', '')}")
            lines.append("")

            reasoning = record.get("reasoning", "")
            if reasoning:
                reasoning_hash = hash(reasoning)
                if reasoning_hash not in seen_reasoning:
                    seen_reasoning.add(reasoning_hash)
                    lines.append("**Reasoning:**")
                    for line in reasoning.split("\n"):
                        lines.append(f"> {line}")
                    lines.append("")
                else:
                    lines.append("**Reasoning:** （与上方相同，省略）")
                    lines.append("")

            lines.append("**Parameters:**")
            lines.append("```json")
            lines.append(json.dumps(record.get("parameters", {}), ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")

            lines.append("**Result:**")
            lines.append("```")
            lines.append(record.get("result", ""))
            lines.append("```")
            lines.append("")

            # 插入匹配的 extraction_details（按顺序消费）
            if tool_name in ext_by_tool and ext_consumed[tool_name] < len(ext_by_tool[tool_name]):
                detail = ext_by_tool[tool_name][ext_consumed[tool_name]]
                ext_consumed[tool_name] += 1

                summary = detail.get("finding_summary", "")
                direction_id = detail.get("direction_id", "")
                lines.append(f"**证据分解** (→ {direction_id}):")
                if summary:
                    lines.append(f"> {summary}")
                    lines.append("")

                # 实体详情
                entities_detail = detail.get("entities_detail", [])
                if entities_detail:
                    lines.append("**Entities:**")
                    for ent in entities_detail:
                        grade_str = f" [{ent['evidence_grade']}]" if ent.get("evidence_grade") else ""
                        obs_str = f' — "{ent["observation_statement"]}"' if ent.get("observation_statement") else ""
                        lines.append(f"- `{ent['canonical_id']}` ({ent['type']}){obs_str}{grade_str}")
                    lines.append("")

                # 边详情
                edges_detail = detail.get("edges_detail", [])
                if edges_detail:
                    lines.append("**Edges:**")
                    for edge in edges_detail:
                        conf_str = f" (conf={edge['confidence']:.1f})" if edge.get("confidence") else ""
                        obs_str = f' — "{edge["observation_statement"]}"' if edge.get("observation_statement") else ""
                        lines.append(f"- `{edge['source']}` → **{edge['predicate']}** → `{edge['target']}`{conf_str}{obs_str}")
                    lines.append("")

                lines.append(f"*统计: {detail.get('new_observations', 0)} obs, {detail.get('new_edges', 0)} edges*")
                lines.append("")

        # 追加未匹配到 tool call 的剩余 extraction_details
        remaining = []
        for tool_key, details_list in ext_by_tool.items():
            consumed = ext_consumed.get(tool_key, 0)
            remaining.extend(details_list[consumed:])
        # 无 source_tool 的 extraction_details
        for detail in ext_details:
            if not detail.get("source_tool"):
                remaining.append(detail)

        if remaining:
            lines.append("#### 其他证据分解")
            lines.append("")
            for detail in remaining:
                summary = detail.get("finding_summary", "")
                source_tool = detail.get("source_tool", "")
                direction_id = detail.get("direction_id", "")
                lines.append(f"**{source_tool}** → {direction_id}")
                if summary:
                    lines.append(f"> {summary}")
                    lines.append("")
                entities_detail = detail.get("entities_detail", [])
                if entities_detail:
                    for ent in entities_detail:
                        grade_str = f" [{ent['evidence_grade']}]" if ent.get("evidence_grade") else ""
                        obs_str = f' — "{ent["observation_statement"]}"' if ent.get("observation_statement") else ""
                        lines.append(f"- `{ent['canonical_id']}` ({ent['type']}){obs_str}{grade_str}")
                edges_detail = detail.get("edges_detail", [])
                if edges_detail:
                    for edge in edges_detail:
                        conf_str = f" (conf={edge['confidence']:.1f})" if edge.get("confidence") else ""
                        obs_str = f' — "{edge["observation_statement"]}"' if edge.get("observation_statement") else ""
                        lines.append(f"- `{edge['source']}` → **{edge['predicate']}** → `{edge['target']}`{conf_str}{obs_str}")
                lines.append("")

        # === Agent 研究输出（summary, direction_updates, needs_deep_research, per_direction_analysis, agent_analysis）===
        lines.append(f"#### {agent_name} 研究输出")
        lines.append("")

        # Summary
        summary = agent_result.get("summary", "")
        if summary:
            lines.append(f"**摘要**: {summary}")
            lines.append("")

        # Direction updates
        direction_updates = agent_result.get("direction_updates", {})
        if direction_updates:
            lines.append("**方向状态判断**:")
            for d_id, d_status in direction_updates.items():
                lines.append(f"- {d_id}: {d_status}")
            lines.append("")

        # Needs deep research
        needs_deep = agent_result.get("needs_deep_research", [])
        if needs_deep:
            lines.append("**标记需深入研究**:")
            for item in needs_deep:
                if isinstance(item, dict):
                    lines.append(f"- [{item.get('direction_id','')}] {item.get('finding','')}")
                    reason = item.get('reason', '')
                    if reason:
                        lines.append(f"  原因: {reason}")
                else:
                    lines.append(f"- {item}")
            lines.append("")

        # Per-direction analysis
        per_dir_analysis = agent_result.get("per_direction_analysis", {})
        if per_dir_analysis:
            lines.append("**各方向研究分析**:")
            lines.append("")
            label_map = {
                "research_question": "研究问题",
                "tools_used": "使用工具",
                "what_found": "已找到",
                "what_not_found": "未找到",
                "new_questions": "新问题",
                "conclusion": "结论",
            }
            for d_id, analysis in per_dir_analysis.items():
                if isinstance(analysis, dict):
                    lines.append(f"##### {d_id}")
                    for key in ["research_question", "tools_used", "what_found",
                                "what_not_found", "new_questions", "conclusion"]:
                        val = analysis.get(key, "")
                        if val:
                            label = label_map.get(key, key)
                            lines.append(f"- **{label}**: {val}")
                    lines.append("")

        # Agent analysis (JSON 外文本)
        agent_analysis = agent_result.get("agent_analysis", "")
        if agent_analysis:
            lines.append("**Agent 自由分析文本**:")
            lines.append("")
            lines.append(agent_analysis)
            lines.append("")

        lines.append("")

    # === 3. 本轮新增证据明细 ===
    lines.append("## 3. 本轮新增证据明细")
    lines.append("")

    for agent_name in agent_names:
        result_key = f"{agent_name.lower()}_research_result"
        agent_result = state.get(result_key, {})
        new_evidence_ids = agent_result.get("new_evidence_ids", [])

        lines.append(f"### {agent_name}: {len(new_evidence_ids)} 条")
        lines.append("")

        if not new_evidence_ids:
            lines.append("本轮无新增证据")
            lines.append("")
            continue

        for eid in new_evidence_ids:
            # 新模型：evidence_ids 是 entity canonical_id
            entity = graph.get_entity(eid) if graph else None
            if not entity:
                lines.append(f"#### 实体 {eid}")
                lines.append("- *实体未找到*")
                lines.append("")
                continue

            lines.append(f"#### 实体 {entity.canonical_id}")
            lines.append(f"- **名称**: {entity.name}")
            lines.append(f"- **类型**: {entity.entity_type.value if entity.entity_type else 'N/A'}")
            best_grade = entity.get_best_grade()
            grade_val = best_grade.value if best_grade else 'N/A'
            grade_desc = _grade_description(best_grade)
            lines.append(f"- **最佳等级**: {grade_val} ({grade_desc})")
            if entity.aliases:
                lines.append(f"- **别名**: {', '.join(entity.aliases[:5])}")

            # 显示该实体的所有观察
            if entity.observations:
                lines.append(f"- **观察数**: {len(entity.observations)}")
                for i, obs in enumerate(entity.observations, 1):
                    lines.append(f"  **观察 {i}**:")
                    lines.append(f"    - 陈述: {obs.statement}")
                    if obs.evidence_grade:
                        lines.append(f"    - 等级: {obs.evidence_grade.value}")
                    if obs.civic_type:
                        lines.append(f"    - CIViC类型: {obs.civic_type.value}")
                    lines.append(f"    - 来源Agent: {obs.source_agent}")
                    lines.append(f"    - 来源工具: {obs.source_tool or 'N/A'}")
                    if obs.provenance:
                        lines.append(f"    - 来源文献: {obs.provenance}")
                    if obs.source_url:
                        lines.append(f"    - URL: {obs.source_url}")
                    lines.append(f"    - 收集轮次: {obs.iteration}")

            lines.append("")

    # === 4. Evidence Graph 完整统计 ===
    lines.append("## 4. Evidence Graph 完整统计")
    lines.append("")
    if graph:
        summary = graph.summary()
        agent_summary = graph.summary_by_agent()
        lines.append("### 总体统计")
        lines.append(f"- **总实体数**: {summary.get('total_entities', 0)}")
        lines.append(f"- **总边数**: {summary.get('total_edges', 0)}")
        lines.append(f"- **总观察数**: {summary.get('total_observations', 0)}")
        lines.append(f"- **冲突数**: {summary.get('conflicts_count', 0)}")
        lines.append("")

        by_type = summary.get("entities_by_type", {})
        if by_type:
            lines.append("### 按实体类型分布")
            lines.append("| 类型 | 数量 |")
            lines.append("|------|------|")
            for etype, count in by_type.items():
                lines.append(f"| {etype} | {count} |")
            lines.append("")

        if agent_summary:
            lines.append("### 按 Agent 分布")
            lines.append("| Agent | 观察数 | 实体数 |")
            lines.append("|-------|--------|--------|")
            for agent, stats in agent_summary.items():
                obs_count = stats.get('observation_count', 0)
                entity_count = stats.get('entity_count', 0)
                lines.append(f"| {agent} | {obs_count} | {entity_count} |")
            lines.append("")

        by_grade = summary.get("best_grades", {})
        if by_grade:
            lines.append("### 按证据等级分布")
            lines.append("| 等级 | 数量 |")
            lines.append("|------|------|")
            for grade, count in by_grade.items():
                lines.append(f"| {grade} | {count} |")
            lines.append("")

        # 边关系统计
        edges_by_predicate = summary.get("edges_by_predicate", {})
        if edges_by_predicate:
            lines.append("### 边关系类型分布")
            lines.append("| 关系类型 | 数量 |")
            lines.append("|----------|------|")
            for predicate, count in edges_by_predicate.items():
                lines.append(f"| {predicate} | {count} |")
            lines.append("")

        # 冲突详情
        conflicts = graph.get_conflicts()
        if conflicts:
            lines.append("### 证据冲突详情")
            lines.append("")
            for i, conflict in enumerate(conflicts, 1):
                edge_ids = conflict.get("edge_ids", [])
                group = conflict.get("conflict_group", "?")
                lines.append(f"**冲突组 {i}** (group: {group})")
                for eid in edge_ids:
                    edge = graph.get_edge(eid)
                    if edge:
                        lines.append(f"  - `{edge.source_id}` --[{edge.predicate.value}]--> `{edge.target_id}`")
                lines.append("")

        # 药物敏感性关系
        drug_sensitivity = graph.get_drug_sensitivity_map()
        if drug_sensitivity:
            lines.append("### 药物敏感性/耐药性关系")
            lines.append("")
            count = 0
            for drug, relations in drug_sensitivity.items():
                if count >= 10:
                    break
                lines.append(f"**{drug}**:")
                for rel in relations:
                    predicate = rel.get("predicate", "?")
                    variant = rel.get("variant", "?")
                    confidence = rel.get("confidence", 0.0)
                    lines.append(f"  - {variant} → {predicate} (置信度: {confidence:.2f})")
                count += 1
            lines.append("")

        # === 5. Evidence Graph Mermaid 图 ===
        lines.append("## 5. Evidence Graph 可视化")
        lines.append("")
        mermaid_diagram = graph.to_mermaid()
        lines.append(mermaid_diagram)
        lines.append("")
    else:
        lines.append("- 证据图为空")
        lines.append("")

    # 保存文件
    filename = f"{phase.lower()}_iter{iteration}_detailed_report.md"
    filepath = os.path.join(run_folder, filename)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logger.info(f"[DETAILED_REPORT] 已保存: {filename}")
    except Exception as e:
        logger.error(f"[DETAILED_REPORT] 保存失败: {e}")


# ==================== Phase 1 报告生成辅助函数 ====================

def _format_evidence_table(entities: List[Entity], edges: List[Edge], agent_name: str) -> str:
    """
    从 agent 的 entities + edges 生成结构化 markdown 证据表格

    Args:
        entities: 包含该 agent 观察的实体列表
        edges: 包含该 agent 观察的边列表
        agent_name: Agent 名称，用于筛选观察

    Returns:
        markdown 格式的证据表格字符串
    """
    lines = []

    # === 实体观察表 ===
    grade_order = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}

    # 收集所有 agent 的实体观察
    entity_rows = []
    for entity in entities:
        agent_obs = [obs for obs in entity.observations if obs.source_agent == agent_name]
        for obs in agent_obs:
            grade = obs.evidence_grade.value if obs.evidence_grade else "N/A"
            civic = obs.civic_type.value if obs.civic_type else ""
            tool = obs.source_tool or ""
            provenance = obs.provenance or ""
            entity_rows.append({
                "entity": entity.canonical_id,
                "type": entity.entity_type.value,
                "statement": obs.statement,
                "grade": grade,
                "civic_type": civic,
                "tool": tool,
                "provenance": provenance,
                "sort_key": grade_order.get(grade, 5),
            })

    # 按证据等级排序
    entity_rows.sort(key=lambda r: r["sort_key"])

    if entity_rows:
        lines.append(f"### 实体观察表（共 {len(entity_rows)} 条）\n")
        lines.append("| # | 实体 | 类型 | 观察陈述 | 等级 | CIViC类型 | 来源工具 | 出处 |")
        lines.append("|---|------|------|----------|------|-----------|----------|------|")
        for i, row in enumerate(entity_rows, 1):
            # 转义管道符
            stmt = row["statement"].replace("|", "\\|")
            lines.append(
                f"| {i} | {row['entity']} | {row['type']} | {stmt} | {row['grade']} | {row['civic_type']} | {row['tool']} | {row['provenance']} |"
            )
        lines.append("")

    # === 关系边表 ===
    edge_rows = []
    for edge in edges:
        agent_obs = [obs for obs in edge.observations if obs.source_agent == agent_name]
        for obs in agent_obs:
            grade = obs.evidence_grade.value if obs.evidence_grade else "N/A"
            edge_rows.append({
                "source": edge.source_id,
                "predicate": edge.predicate.value,
                "target": edge.target_id,
                "statement": obs.statement,
                "grade": grade,
                "confidence": edge.confidence,
                "sort_key": grade_order.get(grade, 5),
            })

    edge_rows.sort(key=lambda r: r["sort_key"])

    if edge_rows:
        lines.append(f"### 关系边表（共 {len(edge_rows)} 条）\n")
        lines.append("| # | 源实体 | 关系 | 目标实体 | 观察陈述 | 等级 | 置信度 |")
        lines.append("|---|--------|------|----------|----------|------|--------|")
        for i, row in enumerate(edge_rows, 1):
            stmt = row["statement"].replace("|", "\\|")
            lines.append(
                f"| {i} | {row['source']} | {row['predicate']} | {row['target']} | {stmt} | {row['grade']} | {row['confidence']:.1f} |"
            )
        lines.append("")

    if not entity_rows and not edge_rows:
        lines.append("暂无结构化证据数据。\n")

    return "\n".join(lines)


def _format_evidence_for_report(entity_list: List[Entity], agent_name: str = None) -> str:
    """
    将实体列表格式化为报告生成用的摘要

    Args:
        entity_list: Entity 列表
        agent_name: 可选，筛选特定 Agent 的观察

    Returns:
        格式化的证据摘要文本
    """
    if not entity_list:
        return "暂无相关证据。"

    lines = []

    # 按最佳证据等级排序（A 优先）
    grade_order = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}

    def get_sort_key(entity: Entity) -> int:
        best_grade = entity.get_best_grade()
        if best_grade:
            return grade_order.get(best_grade.value, 5)
        return 5

    sorted_entities = sorted(entity_list, key=get_sort_key)

    for i, entity in enumerate(sorted_entities, 1):
        best_grade = entity.get_best_grade()
        grade_str = f"[{best_grade.value}]" if best_grade else "[N/A]"

        lines.append(f"### 实体 {i}: {entity.name} {grade_str}")
        lines.append(f"**类型**: {entity.entity_type.value}")

        # 筛选特定 Agent 的观察（如果指定）
        observations = entity.observations
        if agent_name:
            observations = [obs for obs in observations if obs.source_agent == agent_name]

        for obs in observations:
            obs_grade = f"[{obs.evidence_grade.value}]" if obs.evidence_grade else ""
            civic_str = f" ({obs.civic_type.value})" if obs.civic_type else ""
            lines.append(f"**观察** {obs_grade}{civic_str}: {obs.statement}")
            if obs.provenance:
                lines.append(f"  - 来源: {obs.provenance}")
            if obs.source_tool:
                lines.append(f"  - 工具: {obs.source_tool}")

        lines.append("")

    return "\n".join(lines)


def generate_phase1_reports(state: MtbState) -> Dict[str, Any]:
    """
    Phase 1 收敛后，各专家基于 evidence_graph 生成领域综合报告

    这些报告将传递给 Phase 2 Oncologist，让 Oncologist 能够看到
    各专家的综合分析结论，而不只是原始证据。
    """
    log_separator("PHASE1_REPORTS")
    logger.info("[PHASE1_REPORTS] 生成 Phase 1 专家报告...")

    evidence_graph = state.get("evidence_graph", {})
    raw_pdf_text = state.get("raw_pdf_text", "")

    graph = load_evidence_graph(evidence_graph)
    if not graph:
        logger.warning("[PHASE1_REPORTS] 证据图为空，跳过报告生成")
        return {}

    reports = {}

    # 为每个 Phase 1 Agent 生成报告
    # (agent_name, agent_class, state_key, filename)
    agent_configs = [
        ("Pathologist", ReportPathologist, "pathologist_report", "1_pathologist_report.md"),
        ("Geneticist", ReportGeneticist, "geneticist_report", "2_geneticist_report.md"),
        ("Recruiter", ReportRecruiter, "recruiter_report", "3_recruiter_report.md"),
    ]

    for agent_name, agent_class, report_key, filename in agent_configs:
        logger.info(f"[PHASE1_REPORTS] 生成 {agent_name} 报告...")

        # 提取该 Agent 收集的证据（实体 + 边）
        agent_entities = graph.get_entities_with_agent_observations(agent_name)
        agent_edges = graph.get_agent_edges(agent_name)
        observation_count = graph.get_agent_observation_count(agent_name)
        logger.info(f"[PHASE1_REPORTS]   {agent_name} 实体数: {len(agent_entities)}, 边数: {len(agent_edges)}, 观察数: {observation_count}")

        if not agent_entities:
            reports[report_key] = f"## {agent_name} 报告\n\n暂无相关发现。"
            continue

        # 构建证据摘要（文本格式，供 LLM 理解上下文）
        evidence_summary = _format_evidence_for_report(agent_entities, agent_name)

        # 构建完整证据表格（结构化表格，确保不遗漏）
        evidence_table = _format_evidence_table(agent_entities, agent_edges, agent_name)

        # 构建报告生成 prompt
        report_prompt = f"""基于以下病例信息和已收集的研究证据，生成你的专业领域综合报告。

## 病例背景
{raw_pdf_text}

## 已收集的研究证据（共 {observation_count} 条）
{evidence_summary}

## 完整证据清单
{evidence_table}

## 输出要求
请生成一份完整的 Markdown 格式的领域分析报告。注意：
1. 整合所有证据，给出综合分析结论
2. 保留所有引用（PMID、NCT 等）
3. 明确标注证据等级 [Evidence A/B/C/D/E]
4. 重点突出对治疗决策有指导意义的发现
5. **报告末尾必须包含「完整证据清单」模块**，以表格形式列出上述所有证据，
   每条证据附带你的分析结论（该证据对治疗决策的意义）。这不是综述，是逐条证据分析。
"""

        try:
            # 实例化 Agent 并调用
            agent = agent_class()
            response = agent.invoke(report_prompt)

            if response and response.get("output"):
                report = response["output"]

                # 程序化追加完整证据清单（确保不遗漏）
                report += f"\n\n---\n\n## 完整证据清单（Evidence Graph）\n\n{evidence_table}"

                reports[report_key] = report
                logger.info(f"[PHASE1_REPORTS]   {agent_name} 报告生成成功: {len(report)} 字符")
                # 保存到文件
                _save_agent_report(state, filename, report)
            else:
                reports[report_key] = f"## {agent_name} 报告\n\n报告生成失败。"
                logger.warning(f"[PHASE1_REPORTS]   {agent_name} 报告生成失败")

        except Exception as e:
            logger.error(f"[PHASE1_REPORTS]   {agent_name} 报告生成异常: {e}")
            reports[report_key] = f"## {agent_name} 报告\n\n报告生成异常: {str(e)}"

    logger.info(f"[PHASE1_REPORTS] 报告生成完成")
    return reports


# ==================== Phase 2 研究计划初始化 ====================

def phase2_plan_init(state: MtbState) -> Dict[str, Any]:
    """
    Phase 2 研究计划初始化 - 基于 Phase 1 结果生成针对性的 Oncologist 方向

    在 Phase 1 收敛后、Phase 2 开始前调用。
    读取 Phase 1 完整报告和证据图，生成针对性的 Oncologist 研究方向。
    """
    log_separator("PHASE2_PLAN_INIT")
    logger.info("[PHASE2_PLAN_INIT] 基于 Phase 1 结果生成 Phase 2 研究方向...")

    # 检查 Phase 1 报告是否存在
    pathologist_report = state.get("pathologist_report", "")
    geneticist_report = state.get("geneticist_report", "")
    recruiter_report = state.get("recruiter_report", "")

    if not (pathologist_report or geneticist_report or recruiter_report):
        logger.warning("[PHASE2_PLAN_INIT] Phase 1 报告缺失，使用默认 Phase 2 方向")
        return {}

    logger.info(f"[PHASE2_PLAN_INIT] Phase 1 报告长度: P={len(pathologist_report)}, G={len(geneticist_report)}, R={len(recruiter_report)}")

    # 调用 PlanAgent 生成 Phase 2 方向
    try:
        agent = PlanAgent()
        new_plan = agent.generate_phase2_directions(state)

        # 统计新方向（Phase 1 不含 Oncologist 方向，无需移除）
        plan = load_research_plan(new_plan)

        oncologist_directions = [d for d in plan.directions if d.target_agent == "Oncologist"] if plan else []
        logger.info(f"[PHASE2_PLAN_INIT] 生成 {len(oncologist_directions)} 个 Oncologist 方向:")
        for d in oncologist_directions:
            logger.info(f"[PHASE2_PLAN_INIT]   - {d.id}: {d.topic}")

        return {"research_plan": plan.to_dict() if plan else new_plan}

    except Exception as e:
        logger.error(f"[PHASE2_PLAN_INIT] Phase 2 方向生成失败: {e}")
        logger.info("[PHASE2_PLAN_INIT] 继续使用原有 Oncologist 方向")
        return {}


# ==================== Phase 2 报告生成辅助函数 ====================

def generate_phase2_reports(state: MtbState) -> Dict[str, Any]:
    """
    Phase 2 收敛后，Oncologist 基于 evidence_graph 生成领域综合报告

    这个报告将与 Phase 1 专家报告一起传递给 Chair，让 Chair 能够看到
    所有专家的综合分析结论。
    """
    log_separator("PHASE2_REPORTS")
    logger.info("[PHASE2_REPORTS] 生成 Phase 2 专家报告...")

    evidence_graph = state.get("evidence_graph", {})
    raw_pdf_text = state.get("raw_pdf_text", "")

    graph = load_evidence_graph(evidence_graph)
    if not graph:
        logger.warning("[PHASE2_REPORTS] 证据图为空，跳过报告生成")
        return {}

    # 提取 Oncologist 收集的证据（实体 + 边）
    oncologist_entities = graph.get_entities_with_agent_observations("Oncologist")
    oncologist_edges = graph.get_agent_edges("Oncologist")
    observation_count = graph.get_agent_observation_count("Oncologist")
    logger.info(f"[PHASE2_REPORTS] Oncologist 实体数: {len(oncologist_entities)}, 边数: {len(oncologist_edges)}, 观察数: {observation_count}")

    if not oncologist_entities:
        logger.warning("[PHASE2_REPORTS] Oncologist 无证据，生成默认报告")
        return {"oncologist_plan": "## 治疗方案分析\n\n暂无相关发现。"}

    # 构建证据摘要（文本格式，供 LLM 理解上下文）
    evidence_summary = _format_evidence_for_report(oncologist_entities, "Oncologist")

    # 构建完整证据表格（结构化表格，确保不遗漏）
    evidence_table = _format_evidence_table(oncologist_entities, oncologist_edges, "Oncologist")

    # 获取上游报告作为参考
    pathologist_report = state.get('pathologist_report', '')
    geneticist_report = state.get('geneticist_report', '')
    recruiter_report = state.get('recruiter_report', '')

    # 构建报告生成 prompt
    report_prompt = f"""基于以下病例信息、上游专家报告和已收集的研究证据，生成你的肿瘤学专业领域综合报告。

## 病例背景
{raw_pdf_text}

## 上游专家报告

### 病理学分析报告
{pathologist_report if pathologist_report else "暂无"}

### 分子分析报告
{geneticist_report if geneticist_report else "暂无"}

### 临床试验推荐报告
{recruiter_report if recruiter_report else "暂无"}

## 你收集的研究证据（共 {observation_count} 条）
{evidence_summary}

## 完整证据清单
{evidence_table}

## 输出要求
请生成一份完整的 Markdown 格式的肿瘤学治疗方案分析报告。注意：
1. 整合所有证据和上游报告信息，给出综合治疗建议
2. 保留所有引用（PMID、NCT 等）
3. 明确标注证据等级 [Evidence A/B/C/D/E]
4. 重点突出治疗方案选择、用药建议、安全性考量
5. 包含治疗路线图和分子复查建议
6. **报告末尾必须包含「完整证据清单」模块**，以表格形式列出上述所有证据，
   每条证据附带你的分析结论（该证据对治疗决策的意义）。这不是综述，是逐条证据分析。
"""

    try:
        # 实例化 Oncologist Report Agent（Pro 模型）并调用
        agent = ReportOncologist()
        response = agent.invoke(report_prompt)

        if response and response.get("output"):
            report = response["output"]

            # 程序化追加完整证据清单（确保不遗漏）
            report += f"\n\n---\n\n## 完整证据清单（Evidence Graph）\n\n{evidence_table}"

            logger.info(f"[PHASE2_REPORTS] Oncologist 报告生成成功: {len(report)} 字符")
            # 保存到文件
            _save_agent_report(state, "4_oncologist_report.md", report)
            return {"oncologist_plan": report}
        else:
            logger.warning("[PHASE2_REPORTS] Oncologist 报告生成失败")
            return {"oncologist_plan": "## 治疗方案分析\n\n报告生成失败。"}

    except Exception as e:
        logger.error(f"[PHASE2_REPORTS] Oncologist 报告生成异常: {e}")
        return {"oncologist_plan": f"## 治疗方案分析\n\n报告生成异常: {str(e)}"}


# ==================== Phase 1 节点 ====================

def phase1_router(state: MtbState) -> List[Send]:
    """
    Phase 1 路由：只分发未收敛的 Agent

    检查各 Agent 收敛状态，只分发未收敛的 Agent 继续研究。
    研究模式由每个方向的 preferred_mode 决定，不再使用全局模式。
    """
    iteration = state.get("phase1_iteration", 0)
    plan = load_research_plan(state.get("research_plan", {}))
    graph = load_evidence_graph(state.get("evidence_graph", {}))

    # 检查各 Agent 收敛状态，只分发未收敛的
    agents_to_run = []
    agent_status = {}

    if not state.get("pathologist_converged", False):
        agents_to_run.append("pathologist")
        agent_status["Pathologist"] = "○"
    else:
        agent_status["Pathologist"] = "✓"

    if not state.get("geneticist_converged", False):
        agents_to_run.append("geneticist")
        agent_status["Geneticist"] = "○"
    else:
        agent_status["Geneticist"] = "✓"

    if not state.get("recruiter_converged", False):
        agents_to_run.append("recruiter")
        agent_status["Recruiter"] = "○"
    else:
        agent_status["Recruiter"] = "✓"

    # 增强日志输出
    log_separator("PHASE1")
    logger.info(f"[PHASE1] 迭代 {iteration + 1}/{MAX_PHASE1_ITERATIONS}")

    # 显示各 Agent 状态
    logger.info(f"[PHASE1] Agent 状态:")
    for agent, status in agent_status.items():
        logger.info(f"[PHASE1]   {status} {agent}")

    # 如果所有 Agent 都已收敛，返回空列表
    if not agents_to_run:
        logger.info("[PHASE1] 所有 Agent 已收敛，跳过迭代")
        return []

    # 显示每个方向的研究模式（新逻辑）
    if plan:
        mode_summary = {"breadth_first": 0, "depth_first": 0, "skip": 0}
        for d in plan.directions:
            mode_summary[d.preferred_mode] = mode_summary.get(d.preferred_mode, 0) + 1
        logger.info(f"[PHASE1] 方向模式分布: BFRS={mode_summary['breadth_first']}, DFRS={mode_summary['depth_first']}, Skip={mode_summary['skip']}")

    logger.info(f"[PHASE1] 分发到: {', '.join([a.capitalize() for a in agents_to_run])}")

    # 显示当前证据图状态
    if graph and len(graph) > 0:
        log_evidence_stats(state.get("evidence_graph", {}))

    # 只分发未收敛的 Agent（不再设置全局 research_mode）
    sends = [Send(f"phase1_{agent}", state) for agent in agents_to_run]
    return sends


def phase1_pathologist_node(state: MtbState) -> Dict[str, Any]:
    """Phase 1: 病理学家研究节点"""
    return _execute_phase1_agent(state, "Pathologist", ResearchPathologist)


def phase1_geneticist_node(state: MtbState) -> Dict[str, Any]:
    """Phase 1: 遗传学家研究节点"""
    return _execute_phase1_agent(state, "Geneticist", ResearchGeneticist)


def phase1_recruiter_node(state: MtbState) -> Dict[str, Any]:
    """Phase 1: 临床试验专员研究节点"""
    return _execute_phase1_agent(state, "Recruiter", ResearchRecruiter)


def _execute_phase1_agent(state: MtbState, agent_name: str, agent_class) -> Dict[str, Any]:
    """执行 Phase 1 Agent 的研究迭代，并检查该 Agent 是否收敛"""
    tag = f"PHASE1_{agent_name.upper()}"
    logger.info(f"[{tag}] ───────────────────────────────────────")

    # 检查该 Agent 是否已收敛（应该不会进入，但做防护）
    converged_key = f"{agent_name.lower()}_converged"
    if state.get(converged_key, False):
        logger.info(f"[{tag}] 已收敛，跳过执行")
        return {}

    # 获取状态
    iteration = state.get("phase1_iteration", 0)
    plan = load_research_plan(state.get("research_plan", {}))
    evidence_graph = state.get("evidence_graph", {})
    raw_pdf_text = state.get("raw_pdf_text", "")

    # 获取分配给此 Agent 的方向（包含各自的 preferred_mode）
    directions = []
    if plan:
        for d in plan.directions:
            if d.target_agent == agent_name:
                directions.append(d.to_dict())

    if not directions:
        logger.info(f"[{tag}] 无分配方向，视为收敛")
        return {converged_key: True}

    # 显示分配的方向及其模式（新逻辑）
    logger.info(f"[{tag}] 分配方向: {len(directions)} 个")
    for d in directions:
        status_icon = "✓" if d.get("status") == "completed" else "○"
        mode_icon = {"breadth_first": "B", "depth_first": "D", "skip": "S"}.get(d.get("preferred_mode", "B"), "?")
        logger.info(f"[{tag}]   {status_icon} [{mode_icon}] {d.get('topic', '未命名')[:30]} (P{d.get('priority', '-')})")

    # 创建 Agent 并执行研究
    # 传入默认 mode，实际使用每个方向的 preferred_mode
    agent = agent_class()
    research_plan_dict = state.get("research_plan", {})
    result = agent.research_iterate(
        mode=ResearchMode.BREADTH_FIRST,  # 默认值，实际由 direction.preferred_mode 决定
        directions=directions,
        evidence_graph=evidence_graph,
        iteration=iteration,
        max_iterations=MAX_PHASE1_ITERATIONS,
        case_context=raw_pdf_text,
        research_plan=research_plan_dict
    )

    # 显示执行结果
    new_evidence_ids = result.get('new_evidence_ids', [])
    direction_updates = result.get('direction_updates', {})
    logger.info(f"[{tag}] 完成:")
    logger.info(f"[{tag}]   新证据: {len(new_evidence_ids)}")
    if direction_updates:
        logger.info(f"[{tag}]   方向更新: {direction_updates}")
    if result.get('needs_deep_research'):
        logger.info(f"[{tag}]   需深入研究: {len(result.get('needs_deep_research', []))} 项")

    # 返回更新后的证据图和研究计划
    # 收敛判断已移至 PlanAgent (plan_agent_evaluate_phase1)
    return_dict = {
        "evidence_graph": result.get("evidence_graph", evidence_graph),
        f"{agent_name.lower()}_research_result": result,
    }
    # 如果有更新的研究计划，也返回
    if result.get("research_plan"):
        return_dict["research_plan"] = result.get("research_plan")
    return return_dict


def phase1_aggregator(state: MtbState) -> Dict[str, Any]:
    """
    Phase 1 聚合：合并并行 Agent 的结果，记录迭代历史

    收敛判断已移至 plan_agent_evaluate_phase1 节点，由 PlanAgent 统一处理。
    """
    log_separator("PHASE1")
    logger.info("[PHASE1] 聚合并行结果:")

    # 计算各 Agent 的新发现
    agent_results = {
        "Pathologist": state.get("pathologist_research_result", {}),
        "Geneticist": state.get("geneticist_research_result", {}),
        "Recruiter": state.get("recruiter_research_result", {})
    }

    new_findings = 0
    agent_findings_detail = {}
    for agent_name, result in agent_results.items():
        evidence_ids = result.get("new_evidence_ids", [])
        count = len(evidence_ids)
        new_findings += count
        agent_findings_detail[agent_name] = {
            "count": count,
            "evidence_ids": evidence_ids
        }
        logger.info(f"[PHASE1]   {agent_name}: {count} 条新证据")

    logger.info(f"[PHASE1]   本轮总计: {new_findings}")

    # 显示证据图统计
    log_evidence_stats(state.get("evidence_graph", {}))

    # 更新迭代计数
    current_iteration = state.get("phase1_iteration", 0)
    new_iteration = current_iteration + 1

    # 构建迭代历史记录（收敛检查由 PlanAgent 填充）
    iteration_record = {
        "phase": "PHASE1",
        "iteration": new_iteration,
        "timestamp": datetime.now().isoformat(),
        "agent_findings": agent_findings_detail,
        "total_new_findings": new_findings,
        # 收敛检查详情将由 plan_agent_evaluate_phase1 更新
        "convergence_check": {},
        "final_decision": "pending"  # 由 PlanAgent 决定
    }

    # 追加到迭代历史
    history = list(state.get("iteration_history", []))
    history.append(iteration_record)

    logger.info(f"[PHASE1] 迭代 {new_iteration} 聚合完成，等待 PlanAgent 评估...")

    # 详细迭代报告由 plan_agent_evaluate_phase1() 保存

    return {
        "phase1_iteration": new_iteration,
        "phase1_new_findings": new_findings,
        "iteration_history": history,
    }


def plan_agent_evaluate_phase1(state: MtbState) -> Dict[str, Any]:
    """
    PlanAgent 评估 Phase 1 研究进度并更新计划

    在 Phase 1 聚合后调用，由 PlanAgent 统一判断收敛。
    """
    logger.info("[PHASE1_PLAN_EVAL] PlanAgent 评估研究进度...")

    iteration = state.get("phase1_iteration", 0)

    # 保存评估前的 plan 用于报告对比
    pre_eval_plan = state.get("research_plan", {})

    # 检查迭代上限
    if iteration >= MAX_PHASE1_ITERATIONS:
        logger.warning(f"[PHASE1_PLAN_EVAL] 达到迭代上限 ({MAX_PHASE1_ITERATIONS})，强制收敛")
        forced_eval_result = {
            "decision": "converged",
            "research_mode": "breadth_first",
            "reasoning": "达到迭代上限，强制收敛",
            "quality_assessment": {},
            "gaps": [],
            "next_priorities": []
        }
        # 保存详细迭代报告
        _save_detailed_iteration_report(
            state=state,
            phase="PHASE1",
            iteration=iteration,
            eval_result=forced_eval_result,
            agent_names=["Pathologist", "Geneticist", "Recruiter"],
            pre_eval_plan=pre_eval_plan
        )
        return {
            "phase1_decision": "converged",
            "phase1_all_converged": True,
            "pathologist_converged": True,
            "geneticist_converged": True,
            "recruiter_converged": True,
            "plan_agent_evaluation": {
                "phase": "phase1",
                "iteration": iteration,
                "reasoning": "达到迭代上限，强制收敛",
                "gaps": [],
                "next_priorities": []
            }
        }

    # 调用 PlanAgent 评估
    try:
        plan_agent = PlanAgent()
        eval_result = plan_agent.evaluate_and_update(state, "phase1", iteration)

        decision = eval_result.get("decision", "continue")
        logger.info(f"[PHASE1_PLAN_EVAL] PlanAgent 决策: {decision}")
        logger.info(f"[PHASE1_PLAN_EVAL] 理由: {eval_result.get('reasoning', '')[:100]}...")

        # 保存详细迭代报告
        _save_detailed_iteration_report(
            state=state,
            phase="PHASE1",
            iteration=iteration,
            eval_result=eval_result,
            agent_names=["Pathologist", "Geneticist", "Recruiter"],
            pre_eval_plan=pre_eval_plan
        )

        # 根据决策更新 Agent 收敛状态
        all_converged = (decision == "converged")

        return {
            "research_plan": eval_result.get("research_plan", state.get("research_plan", {})),
            "research_mode": eval_result.get("research_mode", "breadth_first"),
            "phase1_decision": decision,
            "phase1_all_converged": all_converged,
            "pathologist_converged": all_converged,
            "geneticist_converged": all_converged,
            "recruiter_converged": all_converged,
            "plan_agent_evaluation": {
                "phase": "phase1",
                "iteration": iteration,
                "reasoning": eval_result.get("reasoning", ""),
                "quality_assessment": eval_result.get("quality_assessment", {}),
                "gaps": eval_result.get("gaps", []),
                "next_priorities": eval_result.get("next_priorities", [])
            }
        }

    except Exception as e:
        logger.error(f"[PHASE1_PLAN_EVAL] PlanAgent 评估失败: {e}")
        # 评估失败时继续迭代
        error_eval_result = {
            "decision": "continue",
            "research_mode": "breadth_first",
            "reasoning": f"评估失败: {str(e)}",
            "quality_assessment": {},
            "gaps": [],
            "next_priorities": []
        }
        # 仍保存详细报告（记录失败情况）
        _save_detailed_iteration_report(
            state=state,
            phase="PHASE1",
            iteration=iteration,
            eval_result=error_eval_result,
            agent_names=["Pathologist", "Geneticist", "Recruiter"],
            pre_eval_plan=pre_eval_plan
        )
        return {
            "phase1_decision": "continue",
            "plan_agent_evaluation": {
                "phase": "phase1",
                "iteration": iteration,
                "reasoning": f"评估失败: {str(e)}",
                "gaps": [],
                "next_priorities": []
            }
        }


def phase1_convergence_check(state: MtbState) -> Literal["continue", "converged"]:
    """
    Phase 1 收敛检查 - 从 state 中读取 PlanAgent 的决策

    收敛检查逻辑已移至 plan_agent_evaluate_phase1 中执行。
    此函数仅作为条件边，读取 phase1_decision 字段。
    """
    decision = state.get("phase1_decision", "continue")
    return decision


# ==================== Phase 2 节点 ====================

def phase2_oncologist_node(state: MtbState) -> Dict[str, Any]:
    """Phase 2: 肿瘤学家研究节点"""
    # 获取状态
    iteration = state.get("phase2_iteration", 0)
    plan = load_research_plan(state.get("research_plan", {}))
    graph = load_evidence_graph(state.get("evidence_graph", {}))

    # 增强日志输出
    log_separator("PHASE2")
    logger.info(f"[PHASE2] Oncologist 迭代 {iteration + 1}/{MAX_PHASE2_ITERATIONS}")

    # 显示 Oncologist 方向的模式分布（新逻辑）
    if plan:
        onc_directions = [d for d in plan.directions if d.target_agent == "Oncologist"]
        mode_summary = {"breadth_first": 0, "depth_first": 0, "skip": 0}
        for d in onc_directions:
            mode_summary[d.preferred_mode] = mode_summary.get(d.preferred_mode, 0) + 1
        logger.info(f"[PHASE2] Oncologist 方向模式: BFRS={mode_summary['breadth_first']}, DFRS={mode_summary['depth_first']}, Skip={mode_summary['skip']}")

    # 显示上游报告摘要
    pathologist_report = state.get('pathologist_report', '')
    geneticist_report = state.get('geneticist_report', '')
    recruiter_report = state.get('recruiter_report', '')
    logger.info(f"[PHASE2] 上游报告:")
    logger.info(f"[PHASE2]   Pathologist: {len(pathologist_report)} 字符")
    logger.info(f"[PHASE2]   Geneticist: {len(geneticist_report)} 字符")
    logger.info(f"[PHASE2]   Recruiter: {len(recruiter_report)} 字符")

    # 显示当前证据图状态
    if graph and len(graph) > 0:
        log_evidence_stats(state.get("evidence_graph", {}))

    # 获取分配给 Oncologist 的方向
    directions = []
    if plan:
        for d in plan.directions:
            if d.target_agent == "Oncologist":
                directions.append(d.to_dict())

    # 如果没有专门分配的方向，创建默认方向
    if not directions:
        directions = [{
            "id": "D_ONC_DEFAULT",
            "topic": "治疗方案制定",
            "target_agent": "Oncologist",
            "priority": 1,
            "queries": ["treatment guidelines", "drug therapy"],
            "completion_criteria": "制定治疗方案",
            "status": "pending"
        }]

    # 创建 Agent 并执行研究
    agent = ResearchOncologist()
    raw_pdf_text = state.get("raw_pdf_text", "")

    # 构建上下文（包含之前的专家报告摘要）
    context = f"""病例背景:
{raw_pdf_text}

病理学分析摘要:
{state.get('pathologist_report', '')}

分子分析摘要:
{state.get('geneticist_report', '')}

临床试验摘要:
{state.get('recruiter_report', '')}
"""

    result = agent.research_iterate(
        mode=ResearchMode.BREADTH_FIRST,  # 默认值，实际由 direction.preferred_mode 决定
        directions=directions,
        evidence_graph=state.get("evidence_graph", {}),
        iteration=iteration,
        max_iterations=MAX_PHASE2_ITERATIONS,
        case_context=context,
        research_plan=state.get("research_plan", {})
    )

    # 更新迭代计数
    new_evidence_ids = result.get("new_evidence_ids", [])
    new_findings = len(new_evidence_ids)
    new_iteration = iteration + 1

    logger.info(f"[PHASE2_ONCOLOGIST] 完成, 新证据: {new_findings}")

    # 更新 evidence_graph
    updated_evidence_graph = result.get("evidence_graph", state.get("evidence_graph", {}))

    # 构建迭代历史记录（收敛检查由 PlanAgent 填充）
    iteration_record = {
        "phase": "PHASE2",
        "iteration": new_iteration,
        "timestamp": datetime.now().isoformat(),
        "agent_findings": {
            "Oncologist": {
                "count": new_findings,
                "evidence_ids": new_evidence_ids
            }
        },
        "total_new_findings": new_findings,
        # 收敛检查详情将由 plan_agent_evaluate_phase2 更新
        "convergence_check": {},
        "final_decision": "pending"  # 由 PlanAgent 决定
    }

    # 追加到迭代历史
    history = list(state.get("iteration_history", []))
    history.append(iteration_record)

    logger.info(f"[PHASE2] 迭代 {new_iteration} 执行完成，等待 PlanAgent 评估...")

    # 详细迭代报告由 plan_agent_evaluate_phase2() 保存

    return_dict = {
        "evidence_graph": updated_evidence_graph,
        "oncologist_research_result": result,
        "phase2_iteration": new_iteration,
        "phase2_new_findings": new_findings,
        "iteration_history": history,
    }
    # 如果有更新的研究计划，也返回
    if result.get("research_plan"):
        return_dict["research_plan"] = result.get("research_plan")
    return return_dict


def plan_agent_evaluate_phase2(state: MtbState) -> Dict[str, Any]:
    """
    PlanAgent 评估 Phase 2 研究进度并更新计划

    在 Phase 2 Oncologist 执行后调用，由 PlanAgent 统一判断收敛。
    """
    logger.info("[PHASE2_PLAN_EVAL] PlanAgent 评估研究进度...")

    iteration = state.get("phase2_iteration", 0)

    # 保存评估前的 plan 用于报告对比
    pre_eval_plan = state.get("research_plan", {})

    # 检查迭代上限
    if iteration >= MAX_PHASE2_ITERATIONS:
        logger.warning(f"[PHASE2_PLAN_EVAL] 达到迭代上限 ({MAX_PHASE2_ITERATIONS})，强制收敛")
        forced_eval_result = {
            "decision": "converged",
            "research_mode": "breadth_first",
            "reasoning": "达到迭代上限，强制收敛",
            "quality_assessment": {},
            "gaps": [],
            "next_priorities": []
        }
        # 保存详细迭代报告
        _save_detailed_iteration_report(
            state=state,
            phase="PHASE2",
            iteration=iteration,
            eval_result=forced_eval_result,
            agent_names=["Oncologist"],
            pre_eval_plan=pre_eval_plan
        )
        return {
            "phase2_decision": "converged",
            "plan_agent_evaluation": {
                "phase": "phase2",
                "iteration": iteration,
                "reasoning": "达到迭代上限，强制收敛",
                "gaps": [],
                "next_priorities": []
            }
        }

    # 调用 PlanAgent 评估
    try:
        plan_agent = PlanAgent()
        eval_result = plan_agent.evaluate_and_update(state, "phase2", iteration)

        decision = eval_result.get("decision", "continue")
        logger.info(f"[PHASE2_PLAN_EVAL] PlanAgent 决策: {decision}")
        logger.info(f"[PHASE2_PLAN_EVAL] 理由: {eval_result.get('reasoning', '')[:100]}...")

        # 保存详细迭代报告
        _save_detailed_iteration_report(
            state=state,
            phase="PHASE2",
            iteration=iteration,
            eval_result=eval_result,
            agent_names=["Oncologist"],
            pre_eval_plan=pre_eval_plan
        )

        return {
            "research_plan": eval_result.get("research_plan", state.get("research_plan", {})),
            "research_mode": eval_result.get("research_mode", "breadth_first"),
            "phase2_decision": decision,
            "plan_agent_evaluation": {
                "phase": "phase2",
                "iteration": iteration,
                "reasoning": eval_result.get("reasoning", ""),
                "quality_assessment": eval_result.get("quality_assessment", {}),
                "gaps": eval_result.get("gaps", []),
                "next_priorities": eval_result.get("next_priorities", [])
            }
        }

    except Exception as e:
        logger.error(f"[PHASE2_PLAN_EVAL] PlanAgent 评估失败: {e}")
        # 评估失败时继续迭代
        error_eval_result = {
            "decision": "continue",
            "research_mode": "breadth_first",
            "reasoning": f"评估失败: {str(e)}",
            "quality_assessment": {},
            "gaps": [],
            "next_priorities": []
        }
        # 仍保存详细报告（记录失败情况）
        _save_detailed_iteration_report(
            state=state,
            phase="PHASE2",
            iteration=iteration,
            eval_result=error_eval_result,
            agent_names=["Oncologist"],
            pre_eval_plan=pre_eval_plan
        )
        return {
            "phase2_decision": "continue",
            "plan_agent_evaluation": {
                "phase": "phase2",
                "iteration": iteration,
                "reasoning": f"评估失败: {str(e)}",
                "gaps": [],
                "next_priorities": []
            }
        }


def phase2_convergence_check(state: MtbState) -> Literal["continue", "converged"]:
    """
    Phase 2 收敛检查 - 从 state 中读取 PlanAgent 的决策

    收敛检查逻辑已移至 plan_agent_evaluate_phase2 中执行。
    此函数仅作为条件边，读取 phase2_decision 字段。
    """
    decision = state.get("phase2_decision", "continue")
    return decision


# ==================== 报告生成节点 ====================

def generate_agent_reports(state: MtbState) -> Dict[str, Any]:
    """
    提取引用和辅助信息（不覆写综合报告）

    综合报告由以下函数生成：
    - Phase 1 报告: generate_phase1_reports() → pathologist_report, geneticist_report, recruiter_report
    - Phase 2 报告: generate_phase2_reports() → oncologist_plan

    本函数仅提取引用、试验信息、安全警告，以及生成研究进度报告。
    """
    log_separator("REPORT_GEN")
    logger.info("[REPORT_GEN] 提取引用和辅助信息...")

    # 显示最终证据图统计
    log_evidence_stats(state.get("evidence_graph", {}))
    log_edge_stats(state.get("evidence_graph", {}), "EDGE")

    graph = load_evidence_graph(state.get("evidence_graph", {}))
    iteration_history = state.get("iteration_history", [])

    # 收集各 Agent 的观察数
    pathologist_obs_count = graph.get_agent_observation_count("Pathologist") if graph else 0
    geneticist_obs_count = graph.get_agent_observation_count("Geneticist") if graph else 0
    recruiter_obs_count = graph.get_agent_observation_count("Recruiter") if graph else 0
    oncologist_obs_count = graph.get_agent_observation_count("Oncologist") if graph else 0

    # 提取试验信息（从 TRIAL 类型实体）
    recruiter_trials = []
    if graph:
        from src.models.evidence_graph import EntityType
        trial_entities = graph.get_entities_by_type(EntityType.TRIAL)
        for entity in trial_entities:
            # 从观察中提取试验数据
            for obs in entity.observations:
                if obs.source_agent == "Recruiter":
                    trial_data = {
                        "id": entity.canonical_id,
                        "name": entity.name,
                        "statement": obs.statement,
                        "provenance": obs.provenance,
                        "source_url": obs.source_url
                    }
                    recruiter_trials.append(trial_data)
                    break  # 每个实体只添加一次

    oncologist_warnings = []

    # 生成研究进度报告
    progress_report = generate_progress_report(iteration_history)

    logger.info(f"[REPORT_GEN] 观察统计: P={pathologist_obs_count}, G={geneticist_obs_count}, R={recruiter_obs_count}, O={oncologist_obs_count}")

    # 注意：不覆写 pathologist_report, geneticist_report, recruiter_report, oncologist_plan
    # 这些报告已由 generate_phase1_reports() 和 generate_phase2_reports() 生成
    # 引用信息现在通过 evidence_graph 直接传递给 Chair，不再需要单独提取
    return {
        "recruiter_trials": recruiter_trials,
        "oncologist_safety_warnings": oncologist_warnings,
        "research_converged": True,
        "research_progress_report": progress_report,
    }


def generate_progress_report(iteration_history: List[Dict[str, Any]]) -> str:
    """
    生成完整的研究进度报告

    Args:
        iteration_history: 迭代历史记录列表

    Returns:
        Markdown 格式的研究进度报告
    """
    lines = ["# 研究进度报告", ""]

    if not iteration_history:
        lines.append("暂无迭代历史记录。")
        return "\n".join(lines)

    # Phase 1 摘要
    p1_iterations = [r for r in iteration_history if r.get("phase") == "PHASE1"]
    p2_iterations = [r for r in iteration_history if r.get("phase") == "PHASE2"]

    # 总体统计
    total_evidence = sum(r.get("total_new_findings", 0) for r in iteration_history)
    lines.append("## 研究总览")
    lines.append(f"- **Phase 1 迭代**: {len(p1_iterations)} 轮")
    lines.append(f"- **Phase 2 迭代**: {len(p2_iterations)} 轮")
    lines.append(f"- **总证据数**: {total_evidence} 条")
    lines.append("")

    # Phase 1 详情
    if p1_iterations:
        lines.append(f"## Phase 1: 证据收集 ({len(p1_iterations)} 轮)")
        lines.append("")

        for r in p1_iterations:
            lines.append(f"### 第 {r['iteration']} 轮")
            lines.append(f"- **时间**: {r.get('timestamp', 'N/A')}")
            lines.append(f"- **新增证据**: {r.get('total_new_findings', 0)} 条")

            # Agent 分布
            agent_findings = r.get("agent_findings", {})
            for agent, data in agent_findings.items():
                lines.append(f"  - {agent}: {data.get('count', 0)} 条")

            # 收敛检查详情
            conv = r.get("convergence_check", {})
            if conv:
                lines.append("- **收敛检查**:")

                # Step 1
                step1 = conv.get("step1_metrics", {})
                step1_status = "通过" if step1.get("passed") else "未通过"
                step1_reason = step1.get("reason", "")
                lines.append(f"  - Step 1 (Metrics): {step1_status}")
                if step1_reason:
                    lines.append(f"    - 原因: {step1_reason}")
                if step1.get("insufficient_directions"):
                    dirs = ", ".join(step1["insufficient_directions"][:3])
                    lines.append(f"    - 证据不足方向: {dirs}")

                # Step 2
                step2 = conv.get("step2_module", {})
                step2_status = "通过" if step2.get("passed") else "未通过"
                lines.append(f"  - Step 2 (Module): {step2_status}")
                if step2.get("uncovered"):
                    uncovered = ", ".join(step2["uncovered"][:3])
                    lines.append(f"    - 未覆盖模块: {uncovered}")

                # Step 3
                step3 = conv.get("step3_judge")
                if step3:
                    decision = step3.get("decision", "N/A")
                    confidence = step3.get("confidence", "N/A")
                    lines.append(f"  - Step 3 (Judge): {decision} (置信度: {confidence})")
                    if step3.get("reasoning"):
                        lines.append(f"    - 理由: {step3['reasoning']}")
                    if step3.get("gaps"):
                        gaps = step3["gaps"]
                        lines.append(f"    - 研究空白: {gaps}")
                    if step3.get("strengths"):
                        strengths = step3["strengths"]
                        lines.append(f"    - 已覆盖方面: {strengths}")

            lines.append(f"- **最终决策**: **{r.get('final_decision', 'unknown')}**")
            lines.append("")

    # Phase 2 详情
    if p2_iterations:
        lines.append(f"## Phase 2: 治疗规划 ({len(p2_iterations)} 轮)")
        lines.append("")

        for r in p2_iterations:
            lines.append(f"### 第 {r['iteration']} 轮")
            lines.append(f"- **时间**: {r.get('timestamp', 'N/A')}")
            lines.append(f"- **新增证据**: {r.get('total_new_findings', 0)} 条")

            # Agent 分布
            agent_findings = r.get("agent_findings", {})
            for agent, data in agent_findings.items():
                lines.append(f"  - {agent}: {data.get('count', 0)} 条")

            # 收敛检查详情
            conv = r.get("convergence_check", {})
            if conv:
                lines.append("- **收敛检查**:")

                # Step 1
                step1 = conv.get("step1_metrics", {})
                step1_status = "通过" if step1.get("passed") else "未通过"
                step1_reason = step1.get("reason", "")
                lines.append(f"  - Step 1 (Metrics): {step1_status}")
                if step1_reason:
                    lines.append(f"    - 原因: {step1_reason}")
                if step1.get("drug_count") is not None:
                    lines.append(f"    - 药物证据: {step1.get('drug_count', 0)}, 指南证据: {step1.get('guideline_count', 0)}")

                # Step 2
                step2 = conv.get("step2_module", {})
                step2_status = "通过" if step2.get("passed") else "未通过"
                lines.append(f"  - Step 2 (Module): {step2_status}")
                if step2.get("uncovered"):
                    uncovered = ", ".join(step2["uncovered"][:3])
                    lines.append(f"    - 未覆盖模块: {uncovered}")

                # Step 3
                step3 = conv.get("step3_judge")
                if step3:
                    decision = step3.get("decision", "N/A")
                    confidence = step3.get("confidence", "N/A")
                    lines.append(f"  - Step 3 (Judge): {decision} (置信度: {confidence})")
                    if step3.get("reasoning"):
                        lines.append(f"    - 理由: {step3['reasoning']}")
                    if step3.get("gaps"):
                        gaps = step3["gaps"]
                        lines.append(f"    - 研究空白: {gaps}")
                    if step3.get("strengths"):
                        strengths = step3["strengths"]
                        lines.append(f"    - 已覆盖方面: {strengths}")

            lines.append(f"- **最终决策**: **{r.get('final_decision', 'unknown')}**")
            lines.append("")

    return "\n".join(lines)


# ==================== 子图构建 ====================

def create_research_subgraph() -> StateGraph:
    """
    创建研究子图

    结构（新架构，收敛判断由 PlanAgent 统一处理）：
    [entry]
        ↓
    ┌──────────────────────────────────────────┐
    │ Phase 1 Loop                              │
    │ [router] → [pathologist]                  │
    │          → [geneticist]  → [aggregator]   │
    │          → [recruiter]        ↓           │
    │                        [plan_agent_eval]  │
    │                              ↓            │
    │                    [convergence_check]    │
    │           ↓ continue         ↓ converged  │
    └───────────┘                  │            │
                                   ↓
                     [generate_phase1_reports]  ← 生成 P/G/R 综合报告
                                   ↓
    ┌──────────────────────────────────────────┐
    │ Phase 2 Loop                              │
    │       [oncologist]  ← 接收专家报告        │
    │           ↓                               │
    │    [plan_agent_eval]                      │
    │           ↓                               │
    │   [convergence_check]                     │
    │       ↓ continue  ↓ converged             │
    └───────┘           │                       │
                        ↓
               [generate_phase2_reports]  ← 生成 Oncologist 综合报告
                        ↓
               [generate_reports]  ← 提取引用和辅助信息
                        ↓
                      [END]
    """
    workflow = StateGraph(MtbState)

    # ==================== Phase 1 节点 ====================
    workflow.add_node("phase1_router", lambda s: {})  # 路由节点不修改状态
    workflow.add_node("phase1_pathologist", phase1_pathologist_node)
    workflow.add_node("phase1_geneticist", phase1_geneticist_node)
    workflow.add_node("phase1_recruiter", phase1_recruiter_node)
    workflow.add_node("phase1_aggregator", phase1_aggregator)
    workflow.add_node("phase1_plan_eval", plan_agent_evaluate_phase1)  # PlanAgent 评估

    # ==================== Phase 1 报告生成节点 ====================
    workflow.add_node("generate_phase1_reports", generate_phase1_reports)

    # ==================== Phase 2 研究计划初始化节点 ====================
    workflow.add_node("phase2_plan_init", phase2_plan_init)

    # ==================== Phase 2 节点 ====================
    workflow.add_node("phase2_oncologist", phase2_oncologist_node)
    workflow.add_node("phase2_plan_eval", plan_agent_evaluate_phase2)  # PlanAgent 评估

    # ==================== Phase 2 报告生成节点 ====================
    workflow.add_node("generate_phase2_reports", generate_phase2_reports)

    # ==================== 辅助信息提取节点 ====================
    workflow.add_node("generate_reports", generate_agent_reports)

    # ==================== 边定义 ====================

    # 入口 → Phase 1 路由
    workflow.add_conditional_edges(
        "__start__",
        phase1_router,
        ["phase1_pathologist", "phase1_geneticist", "phase1_recruiter"]
    )

    # Phase 1 并行节点 → 聚合器
    workflow.add_edge("phase1_pathologist", "phase1_aggregator")
    workflow.add_edge("phase1_geneticist", "phase1_aggregator")
    workflow.add_edge("phase1_recruiter", "phase1_aggregator")

    # Phase 1 聚合器 → PlanAgent 评估
    workflow.add_edge("phase1_aggregator", "phase1_plan_eval")

    # Phase 1 PlanAgent 评估 → 收敛检查
    workflow.add_conditional_edges(
        "phase1_plan_eval",
        phase1_convergence_check,
        {
            "continue": "phase1_router",  # 继续循环
            "converged": "generate_phase1_reports"  # 生成专家报告
        }
    )

    # Phase 1 专家报告 → Phase 2 研究计划初始化 → Phase 2 Oncologist
    workflow.add_edge("generate_phase1_reports", "phase2_plan_init")
    workflow.add_edge("phase2_plan_init", "phase2_oncologist")

    # Phase 1 路由 → 并行节点（循环时使用）
    workflow.add_conditional_edges(
        "phase1_router",
        phase1_router,
        ["phase1_pathologist", "phase1_geneticist", "phase1_recruiter"]
    )

    # Phase 2 Oncologist → PlanAgent 评估
    workflow.add_edge("phase2_oncologist", "phase2_plan_eval")

    # Phase 2 PlanAgent 评估 → 收敛检查
    workflow.add_conditional_edges(
        "phase2_plan_eval",
        phase2_convergence_check,
        {
            "continue": "phase2_oncologist",  # 继续循环
            "converged": "generate_phase2_reports"  # 生成 Oncologist 综合报告
        }
    )

    # Phase 2 报告 → 辅助信息提取
    workflow.add_edge("generate_phase2_reports", "generate_reports")

    # 辅助信息提取 → 结束
    workflow.add_edge("generate_reports", END)

    logger.info("[RESEARCH_SUBGRAPH] 子图构建完成 (PlanAgent 统一收敛判断)")
    return workflow.compile()


if __name__ == "__main__":
    print("Research Subgraph 模块加载成功")
    print(f"Phase 1 最大迭代: {MAX_PHASE1_ITERATIONS}")
    print(f"Phase 2 最大迭代: {MAX_PHASE2_ITERATIONS}")
    print(f"最小证据节点: {MIN_EVIDENCE_NODES}")
    print(f"每方向最小证据: {MIN_EVIDENCE_PER_DIRECTION}")
