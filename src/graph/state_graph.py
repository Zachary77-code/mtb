"""
LangGraph 主工作流定义

新架构：
1. PDF 解析节点（提取原始文本，不结构化）
2. MTB 子图（并行执行 + 汇总）
   - 并行：pathologist, geneticist, recruiter
   - 顺序：oncologist → chair
3. 格式验证（失败时回到 chair 重试）
4. HTML 生成
"""
from langgraph.graph import StateGraph, END

from src.models.state import MtbState
from src.graph.nodes import (
    pdf_parser_node,
    format_verification_node,
    webpage_generator_node,
    chair_node
)
from src.graph.mtb_subgraph import create_mtb_subgraph
from src.graph.edges import should_retry_chair


def create_mtb_workflow():
    """
    创建 MTB 工作流

    工作流拓扑:
    [开始]
      ↓
    [PDF Parser] - 提取原始文本
      ↓
    [MTB Subgraph] ─────────────────────────────────┐
      │  ┌─────────────┐  ┌─────────────┐  ┌──────────┐
      │  │ pathologist │  │ geneticist  │  │ recruiter│  (并行)
      │  └──────┬──────┘  └──────┬──────┘  └────┬─────┘
      │         └─────────────────┼──────────────┘
      │                           ↓
      │                    [oncologist]
      │                           ↓
      │                      [chair]
      └─────────────────────────────────────────────┘
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

    # 阶段 1: PDF 解析（提取原始文本，不结构化）
    workflow.add_node("pdf_parser", pdf_parser_node)

    # 阶段 2: MTB 分析（并行子图）
    mtb_subgraph = create_mtb_subgraph()
    workflow.add_node("mtb_analysis", mtb_subgraph)

    # 阶段 3: 格式验证
    workflow.add_node("verify_format", format_verification_node)

    # 阶段 3.5: Chair 重试节点（验证失败时使用）
    workflow.add_node("chair_retry", chair_node)

    # 阶段 4: HTML 生成
    workflow.add_node("generate_html", webpage_generator_node)

    # ==================== 设置边 ====================

    # 入口点
    workflow.set_entry_point("pdf_parser")

    # PDF 解析 → MTB 子图
    workflow.add_edge("pdf_parser", "mtb_analysis")

    # MTB 子图 → 格式验证
    workflow.add_edge("mtb_analysis", "verify_format")

    # 条件边: 验证结果决定下一步
    workflow.add_conditional_edges(
        "verify_format",
        should_retry_chair,
        {
            "regenerate": "chair_retry",  # 回到 Chair 重新生成
            "proceed": "generate_html"    # 继续到 HTML 生成
        }
    )

    # Chair 重试 → 格式验证
    workflow.add_edge("chair_retry", "verify_format")

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
    print("新架构: PDF Parser → [Pathologist|Geneticist|Recruiter] → Oncologist → Chair → Verify → HTML")

    # 测试工作流创建
    try:
        workflow = create_mtb_workflow()
        print("工作流编译成功")
        print(f"节点: {workflow.nodes.keys() if hasattr(workflow, 'nodes') else 'N/A'}")
    except Exception as e:
        print(f"工作流创建失败: {e}")
