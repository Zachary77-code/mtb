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

        # 提取主要生物标志物
        biomarkers = self._extract_biomarkers(molecular_profile)

        # 构建搜索请求
        task_prompt = f"""
请为以下患者搜索匹配的临床试验：

**肿瘤类型**: {cancer_type}
**当前状态**: {current_status}
**既往治疗线数**: {len(treatment_lines)}
**ECOG PS**: {organ_function.get('ecog_ps', '未知')}

**主要生物标志物**:
{biomarkers}

**遗传学家分析摘要**:
{geneticist_report[:1500]}...

**工具调用清单** (必须全部执行):

☐ 第1步: 调用 search_clinical_trials(cancer_type="{cancer_type}", biomarker="主要生物标志物") 搜索中国招募中的试验
☐ 第2步: 调用 search_nccn(cancer_type="{cancer_type}") 确认指南推荐的试验策略

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


if __name__ == "__main__":
    print("RecruiterAgent 模块加载成功")
