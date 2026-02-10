"""
Nutritionist Agent（肿瘤营养康复专家）

负责基于病历原文进行营养状态评估和营养管理方案制定，使用 PubMed 工具查询相关文献。
"""
from typing import Dict, Any

from src.agents.base_agent import BaseAgent
from src.tools.literature_tools import PubMedTool
from config.settings import NUTRITIONIST_PROMPT_FILE


class NutritionistAgent(BaseAgent):
    """
    肿瘤营养康复专家 Agent

    负责基于病历原文进行营养评估和营养管理方案制定:
    - 评估患者营养状态（体重变化、BMI、白蛋白、前白蛋白等）
    - 提供癌种特异性饮食建议
    - 制定治疗期营养管理方案
    - 评估药物-营养素相互作用
    - 恶病质预防和管理方案
    - 使用 PubMed 查询营养相关文献
    """

    def __init__(self):
        tools = [
            PubMedTool(),      # 文献检索（营养相关）
        ]
        super().__init__(
            role="Nutritionist",
            prompt_file=NUTRITIONIST_PROMPT_FILE,
            tools=tools,
            temperature=0.3
        )

    def analyze(self, raw_pdf_text: str, **kwargs) -> Dict[str, Any]:
        """
        基于病历原文进行营养评估和营养管理方案制定

        Args:
            raw_pdf_text: PDF 解析后的完整病历原文
            **kwargs: 额外参数

        Returns:
            包含分析报告和引用的字典
        """
        task_prompt = f"""
请基于以下病历原文进行肿瘤营养评估和营养管理方案制定:

**病历原文**:
{raw_pdf_text}

**分析任务**:
1. 首先从病历中提取营养相关信息（体重、BMI、白蛋白、前白蛋白、进食状况、胃肠功能等）
2. 评估患者当前营养状态（NRS2002/PG-SGA 评分估算）
3. 使用 search_pubmed 查询该癌种的营养管理相关文献
4. 提供癌种特异性饮食建议
5. 制定治疗期营养管理方案（化疗/放疗/手术围术期营养支持）
6. 评估药物-营养素相互作用
7. 评估恶病质风险并制定预防/管理方案

**输出格式**:
请输出完整的营养评估报告，包含:
- 营养状态评估（当前营养指标、风险评分）
- 癌种饮食建议（推荐/避免的食物和营养素）
- 治疗期营养管理（各治疗阶段的营养支持方案）
- 药物-营养素相互作用分析
- 恶病质风险评估与管理方案
- 相关文献支持（附 PMID 引用）

请确保报告完整详尽，不要省略任何重要信息。
"""
        result = self.invoke(task_prompt)

        # 生成完整报告（含工具调用详情和引用）
        full_report = self.generate_full_report(
            main_content=result["output"],
            title="Nutritionist Analysis Report"
        )

        return {
            "report": result["output"],
            "references": result["references"],
            "full_report_md": full_report
        }


if __name__ == "__main__":
    print("NutritionistAgent 模块加载成功")
