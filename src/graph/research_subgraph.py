"""
Research Subgraph - 两阶段研究循环子图

实现 DeepEvidence 风格的研究循环：
- Phase 1: Pathologist + Geneticist + Recruiter 并行 BFRS/DFRS 循环
- Phase 2: Oncologist 独立 BFRS/DFRS 循环
- 动态收敛检查
"""
from typing import List, Literal, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.types import Send

from src.models.state import MtbState
from src.models.evidence_graph import load_evidence_graph, EvidenceGraph
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
    log_evidence_stats,
    log_convergence_status
)
from config.settings import (
    MAX_PHASE1_ITERATIONS,
    MAX_PHASE2_ITERATIONS,
    MIN_EVIDENCE_NODES,
    QUESTION_COVERAGE_THRESHOLD,
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


# ==================== Phase 1 节点 ====================

def phase1_router(state: MtbState) -> List[Send]:
    """
    Phase 1 路由：分发任务到并行 Agent

    根据研究计划将方向分配给各个 Agent。
    """
    iteration = state.get("phase1_iteration", 0)
    plan = load_research_plan(state.get("research_plan", {}))
    graph = load_evidence_graph(state.get("evidence_graph", {}))

    # 确定研究模式
    gaps = graph.get_gaps_requiring_depth() if graph else []
    mode = determine_research_mode(iteration, plan, gaps) if plan else ResearchMode.BREADTH_FIRST

    # 增强日志输出
    log_separator("PHASE1")
    logger.info(f"[PHASE1] 迭代 {iteration + 1}/{MAX_PHASE1_ITERATIONS}")
    logger.info(f"[PHASE1] 研究模式: {mode.value}")
    logger.info(f"[PHASE1] 分发到: Pathologist, Geneticist, Recruiter")

    # 显示当前证据图状态
    if graph and len(graph) > 0:
        log_evidence_stats(state.get("evidence_graph", {}))

    # 更新状态中的模式
    updated_state = dict(state)
    updated_state["research_mode"] = mode.value

    return [
        Send("phase1_pathologist", updated_state),
        Send("phase1_geneticist", updated_state),
        Send("phase1_recruiter", updated_state),
    ]


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
    """执行 Phase 1 Agent 的研究迭代"""
    tag = f"PHASE1_{agent_name.upper()}"
    logger.info(f"[{tag}] ───────────────────────────────────────")

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
        logger.info(f"[{tag}] 无分配方向，跳过")
        return {}

    # 显示分配的方向
    logger.info(f"[{tag}] 分配方向: {len(directions)} 个")
    for d in directions:
        status_icon = "✓" if d.get("status") == "completed" else "○"
        logger.info(f"[{tag}]   {status_icon} {d.get('topic', '未命名')} (优先级: {d.get('priority', '-')})")

    # 创建 Agent 并执行研究
    agent = agent_class()
    result = agent.research_iterate(
        mode=mode,
        directions=directions,
        evidence_graph=evidence_graph,
        iteration=iteration,
        max_iterations=MAX_PHASE1_ITERATIONS,
        case_context=raw_pdf_text[:3000]
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

    return {
        "evidence_graph": result.get("evidence_graph", evidence_graph),
        f"{agent_name.lower()}_research_result": result,
    }


def phase1_aggregator(state: MtbState) -> Dict[str, Any]:
    """
    Phase 1 聚合：合并并行 Agent 的结果

    计算新发现数量，更新迭代计数。
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
    for agent_name, result in agent_results.items():
        count = len(result.get("new_evidence_ids", []))
        new_findings += count
        logger.info(f"[PHASE1]   {agent_name}: {count} 条新证据")

    logger.info(f"[PHASE1]   本轮总计: {new_findings}")

    # 显示证据图统计
    log_evidence_stats(state.get("evidence_graph", {}))

    # 更新迭代计数
    current_iteration = state.get("phase1_iteration", 0)

    return {
        "phase1_iteration": current_iteration + 1,
        "phase1_new_findings": new_findings,
    }


def phase1_convergence_check(state: MtbState) -> Literal["continue", "converged"]:
    """
    Phase 1 收敛检查 - 三步收敛流程

    Step 1: Metric-based Fast Check
        - 迭代上限 / 方向完成 / 证据饱和 / 问题覆盖率
    Step 2: Module Coverage Check
        - 9 个必需模块是否有研究方向覆盖
    Step 3: ConvergenceJudge Agent
        - LLM 评估研究质量

    如果达到迭代上限，无论其他条件如何都会收敛（带警告）
    """
    iteration = state.get("phase1_iteration", 0)
    new_findings = state.get("phase1_new_findings", 0)

    # 收集检查信息
    plan = load_research_plan(state.get("research_plan", {}))
    graph = load_evidence_graph(state.get("evidence_graph", {}))

    # 计算待完成方向数
    pending_count = 0
    if plan:
        phase1_agents = ["Pathologist", "Geneticist", "Recruiter"]
        phase1_directions = [d for d in plan.directions if d.target_agent in phase1_agents]
        pending = [d for d in phase1_directions if d.status == DirectionStatus.PENDING]
        pending_count = len(pending)

    # 计算问题覆盖率
    coverage = plan.calculate_coverage() if plan else 0.0
    evidence_count = len(graph) if graph else 0

    # ==================== 迭代上限检查（优先） ====================
    if iteration >= MAX_PHASE1_ITERATIONS:
        # 检查模块覆盖，记录警告
        module_passed, uncovered = check_module_coverage(state)
        if not module_passed:
            logger.warning(f"[PHASE1_CONVERGENCE] 达到迭代上限，以下模块可能证据不足: {uncovered}")
        log_convergence_status("PHASE1", iteration, MAX_PHASE1_ITERATIONS,
                               pending_count, evidence_count, new_findings, coverage, "converged")
        logger.info("[PHASE1_CONVERGENCE]   原因: 达到迭代上限")
        return "converged"

    # ==================== Step 1: Metric-based Fast Check ====================
    logger.info("[PHASE1_CONVERGENCE] Step 1: Metric-based 检查...")

    metrics_passed = False
    metrics_reason = ""

    # 条件 1: 研究方向完成
    if plan and pending_count == 0:
        metrics_passed = True
        metrics_reason = "所有方向完成"

    # 条件 2: 证据充分且无新发现
    elif graph and evidence_count >= MIN_EVIDENCE_NODES and new_findings == 0:
        metrics_passed = True
        metrics_reason = f"证据充分 ({evidence_count}) 且无新发现"

    # 条件 3: 问题覆盖率达标
    elif plan and coverage >= QUESTION_COVERAGE_THRESHOLD:
        metrics_passed = True
        metrics_reason = f"问题覆盖率达标 ({coverage:.1%})"

    if not metrics_passed:
        log_convergence_status("PHASE1", iteration, MAX_PHASE1_ITERATIONS,
                               pending_count, evidence_count, new_findings, coverage, "continue")
        logger.info("[PHASE1_CONVERGENCE]   Step 1 未通过，继续迭代")
        return "continue"

    logger.info(f"[PHASE1_CONVERGENCE]   Step 1 通过: {metrics_reason}")

    # ==================== Step 2: Module Coverage Check ====================
    logger.info("[PHASE1_CONVERGENCE] Step 2: Module Coverage 检查...")

    module_passed, uncovered = check_module_coverage(state)
    if not module_passed:
        log_convergence_status("PHASE1", iteration, MAX_PHASE1_ITERATIONS,
                               pending_count, evidence_count, new_findings, coverage, "continue")
        logger.info(f"[PHASE1_CONVERGENCE]   Step 2 未通过: 未覆盖模块 {uncovered}")
        return "continue"

    logger.info("[PHASE1_CONVERGENCE]   Step 2 通过: 所有模块已覆盖")

    # ==================== Step 3: ConvergenceJudge Agent ====================
    logger.info("[PHASE1_CONVERGENCE] Step 3: ConvergenceJudge 评估...")

    try:
        judge = ConvergenceJudgeAgent()
        decision = judge.evaluate(state)

        if decision == "continue":
            log_convergence_status("PHASE1", iteration, MAX_PHASE1_ITERATIONS,
                                   pending_count, evidence_count, new_findings, coverage, "continue")
            logger.info("[PHASE1_CONVERGENCE]   Step 3 判断: 需要继续研究")
            return "continue"

        logger.info("[PHASE1_CONVERGENCE]   Step 3 判断: 研究充分")

    except Exception as e:
        logger.error(f"[PHASE1_CONVERGENCE]   Step 3 评估失败: {e}")
        # 评估失败时，如果 Step 1 和 Step 2 都通过，允许收敛
        logger.info("[PHASE1_CONVERGENCE]   Step 3 失败，但 Step 1/2 通过，允许收敛")

    # ==================== 三步检查全部通过 ====================
    log_convergence_status("PHASE1", iteration, MAX_PHASE1_ITERATIONS,
                           pending_count, evidence_count, new_findings, coverage, "converged")
    logger.info(f"[PHASE1_CONVERGENCE] → 收敛 (三步检查通过: {metrics_reason})")
    return "converged"


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
        case_context=context
    )

    # 更新迭代计数
    new_findings = len(result.get("new_evidence_ids", []))

    logger.info(f"[PHASE2_ONCOLOGIST] 完成, 新证据: {new_findings}")

    return {
        "evidence_graph": result.get("evidence_graph", state.get("evidence_graph", {})),
        "oncologist_research_result": result,
        "phase2_iteration": iteration + 1,
        "phase2_new_findings": new_findings,
    }


def phase2_convergence_check(state: MtbState) -> Literal["continue", "converged"]:
    """
    Phase 2 收敛检查 - 三步收敛流程

    Step 1: Metric-based Fast Check
        - 迭代上限 / 方向完成 / 治疗方案证据
    Step 2: Module Coverage Check
        - 9 个必需模块是否有研究方向覆盖
    Step 3: ConvergenceJudge Agent
        - LLM 评估研究质量

    如果达到迭代上限，无论其他条件如何都会收敛（带警告）
    """
    iteration = state.get("phase2_iteration", 0)
    new_findings = state.get("phase2_new_findings", 0)

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

    # 显示检查状态
    logger.info("[PHASE2_CONVERGENCE] 检查收敛条件...")
    logger.info(f"[PHASE2_CONVERGENCE]   迭代: {iteration}/{MAX_PHASE2_ITERATIONS}")
    logger.info(f"[PHASE2_CONVERGENCE]   待完成方向: {pending_count}")
    logger.info(f"[PHASE2_CONVERGENCE]   证据节点: {evidence_count}")
    logger.info(f"[PHASE2_CONVERGENCE]   本轮新发现: {new_findings}")
    logger.info(f"[PHASE2_CONVERGENCE]   治疗证据: 药物={drug_count}, 指南={guideline_count}")

    # ==================== 迭代上限检查（优先） ====================
    if iteration >= MAX_PHASE2_ITERATIONS:
        # 检查模块覆盖，记录警告
        module_passed, uncovered = check_module_coverage(state)
        if not module_passed:
            logger.warning(f"[PHASE2_CONVERGENCE] 达到迭代上限，以下模块可能证据不足: {uncovered}")
        logger.info("[PHASE2_CONVERGENCE] → 收敛 (原因: 达到迭代上限)")
        return "converged"

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

    if not metrics_passed:
        logger.info("[PHASE2_CONVERGENCE]   Step 1 未通过，继续迭代")
        return "continue"

    logger.info(f"[PHASE2_CONVERGENCE]   Step 1 通过: {metrics_reason}")

    # ==================== Step 2: Module Coverage Check ====================
    logger.info("[PHASE2_CONVERGENCE] Step 2: Module Coverage 检查...")

    module_passed, uncovered = check_module_coverage(state)
    if not module_passed:
        logger.info(f"[PHASE2_CONVERGENCE]   Step 2 未通过: 未覆盖模块 {uncovered}")
        return "continue"

    logger.info("[PHASE2_CONVERGENCE]   Step 2 通过: 所有模块已覆盖")

    # ==================== Step 3: ConvergenceJudge Agent ====================
    logger.info("[PHASE2_CONVERGENCE] Step 3: ConvergenceJudge 评估...")

    try:
        judge = ConvergenceJudgeAgent()
        decision = judge.evaluate(state)

        if decision == "continue":
            logger.info("[PHASE2_CONVERGENCE]   Step 3 判断: 需要继续研究")
            return "continue"

        logger.info("[PHASE2_CONVERGENCE]   Step 3 判断: 研究充分")

    except Exception as e:
        logger.error(f"[PHASE2_CONVERGENCE]   Step 3 评估失败: {e}")
        # 评估失败时，如果 Step 1 和 Step 2 都通过，允许收敛
        logger.info("[PHASE2_CONVERGENCE]   Step 3 失败，但 Step 1/2 通过，允许收敛")

    # ==================== 三步检查全部通过 ====================
    logger.info(f"[PHASE2_CONVERGENCE] → 收敛 (三步检查通过: {metrics_reason})")
    return "converged"


# ==================== 报告生成节点 ====================

def generate_agent_reports(state: MtbState) -> Dict[str, Any]:
    """
    根据研究结果生成各 Agent 的报告

    这个节点在研究循环结束后，将累积的证据整理成报告格式。
    """
    log_separator("REPORT_GEN")
    logger.info("[REPORT_GEN] 生成 Agent 报告...")

    # 显示最终证据图统计
    log_evidence_stats(state.get("evidence_graph", {}))

    graph = load_evidence_graph(state.get("evidence_graph", {}))

    # 收集各 Agent 的证据
    pathologist_evidence = graph.get_nodes_by_agent("Pathologist") if graph else []
    geneticist_evidence = graph.get_nodes_by_agent("Geneticist") if graph else []
    recruiter_evidence = graph.get_nodes_by_agent("Recruiter") if graph else []
    oncologist_evidence = graph.get_nodes_by_agent("Oncologist") if graph else []

    # 生成报告
    def format_evidence_report(evidence_list, title):
        if not evidence_list:
            return f"## {title}\n\n暂无相关发现。"

        lines = [f"## {title}", ""]
        for i, ev in enumerate(evidence_list, 1):
            content = ev.content.get("text", str(ev.content))
            grade = f" (证据等级: {ev.grade.value})" if ev.grade else ""
            lines.append(f"### 发现 {i}{grade}")
            lines.append(content)
            lines.append("")
        return "\n".join(lines)

    pathologist_report = format_evidence_report(pathologist_evidence, "病理学分析")
    geneticist_report = format_evidence_report(geneticist_evidence, "分子分析")
    recruiter_report = format_evidence_report(recruiter_evidence, "临床试验")

    # 提取试验信息
    recruiter_trials = []
    for ev in recruiter_evidence:
        if ev.evidence_type.value == "trial":
            trial_data = ev.content.get("raw", {})
            if trial_data:
                recruiter_trials.append(trial_data)

    # Oncologist 报告作为治疗方案
    oncologist_plan = format_evidence_report(oncologist_evidence, "治疗方案")
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
    }


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
    print(f"问题覆盖阈值: {QUESTION_COVERAGE_THRESHOLD}")
