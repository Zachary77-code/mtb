"""
MTB Subgraph with Parallel Execution

该子图实现 MTB 专家的并行执行：
- 病理学家、遗传学家、临床试验专员并行执行
- 三者完成后，肿瘤学家制定治疗方案
- 最后由主席汇总整合生成最终报告
"""
from typing import List
from langgraph.graph import StateGraph, END
from langgraph.types import Send

from src.models.state import MtbState
from src.graph.nodes import (
    pathologist_node,
    geneticist_node,
    recruiter_node,
    oncologist_node,
    chair_node
)
from src.utils.logger import mtb_logger as logger


def fan_out_to_specialists(state: MtbState) -> List[Send]:
    """
    Fan-out: 将状态发送到 3 个并行的专家节点

    Args:
        state: 当前状态

    Returns:
        发送到各专家节点的 Send 列表
    """
    logger.info("[MTB_SUBGRAPH] Fan-out: 分发到并行专家节点...")
    return [
        Send("pathologist", state),
        Send("geneticist", state),
        Send("recruiter", state),
    ]


def create_mtb_subgraph() -> StateGraph:
    """
    创建 MTB 子图

    结构：
    [entry] ──fan-out──> [pathologist]
                       > [geneticist]   ──fan-in──> [oncologist] ──> [chair] ──> [END]
                       > [recruiter]

    Returns:
        编译后的子图
    """
    workflow = StateGraph(MtbState)

    # 添加并行专家节点
    workflow.add_node("pathologist", pathologist_node)
    workflow.add_node("geneticist", geneticist_node)
    workflow.add_node("recruiter", recruiter_node)

    # 添加顺序节点
    workflow.add_node("oncologist", oncologist_node)
    workflow.add_node("chair", chair_node)

    # Fan-out: 从入口到并行节点
    workflow.add_conditional_edges(
        "__start__",
        fan_out_to_specialists,
        ["pathologist", "geneticist", "recruiter"]
    )

    # Fan-in: 所有并行节点 → oncologist
    workflow.add_edge("pathologist", "oncologist")
    workflow.add_edge("geneticist", "oncologist")
    workflow.add_edge("recruiter", "oncologist")

    # oncologist → chair
    workflow.add_edge("oncologist", "chair")

    # chair → 子图结束
    workflow.add_edge("chair", END)

    logger.info("[MTB_SUBGRAPH] 子图构建完成")
    return workflow.compile()


if __name__ == "__main__":
    print("MTB 子图模块加载成功")
    print("子图结构: [pathologist|geneticist|recruiter] → oncologist → chair")
