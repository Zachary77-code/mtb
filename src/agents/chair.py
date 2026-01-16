"""
Chair Agent（MTB 主席）
"""
from typing import Dict, Any, List

from src.agents.base_agent import BaseAgent
from config.settings import CHAIR_PROMPT_FILE, REQUIRED_SECTIONS


class ChairAgent(BaseAgent):
    """
    MTB 主席 Agent

    汇总所有专家意见，生成最终的 12 模块报告。
    负责仲裁冲突（安全优先）和确保引用完整性。
    """

    def __init__(self):
        # 注意：对于简单模型（如 xiaomi/mimo-v2-flash:free），禁用工具调用
        # 让模型专注于综合报告生成，而不是调用工具
        # 如果使用更强大的模型（如 GPT-4），可以启用工具
        tools = []  # 禁用工具以提高报告生成质量

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
2. 如果某模块不适用，仍需包含该模块并说明"本病例不适用"
3. 每条建议都需要证据等级标注 [Evidence A/B/C/D]
4. 必须包含"不建议"章节
5. 仲裁原则：当安全性与疗效冲突时，以安全性为准
6. 所有引用使用 [PMID: xxx] 或 [NCT xxx] 格式

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


if __name__ == "__main__":
    print("ChairAgent 模块加载成功")
    print(f"必选模块数量: {len(REQUIRED_SECTIONS)}")
