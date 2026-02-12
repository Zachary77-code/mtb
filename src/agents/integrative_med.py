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

    基于患者病情动态探索替代疗法和支持治疗方案（患者驱动模式）:
    - 从患者癌种、突变、用药、合并症等因素出发搜索相关 CAM (complementary and alternative therapies) 疗法
    - 常见 CAM 品类（吸氢/大剂量VC/中医/免疫调节/针灸/运动等）作为参考，不强制逐项覆盖
    - 每种相关疗法需包含: 与患者的关联、机制、证据等级、适用性、风险警告、与常规治疗冲突评估
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
请基于以下病历原文，以患者病情为中心动态探索相关的替代/支持疗法:

**病历原文**:
{raw_pdf_text}

**分析任务**:
1. 首先从病历中提取关键患者因素（癌种/亚型/分期、突变谱、当前用药、合并症、副作用、患者已使用的补充剂/中药/替代疗法）
2. 基于这些患者因素，使用 search_pubmed 搜索与该患者特异性相关的替代/支持疗法
3. 对每个搜索发现的相关疗法进行系统性评估（不相关的疗法可跳过）
4. 常见 CAM 品类（吸氢/大剂量VC/中医/免疫调节/针灸/运动等）仅作为参考，不需要逐一覆盖

**每种相关疗法的评估必须包含**:
- 与患者的关联（为什么选择评估这个疗法）
- 作用机制
- 证据等级（基于现有临床研究质量）
- 对该患者的适用性评估
- 风险警告（副作用、毒性）
- 与当前常规治疗的潜在冲突/相互作用评估
- 结论性建议

**输出格式**:
请输出替代疗法评估报告，包含:
- 患者概况摘要（驱动评估的关键因素）
- 各相关疗法独立评估（含上述评估要素）
- 安全性总结（绝对禁忌/相对禁忌/可安全并用）
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
