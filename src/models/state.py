"""
LangGraph 状态定义
"""
from typing import TypedDict, Dict, List, Any
from typing_extensions import NotRequired


class MtbState(TypedDict):
    """
    MTB 工作流状态

    该状态在所有节点之间传递，包含从输入到输出的完整数据流。
    使用 NotRequired 标记可选字段，避免初始化错误。
    """

    # ==================== 输入 ====================
    input_text: str  # 原始病历文本

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
    chair_synthesis: NotRequired[str]  # Markdown 格式的最终综合报告
    chair_final_references: NotRequired[List[Dict[str, str]]]  # 最终引用列表

    # ==================== 阶段 3: 格式验证 ====================
    is_compliant: NotRequired[bool]  # 是否通过格式验证
    missing_sections: NotRequired[List[str]]  # 缺失的模块列表
    validation_iteration: NotRequired[int]  # 验证重试次数（防止无限循环）

    # ==================== 阶段 4: 输出 ====================
    final_html: NotRequired[str]  # 生成的 HTML 内容
    output_path: NotRequired[str]  # HTML 文件保存路径

    # ==================== 元数据 ====================
    workflow_errors: NotRequired[List[str]]  # 工作流错误列表
    execution_time: NotRequired[float]  # 执行时间（秒）


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
