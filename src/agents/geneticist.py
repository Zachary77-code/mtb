"""
Geneticist Agent（遗传学家）
"""
from typing import Dict, Any

from src.agents.base_agent import BaseAgent
from src.tools.molecular_tools import CIViCTool, ClinVarTool, cBioPortalTool
from src.tools.literature_tools import PubMedTool
from config.settings import GENETICIST_PROMPT_FILE


class GeneticistAgent(BaseAgent):
    """
    遗传学家 Agent

    分析分子图谱，确定变异的可操作性和证据等级。
    使用 CIViC (替代 OncoKB), ClinVar, cBioPortal (替代 COSMIC), PubMed 工具。
    """

    def __init__(self):
        tools = [
            CIViCTool(),      # 替代 OncoKB，提供变异证据等级
            ClinVarTool(),    # 变异致病性分类
            cBioPortalTool(), # 替代 COSMIC，提供突变频率
            PubMedTool()      # 文献检索
        ]

        super().__init__(
            role="Geneticist",
            prompt_file=GENETICIST_PROMPT_FILE,
            tools=tools,
            temperature=0.2
        )

    def analyze(self, raw_pdf_text: str) -> Dict[str, Any]:
        """
        基于病历原文分析分子图谱

        Args:
            raw_pdf_text: PDF 解析后的完整病历原文

        Returns:
            包含报告和引用的字典
        """
        # 构建分析请求 - 直接使用原始病历文本
        task_prompt = f"""
请基于以下病历原文分析分子图谱：

**病历原文**:
{raw_pdf_text}

**分析任务**:
1. 首先从病历中提取分子变异信息（基因、突变位点、VAF、变异类型等）
2. 提取免疫标志物信息（MSI状态、TMB、PD-L1等）
3. 使用 search_civic 查询每个主要变异的证据等级和治疗意义
4. 使用 search_clinvar 检查致病性（特别关注是否有胚系突变风险）
5. 使用 search_cbioportal 查询突变频率
6. 使用 search_pubmed 寻找相关临床证据
7. **特别注意**：如果患者接受过靶向治疗（如TKI），分析是否存在获得性耐药突变（如EGFR T790M）

**输出格式**:
请输出完整的分子分析报告，包含:
- 分子变异概况（所有检出变异及其特征）
- 每个可操作变异的证据等级和治疗意义
- 致病性评估
- 免疫治疗相关标志物分析
- 获得性耐药分析（如适用）
- 相关文献支持（附 PMID/NCT 引用）

请确保报告完整详尽，不要省略任何重要信息。
"""

        result = self.invoke(task_prompt)

        return {
            "report": result["output"],
            "references": result["references"]
        }


if __name__ == "__main__":
    print("GeneticistAgent 模块加载成功")
