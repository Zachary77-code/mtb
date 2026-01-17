"""
Recruiter Agent（临床试验专员）
"""
from typing import Dict, Any, List

from src.agents.base_agent import BaseAgent
from src.tools.trial_tools import ClinicalTrialsTool
from src.tools.guideline_tools import NCCNTool
from src.tools.literature_tools import PubMedTool
from config.settings import RECRUITER_PROMPT_FILE


class RecruiterAgent(BaseAgent):
    """
    临床试验专员 Agent

    匹配适合患者的临床试验，优先中国招募中的试验。
    使用 ClinicalTrials, NCCN, PubMed 工具。
    """

    def __init__(self):
        tools = [
            ClinicalTrialsTool(),
            NCCNTool(),
            PubMedTool()
        ]

        super().__init__(
            role="Recruiter",
            prompt_file=RECRUITER_PROMPT_FILE,
            tools=tools,
            temperature=0.2
        )

    def search_trials(
        self,
        structured_case: Dict[str, Any],
        geneticist_report: str
    ) -> Dict[str, Any]:
        """
        搜索临床试验

        Args:
            structured_case: 结构化病例数据
            geneticist_report: 遗传学家报告

        Returns:
            包含报告和试验列表的字典
        """
        # 提取关键信息
        cancer_type = structured_case.get("primary_cancer", "未知肿瘤")
        molecular_profile = structured_case.get("molecular_profile", [])
        current_status = structured_case.get("current_status", "unknown")
        treatment_lines = structured_case.get("treatment_lines", [])
        organ_function = structured_case.get("organ_function", {})

        # 新增：提取患者筛查关键信息
        age = structured_case.get("age", "?")
        sex = structured_case.get("sex", "?")
        stage = structured_case.get("stage", "?")
        metastatic_sites = structured_case.get("metastatic_sites", [])
        comorbidities = structured_case.get("comorbidities", [])

        # 计算实际治疗线数
        max_line = max((t.get('line_number', 0) for t in treatment_lines), default=0)

        # 提取主要生物标志物
        biomarkers = self._extract_biomarkers(molecular_profile)

        # 构建搜索请求
        task_prompt = f"""
请为以下患者搜索匹配的临床试验：

**患者入组筛查信息**:
- 年龄: {age}岁
- 性别: {sex}
- 肿瘤类型: {cancer_type}
- 分期: {stage}
- 转移部位: {', '.join(metastatic_sites) if metastatic_sites else '无'}

**治疗史**:
- 既往治疗线数: {max_line}（共{len(treatment_lines)}条记录）
- 当前状态: {current_status}

**详细治疗记录**:
{self._format_treatment_history(treatment_lines)}

**主要生物标志物**:
{biomarkers}

**器官功能**:
- ECOG PS: {organ_function.get('ecog_ps', '未知')}
- eGFR: {organ_function.get('egfr_ml_min', '?')} mL/min
- ALT: {organ_function.get('alt_u_l', '?')} U/L
- AST: {organ_function.get('ast_u_l', '?')} U/L
- 血小板: {organ_function.get('platelet_count', '?')} × 10^9/L
- ANC: {organ_function.get('neutrophil_count', '?')} × 10^9/L
- LVEF: {organ_function.get('lvef_percent', '?')}%

**合并症**: {', '.join(comorbidities) if comorbidities else '无'}

**遗传学家分析摘要**:
{geneticist_report[:1500]}...

**工具调用清单** (必须全部执行):

☐ 第1步: 调用 search_clinical_trials(cancer_type="{cancer_type}", biomarker="主要生物标志物") 搜索中国招募中的试验
☐ 第2步: 调用 search_nccn(cancer_type="{cancer_type}") 确认指南推荐的试验策略
☐ 第3步: 根据患者的**年龄、器官功能、合并症**筛选入组可行的试验

**入组可行性评估要求**:
1. 年龄限制：排除年龄不符的试验（如"18-70岁"而患者75岁）
2. 器官功能：排除器官功能要求不符的试验（如要求eGFR≥60但患者只有45）
3. ECOG PS：排除体能状态要求不符的试验
4. 合并症：标注可能影响入组的合并症（如心脏病史、肝病史）

**警告**: 如果你跳过任何一个工具调用，试验匹配将不准确！

请现在开始执行第1步，调用 search_clinical_trials。
"""

        result = self.invoke(task_prompt, context={
            "cancer_type": cancer_type,
            "biomarkers": biomarkers
        })

        # 提取试验列表
        trials = self._extract_trials(result["output"])

        return {
            "report": result["output"],
            "trials": trials
        }

    def _extract_biomarkers(self, molecular_profile: list) -> str:
        """提取主要生物标志物"""
        if not molecular_profile:
            return "无分子检测结果"

        markers = []
        for alt in molecular_profile:
            gene = alt.get("gene", "")
            variant = alt.get("variant", "")
            if gene:
                marker = f"{gene} {variant}".strip()
                markers.append(marker)

        return "\n".join([f"- {m}" for m in markers])

    def _extract_trials(self, report: str) -> List[Dict[str, Any]]:
        """从报告中提取试验信息"""
        import re

        trials = []

        # 匹配 NCT ID
        nct_pattern = r'(NCT\d{8})'
        for match in re.finditer(nct_pattern, report):
            nct_id = match.group(1)
            if not any(t["nct_id"] == nct_id for t in trials):
                trials.append({
                    "nct_id": nct_id,
                    "url": f"https://clinicaltrials.gov/study/{nct_id}"
                })

        return trials

    def _format_treatment_history(self, treatment_lines: list) -> str:
        """格式化治疗史为完整明细（用于试验入组筛查）"""
        if not treatment_lines:
            return "无治疗史"

        lines = []
        for i, t in enumerate(treatment_lines, 1):
            line_num = t.get('line_number', '?')
            regimen = t.get('regimen', '未知方案')
            start = t.get('start_date', '')
            end = t.get('end_date', '')
            response = t.get('best_response', '')
            note = t.get('notes', '')

            date_range = f"{start}-{end}" if start and end else (start or end or "日期未知")

            line_text = f"{i}. [{line_num}线] {regimen} ({date_range})"
            if response:
                line_text += f" → {response}"
            if note:
                line_text += f" | {note}"
            lines.append(line_text)

        return "\n".join(lines)


if __name__ == "__main__":
    print("RecruiterAgent 模块加载成功")
