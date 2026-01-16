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

    def analyze(self, structured_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析分子图谱

        Args:
            structured_case: 结构化病例数据

        Returns:
            包含报告和引用的字典
        """
        # 提取关键信息
        cancer_type = structured_case.get("primary_cancer", "未知肿瘤")
        molecular_profile = structured_case.get("molecular_profile", [])
        msi_status = structured_case.get("msi_status", "未检测")
        tmb_score = structured_case.get("tmb_score", "未检测")
        pd_l1_tps = structured_case.get("pd_l1_tps", "未检测")

        # 构建分析请求
        task_prompt = f"""
请分析以下患者的分子图谱：

**肿瘤类型**: {cancer_type}

**分子变异**:
{self._format_molecular_profile(molecular_profile)}

**免疫标志物**:
- MSI状态: {msi_status}
- TMB: {tmb_score} mut/Mb
- PD-L1 TPS: {pd_l1_tps}%

**任务**:
1. 使用 search_civic 查询每个主要变异的证据等级和治疗意义
2. 使用 search_clinvar 检查致病性
3. 使用 search_cbioportal 查询突变频率
4. 使用 search_pubmed 寻找相关临床证据

请按照提示词中的格式输出完整的分子分析报告。
"""

        result = self.invoke(task_prompt, context={"cancer_type": cancer_type})

        return {
            "report": result["output"],
            "references": result["references"]
        }

    def _format_molecular_profile(self, profile: list) -> str:
        """格式化分子图谱为可读文本"""
        if not profile:
            return "未检测到分子变异"

        lines = []
        for alt in profile:
            gene = alt.get("gene", "Unknown")
            variant = alt.get("variant", "")
            alt_type = alt.get("alteration_type", "")
            vaf = alt.get("vaf", None)

            line = f"- {gene}"
            if variant:
                line += f" {variant}"
            if alt_type:
                line += f" ({alt_type})"
            if vaf:
                line += f", VAF: {vaf * 100:.1f}%"

            lines.append(line)

        return "\n".join(lines)


if __name__ == "__main__":
    print("GeneticistAgent 模块加载成功")
