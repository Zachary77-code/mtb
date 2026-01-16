"""
LangGraph 条件边逻辑
"""
from typing import Literal

from src.models.state import MtbState
from config.settings import MAX_RETRY_ITERATIONS
from src.utils.logger import mtb_logger as logger


def should_retry_chair(state: MtbState) -> Literal["regenerate", "proceed"]:
    """
    判断是否需要重新生成报告

    Args:
        state: 当前状态

    Returns:
        "regenerate": 回到 Chair 重新生成
        "proceed": 继续到 HTML 生成
    """
    is_compliant = state.get("is_compliant", False)
    iteration = state.get("validation_iteration", 0)
    missing = state.get("missing_sections", [])

    logger.info(f"[EDGE] 条件判断: compliant={is_compliant}, iteration={iteration}/{MAX_RETRY_ITERATIONS}")

    # 如果验证通过，继续
    if is_compliant:
        logger.info("[EDGE] 决策: proceed (验证通过)")
        return "proceed"

    # 检查重试次数
    if iteration >= MAX_RETRY_ITERATIONS:
        # 超过重试次数，强制继续（带警告）
        logger.warning(f"[EDGE] 决策: proceed (已达最大重试次数 {iteration}，缺失: {missing})")
        errors = state.get("workflow_errors", [])
        errors.append(
            f"格式验证失败但已达最大重试次数({iteration})，强制生成报告。"
            f"缺失模块: {missing}"
        )
        return "proceed"

    # 需要重新生成
    logger.info(f"[EDGE] 决策: regenerate (缺失模块: {missing})")
    return "regenerate"


def check_parsing_success(state: MtbState) -> Literal["success", "error"]:
    """
    检查病例解析是否成功

    Args:
        state: 当前状态

    Returns:
        "success": 解析成功
        "error": 解析失败
    """
    if state.get("structured_case") is None:
        logger.error("[EDGE] 病例解析失败: structured_case 为空")
        return "error"

    # 检查是否有关键数据
    case = state["structured_case"]
    if not case.get("primary_cancer") or case.get("primary_cancer") == "未提取":
        logger.error("[EDGE] 病例解析失败: primary_cancer 未提取")
        return "error"

    logger.info("[EDGE] 病例解析检查通过")
    return "success"


if __name__ == "__main__":
    print("条件边模块加载成功")
