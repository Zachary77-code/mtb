"""
Research Subgraph - 两阶段研究循环子图

实现 DeepEvidence 风格的研究循环：
- Phase 1: Pathologist + Geneticist + Recruiter 并行 BFRS/DFRS 循环
- Phase 2: Oncologist 独立 BFRS/DFRS 循环
"""
from typing import List, Literal, Dict, Any
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.types import Send

from src.models.state import MtbState
from src.models.evidence_graph import load_evidence_graph
from src.models.research_plan import (
    load_research_plan,
    ResearchMode
)
from src.agents.base_agent import SUBGRAPH_MODEL
from src.agents.pathologist import PathologistAgent
from src.agents.geneticist import GeneticistAgent
from src.agents.recruiter import RecruiterAgent
from src.agents.oncologist import OncologistAgent
from src.agents.research_mixin import ResearchMixin
from src.agents.plan_agent import PlanAgent
from src.utils.logger import (
    mtb_logger as logger,
    log_separator,
    log_evidence_stats
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
                node = graph.get_node(eid)
                if node:
                    grade = f"[{node.grade.value}]" if node.grade else ""
                    etype = node.evidence_type.value if node.evidence_type else "unknown"
                    text = node.content.get("text", str(node.content))[:100] if node.content else ""
                    lines.append(f"- {grade} [{etype}] {text}...")
        lines.append("")

    # === Evidence Graph 当前状态 ===
    lines.append("## Evidence Graph 当前状态")
    lines.append("")
    if graph:
        summary = graph.summary()
        lines.append(f"- **总节点数**: {summary.get('total_nodes', 0)}")
        lines.append(f"- **类型分布**: {summary.get('by_type', {})}")
        lines.append(f"- **Agent 分布**: {summary.get('by_agent', {})}")
        lines.append(f"- **证据等级分布**: {summary.get('by_grade', {})}")
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
    agent_names: List[str]
):
    """
    保存 PlanAgent 评估后的详细迭代报告

    报告包含：
    1. PlanAgent 决策和理由
    2. 各研究方向的完成度和证据质量
    3. 本轮新增证据的完整明细（不截断）
    4. Evidence Graph 完整统计

    Args:
        state: MtbState 状态
        phase: 阶段名称 "PHASE1" 或 "PHASE2"
        iteration: 迭代轮次
        eval_result: PlanAgent 评估结果
        agent_names: 参与的 Agent 列表
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
        "",
    ]

    # === 0. 下一轮各方向研究模式 (新增) ===
    research_plan = eval_result.get("research_plan", state.get("research_plan", {}))
    plan = load_research_plan(research_plan)
    if plan and plan.directions:
        lines.append("## 0. 下一轮各方向研究模式")
        lines.append("")
        lines.append("| 方向 ID | 主题 | Agent | 模式 | 理由 |")
        lines.append("|---------|------|-------|------|------|")
        for d in plan.directions:
            if d.target_agent in agent_names:
                mode_display = {"breadth_first": "BFRS", "depth_first": "DFRS", "skip": "Skip"}.get(d.preferred_mode, d.preferred_mode)
                topic_short = d.topic[:25] + "..." if len(d.topic) > 25 else d.topic
                reason_short = d.mode_reason[:40] + "..." if len(d.mode_reason) > 40 else d.mode_reason
                lines.append(f"| {d.id} | {topic_short} | {d.target_agent} | {mode_display} | {reason_short} |")
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

    # === 2. 本轮新增证据明细 ===
    lines.append("## 2. 本轮新增证据明细")
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
            node = graph.get_node(eid) if graph else None
            if not node:
                lines.append(f"#### 证据 {eid}")
                lines.append("- *节点未找到*")
                lines.append("")
                continue

            lines.append(f"#### 证据 {node.id}")
            lines.append(f"- **类型**: {node.evidence_type.value if node.evidence_type else 'N/A'}")
            grade_val = node.grade.value if node.grade else 'N/A'
            grade_desc = _grade_description(node.grade)
            lines.append(f"- **等级**: {grade_val} ({grade_desc})")
            if node.civic_evidence_type:
                lines.append(f"- **CIViC类型**: {node.civic_evidence_type.value}")
            lines.append(f"- **来源Agent**: {node.source_agent}")
            lines.append(f"- **来源工具**: {node.source_tool or 'N/A'}")
            if node.provenance:
                lines.append(f"- **来源文献**: {node.provenance}")
            if node.observation:
                lines.append(f"- **Observation**: {node.observation}")

            # Context
            if node.context and not node.context.is_empty():
                lines.append("- **Context**:")
                ctx = node.context
                if ctx.cell_type:
                    lines.append(f"  - 癌种: {ctx.cell_type}")
                if ctx.disease_stage:
                    lines.append(f"  - 分期: {ctx.disease_stage}")
                if ctx.tissue:
                    lines.append(f"  - 组织: {ctx.tissue}")
                if ctx.assay:
                    lines.append(f"  - 方法: {ctx.assay}")
                if ctx.sample_size:
                    lines.append(f"  - 样本量: {ctx.sample_size}")
                if ctx.treatment_line:
                    lines.append(f"  - 治疗线: {ctx.treatment_line}")
                if ctx.biomarker_status:
                    lines.append(f"  - 标志物状态: {ctx.biomarker_status}")
                if ctx.species and ctx.species != "human":
                    lines.append(f"  - 物种: {ctx.species}")

            # 完整内容（不截断）
            if node.content:
                content_text = node.content.get("text", "") if isinstance(node.content, dict) else str(node.content)
                if content_text:
                    lines.append("- **完整内容**:")
                    # 多行内容缩进处理
                    for line in content_text.split('\n'):
                        lines.append(f"  {line}")

            # 量化结果
            if node.numeric_result:
                lines.append("- **量化结果**:")
                for k, v in node.numeric_result.items():
                    lines.append(f"  - {k}: {v}")

            # 研究元信息
            lines.append(f"- **收集轮次**: {node.iteration}")
            lines.append(f"- **收集模式**: {node.research_mode}")
            if node.needs_deep_research:
                lines.append(f"- **需深入研究**: 是 - {node.depth_research_reason or 'N/A'}")

            lines.append("")

    # === 3. Evidence Graph 完整统计 ===
    lines.append("## 3. Evidence Graph 完整统计")
    lines.append("")
    if graph:
        summary = graph.summary()
        lines.append("### 总体统计")
        lines.append(f"- **总节点数**: {summary.get('total_nodes', 0)}")
        lines.append(f"- **总边数**: {summary.get('total_edges', 0)}")
        lines.append("")

        by_type = summary.get("by_type", {})
        if by_type:
            lines.append("### 按类型分布")
            lines.append("| 类型 | 数量 |")
            lines.append("|------|------|")
            for etype, count in by_type.items():
                lines.append(f"| {etype} | {count} |")
            lines.append("")

        by_agent = summary.get("by_agent", {})
        if by_agent:
            lines.append("### 按 Agent 分布")
            lines.append("| Agent | 数量 |")
            lines.append("|-------|------|")
            for agent, count in by_agent.items():
                lines.append(f"| {agent} | {count} |")
            lines.append("")

        by_grade = summary.get("by_grade", {})
        if by_grade:
            lines.append("### 按证据等级分布")
            lines.append("| 等级 | 数量 |")
            lines.append("|------|------|")
            for grade, count in by_grade.items():
                lines.append(f"| {grade} | {count} |")
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

def _format_evidence_for_report(evidence_list: List[Any]) -> str:
    """
    将证据列表格式化为报告生成用的摘要

    Args:
        evidence_list: EvidenceNode 列表

    Returns:
        格式化的证据摘要文本
    """
    if not evidence_list:
        return "暂无相关证据。"

    lines = []

    # 按证据等级排序（A 优先）
    grade_order = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}
    sorted_evidence = sorted(
        evidence_list,
        key=lambda n: grade_order.get(n.grade.value if n.grade else "E", 5)
    )

    for i, node in enumerate(sorted_evidence, 1):
        grade_str = f"[{node.grade.value}]" if node.grade else "[N/A]"
        civic_str = f" ({node.civic_evidence_type.value})" if node.civic_evidence_type else ""

        lines.append(f"### 证据 {i} {grade_str}{civic_str}")

        if node.observation:
            lines.append(f"**观察**: {node.observation}")

        if node.content:
            content_text = node.content.get("text", "") if isinstance(node.content, dict) else str(node.content)
            if content_text:
                # 保留完整内容，不截断
                lines.append(f"**内容**: {content_text}")

        if node.provenance:
            lines.append(f"**来源**: {node.provenance}")

        if node.source_tool:
            lines.append(f"**工具**: {node.source_tool}")

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
    agent_configs = [
        ("Pathologist", ResearchPathologist, "pathologist_report"),
        ("Geneticist", ResearchGeneticist, "geneticist_report"),
        ("Recruiter", ResearchRecruiter, "recruiter_report"),
    ]

    for agent_name, agent_class, report_key in agent_configs:
        logger.info(f"[PHASE1_REPORTS] 生成 {agent_name} 报告...")

        # 提取该 Agent 收集的证据
        agent_evidence = graph.get_nodes_by_agent(agent_name)
        evidence_count = len(agent_evidence) if agent_evidence else 0
        logger.info(f"[PHASE1_REPORTS]   {agent_name} 证据数: {evidence_count}")

        if not agent_evidence:
            reports[report_key] = f"## {agent_name} 报告\n\n暂无相关发现。"
            continue

        # 构建证据摘要
        evidence_summary = _format_evidence_for_report(agent_evidence)

        # 构建报告生成 prompt
        report_prompt = f"""基于以下病例信息和已收集的研究证据，生成你的专业领域综合报告。

## 病例背景
{raw_pdf_text}

## 已收集的研究证据（共 {evidence_count} 条）
{evidence_summary}

## 输出要求
请生成一份完整的 Markdown 格式的领域分析报告。注意：
1. 整合所有证据，给出综合分析结论
2. 保留所有引用（PMID、NCT 等）
3. 明确标注证据等级 [Evidence A/B/C/D/E]
4. 重点突出对治疗决策有指导意义的发现
"""

        try:
            # 实例化 Agent 并调用
            agent = agent_class()
            response = agent.invoke(report_prompt)

            if response and response.get("output"):
                report = response["output"]
                reports[report_key] = report
                logger.info(f"[PHASE1_REPORTS]   {agent_name} 报告生成成功: {len(report)} 字符")
            else:
                reports[report_key] = f"## {agent_name} 报告\n\n报告生成失败。"
                logger.warning(f"[PHASE1_REPORTS]   {agent_name} 报告生成失败")

        except Exception as e:
            logger.error(f"[PHASE1_REPORTS]   {agent_name} 报告生成异常: {e}")
            reports[report_key] = f"## {agent_name} 报告\n\n报告生成异常: {str(e)}"

    logger.info(f"[PHASE1_REPORTS] 报告生成完成")
    return reports


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

    # 提取 Oncologist 收集的证据
    oncologist_evidence = graph.get_nodes_by_agent("Oncologist")
    evidence_count = len(oncologist_evidence) if oncologist_evidence else 0
    logger.info(f"[PHASE2_REPORTS] Oncologist 证据数: {evidence_count}")

    if not oncologist_evidence:
        logger.warning("[PHASE2_REPORTS] Oncologist 无证据，生成默认报告")
        return {"oncologist_plan": "## 治疗方案分析\n\n暂无相关发现。"}

    # 构建证据摘要（完整，不截断）
    evidence_summary = _format_evidence_for_report(oncologist_evidence)

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

## 你收集的研究证据（共 {evidence_count} 条）
{evidence_summary}

## 输出要求
请生成一份完整的 Markdown 格式的肿瘤学治疗方案分析报告。注意：
1. 整合所有证据和上游报告信息，给出综合治疗建议
2. 保留所有引用（PMID、NCT 等）
3. 明确标注证据等级 [Evidence A/B/C/D/E]
4. 重点突出治疗方案选择、用药建议、安全性考量
5. 包含治疗路线图和分子复查建议
"""

    try:
        # 实例化 Oncologist Agent 并调用
        agent = ResearchOncologist()
        response = agent.invoke(report_prompt)

        if response and response.get("output"):
            report = response["output"]
            logger.info(f"[PHASE2_REPORTS] Oncologist 报告生成成功: {len(report)} 字符")
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
            agent_names=["Pathologist", "Geneticist", "Recruiter"]
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
            agent_names=["Pathologist", "Geneticist", "Recruiter"]
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
            agent_names=["Pathologist", "Geneticist", "Recruiter"]
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
            agent_names=["Oncologist"]
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
            agent_names=["Oncologist"]
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
            agent_names=["Oncologist"]
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

    graph = load_evidence_graph(state.get("evidence_graph", {}))
    iteration_history = state.get("iteration_history", [])

    # 收集各 Agent 的证据
    pathologist_evidence = graph.get_nodes_by_agent("Pathologist") if graph else []
    geneticist_evidence = graph.get_nodes_by_agent("Geneticist") if graph else []
    recruiter_evidence = graph.get_nodes_by_agent("Recruiter") if graph else []
    oncologist_evidence = graph.get_nodes_by_agent("Oncologist") if graph else []

    # 提取试验信息
    recruiter_trials = []
    for ev in recruiter_evidence:
        if ev.evidence_type.value == "trial":
            trial_data = ev.content.get("raw", {})
            if trial_data:
                recruiter_trials.append(trial_data)

    oncologist_warnings = []

    # 提取引用
    def extract_references(evidence_list):
        refs = []
        for ev in evidence_list:
            if ev.source_tool:
                refs.append({
                    "type": ev.evidence_type.value,
                    "id": ev.id,
                    "source": ev.source_tool
                })
        return refs

    # 生成研究进度报告
    progress_report = generate_progress_report(iteration_history)

    logger.info(f"[REPORT_GEN] 引用提取完成: P={len(pathologist_evidence)}, G={len(geneticist_evidence)}, R={len(recruiter_evidence)}, O={len(oncologist_evidence)}")

    # 注意：不覆写 pathologist_report, geneticist_report, recruiter_report, oncologist_plan
    # 这些报告已由 generate_phase1_reports() 和 generate_phase2_reports() 生成
    return {
        "pathologist_references": extract_references(pathologist_evidence),
        "geneticist_references": extract_references(geneticist_evidence),
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

    # ==================== Phase 1 报告生成节点（新增）====================
    workflow.add_node("generate_phase1_reports", generate_phase1_reports)

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

    # Phase 1 专家报告 → Phase 2 Oncologist
    workflow.add_edge("generate_phase1_reports", "phase2_oncologist")

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
