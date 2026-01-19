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

    def search_trials(self, raw_pdf_text: str) -> Dict[str, Any]:
        """
        基于病历原文搜索临床试验

        Args:
            raw_pdf_text: PDF 解析后的完整病历原文

        Returns:
            包含报告和试验列表的字典
        """
        # 构建搜索请求 - 直接使用原始病历文本
        task_prompt = f"""
请基于以下病历原文为患者搜索匹配的临床试验：

**病历原文**:
{raw_pdf_text}

**分析任务**:
1. 首先从病历中提取患者入组筛查关键信息：
   - 年龄、性别
   - 肿瘤类型、分期、转移部位
   - 既往治疗线数和治疗记录
   - 分子特征/生物标志物
   - 器官功能（ECOG PS、eGFR、肝功能、血象等）
   - 合并症

2. 使用 search_clinical_trials 搜索匹配的临床试验（优先中国招募中的试验）

3. 使用 search_nccn 确认指南推荐的试验策略

4. 对搜索到的试验进行入组可行性评估：
   - 年龄限制：排除年龄不符的试验
   - 器官功能：排除器官功能要求不符的试验
   - ECOG PS：排除体能状态要求不符的试验
   - 合并症：标注可能影响入组的合并症

**输出格式**:
请输出完整的临床试验推荐报告，包含:
- 患者入组资格概述
- 推荐的临床试验列表（含 NCT ID、试验名称、状态、入组条件）
- 每个试验的入组可行性评估
- 排除的试验及排除原因
- 相关文献/指南支持

请确保报告完整详尽，不要省略任何重要信息。
"""

        result = self.invoke(task_prompt)

        # 提取试验列表
        trials = self._extract_trials(result["output"])

        return {
            "report": result["output"],
            "trials": trials
        }

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
