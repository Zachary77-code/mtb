"""
LangGraph 主工作流定义
"""
from langgraph.graph import StateGraph, END

from src.models.state import MtbState
from src.graph.nodes import (
    case_parsing_node,
    geneticist_node,
    recruiter_node,
    oncologist_node,
    chair_node,
    format_verification_node,
    webpage_generator_node
)
from src.graph.edges import should_retry_chair


def create_mtb_workflow():
    """
    创建 MTB 工作流

    工作流拓扑:
    [开始]
      ↓
    [Case Parsing] (Pathologist)
      ↓
    [MDT Collaboration]
      ├─ Geneticist → Recruiter → Oncologist → Chair
      ↓
    [Format Verification]
      ├─ 通过 → [HTML Generator] → [结束]
      └─ 失败 → 回到 Chair（最多 2 次重试）

    Returns:
        编译后的工作流
    """
    # 创建状态图
    workflow = StateGraph(MtbState)

    # ==================== 添加节点 ====================

    # 阶段 1: 病例解析
    workflow.add_node("parse_case", case_parsing_node)

    # 阶段 2: MDT 协作（顺序执行）
    workflow.add_node("geneticist", geneticist_node)
    workflow.add_node("recruiter", recruiter_node)
    workflow.add_node("oncologist", oncologist_node)
    workflow.add_node("chair", chair_node)

    # 阶段 3: 格式验证
    workflow.add_node("verify_format", format_verification_node)

    # 阶段 4: HTML 生成
    workflow.add_node("generate_html", webpage_generator_node)

    # ==================== 设置边 ====================

    # 入口点
    workflow.set_entry_point("parse_case")

    # 线性流程: 解析 → MDT 协作
    workflow.add_edge("parse_case", "geneticist")
    workflow.add_edge("geneticist", "recruiter")
    workflow.add_edge("recruiter", "oncologist")
    workflow.add_edge("oncologist", "chair")
    workflow.add_edge("chair", "verify_format")

    # 条件边: 验证结果决定下一步
    workflow.add_conditional_edges(
        "verify_format",
        should_retry_chair,
        {
            "regenerate": "chair",  # 回到 Chair 重新生成
            "proceed": "generate_html"  # 继续到 HTML 生成
        }
    )

    # 终点
    workflow.add_edge("generate_html", END)

    # 编译并返回
    return workflow.compile()


def run_mtb_workflow(input_text: str) -> MtbState:
    """
    运行 MTB 工作流

    Args:
        input_text: 原始病历文本

    Returns:
        最终状态
    """
    from src.models.state import create_initial_state
    import time

    # 创建初始状态
    initial_state = create_initial_state(input_text)

    # 创建工作流
    workflow = create_mtb_workflow()

    # 记录开始时间
    start_time = time.time()

    # 执行工作流
    final_state = workflow.invoke(initial_state)

    # 记录执行时间
    final_state["execution_time"] = time.time() - start_time

    return final_state


if __name__ == "__main__":
    print("MTB 工作流模块加载成功")

    # 测试工作流创建
    try:
        workflow = create_mtb_workflow()
        print("工作流编译成功")
        print(f"节点: {workflow.nodes.keys() if hasattr(workflow, 'nodes') else 'N/A'}")
    except Exception as e:
        print(f"工作流创建失败: {e}")
