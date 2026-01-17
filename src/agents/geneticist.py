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

        # 新增：提取患者基本信息
        age = structured_case.get("age", "?")
        sex = structured_case.get("sex", "?")
        stage = structured_case.get("stage", "?")

        # 新增：提取治疗史（用于分析获得性耐药）
        treatment_lines = structured_case.get("treatment_lines", [])
        treatment_summary = self._format_treatment_summary(treatment_lines)

        # 新增：提取器官功能和合并症
        organ_function = structured_case.get("organ_function", {})
        comorbidities = structured_case.get("comorbidities", [])

        # 构建分析请求
        task_prompt = f"""
请分析以下患者的分子图谱：

**患者背景**:
- 年龄: {age}岁
- 性别: {sex}
- 肿瘤类型: {cancer_type}
- 分期: {stage}

**既往治疗史**:
{treatment_summary}

**分子变异**:
{self._format_molecular_profile(molecular_profile)}

**免疫标志物**:
- MSI状态: {msi_status}
- TMB: {tmb_score} mut/Mb
- PD-L1 TPS: {pd_l1_tps}%

**器官功能**:
- ECOG PS: {organ_function.get('ecog_ps', '?')}
- eGFR: {organ_function.get('egfr_ml_min', '?')} mL/min

**合并症**: {', '.join(comorbidities) if comorbidities else '无'}

**任务**:
1. 使用 search_civic 查询每个主要变异的证据等级和治疗意义
2. 使用 search_clinvar 检查致病性（特别关注年龄<50的患者是否有胚系突变风险）
3. 使用 search_cbioportal 查询突变频率
4. 使用 search_pubmed 寻找相关临床证据
5. **特别注意**：如果患者接受过靶向治疗（如TKI），分析是否存在获得性耐药突变（如EGFR T790M）

请按照提示词中的格式输出完整的分子分析报告。
"""

        result = self.invoke(task_prompt, context={"cancer_type": cancer_type})

        return {
            "report": result["output"],
            "references": result["references"]
        }

    def _format_treatment_summary(self, treatment_lines: list) -> str:
        """格式化治疗史为完整明细（用于遗传学家分析获得性耐药和克隆演化）"""
        if not treatment_lines:
            return "无既往治疗"

        max_line = max((t.get('line_number', 0) for t in treatment_lines), default=0)

        # 格式化每条治疗记录的完整信息
        lines = []
        for i, t in enumerate(treatment_lines, 1):
            line_num = t.get('line_number', '?')
            regimen = t.get('regimen', '未知方案')
            start = t.get('start_date', '')
            end = t.get('end_date', '')
            response = t.get('best_response', '')
            note = t.get('notes', '')
            cycles = t.get('cycles', '')

            date_range = f"{start}-{end}" if start and end else (start or end or "日期未知")

            line_text = f"{i}. [{line_num}线] {regimen} ({date_range})"
            if response:
                line_text += f" → {response}"
            if cycles:
                line_text += f" ({cycles}程)"
            if note:
                line_text += f" | {note}"
            lines.append(line_text)

        header = f"共{max_line}线治疗（{len(treatment_lines)}条记录）：\n"
        return header + "\n".join(lines)

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
