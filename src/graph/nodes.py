"""
LangGraph 节点函数
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from config.settings import REPORTS_DIR
from src.models.state import MtbState
from src.agents.pathologist import PathologistAgent
from src.agents.geneticist import GeneticistAgent
from src.agents.recruiter import RecruiterAgent
from src.agents.oncologist import OncologistAgent
from src.agents.chair import ChairAgent
from src.utils.logger import mtb_logger as logger


def _create_run_folder(patient_id: str = "unknown") -> Path:
    """
    创建本次运行的报告文件夹

    Args:
        patient_id: 患者 ID（用于文件夹命名）

    Returns:
        文件夹路径
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 清理患者 ID 中的特殊字符
    safe_patient_id = re.sub(r'[^\w\-]', '_', patient_id)[:50]
    folder_name = f"{timestamp}_{safe_patient_id}"
    run_folder = REPORTS_DIR / folder_name
    run_folder.mkdir(parents=True, exist_ok=True)
    logger.info(f"[RUN_FOLDER] 创建报告文件夹: {run_folder}")
    return run_folder


def _extract_patient_id(text: str) -> str:
    """从病历文本中提取患者 ID"""
    # 尝试匹配常见的患者 ID 格式
    patterns = [
        r'患者ID[：:]\s*(\S+)',
        r'病案号[：:]\s*(\S+)',
        r'住院号[：:]\s*(\S+)',
        r'门诊号[：:]\s*(\S+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text[:2000])
        if match:
            return match.group(1)
    return "unknown"


def _save_markdown_report(run_folder: Path, filename: str, content: str):
    """
    保存 Markdown 报告到文件

    Args:
        run_folder: 报告文件夹路径
        filename: 文件名
        content: Markdown 内容
    """
    filepath = run_folder / filename
    filepath.write_text(content, encoding="utf-8")
    logger.info(f"[SAVE_MD] 已保存: {filepath}")


def pdf_parser_node(state: MtbState) -> Dict[str, Any]:
    """
    PDF 解析节点

    将输入文本直接传递为 raw_pdf_text，供后续并行节点使用。
    不进行结构化处理，每个专家节点自行处理所需的结构化信息。
    同时创建本次运行的报告文件夹。

    Args:
        state: 当前状态

    Returns:
        更新的状态字段
    """
    logger.info("[PDF_PARSER] 开始解析 PDF 文本...")

    input_text = state["input_text"]
    logger.info(f"[PDF_PARSER] 原始文本长度: {len(input_text)} 字符")

    # 提取患者 ID 并创建运行文件夹
    patient_id = _extract_patient_id(input_text)
    run_folder = _create_run_folder(patient_id)

    return {
        "raw_pdf_text": input_text,
        "run_folder": str(run_folder)
    }


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


def pathologist_node(state: MtbState) -> Dict[str, Any]:
    """
    病理学家节点（病理学/影像学分析）

    Args:
        state: 当前状态

    Returns:
        更新的状态字段
    """
    logger.info("[PATHOLOGIST] 开始病理学分析...")

    raw_pdf_text = state.get("raw_pdf_text", "")

    # 打印输入摘要
    input_summary = f"原始病历文本长度: {len(raw_pdf_text)} 字符"
    _print_section("[PATHOLOGIST] 输入", input_summary)

    agent = PathologistAgent()
    result = agent.analyze(raw_pdf_text)

    report_len = len(result["report"]) if result["report"] else 0
    ref_count = len(result["references"]) if result["references"] else 0
    logger.info(f"[PATHOLOGIST] 完成，报告长度: {report_len} 字符，引用数: {ref_count}")

    # 保存完整 Markdown 报告
    run_folder = state.get("run_folder")
    if run_folder and result.get("full_report_md"):
        _save_markdown_report(Path(run_folder), "1_pathologist_report.md", result["full_report_md"])

    # 打印输出
    _print_section("[PATHOLOGIST] 输出 - 病理学分析报告", result["report"] or "无报告")

    return {
        "pathologist_report": result["report"],
        "pathologist_references": result["references"]
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

    raw_pdf_text = state.get("raw_pdf_text", "")

    # 打印输入摘要
    input_summary = f"原始病历文本长度: {len(raw_pdf_text)} 字符"
    _print_section("[GENETICIST] 输入", input_summary)

    agent = GeneticistAgent()
    result = agent.analyze(raw_pdf_text)

    report_len = len(result["report"]) if result["report"] else 0
    ref_count = len(result["references"]) if result["references"] else 0
    logger.info(f"[GENETICIST] 完成，报告长度: {report_len} 字符，引用数: {ref_count}")

    # 保存完整 Markdown 报告
    run_folder = state.get("run_folder")
    if run_folder and result.get("full_report_md"):
        _save_markdown_report(Path(run_folder), "2_geneticist_report.md", result["full_report_md"])

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

    raw_pdf_text = state.get("raw_pdf_text", "")

    # 打印输入摘要
    input_summary = f"原始病历文本长度: {len(raw_pdf_text)} 字符"
    _print_section("[RECRUITER] 输入", input_summary)

    agent = RecruiterAgent()
    result = agent.search_trials(raw_pdf_text)

    report_len = len(result["report"]) if result["report"] else 0
    trial_count = len(result["trials"]) if result["trials"] else 0
    logger.info(f"[RECRUITER] 完成，报告长度: {report_len} 字符，试验数: {trial_count}")

    # 保存完整 Markdown 报告
    run_folder = state.get("run_folder")
    if run_folder and result.get("full_report_md"):
        _save_markdown_report(Path(run_folder), "3_recruiter_report.md", result["full_report_md"])

    # 打印输出
    _print_section("[RECRUITER] 输出 - 临床试验推荐", result["report"] or "无报告")

    return {
        "recruiter_report": result["report"],
        "recruiter_trials": result["trials"]
    }


def oncologist_node(state: MtbState) -> Dict[str, Any]:
    """
    肿瘤学家节点

    接收所有并行节点的完整报告，制定治疗方案。

    Args:
        state: 当前状态

    Returns:
        更新的状态字段
    """
    logger.info("[ONCOLOGIST] 开始制定治疗方案...")

    # 获取所有输入（完整，不截断）
    raw_pdf_text = state.get("raw_pdf_text", "")
    pathologist_report = state.get("pathologist_report", "")
    geneticist_report = state.get("geneticist_report", "")
    recruiter_report = state.get("recruiter_report", "")

    # 打印输入摘要
    total_input = len(raw_pdf_text) + len(pathologist_report) + len(geneticist_report) + len(recruiter_report)
    input_summary = f"""**输入总量**: {total_input} 字符

- 原始病历文本: {len(raw_pdf_text)} 字符
- 病理学分析报告: {len(pathologist_report)} 字符
- 分子分析报告: {len(geneticist_report)} 字符
- 临床试验推荐: {len(recruiter_report)} 字符"""
    _print_section("[ONCOLOGIST] 输入", input_summary)

    agent = OncologistAgent()
    result = agent.create_plan(
        raw_pdf_text=raw_pdf_text,
        pathologist_report=pathologist_report,
        geneticist_report=geneticist_report,
        recruiter_report=recruiter_report
    )

    plan_len = len(result["plan"]) if result["plan"] else 0
    warning_count = len(result["warnings"]) if result["warnings"] else 0
    logger.info(f"[ONCOLOGIST] 完成，方案长度: {plan_len} 字符，安全警告: {warning_count}")

    # 保存完整 Markdown 报告
    run_folder = state.get("run_folder")
    if run_folder and result.get("full_report_md"):
        _save_markdown_report(Path(run_folder), "4_oncologist_report.md", result["full_report_md"])

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

    汇总整合所有专家报告，生成最终 MTB 报告。
    注意：是汇总整合，不是摘要压缩！

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
        logger.info("[CHAIR] 开始汇总整合所有报告...")

    # 获取所有输入（完整，不截断）
    raw_pdf_text = state.get("raw_pdf_text", "")
    pathologist_report = state.get("pathologist_report", "")
    geneticist_report = state.get("geneticist_report", "")
    recruiter_report = state.get("recruiter_report", "")
    oncologist_plan = state.get("oncologist_plan", "")

    # 收集上游报告的引用
    upstream_references = []
    upstream_references.extend(state.get("pathologist_references", []))
    upstream_references.extend(state.get("geneticist_references", []))
    # recruiter_trials 结构不同，提取 NCT IDs
    for trial in state.get("recruiter_trials", []):
        if trial.get("nct_id"):
            upstream_references.append({
                "type": "NCT",
                "id": trial["nct_id"],
                "url": f"https://clinicaltrials.gov/study/{trial['nct_id']}"
            })

    # 计算总输入量
    total_input = (len(raw_pdf_text) + len(pathologist_report) +
                   len(geneticist_report) + len(recruiter_report) + len(oncologist_plan))
    logger.info(f"[CHAIR] 输入总量: {total_input} 字符, 上游引用: {len(upstream_references)} 条")

    input_summary = f"""**迭代次数**: {iteration + 1}
**缺失模块**: {missing if missing else '无'}

**输入总量**: {total_input} 字符
- 原始病历文本: {len(raw_pdf_text)} 字符
- 病理学分析报告: {len(pathologist_report)} 字符
- 分子分析报告: {len(geneticist_report)} 字符
- 临床试验推荐: {len(recruiter_report)} 字符
- 治疗方案: {len(oncologist_plan)} 字符
- 上游引用数: {len(upstream_references)} 条"""
    _print_section("[CHAIR] 输入", input_summary)

    agent = ChairAgent()
    result = agent.synthesize(
        raw_pdf_text=raw_pdf_text,
        pathologist_report=pathologist_report,
        geneticist_report=geneticist_report,
        recruiter_report=recruiter_report,
        oncologist_plan=oncologist_plan,
        missing_sections=missing,
        upstream_references=upstream_references
    )

    synthesis_len = len(result["synthesis"]) if result["synthesis"] else 0
    ref_count = len(result["references"]) if result["references"] else 0
    logger.info(f"[CHAIR] 完成，综合报告长度: {synthesis_len} 字符，引用数: {ref_count}")

    # 保存完整 Markdown 报告
    run_folder = state.get("run_folder")
    if run_folder and result.get("full_report_md"):
        _save_markdown_report(Path(run_folder), "5_chair_final_report.md", result["full_report_md"])

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
        raw_pdf_text=state.get("raw_pdf_text", ""),
        chair_synthesis=state.get("chair_synthesis", ""),
        references=state.get("chair_final_references", []),
        run_folder=state.get("run_folder")  # 传递运行文件夹路径
    )

    # 打印生成结果
    run_folder = state.get("run_folder", "")
    result_summary = f"""HTML 报告已生成！
报告文件夹: {run_folder}
HTML 路径: {output_path}
综合报告长度: {len(state.get('chair_synthesis', ''))} 字符
引用数: {len(state.get('chair_final_references', []))}"""
    _print_section("[HTML] 生成完成", result_summary, max_len=500)

    logger.info(f"[HTML] 报告已保存: {output_path}")

    return {
        "output_path": output_path
    }


if __name__ == "__main__":
    print("节点函数模块加载成功")
