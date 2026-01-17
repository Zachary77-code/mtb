"""
Chair Agent（MTB 主席）
"""
from typing import Dict, Any, List

from src.agents.base_agent import BaseAgent
from src.tools.guideline_tools import NCCNTool, FDALabelTool
from src.tools.literature_tools import PubMedTool
from config.settings import CHAIR_PROMPT_FILE, REQUIRED_SECTIONS


class ChairAgent(BaseAgent):
    """
    MTB 主席 Agent

    汇总所有专家意见，生成最终的 12 模块报告。
    负责仲裁冲突（安全优先）和确保引用完整性。
    """

    def __init__(self):
        tools = [
            NCCNTool(),
            FDALabelTool(),
            PubMedTool()
        ]

        super().__init__(
            role="Chair",
            prompt_file=CHAIR_PROMPT_FILE,
            tools=tools,
            temperature=0.3  # 稍高温度以增加综合能力
        )

    def synthesize(
        self,
        structured_case: Dict[str, Any],
        geneticist_report: str,
        recruiter_report: str,
        oncologist_plan: str,
        missing_sections: List[str] = None
    ) -> Dict[str, Any]:
        """
        综合所有报告生成最终 MTB 报告

        Args:
            structured_case: 结构化病例数据
            geneticist_report: 遗传学家报告
            recruiter_report: 临床试验专员报告
            oncologist_plan: 肿瘤学家方案
            missing_sections: 上一次验证失败时缺失的模块

        Returns:
            包含综合报告和引用的字典
        """
        # 基本信息
        cancer_type = structured_case.get("primary_cancer", "未知肿瘤")
        age = structured_case.get("age", "?")
        sex = structured_case.get("sex", "?")

        # 提取详细治疗史
        treatment_lines = structured_case.get("treatment_lines", [])
        treatment_history_detail = self._format_treatment_history(treatment_lines)

        # 提取分子特征
        molecular_profile = structured_case.get("molecular_profile", [])
        molecular_detail = self._format_molecular_profile(molecular_profile)

        # 构建综合请求
        regenerate_note = ""
        if missing_sections:
            regenerate_note = f"""
**重要**: 上一次报告缺少以下模块，请确保本次包含:
{chr(10).join([f'- {s}' for s in missing_sections])}
"""

        task_prompt = f"""
请作为 MTB 主席，综合以下专家报告生成最终 MTB 报告。

**患者基本信息**:
- 年龄: {age}岁
- 性别: {sex}
- 肿瘤类型: {cancer_type}

**完整治疗史（共{len(treatment_lines)}条记录）**:
{treatment_history_detail}

**分子特征详情**:
{molecular_detail}

{regenerate_note}

---

**遗传学家报告**:
{geneticist_report}

---

**临床试验专员报告**:
{recruiter_report}

---

**肿瘤学家治疗方案**:
{oncologist_plan}

---

**必须包含的 12 个模块**:
{chr(10).join([f'{i+1}. {s}' for i, s in enumerate(REQUIRED_SECTIONS)])}

**关键要求**:
1. 报告必须包含**全部 12 个模块**，按顺序排列
2. 第4模块"治疗史回顾"必须使用:::timeline格式展示上述**所有{len(treatment_lines)}条治疗记录**
3. 第9模块"临床试验推荐"必须保留临床试验专员报告中的**所有试验**（不少于3个）
4. **禁止压缩、合并、简化**任何治疗记录或试验信息
5. 每条建议都需要证据等级标注 [Evidence A/B/C/D]
6. 必须包含"不建议"章节
7. 仲裁原则：当安全性与疗效冲突时，以安全性为准
8. 所有引用使用 [PMID: xxx] 或 [NCT xxx] 格式

请生成完整的 Markdown 格式 MTB 报告。
"""

        result = self.invoke(task_prompt, context={
            "patient_id": structured_case.get("patient_id", "Unknown")
        })

        # 合并所有引用
        all_references = result["references"]

        return {
            "synthesis": result["output"],
            "references": all_references
        }

    def _format_treatment_history(self, treatment_lines: List[Dict]) -> str:
        """格式化治疗史为详细列表"""
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
                line_text += f" -> {response}"
            if note:
                line_text += f" | {note}"
            lines.append(line_text)

        return "\n".join(lines)

    def _format_molecular_profile(self, molecular_profile: List[Dict]) -> str:
        """格式化分子特征"""
        if not molecular_profile:
            return "无分子检测结果"

        lines = []
        for m in molecular_profile:
            gene = m.get('gene', '?')
            variant = m.get('variant', '')
            alt_type = m.get('alteration_type', '')
            vaf = m.get('vaf', '')

            line_text = f"- {gene}"
            if variant:
                line_text += f" {variant}"
            if alt_type:
                line_text += f" ({alt_type})"
            if vaf:
                line_text += f" [VAF: {vaf*100:.1f}%]"
            lines.append(line_text)

        return "\n".join(lines)


if __name__ == "__main__":
    print("ChairAgent 模块加载成功")
    print(f"必选模块数量: {len(REQUIRED_SECTIONS)}")
