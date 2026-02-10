"""
Pharmacist Agent（临床药师，双模式）

双模式 Agent:
- Phase 1 (analyze): 合并症、用药清单、过敏史、器官功能基线、药物互作初步分析
- Phase 2b (review): 药学审查，为每个候选治疗手段打药学标签

使用 FDALabel, RxNorm, PubMed 工具。
"""
from typing import Dict, Any

from src.agents.base_agent import BaseAgent
from src.tools.guideline_tools import FDALabelTool, RxNormTool
from src.tools.literature_tools import PubMedTool
from config.settings import PHARMACIST_PROMPT_FILE
from src.utils.logger import mtb_logger as logger


class PharmacistAgent(BaseAgent):
    """
    临床药师 Agent（双模式）

    Phase 1 - Research 模式:
    - 提取合并症（病症+用药清单）
    - 提取过敏史
    - 评估器官功能基线
    - 初步药物互作分析

    Phase 2b - Review 模式:
    - 审查所有候选治疗手段的药物交互风险
    - 肝肾功能剂量调整建议
    - 毒性预测与管理方案
    - 绝对/相对禁忌标注
    - 超适应症用药的伦理/审批要求标注

    使用 FDALabel, RxNorm, PubMed 工具。
    """

    def __init__(self):
        tools = [
            FDALabelTool(),    # FDA 药品说明书
            RxNormTool(),      # 药物相互作用
            PubMedTool(),      # 文献检索
        ]
        super().__init__(
            role="Pharmacist",
            prompt_file=PHARMACIST_PROMPT_FILE,
            tools=tools,
            temperature=0.2
        )

    def analyze(self, raw_pdf_text: str, **kwargs) -> Dict[str, Any]:
        """
        Phase 1: 基于病历原文提取合并症、用药、过敏史并进行初步药学分析

        Args:
            raw_pdf_text: PDF 解析后的完整病历原文
            **kwargs: 额外参数

        Returns:
            包含分析报告和引用的字典
        """
        logger.info("[Pharmacist] Phase 1 - Research 模式: 合并症/用药/过敏史分析")

        task_prompt = f"""
请基于以下病历原文进行临床药学分析（Phase 1 - 信息提取与解读）:

**病历原文**:
{raw_pdf_text}

**分析任务**:
1. 从病历中完整提取合并症信息（所有病症及其用药清单）
2. 从病历中完整提取过敏史（药物过敏、食物过敏、其他过敏）
3. 评估器官功能基线:
   - 肝功能（ALT、AST、胆红素、白蛋白）
   - 肾功能（eGFR、肌酐、BUN）
   - 心功能（LVEF、心电图异常）
   - 骨髓功能（WBC、ANC、PLT、Hb）
4. 使用 search_fda_labels 查询当前用药的说明书信息
5. 使用 search_rxnorm 检查当前合并用药之间的相互作用
6. 使用 search_pubmed 查询药物互作相关文献
7. 进行初步药物互作分析

**输出格式**:
请输出完整的临床药学分析报告，包含:
- 合并症清单（病症名称 + 对应用药）
- 过敏史记录
- 器官功能基线评估
- 当前用药清单及分析
- 药物相互作用初步分析
- 相关文献支持（附 PMID 引用）

请确保报告完整详尽，不要省略任何重要信息。
"""
        result = self.invoke(task_prompt)

        # 生成完整报告（含工具调用详情和引用）
        full_report = self.generate_full_report(
            main_content=result["output"],
            title="Pharmacist Analysis Report (Phase 1)"
        )

        return {
            "report": result["output"],
            "references": result["references"],
            "full_report_md": full_report
        }

    def review(self, phase2a_reports: dict, phase1_pharmacist_report: str, **kwargs) -> Dict[str, Any]:
        """
        Phase 2b: 基于全部 Phase 2a 报告进行药学审查

        Args:
            phase2a_reports: Phase 2a 全部报告的字典，包含:
                - oncologist_mapping_report: 肿瘤学家全身治疗 Mapping 报告
                - local_therapist_report: 局部治疗专家报告
                - recruiter_report: 临床试验专员报告
                - nutritionist_report: 营养师报告
                - integrative_med_report: 整合医学报告
            phase1_pharmacist_report: Phase 1 药师报告（合并症/用药基线）
            **kwargs: 额外参数

        Returns:
            包含审查报告和引用的字典
        """
        logger.info("[Pharmacist] Phase 2b - Review 模式: 药学审查")

        # 构建 Phase 2a 报告汇总
        oncologist_mapping = phase2a_reports.get("oncologist_mapping_report", "")
        local_therapist = phase2a_reports.get("local_therapist_report", "")
        recruiter = phase2a_reports.get("recruiter_report", "")
        nutritionist = phase2a_reports.get("nutritionist_report", "")
        integrative_med = phase2a_reports.get("integrative_med_report", "")

        task_prompt = f"""
请基于以下全部报告进行药学审查（Phase 2b - 药学审查模式）:

**Phase 1 药师报告（合并症/用药基线）** (完整):
{phase1_pharmacist_report}

**Phase 2a 肿瘤学家全身治疗 Mapping 报告** (完整):
{oncologist_mapping}

**Phase 2a 局部治疗专家报告** (完整):
{local_therapist}

**Phase 2a 临床试验专员报告** (完整):
{recruiter}

**Phase 2a 营养师报告** (完整):
{nutritionist}

**Phase 2a 整合医学报告** (完整):
{integrative_med}

**药学审查任务**:
1. 逐一审查 Phase 2a 中所有候选治疗手段（全身治疗、局部治疗、临床试验药物、营养补充、替代疗法）
2. 使用 search_fda_labels 核实每个候选药物的说明书信息
3. 使用 search_rxnorm 检查候选药物与当前合并用药之间的相互作用
4. 使用 search_pubmed 查询相关药学文献
5. 为每个候选治疗手段提供药学标签

**每个候选治疗手段的药学标签须包含**:
- 药物交互风险评估（与合并用药的相互作用）
- 肝肾功能剂量调整建议（基于 Phase 1 器官功能基线）
- 毒性预测与管理方案
- 绝对禁忌 / 相对禁忌标注
- 超适应症用药的伦理/审批要求标注（如适用）

**输出格式**:
请输出完整的药学审查报告，包含:
- 审查概述
- 逐一候选治疗手段的药学标签（按全身治疗→局部治疗→试验药物→营养→替代疗法排列）
- 高风险交互提醒汇总
- 剂量调整建议汇总
- 相关文献支持（附 PMID 引用）

请确保报告完整详尽，不要省略任何重要信息。
"""
        result = self.invoke(task_prompt)

        # 生成完整报告（含工具调用详情和引用）
        full_report = self.generate_full_report(
            main_content=result["output"],
            title="Pharmacist Review Report (Phase 2b)"
        )

        return {
            "report": result["output"],
            "references": result["references"],
            "full_report_md": full_report
        }


if __name__ == "__main__":
    print("PharmacistAgent 模块加载成功")
