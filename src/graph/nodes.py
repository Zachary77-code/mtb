"""
LangGraph 节点函数
"""
import json
from typing import Dict, Any

from src.models.state import MtbState
from src.agents.pathologist import PathologistAgent
from src.agents.geneticist import GeneticistAgent
from src.agents.recruiter import RecruiterAgent
from src.agents.oncologist import OncologistAgent
from src.agents.chair import ChairAgent
from src.utils.logger import mtb_logger as logger


def _print_section(title: str, content: str, max_len: int = 3000):
    """打印格式化的节内容（处理 Windows 编码问题）"""
    # 替换 Windows GBK 无法显示的 Unicode 符号
    safe_content = content.replace("✓", "[OK]").replace("✗", "[X]").replace("✅", "[PASS]").replace("❌", "[FAIL]").replace("⚠️", "[!]").replace("⚠", "[!]")
    safe_title = title.replace("✓", "[OK]").replace("✗", "[X]").replace("✅", "[PASS]").replace("❌", "[FAIL]").replace("⚠️", "[!]").replace("⚠", "[!]")

    try:
        print("\n" + "=" * 70)
        print(f"  {safe_title}")
        print("-" * 70)
        if len(safe_content) > max_len:
            print(safe_content[:max_len])
            print(f"\n... [截断，共 {len(content)} 字符]")
        else:
            print(safe_content)
        print("=" * 70)
    except UnicodeEncodeError:
        # 如果仍有编码问题，使用 ASCII 安全模式
        print("\n" + "=" * 70)
        print(f"  {safe_title}")
        print("-" * 70)
        print(safe_content[:max_len].encode('ascii', 'replace').decode('ascii'))
        print("=" * 70)


def case_parsing_node(state: MtbState) -> Dict[str, Any]:
    """
    病例解析节点（Pathologist）

    Args:
        state: 当前状态

    Returns:
        更新的状态字段
    """
    logger.info("[PARSE] 开始解析病例文本...")

    # 打印输入
    _print_section("[PATHOLOGIST] 输入 - 原始病例文本", state["input_text"])

    agent = PathologistAgent()
    result = agent.parse_case(state["input_text"])

    case_keys = list(result["structured_case"].keys()) if result["structured_case"] else []
    logger.info(f"[PARSE] 完成，解析字段: {case_keys}")

    # 打印输出
    case = result["structured_case"]

    # 格式化免疫组化标记物
    ihc_markers = case.get('ihc_markers', [])
    ihc_str = ""
    if ihc_markers:
        ihc_items = [f"  - {m.get('marker', 'N/A')}: {m.get('result', 'N/A')}" for m in ihc_markers]
        ihc_str = "\n".join(ihc_items)
    else:
        ihc_str = "  无"

    # 格式化肿瘤标志物
    tumor_markers = case.get('tumor_markers', {})
    markers_str = ""
    if tumor_markers:
        markers_items = [f"  - {k}: {v}" for k, v in tumor_markers.items()]
        markers_str = "\n".join(markers_items)
    else:
        markers_str = "  无"

    # 格式化治疗史
    treatment_lines = case.get('treatment_lines', [])
    treatment_str = ""
    if treatment_lines:
        for t in treatment_lines:
            line_num = t.get('line_number', '?')
            regimen = t.get('regimen', 'N/A')
            start = t.get('start_date', '')
            end = t.get('end_date', '')
            time_range = f"{start}-{end}" if start else ""
            response = t.get('best_response', '-')
            notes = t.get('notes', '')
            treatment_str += f"  [{line_num}线] {regimen}"
            if time_range:
                treatment_str += f" ({time_range})"
            if response:
                treatment_str += f" -> {response}"
            if notes:
                treatment_str += f" | {notes}"
            treatment_str += "\n"
    else:
        treatment_str = "  无\n"

    # 格式化合并症
    comorbidities = case.get('comorbidities', [])
    comorbidities_str = ", ".join(comorbidities) if comorbidities else "无"

    # 格式化器官功能
    organ = case.get('organ_function', {})
    organ_str = f"ECOG PS: {organ.get('ecog_ps', 'N/A')}"
    if organ.get('creatinine'):
        organ_str += f" | 肌酐: {organ.get('creatinine')}"
    if organ.get('egfr_ml_min'):
        organ_str += f" | eGFR: {organ.get('egfr_ml_min')}"

    output_summary = f"""患者ID: {case.get('patient_id', 'Unknown')}
年龄: {case.get('age', 'N/A')}岁 | 性别: {case.get('sex', 'N/A')}
肿瘤类型: {case.get('primary_cancer', 'N/A')}
组织学: {case.get('histology', 'N/A')}
分期: {case.get('stage', 'N/A')}
转移部位: {case.get('metastatic_sites', [])}
MSI状态: {case.get('msi_status', 'N/A')} | TMB: {case.get('tmb_score', 'N/A')} | PD-L1 CPS: {case.get('pd_l1_cps', 'N/A')}
器官功能: {organ_str}

免疫组化:
{ihc_str}

分子特征:
{json.dumps(case.get('molecular_profile', []), ensure_ascii=False, indent=2)}

肿瘤标志物:
{markers_str}

合并症: {comorbidities_str}

治疗史 ({max((t.get('line_number', 0) for t in treatment_lines), default=0)} 线, {len(treatment_lines)} 条记录):
{treatment_str}"""
    _print_section("[PATHOLOGIST] 输出 - 结构化病例", output_summary)

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

    # 打印输入
    case = state["structured_case"]
    input_summary = f"""肿瘤类型: {case.get('primary_cancer', 'N/A')}
MSI状态: {case.get('msi_status', 'N/A')} | TMB: {case.get('tmb_score', 'N/A')}

分子特征:
{json.dumps(case.get('molecular_profile', []), ensure_ascii=False, indent=2)}"""
    _print_section("[GENETICIST] 输入 - 分子特征", input_summary)

    agent = GeneticistAgent()
    result = agent.analyze(state["structured_case"])

    report_len = len(result["report"]) if result["report"] else 0
    ref_count = len(result["references"]) if result["references"] else 0
    logger.info(f"[GENETICIST] 完成，报告长度: {report_len} 字符，引用数: {ref_count}")

    # 打印输出
    _print_section("[GENETICIST] 输出 - 分子分析报告", result["report"] or "无报告")

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

    # 打印输入
    case = state["structured_case"]
    geneticist_report = state.get("geneticist_report", "")
    input_summary = f"""肿瘤类型: {case.get('primary_cancer', 'N/A')}
分期: {case.get('stage', 'N/A')}
ECOG PS: {case.get('organ_function', {}).get('ecog_ps', 'N/A')}

遗传学家报告摘要 (前1000字符):
{geneticist_report[:1000] if geneticist_report else '无'}"""
    _print_section("[RECRUITER] 输入 - 试验匹配条件", input_summary)

    agent = RecruiterAgent()
    result = agent.search_trials(
        state["structured_case"],
        geneticist_report
    )

    report_len = len(result["report"]) if result["report"] else 0
    trial_count = len(result["trials"]) if result["trials"] else 0
    logger.info(f"[RECRUITER] 完成，报告长度: {report_len} 字符，试验数: {trial_count}")

    # 打印输出
    _print_section("[RECRUITER] 输出 - 临床试验推荐", result["report"] or "无报告")

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

    # 打印输入
    case = state["structured_case"]
    organ = case.get("organ_function", {})
    geneticist_report = state.get("geneticist_report", "")
    recruiter_report = state.get("recruiter_report", "")
    input_summary = f"""肿瘤类型: {case.get('primary_cancer', 'N/A')}
治疗线数: {len(case.get('treatment_lines', []))}

器官功能:
- ECOG PS: {organ.get('ecog_ps', 'N/A')}
- eGFR: {organ.get('egfr_ml_min', 'N/A')} mL/min
- 肌酐: {organ.get('creatinine', 'N/A')}

遗传学家报告摘要 (前800字符):
{geneticist_report[:800] if geneticist_report else '无'}

试验专员报告摘要 (前800字符):
{recruiter_report[:800] if recruiter_report else '无'}"""
    _print_section("[ONCOLOGIST] 输入 - 治疗规划条件", input_summary)

    agent = OncologistAgent()
    result = agent.create_plan(
        state["structured_case"],
        geneticist_report,
        recruiter_report
    )

    plan_len = len(result["plan"]) if result["plan"] else 0
    warning_count = len(result["warnings"]) if result["warnings"] else 0
    logger.info(f"[ONCOLOGIST] 完成，方案长度: {plan_len} 字符，安全警告: {warning_count}")

    # 打印输出
    _print_section("[ONCOLOGIST] 输出 - 治疗方案", result["plan"] or "无方案")

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

    # 打印输入
    geneticist_report = state.get("geneticist_report", "")
    recruiter_report = state.get("recruiter_report", "")
    oncologist_plan = state.get("oncologist_plan", "")
    input_summary = f"""迭代次数: {iteration + 1}
缺失模块: {missing if missing else '无'}

遗传学家报告长度: {len(geneticist_report)} 字符
试验专员报告长度: {len(recruiter_report)} 字符
肿瘤学家方案长度: {len(oncologist_plan)} 字符

各报告摘要:
--- 遗传学家 (前500字符) ---
{geneticist_report[:500] if geneticist_report else '无'}

--- 试验专员 (前500字符) ---
{recruiter_report[:500] if recruiter_report else '无'}

--- 肿瘤学家 (前500字符) ---
{oncologist_plan[:500] if oncologist_plan else '无'}"""
    _print_section("[CHAIR] 输入 - 各专家报告汇总", input_summary)

    agent = ChairAgent()
    result = agent.synthesize(
        structured_case=state["structured_case"],
        geneticist_report=geneticist_report,
        recruiter_report=recruiter_report,
        oncologist_plan=oncologist_plan,
        missing_sections=missing
    )

    synthesis_len = len(result["synthesis"]) if result["synthesis"] else 0
    ref_count = len(result["references"]) if result["references"] else 0
    logger.info(f"[CHAIR] 完成，综合报告长度: {synthesis_len} 字符，引用数: {ref_count}")

    # 打印输出
    _print_section("[CHAIR] 输出 - 最终综合报告", result["synthesis"] or "无报告")

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
    synthesis = state.get("chair_synthesis", "")
    is_compliant, missing = checker.validate(synthesis)

    # 更新迭代计数
    current_iteration = state.get("validation_iteration", 0)

    # 打印验证结果
    result_summary = f"""报告长度: {len(synthesis)} 字符
验证结果: {'✅ 通过' if is_compliant else '❌ 失败'}
缺失模块: {missing if missing else '无'}
当前迭代: {current_iteration + 1}"""
    _print_section("[VERIFY] 格式验证结果", result_summary, max_len=500)

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

    # 打印生成结果
    result_summary = f"""HTML 报告已生成！
路径: {output_path}
综合报告长度: {len(state.get('chair_synthesis', ''))} 字符
引用数: {len(state.get('chair_final_references', []))}"""
    _print_section("[HTML] 生成完成", result_summary, max_len=500)

    logger.info(f"[HTML] 报告已保存: {output_path}")

    return {
        "output_path": output_path
    }


if __name__ == "__main__":
    print("节点函数模块加载成功")
