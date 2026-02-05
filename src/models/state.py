"""
LangGraph 状态定义
"""
from typing import TypedDict, Dict, List, Any, Annotated
from typing_extensions import NotRequired


# ==================== 并发更新合并函数 ====================

def merge_evidence_graphs(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并两个证据图（用于并行 Agent 更新）

    LangGraph 在并行节点返回相同 key 时调用此函数合并结果。

    实体中心合并策略 (DeepEvidence Style):
    - 实体按 canonical_id 合并 (observations 追加)
    - 边按 (source_id, target_id, predicate) 合并 (observations 追加)
    """
    if not left:
        return right
    if not right:
        return left

    # ========== 合并实体 (按 canonical_id) ==========
    merged_entities = dict(left.get("entities", {}))
    for cid, entity_data in right.get("entities", {}).items():
        if cid in merged_entities:
            # 已存在：合并 observations
            existing_obs = merged_entities[cid].get("observations", [])
            new_obs = entity_data.get("observations", [])
            # 按 ID 去重
            existing_obs_ids = {o.get("id") for o in existing_obs}
            for obs in new_obs:
                if obs.get("id") not in existing_obs_ids:
                    existing_obs.append(obs)
            merged_entities[cid]["observations"] = existing_obs

            # 合并 aliases
            existing_aliases = set(merged_entities[cid].get("aliases", []))
            existing_aliases.update(entity_data.get("aliases", []))
            merged_entities[cid]["aliases"] = list(existing_aliases)

            # 更新 updated_at (取较晚的)
            left_updated = merged_entities[cid].get("updated_at", "")
            right_updated = entity_data.get("updated_at", "")
            if right_updated > left_updated:
                merged_entities[cid]["updated_at"] = right_updated
        else:
            # 新实体：直接添加
            merged_entities[cid] = entity_data

    # ========== 合并边 (按 source_id|target_id|predicate) ==========
    merged_edges = dict(left.get("edges", {}))

    def make_edge_key(edge_data: Dict[str, Any]) -> str:
        return f"{edge_data.get('source_id', '')}|{edge_data.get('target_id', '')}|{edge_data.get('predicate', '')}"

    # 构建现有边的键索引
    existing_edge_keys = {make_edge_key(e): eid for eid, e in merged_edges.items()}

    for eid, edge_data in right.get("edges", {}).items():
        edge_key = make_edge_key(edge_data)

        if edge_key in existing_edge_keys:
            # 已存在：合并 observations
            existing_eid = existing_edge_keys[edge_key]
            existing_obs = merged_edges[existing_eid].get("observations", [])
            new_obs = edge_data.get("observations", [])
            existing_obs_ids = {o.get("id") for o in existing_obs}
            for obs in new_obs:
                if obs.get("id") not in existing_obs_ids:
                    existing_obs.append(obs)
            merged_edges[existing_eid]["observations"] = existing_obs

            # 更新 confidence (取较高的)
            merged_edges[existing_eid]["confidence"] = max(
                merged_edges[existing_eid].get("confidence", 0),
                edge_data.get("confidence", 0)
            )

            # 合并 conflict_group
            if edge_data.get("conflict_group"):
                merged_edges[existing_eid]["conflict_group"] = edge_data["conflict_group"]
        else:
            # 新边：直接添加
            merged_edges[eid] = edge_data
            existing_edge_keys[edge_key] = eid

    return {
        "entities": merged_entities,
        "edges": merged_edges
    }


def merge_research_plans(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并两个研究计划（用于并行 Agent 更新方向状态）

    方向按 ID 合并，right 覆盖 left 中的同 ID 方向。
    """
    if not left:
        return right
    if not right:
        return left

    merged = dict(left)
    if "directions" in right:
        left_dirs = {d["id"]: d for d in left.get("directions", [])}
        for d in right.get("directions", []):
            left_dirs[d["id"]] = d
        merged["directions"] = list(left_dirs.values())
    return merged


class MtbState(TypedDict):
    """
    MTB 工作流状态

    该状态在所有节点之间传递，包含从输入到输出的完整数据流。
    使用 NotRequired 标记可选字段，避免初始化错误。
    """

    # ==================== 输入 ====================
    input_text: str  # 原始病历文本

    # ==================== 运行 ID ====================
    run_id: NotRequired[str]  # 本次运行的唯一标识符

    # ==================== 阶段 1: PDF 解析 ====================
    raw_pdf_text: NotRequired[str]  # PDF 解析后的原始文本（完整，不截断）

    # ==================== 阶段 2: MDT 协作（并行子图） ====================
    # Pathologist 输出（病理学/影像学分析）
    pathologist_report: NotRequired[str]  # Markdown 格式的病理分析报告
    pathologist_references: NotRequired[List[Dict[str, str]]]  # 病理引用列表

    # Geneticist 输出
    geneticist_report: NotRequired[str]  # Markdown 格式的变异分析报告
    geneticist_references: NotRequired[List[Dict[str, str]]]  # 引用列表

    # Recruiter 输出
    recruiter_report: NotRequired[str]  # Markdown 格式的试验推荐报告
    recruiter_trials: NotRequired[List[Dict[str, Any]]]  # 试验详情列表

    # Oncologist 输出
    oncologist_plan: NotRequired[str]  # Markdown 格式的治疗方案
    oncologist_safety_warnings: NotRequired[List[str]]  # 安全警告列表

    # Chair 输出
    chair_synthesis: NotRequired[str]  # Markdown 格式的最终综合报告（含完整证据引用列表）

    # ==================== 阶段 3: 格式验证 ====================
    is_compliant: NotRequired[bool]  # 是否通过格式验证
    missing_sections: NotRequired[List[str]]  # 缺失的模块列表
    validation_iteration: NotRequired[int]  # 验证重试次数（防止无限循环）

    # ==================== 阶段 4: 输出 ====================
    run_folder: NotRequired[str]  # 本次运行的报告文件夹路径
    final_html: NotRequired[str]  # 生成的 HTML 内容
    output_path: NotRequired[str]  # HTML 文件保存路径

    # ==================== 元数据 ====================
    workflow_errors: NotRequired[List[str]]  # 工作流错误列表
    execution_time: NotRequired[float]  # 执行时间（秒）

    # ==================== DeepEvidence 研究循环 ====================
    # 研究计划（PlanAgent 生成）
    # 使用 Annotated + reducer 支持并行 Agent 更新
    research_plan: NotRequired[Annotated[Dict[str, Any], merge_research_plans]]
    research_mode: NotRequired[str]  # "breadth_first" | "depth_first"

    # 全局证据图
    # 使用 Annotated + reducer 支持并行 Agent 更新
    evidence_graph: NotRequired[Annotated[Dict[str, Any], merge_evidence_graphs]]

    # Phase 1 迭代控制（Pathologist + Geneticist + Recruiter）
    phase1_iteration: NotRequired[int]  # 当前迭代轮次
    phase1_new_findings: NotRequired[int]  # 本轮新发现数量

    # Phase 2 迭代控制（Oncologist）
    phase2_iteration: NotRequired[int]  # 当前迭代轮次
    phase2_new_findings: NotRequired[int]  # 本轮新发现数量

    # 收敛标志
    research_converged: NotRequired[bool]  # 研究是否已收敛

    # Phase 1 Agent 收敛状态（分别判断）
    pathologist_converged: NotRequired[bool]  # Pathologist 是否收敛
    geneticist_converged: NotRequired[bool]   # Geneticist 是否收敛
    recruiter_converged: NotRequired[bool]    # Recruiter 是否收敛
    phase1_all_converged: NotRequired[bool]   # Phase 1 所有 Agent 是否都收敛

    # Phase 1 Agent 研究结果（用于迭代间传递，供 aggregator 读取）
    pathologist_research_result: NotRequired[Dict[str, Any]]
    geneticist_research_result: NotRequired[Dict[str, Any]]
    recruiter_research_result: NotRequired[Dict[str, Any]]

    # Phase 2 Agent 研究结果
    oncologist_research_result: NotRequired[Dict[str, Any]]

    # Phase 1/2 Agent 收敛检查详情（已废弃，由 PlanAgent 统一处理）
    pathologist_convergence_details: NotRequired[Dict[str, Any]]
    geneticist_convergence_details: NotRequired[Dict[str, Any]]
    recruiter_convergence_details: NotRequired[Dict[str, Any]]
    oncologist_convergence_details: NotRequired[Dict[str, Any]]

    # 收敛检查决策（供条件边使用，由 PlanAgent 设置）
    phase1_decision: NotRequired[str]  # "continue" | "converged"
    phase2_decision: NotRequired[str]  # "continue" | "converged"

    # PlanAgent 评估结果（每轮迭代更新）
    plan_agent_evaluation: NotRequired[Dict[str, Any]]
    # 结构: {
    #     "phase": "phase1" | "phase2",
    #     "iteration": int,
    #     "reasoning": str,              # 决策理由
    #     "quality_assessment": {        # 证据质量评估
    #         "high_quality_coverage": ["模块1"],  # 有 A/B 级证据的模块
    #         "low_quality_only": ["模块2"],       # 只有 D/E 级证据的模块
    #         "conflicts": []                      # 证据冲突
    #     },
    #     "gaps": List[str],             # 待填补空白
    #     "next_priorities": List[str]   # 下一轮优先事项
    # }

    # 迭代历史记录（用于追溯研究进度）
    iteration_history: NotRequired[List[Dict[str, Any]]]
    # 结构: [
    #   {
    #     "phase": "PHASE1" | "PHASE2",
    #     "iteration": 1,
    #     "timestamp": "2024-01-23T10:30:00",
    #     "agent_findings": {
    #       "Pathologist": {"count": 5, "entity_ids": [...]},
    #       ...
    #     },
    #     "total_new_findings": 12,
    #     "convergence_check": {...},  # PlanAgent 评估结果
    #     "final_decision": "continue" | "converged"
    #   }
    # ]

    # 研究进度报告（Markdown 格式）
    research_progress_report: NotRequired[str]

    # 假设验证历史（跨迭代累积，由 aggregator 收集）
    # 结构: {
    #     "Pathologist": [
    #         {"iteration": 1, "direction_id": "D1", "hypothesis": "...",
    #          "validation_tool": "...", "result": "validated|refuted|inconclusive", "detail": "..."},
    #     ],
    #     "Geneticist": [...],
    #     ...
    # }
    hypotheses_history: NotRequired[Dict[str, List[Dict[str, Any]]]]


# ==================== 辅助函数 ====================
def create_initial_state(input_text: str) -> MtbState:
    """
    创建初始状态

    Args:
        input_text: 原始病历文本

    Returns:
        初始化的 MtbState
    """
    return {
        "input_text": input_text,
        "raw_pdf_text": "",  # PDF 解析后填充
        "pathologist_report": "",  # 病理分析报告
        "pathologist_references": [],  # 病理引用
        "validation_iteration": 0,
        "workflow_errors": [],
        # DeepEvidence 研究循环初始化
        "research_plan": {},
        "research_mode": "breadth_first",
        "evidence_graph": {"entities": {}, "edges": {}},
        "phase1_iteration": 0,
        "phase1_new_findings": 0,
        "phase2_iteration": 0,
        "phase2_new_findings": 0,
        "research_converged": False,
        "iteration_history": [],  # 迭代历史记录
        # Phase 1 Agent 收敛状态初始化
        "pathologist_converged": False,
        "geneticist_converged": False,
        "recruiter_converged": False,
        "phase1_all_converged": False,
        "phase1_decision": "continue",
        "phase2_decision": "continue",
    }


def is_state_valid(state: MtbState) -> bool:
    """
    检查状态是否有效（包含必需的字段）

    Args:
        state: MTB 状态

    Returns:
        是否有效
    """
    # 检查必需字段
    if "input_text" not in state or not state["input_text"]:
        return False

    return True


if __name__ == "__main__":
    # 测试状态创建
    test_state = create_initial_state("测试病历文本")
    print("初始状态创建成功:")
    print(f"  - input_text: {test_state['input_text'][:20]}...")
    print(f"  - validation_iteration: {test_state.get('validation_iteration', 0)}")
    print(f"  - 状态有效: {is_state_valid(test_state)}")
