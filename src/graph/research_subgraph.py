"""
Research Subgraph - 两阶段研究循环子图

实现 DeepEvidence 风格的研究循环：
- Phase 1: Pathologist + Geneticist + Recruiter 并行 BFRS/DFRS 循环
- Phase 2: Oncologist 独立 BFRS/DFRS 循环
- 动态收敛检查
"""
from typing import List, Literal, Dict, Any
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.types import Send

from src.models.state import MtbState
from src.models.evidence_graph import load_evidence_graph
from src.models.research_plan import (
    load_research_plan,
    ResearchMode,
    DirectionStatus,
    determine_research_mode
)
from src.agents.base_agent import SUBGRAPH_MODEL
from src.agents.pathologist import PathologistAgent
from src.agents.geneticist import GeneticistAgent
from src.agents.recruiter import RecruiterAgent
from src.agents.oncologist import OncologistAgent
from src.agents.research_mixin import ResearchMixin
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
from src.agents.convergence_judge import ConvergenceJudgeAgent


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


def check_single_agent_convergence(state: MtbState, agent_name: str) -> tuple[bool, Dict[str, Any]]:
    """
    检查单个 Agent 是否收敛

    收敛条件：
    1. 该 Agent 所有分配的方向都有证据
    2. 每个方向证据数 >= MIN_EVIDENCE_PER_DIRECTION
    3. ConvergenceJudge 评估通过

    Args:
        state: MtbState 状态
        agent_name: Agent 名称

    Returns:
        (是否收敛, 检查详情字典)
    """
    check_details = {
        "agent_name": agent_name,
        "step1_direction_evidence": {"passed": False, "insufficient": []},
        "step2_module_coverage": {"passed": False, "uncovered": []},
        "step3_judge": None
    }

    plan = load_research_plan(state.get("research_plan", {}))
    if not plan:
        logger.info(f"[{agent_name}_CONVERGENCE] 无研究计划，视为收敛")
        return True, check_details

    # Step 1: 检查方向证据充分性
    directions = [d for d in plan.directions if d.target_agent == agent_name]
    if not directions:
        logger.info(f"[{agent_name}_CONVERGENCE] 无分配方向，视为收敛")
        return True, check_details

    insufficient = []
    for direction in directions:
        evidence_count = len(direction.evidence_ids)
        if evidence_count < MIN_EVIDENCE_PER_DIRECTION:
            insufficient.append(f"{direction.id}({evidence_count}/{MIN_EVIDENCE_PER_DIRECTION})")

    check_details["step1_direction_evidence"] = {
        "passed": len(insufficient) == 0,
        "insufficient": insufficient
    }

    if insufficient:
        logger.info(f"[{agent_name}_CONVERGENCE] Step 1 未通过: 方向证据不足 {insufficient}")
        return False, check_details

    logger.info(f"[{agent_name}_CONVERGENCE] Step 1 通过: 所有方向证据充分")

    # Step 2: 检查模块覆盖
    module_passed, uncovered = check_agent_module_coverage(state, [agent_name])
    check_details["step2_module_coverage"] = {"passed": module_passed, "uncovered": uncovered}

    if not module_passed:
        logger.info(f"[{agent_name}_CONVERGENCE] Step 2 未通过: 未覆盖模块 {uncovered}")
        return False, check_details

    logger.info(f"[{agent_name}_CONVERGENCE] Step 2 通过: 所有分配模块已覆盖")

    # Step 3: ConvergenceJudge 评估（单个 Agent）
    try:
        judge = ConvergenceJudgeAgent()
        judge_result = judge.evaluate(state, phase="phase1", agent_name=agent_name)
        check_details["step3_judge"] = judge_result

        if judge_result["decision"] == "continue":
            logger.info(f"[{agent_name}_CONVERGENCE] Step 3 未通过: Judge 判断需继续")
            return False, check_details

        logger.info(f"[{agent_name}_CONVERGENCE] Step 3 通过: Judge 判断收敛")

    except Exception as e:
        logger.warning(f"[{agent_name}_CONVERGENCE] Step 3 评估失败: {e}")
        check_details["step3_judge"] = {
            "decision": "converged",
            "confidence": 0.0,
            "reasoning": f"评估失败: {str(e)}，Step 1/2 通过，允许收敛",
            "gaps": [],
            "strengths": []
        }

    logger.info(f"[{agent_name}_CONVERGENCE] ✓ 收敛")
    return True, check_details


# ==================== Phase 1 节点 ====================

def phase1_router(state: MtbState) -> List[Send]:
    """
    Phase 1 路由：只分发未收敛的 Agent

    检查各 Agent 收敛状态，只分发未收敛的 Agent 继续研究。
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

    # 确定研究模式
    gaps = graph.get_gaps_requiring_depth() if graph else []
    mode = determine_research_mode(iteration, plan, gaps) if plan else ResearchMode.BREADTH_FIRST

    logger.info(f"[PHASE1] 研究模式: {mode.value}")
    logger.info(f"[PHASE1] 分发到: {', '.join([a.capitalize() for a in agents_to_run])}")

    # 显示当前证据图状态
    if graph and len(graph) > 0:
        log_evidence_stats(state.get("evidence_graph", {}))

    # 更新状态中的模式
    updated_state = dict(state)
    updated_state["research_mode"] = mode.value

    # 只分发未收敛的 Agent
    sends = [Send(f"phase1_{agent}", updated_state) for agent in agents_to_run]
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
    mode_str = state.get("research_mode", "breadth_first")
    mode = ResearchMode(mode_str)
    plan = load_research_plan(state.get("research_plan", {}))
    evidence_graph = state.get("evidence_graph", {})
    raw_pdf_text = state.get("raw_pdf_text", "")

    # 获取分配给此 Agent 的方向
    directions = []
    if plan:
        for d in plan.directions:
            if d.target_agent == agent_name:
                directions.append(d.to_dict())

    if not directions:
        logger.info(f"[{tag}] 无分配方向，视为收敛")
        return {converged_key: True}

    # 显示分配的方向
    logger.info(f"[{tag}] 分配方向: {len(directions)} 个")
    for d in directions:
        status_icon = "✓" if d.get("status") == "completed" else "○"
        logger.info(f"[{tag}]   {status_icon} {d.get('topic', '未命名')} (优先级: {d.get('priority', '-')})")

    # 创建 Agent 并执行研究
    agent = agent_class()
    research_plan_dict = state.get("research_plan", {})
    result = agent.research_iterate(
        mode=mode,
        directions=directions,
        evidence_graph=evidence_graph,
        iteration=iteration,
        max_iterations=MAX_PHASE1_ITERATIONS,
        case_context=raw_pdf_text[:3000],
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

    # 构建临时 state 用于收敛检查
    temp_state = dict(state)
    temp_state["evidence_graph"] = result.get("evidence_graph", evidence_graph)
    if result.get("research_plan"):
        temp_state["research_plan"] = result.get("research_plan")

    # 检查该 Agent 是否收敛
    is_converged, convergence_details = check_single_agent_convergence(temp_state, agent_name)

    if is_converged:
        logger.info(f"[{tag}] ✓ Agent 收敛")
    else:
        logger.info(f"[{tag}] ○ Agent 未收敛，继续下轮迭代")

    # 返回更新后的证据图、研究计划和收敛状态
    return_dict = {
        "evidence_graph": result.get("evidence_graph", evidence_graph),
        f"{agent_name.lower()}_research_result": result,
        converged_key: is_converged,  # 收敛状态
        f"{agent_name.lower()}_convergence_details": convergence_details,  # 收敛检查详情
    }
    # 如果有更新的研究计划，也返回
    if result.get("research_plan"):
        return_dict["research_plan"] = result.get("research_plan")
    return return_dict


def phase1_aggregator(state: MtbState) -> Dict[str, Any]:
    """
    Phase 1 聚合：合并并行 Agent 的结果，汇总收敛状态，记录迭代历史

    每个 Agent 独立判断收敛，当所有 Agent 都收敛时，Phase 1 整体收敛。
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

    # ==================== 汇总各 Agent 收敛状态 ====================
    pathologist_converged = state.get("pathologist_converged", False)
    geneticist_converged = state.get("geneticist_converged", False)
    recruiter_converged = state.get("recruiter_converged", False)

    # 显示各 Agent 收敛状态
    logger.info("[PHASE1] Agent 收敛状态:")
    logger.info(f"[PHASE1]   Pathologist: {'✓ 已收敛' if pathologist_converged else '○ 未收敛'}")
    logger.info(f"[PHASE1]   Geneticist: {'✓ 已收敛' if geneticist_converged else '○ 未收敛'}")
    logger.info(f"[PHASE1]   Recruiter: {'✓ 已收敛' if recruiter_converged else '○ 未收敛'}")

    # 检查是否所有 Agent 都收敛
    all_converged = pathologist_converged and geneticist_converged and recruiter_converged

    # 检查迭代上限
    if new_iteration >= MAX_PHASE1_ITERATIONS and not all_converged:
        logger.warning(f"[PHASE1] 达到迭代上限 ({MAX_PHASE1_ITERATIONS})，强制收敛")
        all_converged = True
        # 强制标记所有未收敛的 Agent 为收敛
        pathologist_converged = True
        geneticist_converged = True
        recruiter_converged = True

    # 确定 Phase 1 整体决策
    phase1_decision = "converged" if all_converged else "continue"

    # 收集各 Agent 的收敛检查详情
    convergence_details = {
        "Pathologist": state.get("pathologist_convergence_details", {}),
        "Geneticist": state.get("geneticist_convergence_details", {}),
        "Recruiter": state.get("recruiter_convergence_details", {}),
    }

    # 构建迭代历史记录
    iteration_record = {
        "phase": "PHASE1",
        "iteration": new_iteration,
        "timestamp": datetime.now().isoformat(),
        "agent_findings": agent_findings_detail,
        "total_new_findings": new_findings,
        "agent_convergence_status": {
            "Pathologist": pathologist_converged,
            "Geneticist": geneticist_converged,
            "Recruiter": recruiter_converged,
        },
        "convergence_check": convergence_details,
        "final_decision": phase1_decision
    }

    # 追加到迭代历史
    history = list(state.get("iteration_history", []))
    history.append(iteration_record)

    logger.info(f"[PHASE1] 迭代 {new_iteration} 记录完成")
    logger.info(f"[PHASE1] 整体决策: {phase1_decision}")

    # 保存迭代报告
    _save_iteration_report(
        state=state,
        phase="PHASE1",
        iteration=new_iteration,
        agent_findings=agent_findings_detail,
        convergence_details=convergence_details,
        final_decision=phase1_decision
    )

    return {
        "phase1_iteration": new_iteration,
        "phase1_new_findings": new_findings,
        "iteration_history": history,
        "phase1_decision": phase1_decision,
        "phase1_all_converged": all_converged,
        # 确保收敛状态被更新（强制收敛时需要）
        "pathologist_converged": pathologist_converged,
        "geneticist_converged": geneticist_converged,
        "recruiter_converged": recruiter_converged,
    }


def phase1_convergence_check(state: MtbState) -> Literal["continue", "converged"]:
    """
    Phase 1 收敛检查 - 从 state 中读取已计算的决策

    收敛检查逻辑已移至 phase1_aggregator 中执行，以便记录完整的检查详情。
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

    # 确定研究模式
    gaps = graph.get_gaps_requiring_depth() if graph else []
    mode = determine_research_mode(iteration, plan, gaps) if plan else ResearchMode.BREADTH_FIRST

    # 增强日志输出
    log_separator("PHASE2")
    logger.info(f"[PHASE2] Oncologist 迭代 {iteration + 1}/{MAX_PHASE2_ITERATIONS}")
    logger.info(f"[PHASE2] 研究模式: {mode.value}")

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
{raw_pdf_text[:2000]}

病理学分析摘要:
{state.get('pathologist_report', '')[:1000]}

分子分析摘要:
{state.get('geneticist_report', '')[:1000]}

临床试验摘要:
{state.get('recruiter_report', '')[:1000]}
"""

    result = agent.research_iterate(
        mode=mode,
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

    # 更新 evidence_graph 到 state 供收敛检查使用
    updated_evidence_graph = result.get("evidence_graph", state.get("evidence_graph", {}))
    updated_research_plan = result.get("research_plan", state.get("research_plan", {}))

    # 构建临时 state 用于收敛检查
    temp_state = dict(state)
    temp_state["evidence_graph"] = updated_evidence_graph
    temp_state["research_plan"] = updated_research_plan
    temp_state["phase2_iteration"] = new_iteration
    temp_state["phase2_new_findings"] = new_findings

    # ==================== 执行收敛检查并记录 ====================
    convergence_result = _perform_phase2_convergence_check(temp_state, new_iteration, new_findings)

    # 构建迭代历史记录
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
        "convergence_check": convergence_result["check_details"],
        "final_decision": convergence_result["decision"]
    }

    # 追加到迭代历史
    history = list(state.get("iteration_history", []))
    history.append(iteration_record)

    logger.info(f"[PHASE2] 迭代 {new_iteration} 记录完成，决策: {convergence_result['decision']}")

    # 保存迭代报告
    _save_iteration_report(
        state=temp_state,  # 使用更新后的临时 state
        phase="PHASE2",
        iteration=new_iteration,
        agent_findings={
            "Oncologist": {
                "count": new_findings,
                "evidence_ids": new_evidence_ids
            }
        },
        convergence_details=convergence_result["check_details"],
        final_decision=convergence_result["decision"]
    )

    return_dict = {
        "evidence_graph": updated_evidence_graph,
        "oncologist_research_result": result,
        "phase2_iteration": new_iteration,
        "phase2_new_findings": new_findings,
        "iteration_history": history,
        "phase2_decision": convergence_result["decision"],  # 供条件边使用
    }
    # 如果有更新的研究计划，也返回
    if result.get("research_plan"):
        return_dict["research_plan"] = result.get("research_plan")
    return return_dict


def _perform_phase2_convergence_check(state: MtbState, iteration: int, new_findings: int) -> Dict[str, Any]:
    """
    执行 Phase 2 收敛检查，返回完整检查结果

    Returns:
        {
            "decision": "continue" | "converged",
            "check_details": {
                "step1_metrics": {...},
                "step2_module": {...},
                "step3_judge": {...}
            }
        }
    """
    # 收集检查信息
    plan = load_research_plan(state.get("research_plan", {}))
    graph = load_evidence_graph(state.get("evidence_graph", {}))

    # 计算待完成方向数
    pending_count = 0
    onc_directions = []
    if plan:
        onc_directions = [d for d in plan.directions if d.target_agent == "Oncologist"]
        pending = [d for d in onc_directions if d.status == DirectionStatus.PENDING]
        pending_count = len(pending)

    evidence_count = len(graph) if graph else 0

    # 计算治疗方案证据数
    drug_count = 0
    guideline_count = 0
    if graph:
        from src.models.evidence_graph import EvidenceType
        drug_nodes = graph.get_nodes_by_type(EvidenceType.DRUG)
        guideline_nodes = graph.get_nodes_by_type(EvidenceType.GUIDELINE)
        drug_count = len(drug_nodes)
        guideline_count = len(guideline_nodes)

    check_details = {
        "step1_metrics": {"passed": False, "reason": "", "drug_count": drug_count, "guideline_count": guideline_count},
        "step2_module": {"passed": False, "uncovered": []},
        "step3_judge": None
    }

    # 显示检查状态
    logger.info("[PHASE2_CONVERGENCE] 检查收敛条件...")
    logger.info(f"[PHASE2_CONVERGENCE]   迭代: {iteration}/{MAX_PHASE2_ITERATIONS}")
    logger.info(f"[PHASE2_CONVERGENCE]   待完成方向: {pending_count}")
    logger.info(f"[PHASE2_CONVERGENCE]   证据节点: {evidence_count}")
    logger.info(f"[PHASE2_CONVERGENCE]   本轮新发现: {new_findings}")
    logger.info(f"[PHASE2_CONVERGENCE]   治疗证据: 药物={drug_count}, 指南={guideline_count}")

    # ==================== 迭代上限检查（优先） ====================
    if iteration >= MAX_PHASE2_ITERATIONS:
        module_passed, uncovered = check_module_coverage(state)
        if not module_passed:
            logger.warning(f"[PHASE2_CONVERGENCE] 达到迭代上限，以下模块可能证据不足: {uncovered}")

        check_details["step1_metrics"] = {
            "passed": True,
            "reason": "达到迭代上限",
            "drug_count": drug_count,
            "guideline_count": guideline_count
        }
        check_details["step2_module"] = {"passed": module_passed, "uncovered": uncovered}

        logger.info("[PHASE2_CONVERGENCE] → 收敛 (原因: 达到迭代上限)")
        return {"decision": "converged", "check_details": check_details}

    # ==================== Step 1: Metric-based Fast Check ====================
    logger.info("[PHASE2_CONVERGENCE] Step 1: Metric-based 检查...")

    metrics_passed = False
    metrics_reason = ""

    # 条件 1: 研究方向完成
    if plan and pending_count == 0 and len(onc_directions) > 0:
        metrics_passed = True
        metrics_reason = "所有 Oncologist 方向完成"

    # 条件 2: 已有治疗方案证据
    elif (drug_count >= 1 or guideline_count >= 1) and iteration >= 1:
        metrics_passed = True
        metrics_reason = f"已有治疗方案 (药物={drug_count}, 指南={guideline_count})"

    check_details["step1_metrics"] = {
        "passed": metrics_passed,
        "reason": metrics_reason if metrics_passed else "尚无足够治疗方案证据",
        "drug_count": drug_count,
        "guideline_count": guideline_count
    }

    if not metrics_passed:
        logger.info("[PHASE2_CONVERGENCE]   Step 1 未通过，继续迭代")
        return {"decision": "continue", "check_details": check_details}

    logger.info(f"[PHASE2_CONVERGENCE]   Step 1 通过: {metrics_reason}")

    # ==================== Step 2: Agent Module Coverage Check ====================
    logger.info("[PHASE2_CONVERGENCE] Step 2: Agent Module Coverage 检查...")

    module_passed, uncovered = check_agent_module_coverage(state, ["Oncologist"])
    check_details["step2_module"] = {"passed": module_passed, "uncovered": uncovered}

    if not module_passed:
        logger.info(f"[PHASE2_CONVERGENCE]   Step 2 未通过: Oncologist未覆盖分配模块 {uncovered}")
        return {"decision": "continue", "check_details": check_details}

    logger.info("[PHASE2_CONVERGENCE]   Step 2 通过: Oncologist所有分配模块已覆盖")

    # ==================== Step 3: ConvergenceJudge Agent ====================
    logger.info("[PHASE2_CONVERGENCE] Step 3: ConvergenceJudge 评估...")

    try:
        judge = ConvergenceJudgeAgent()
        # 传递 phase="phase2" 以使用 Phase 2 特定的评估标准
        judge_result = judge.evaluate(state, phase="phase2")
        check_details["step3_judge"] = judge_result

        if judge_result["decision"] == "continue":
            logger.info("[PHASE2_CONVERGENCE]   Step 3 判断: 需要继续研究")
            return {"decision": "continue", "check_details": check_details}

        logger.info("[PHASE2_CONVERGENCE]   Step 3 判断: 研究充分")

    except Exception as e:
        logger.error(f"[PHASE2_CONVERGENCE]   Step 3 评估失败: {e}")
        check_details["step3_judge"] = {
            "decision": "converged",
            "confidence": 0.0,
            "reasoning": f"评估失败: {str(e)}，但 Step 1/2 通过，允许收敛",
            "gaps": [],
            "strengths": []
        }
        logger.info("[PHASE2_CONVERGENCE]   Step 3 失败，但 Step 1/2 通过，允许收敛")

    # ==================== 三步检查全部通过 ====================
    logger.info(f"[PHASE2_CONVERGENCE] → 收敛 (三步检查通过: {metrics_reason})")
    return {"decision": "converged", "check_details": check_details}


def phase2_convergence_check(state: MtbState) -> Literal["continue", "converged"]:
    """
    Phase 2 收敛检查 - 从 state 中读取已计算的决策

    收敛检查逻辑已移至 phase2_oncologist_node 中执行，以便记录完整的检查详情。
    此函数仅作为条件边，读取 phase2_decision 字段。
    """
    decision = state.get("phase2_decision", "continue")
    return decision


# ==================== 报告生成节点 ====================

def generate_agent_reports(state: MtbState) -> Dict[str, Any]:
    """
    根据研究结果生成各 Agent 的报告

    这个节点在研究循环结束后，将累积的证据整理成报告格式。
    包含迭代历史和收敛检查详情。
    """
    log_separator("REPORT_GEN")
    logger.info("[REPORT_GEN] 生成 Agent 报告...")

    # 显示最终证据图统计
    log_evidence_stats(state.get("evidence_graph", {}))

    graph = load_evidence_graph(state.get("evidence_graph", {}))
    iteration_history = state.get("iteration_history", [])

    # 收集各 Agent 的证据
    pathologist_evidence = graph.get_nodes_by_agent("Pathologist") if graph else []
    geneticist_evidence = graph.get_nodes_by_agent("Geneticist") if graph else []
    recruiter_evidence = graph.get_nodes_by_agent("Recruiter") if graph else []
    oncologist_evidence = graph.get_nodes_by_agent("Oncologist") if graph else []

    # 生成带迭代历史的报告
    def format_evidence_report_with_history(evidence_list, title, agent_name):
        lines = [f"## {title}", ""]

        # 添加研究进度摘要
        agent_iterations = [r for r in iteration_history
                          if agent_name in r.get("agent_findings", {})]

        if agent_iterations:
            total_evidence = sum(r["agent_findings"][agent_name]["count"]
                               for r in agent_iterations)
            lines.append(f"**研究轮次**: {len(agent_iterations)} 轮")
            lines.append(f"**证据总数**: {total_evidence} 条")
            lines.append("")

            # 每轮详情
            lines.append("### 迭代历史")
            for r in agent_iterations:
                findings = r["agent_findings"][agent_name]
                conv = r.get("convergence_check", {})
                decision = r.get("final_decision", "unknown")

                lines.append(f"- **第 {r['iteration']} 轮** ({r.get('timestamp', 'N/A')[:10]})")
                lines.append(f"  - 新增证据: {findings['count']} 条")
                lines.append(f"  - 决策: {decision}")

                # 显示 Judge 判断详情
                step3 = conv.get("step3_judge")
                if step3:
                    lines.append(f"  - Judge 置信度: {step3.get('confidence', 'N/A')}")
                    if step3.get("reasoning"):
                        lines.append(f"  - 理由: {step3['reasoning'][:100]}...")
                    if step3.get("gaps") and decision == "continue":
                        gaps_str = ", ".join(step3["gaps"][:3])
                        lines.append(f"  - 研究空白: {gaps_str}")
            lines.append("")

        # 证据内容
        lines.append("### 证据详情")
        if not evidence_list:
            lines.append("暂无相关发现。")
        else:
            for i, ev in enumerate(evidence_list, 1):
                content = ev.content.get("text", str(ev.content))
                grade = f" (证据等级: {ev.grade.value})" if ev.grade else ""
                iteration_info = f" [迭代 {ev.iteration}]" if hasattr(ev, 'iteration') and ev.iteration else ""
                lines.append(f"#### 发现 {i}{grade}{iteration_info}")
                lines.append(content)
                lines.append("")

        return "\n".join(lines)

    pathologist_report = format_evidence_report_with_history(pathologist_evidence, "病理学分析", "Pathologist")
    geneticist_report = format_evidence_report_with_history(geneticist_evidence, "分子分析", "Geneticist")
    recruiter_report = format_evidence_report_with_history(recruiter_evidence, "临床试验", "Recruiter")
    oncologist_plan = format_evidence_report_with_history(oncologist_evidence, "治疗方案", "Oncologist")

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

    logger.info(f"[REPORT_GEN] 报告生成完成: P={len(pathologist_evidence)}, G={len(geneticist_evidence)}, R={len(recruiter_evidence)}, O={len(oncologist_evidence)}")

    return {
        "pathologist_report": pathologist_report,
        "pathologist_references": extract_references(pathologist_evidence),
        "geneticist_report": geneticist_report,
        "geneticist_references": extract_references(geneticist_evidence),
        "recruiter_report": recruiter_report,
        "recruiter_trials": recruiter_trials,
        "oncologist_plan": oncologist_plan,
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

    结构：
    [entry]
        ↓
    ┌──────────────────────────────────────────┐
    │ Phase 1 Loop                              │
    │ [router] → [pathologist]                  │
    │          → [geneticist]  → [aggregator]   │
    │          → [recruiter]                    │
    │              ↓                            │
    │       [convergence_check]                 │
    │           ↓ continue  ↓ converged         │
    └───────────┘           │                   │
                            ↓
    ┌──────────────────────────────────────────┐
    │ Phase 2 Loop                              │
    │       [oncologist]                        │
    │           ↓                               │
    │   [convergence_check]                     │
    │       ↓ continue  ↓ converged             │
    └───────┘           │                       │
                        ↓
               [generate_reports]
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

    # ==================== Phase 2 节点 ====================
    workflow.add_node("phase2_oncologist", phase2_oncologist_node)

    # ==================== 报告生成节点 ====================
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

    # Phase 1 聚合器 → 收敛检查
    workflow.add_conditional_edges(
        "phase1_aggregator",
        phase1_convergence_check,
        {
            "continue": "phase1_router",  # 继续循环
            "converged": "phase2_oncologist"  # 进入 Phase 2
        }
    )

    # Phase 1 路由 → 并行节点（循环时使用）
    workflow.add_conditional_edges(
        "phase1_router",
        phase1_router,
        ["phase1_pathologist", "phase1_geneticist", "phase1_recruiter"]
    )

    # Phase 2 收敛检查
    workflow.add_conditional_edges(
        "phase2_oncologist",
        phase2_convergence_check,
        {
            "continue": "phase2_oncologist",  # 继续循环
            "converged": "generate_reports"  # 生成报告
        }
    )

    # 报告生成 → 结束
    workflow.add_edge("generate_reports", END)

    logger.info("[RESEARCH_SUBGRAPH] 子图构建完成")
    return workflow.compile()


if __name__ == "__main__":
    print("Research Subgraph 模块加载成功")
    print(f"Phase 1 最大迭代: {MAX_PHASE1_ITERATIONS}")
    print(f"Phase 2 最大迭代: {MAX_PHASE2_ITERATIONS}")
    print(f"最小证据节点: {MIN_EVIDENCE_NODES}")
    print(f"每方向最小证据: {MIN_EVIDENCE_PER_DIRECTION}")
