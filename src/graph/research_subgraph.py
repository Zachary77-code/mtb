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
from src.utils.logger import mtb_logger as logger
from config.settings import (
    MAX_PHASE1_ITERATIONS,
    MAX_PHASE2_ITERATIONS,
    MIN_EVIDENCE_NODES,
    QUESTION_COVERAGE_THRESHOLD
)


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


# ==================== Phase 1 节点 ====================

def phase1_router(state: MtbState) -> List[Send]:
    """
    Phase 1 路由：分发任务到并行 Agent

    根据研究计划将方向分配给各个 Agent。
    """
    logger.info("[PHASE1] 路由分发到并行 Agent...")

    iteration = state.get("phase1_iteration", 0)
    plan = load_research_plan(state.get("research_plan", {}))
    graph = load_evidence_graph(state.get("evidence_graph", {}))

    # 确定研究模式
    gaps = graph.get_gaps_requiring_depth() if graph else []
    mode = determine_research_mode(iteration, plan, gaps) if plan else ResearchMode.BREADTH_FIRST

    logger.info(f"[PHASE1] 迭代 {iteration + 1}/{MAX_PHASE1_ITERATIONS}, 模式: {mode.value}")

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
    logger.info(f"[PHASE1_{agent_name.upper()}] 开始研究迭代...")

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
        logger.info(f"[PHASE1_{agent_name.upper()}] 无分配方向，跳过")
        return {}

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

    logger.info(f"[PHASE1_{agent_name.upper()}] 完成, 新证据: {len(result.get('new_evidence_ids', []))}")

    return {
        "evidence_graph": result.get("evidence_graph", evidence_graph),
        f"{agent_name.lower()}_research_result": result,
    }


def phase1_aggregator(state: MtbState) -> Dict[str, Any]:
    """
    Phase 1 聚合：合并并行 Agent 的结果

    计算新发现数量，更新迭代计数。
    """
    logger.info("[PHASE1] 聚合并行结果...")

    # 计算新发现总数
    new_findings = 0
    for key in ["pathologist_research_result", "geneticist_research_result", "recruiter_research_result"]:
        result = state.get(key, {})
        new_findings += len(result.get("new_evidence_ids", []))

    # 更新迭代计数
    current_iteration = state.get("phase1_iteration", 0)

    logger.info(f"[PHASE1] 聚合完成, 本轮新发现: {new_findings}")

    return {
        "phase1_iteration": current_iteration + 1,
        "phase1_new_findings": new_findings,
    }


def phase1_convergence_check(state: MtbState) -> Literal["continue", "converged"]:
    """
    Phase 1 收敛检查

    返回 "converged" 如果满足以下任一条件：
    1. 迭代上限
    2. 研究方向全部完成
    3. 证据充分且无新发现
    4. 问题覆盖率达标
    """
    iteration = state.get("phase1_iteration", 0)
    new_findings = state.get("phase1_new_findings", 0)

    # 条件 1: 迭代上限
    if iteration >= MAX_PHASE1_ITERATIONS:
        logger.info(f"[PHASE1_CONVERGENCE] 达到迭代上限 ({MAX_PHASE1_ITERATIONS}), 收敛")
        return "converged"

    # 条件 2: 研究方向完成
    plan = load_research_plan(state.get("research_plan", {}))
    if plan:
        phase1_agents = ["Pathologist", "Geneticist", "Recruiter"]
        phase1_directions = [d for d in plan.directions if d.target_agent in phase1_agents]
        pending = [d for d in phase1_directions if d.status == DirectionStatus.PENDING]
        if not pending:
            logger.info("[PHASE1_CONVERGENCE] 所有方向完成, 收敛")
            return "converged"

    # 条件 3: 证据充分且无新发现
    graph = load_evidence_graph(state.get("evidence_graph", {}))
    if graph and len(graph) >= MIN_EVIDENCE_NODES:
        if new_findings == 0:
            logger.info(f"[PHASE1_CONVERGENCE] 证据充分 ({len(graph)}) 且无新发现, 收敛")
            return "converged"

    # 条件 4: 问题覆盖率
    if plan:
        coverage = plan.calculate_coverage()
        if coverage >= QUESTION_COVERAGE_THRESHOLD:
            logger.info(f"[PHASE1_CONVERGENCE] 问题覆盖率达标 ({coverage:.1%}), 收敛")
            return "converged"

    logger.info(f"[PHASE1_CONVERGENCE] 继续迭代 (iteration={iteration}, new_findings={new_findings})")
    return "continue"


# ==================== Phase 2 节点 ====================

def phase2_oncologist_node(state: MtbState) -> Dict[str, Any]:
    """Phase 2: 肿瘤学家研究节点"""
    logger.info("[PHASE2_ONCOLOGIST] 开始研究迭代...")

    # 获取状态
    iteration = state.get("phase2_iteration", 0)
    plan = load_research_plan(state.get("research_plan", {}))
    graph = load_evidence_graph(state.get("evidence_graph", {}))

    # 确定研究模式
    gaps = graph.get_gaps_requiring_depth() if graph else []
    mode = determine_research_mode(iteration, plan, gaps) if plan else ResearchMode.BREADTH_FIRST

    logger.info(f"[PHASE2_ONCOLOGIST] 迭代 {iteration + 1}/{MAX_PHASE2_ITERATIONS}, 模式: {mode.value}")

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
    Phase 2 收敛检查

    返回 "converged" 如果满足以下任一条件：
    1. 迭代上限
    2. Oncologist 方向全部完成
    3. 已有治疗方案
    """
    iteration = state.get("phase2_iteration", 0)
    new_findings = state.get("phase2_new_findings", 0)

    # 条件 1: 迭代上限
    if iteration >= MAX_PHASE2_ITERATIONS:
        logger.info(f"[PHASE2_CONVERGENCE] 达到迭代上限 ({MAX_PHASE2_ITERATIONS}), 收敛")
        return "converged"

    # 条件 2: 研究方向完成
    plan = load_research_plan(state.get("research_plan", {}))
    if plan:
        onc_directions = [d for d in plan.directions if d.target_agent == "Oncologist"]
        pending = [d for d in onc_directions if d.status == DirectionStatus.PENDING]
        if not pending and onc_directions:
            logger.info("[PHASE2_CONVERGENCE] 所有 Oncologist 方向完成, 收敛")
            return "converged"

    # 条件 3: 已有治疗方案证据
    graph = load_evidence_graph(state.get("evidence_graph", {}))
    if graph:
        from src.models.evidence_graph import EvidenceType
        drug_nodes = graph.get_nodes_by_type(EvidenceType.DRUG)
        guideline_nodes = graph.get_nodes_by_type(EvidenceType.GUIDELINE)
        if len(drug_nodes) >= 1 or len(guideline_nodes) >= 1:
            # 额外检查：至少迭代过一次
            if iteration >= 1:
                logger.info(f"[PHASE2_CONVERGENCE] 已有治疗方案 (drugs={len(drug_nodes)}, guidelines={len(guideline_nodes)}), 收敛")
                return "converged"

    logger.info(f"[PHASE2_CONVERGENCE] 继续迭代 (iteration={iteration}, new_findings={new_findings})")
    return "continue"


# ==================== 报告生成节点 ====================

def generate_agent_reports(state: MtbState) -> Dict[str, Any]:
    """
    根据研究结果生成各 Agent 的报告

    这个节点在研究循环结束后，将累积的证据整理成报告格式。
    """
    logger.info("[REPORT_GEN] 生成 Agent 报告...")

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
