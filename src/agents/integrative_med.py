"""
Integrative Medicine Agent（整合医学/支持治疗专家）

负责基于病历原文评估替代疗法和支持治疗方案，使用 PubMed 工具查询相关文献。
"""
from typing import Dict, Any

from src.agents.base_agent import BaseAgent
from src.tools.literature_tools import PubMedTool
from config.settings import INTEGRATIVE_MED_PROMPT_FILE


class IntegrativeMedAgent(BaseAgent):
    """
    整合医学/支持治疗专家 Agent

    负责基于病历原文逐一评估各种替代疗法和支持治疗方案:
    - 吸氢疗法评估
    - 大剂量维生素 C 疗法评估
    - 中医药疗法评估
    - 免疫调节治疗评估
    - 其他替代疗法评估
    - 每种疗法需包含: 机制、证据等级、适用性、风险警告、与常规治疗冲突评估
    - 使用 PubMed 查询替代疗法相关文献
    """

    def __init__(self):
        tools = [
            PubMedTool(),      # 文献检索（替代疗法相关）
        ]
        super().__init__(
            role="IntegrativeMed",
            prompt_file=INTEGRATIVE_MED_PROMPT_FILE,
            tools=tools,
            temperature=0.3
        )

    def analyze(self, raw_pdf_text: str, **kwargs) -> Dict[str, Any]:
        """
        基于病历原文评估替代疗法和支持治疗方案

        Args:
            raw_pdf_text: PDF 解析后的完整病历原文
            **kwargs: 额外参数

        Returns:
            包含分析报告和引用的字典
        """
        task_prompt = f"""
请基于以下病历原文逐一评估各种替代疗法和支持治疗方案:

**病历原文**:
{raw_pdf_text}

**分析任务**:
1. 首先从病历中提取与替代疗法相关的信息（患者使用的补充剂、中药、替代疗法等）
2. 逐一评估以下替代疗法在该患者情况下的适用性:
   - 吸氢疗法
   - 大剂量维生素 C 疗法
   - 中医药疗法（中药、针灸等）
   - 免疫调节治疗（胸腺肽、干扰素等）
   - 其他替代疗法（患者已使用或常见于该癌种的疗法）
3. 使用 search_pubmed 查询每种替代疗法的循证医学证据
4. 对每种疗法进行系统性分析

**每种疗法的分析必须包含以下内容**:
- 作用机制
- 证据等级（基于现有临床研究质量）
- 对该患者的适用性评估
- 风险警告（副作用、毒性）
- 与当前常规治疗的潜在冲突/相互作用评估
- 结论性建议

**输出格式**:
请输出完整的替代疗法评估报告，逐一分析每种疗法，包含:
- 各疗法独立评估（含上述所有分析要素）
- 综合建议（哪些可考虑、哪些应避免、哪些需进一步讨论）
- 相关文献支持（附 PMID 引用）

请确保报告完整详尽，不要省略任何重要信息。
"""
        result = self.invoke(task_prompt)

        # 生成完整报告（含工具调用详情和引用）
        full_report = self.generate_full_report(
            main_content=result["output"],
            title="Integrative Medicine Analysis Report"
        )

        return {
            "report": result["output"],
            "references": result["references"],
            "full_report_md": full_report
        }


if __name__ == "__main__":
    print("IntegrativeMedAgent 模块加载成功")
