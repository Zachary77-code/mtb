"""
LangGraph 节点函数
"""
from typing import Dict, Any

from src.models.state import MtbState
from src.agents.pathologist import PathologistAgent
from src.agents.geneticist import GeneticistAgent
from src.agents.recruiter import RecruiterAgent
from src.agents.oncologist import OncologistAgent
from src.agents.chair import ChairAgent
from src.utils.logger import mtb_logger as logger


def case_parsing_node(state: MtbState) -> Dict[str, Any]:
    """
    病例解析节点（Pathologist）

    Args:
        state: 当前状态

    Returns:
        更新的状态字段
    """
    logger.info("[PARSE] 开始解析病例文本...")
    logger.debug(f"[PARSE] 输入文本长度: {len(state['input_text'])} 字符")

    agent = PathologistAgent()
    result = agent.parse_case(state["input_text"])

    case_keys = list(result["structured_case"].keys()) if result["structured_case"] else []
    logger.info(f"[PARSE] 完成，解析字段: {case_keys}")

    if result["parsing_errors"]:
        logger.warning(f"[PARSE] 解析警告: {result['parsing_errors']}")

    return {
        "structured_case": result["structured_case"],
        "parsing_errors": result["parsing_errors"]
    }


def geneticist_node(state: MtbState) -> Dict[str, Any]:
    """
    遗传学家节点

    Args:
        state: 当前状态

    Returns:
        更新的状态字段
    """
    logger.info("[GENETICIST] 开始分子分析...")

    agent = GeneticistAgent()
    result = agent.analyze(state["structured_case"])

    report_len = len(result["report"]) if result["report"] else 0
    ref_count = len(result["references"]) if result["references"] else 0
    logger.info(f"[GENETICIST] 完成，报告长度: {report_len} 字符，引用数: {ref_count}")

    return {
        "geneticist_report": result["report"],
        "geneticist_references": result["references"]
    }


def recruiter_node(state: MtbState) -> Dict[str, Any]:
    """
    临床试验专员节点

    Args:
        state: 当前状态

    Returns:
        更新的状态字段
    """
    logger.info("[RECRUITER] 开始搜索临床试验...")

    agent = RecruiterAgent()
    result = agent.search_trials(
        state["structured_case"],
        state.get("geneticist_report", "")
    )

    report_len = len(result["report"]) if result["report"] else 0
    trial_count = len(result["trials"]) if result["trials"] else 0
    logger.info(f"[RECRUITER] 完成，报告长度: {report_len} 字符，试验数: {trial_count}")

    return {
        "recruiter_report": result["report"],
        "recruiter_trials": result["trials"]
    }


def oncologist_node(state: MtbState) -> Dict[str, Any]:
    """
    肿瘤学家节点

    Args:
        state: 当前状态

    Returns:
        更新的状态字段
    """
    logger.info("[ONCOLOGIST] 开始制定治疗方案...")

    agent = OncologistAgent()
    result = agent.create_plan(
        state["structured_case"],
        state.get("geneticist_report", ""),
        state.get("recruiter_report", "")
    )

    plan_len = len(result["plan"]) if result["plan"] else 0
    warning_count = len(result["warnings"]) if result["warnings"] else 0
    logger.info(f"[ONCOLOGIST] 完成，方案长度: {plan_len} 字符，安全警告: {warning_count}")

    if result["warnings"]:
        logger.warning(f"[ONCOLOGIST] 安全警告: {result['warnings']}")

    return {
        "oncologist_plan": result["plan"],
        "oncologist_safety_warnings": result["warnings"]
    }


def chair_node(state: MtbState) -> Dict[str, Any]:
    """
    主席节点

    Args:
        state: 当前状态

    Returns:
        更新的状态字段
    """
    iteration = state.get("validation_iteration", 0)
    missing = state.get("missing_sections", [])

    if iteration > 0:
        logger.info(f"[CHAIR] 重新生成报告 (第 {iteration + 1} 次)，需补充模块: {missing}")
    else:
        logger.info("[CHAIR] 开始综合所有报告...")

    agent = ChairAgent()
    result = agent.synthesize(
        structured_case=state["structured_case"],
        geneticist_report=state.get("geneticist_report", ""),
        recruiter_report=state.get("recruiter_report", ""),
        oncologist_plan=state.get("oncologist_plan", ""),
        missing_sections=missing
    )

    synthesis_len = len(result["synthesis"]) if result["synthesis"] else 0
    ref_count = len(result["references"]) if result["references"] else 0
    logger.info(f"[CHAIR] 完成，综合报告长度: {synthesis_len} 字符，引用数: {ref_count}")

    return {
        "chair_synthesis": result["synthesis"],
        "chair_final_references": result["references"]
    }


def format_verification_node(state: MtbState) -> Dict[str, Any]:
    """
    格式验证节点

    Args:
        state: 当前状态

    Returns:
        更新的状态字段
    """
    logger.info("[VERIFY] 开始格式验证...")

    from src.validators.format_checker import FormatChecker

    checker = FormatChecker()
    is_compliant, missing = checker.validate(state.get("chair_synthesis", ""))

    # 更新迭代计数
    current_iteration = state.get("validation_iteration", 0)

    if is_compliant:
        logger.info("[VERIFY] 格式验证通过，包含全部 12 个必选模块")
    else:
        logger.warning(f"[VERIFY] 格式验证失败，缺失模块: {missing}")

    return {
        "is_compliant": is_compliant,
        "missing_sections": missing,
        "validation_iteration": current_iteration + 1
    }


def webpage_generator_node(state: MtbState) -> Dict[str, Any]:
    """
    HTML 生成节点

    Args:
        state: 当前状态

    Returns:
        更新的状态字段
    """
    logger.info("[HTML] 开始生成 HTML 报告...")

    from src.renderers.html_generator import HtmlReportGenerator

    generator = HtmlReportGenerator()
    output_path = generator.generate(
        structured_case=state["structured_case"],
        chair_synthesis=state.get("chair_synthesis", ""),
        references=state.get("chair_final_references", [])
    )

    logger.info(f"[HTML] 报告已保存: {output_path}")

    return {
        "output_path": output_path
    }


if __name__ == "__main__":
    print("节点函数模块加载成功")
