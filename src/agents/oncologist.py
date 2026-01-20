"""
Oncologist Agent（肿瘤学家）
"""
from typing import Dict, Any, List

from src.agents.base_agent import BaseAgent
from src.tools.guideline_tools import NCCNTool, FDALabelTool, RxNormTool
from src.tools.literature_tools import PubMedTool
from config.settings import ONCOLOGIST_PROMPT_FILE


class OncologistAgent(BaseAgent):
    """
    肿瘤学家 Agent

    制定治疗方案，进行安全性审查。
    使用 NCCN (RAG), FDA Labels, RxNorm (替代 DrugBank), PubMed 工具。
    强制执行安全优先规则。
    """

    def __init__(self):
        tools = [
            NCCNTool(),       # NCCN 指南 (基于 RAG)
            FDALabelTool(),   # FDA 药品说明书
            RxNormTool(),     # 替代 DrugBank，提供药物相互作用
            PubMedTool()      # 文献检索
        ]

        super().__init__(
            role="Oncologist",
            prompt_file=ONCOLOGIST_PROMPT_FILE,
            tools=tools,
            temperature=0.2
        )

    def create_plan(
        self,
        raw_pdf_text: str,
        pathologist_report: str,
        geneticist_report: str,
        recruiter_report: str
    ) -> Dict[str, Any]:
        """
        基于完整报告制定治疗方案

        Args:
            raw_pdf_text: PDF 解析后的完整病历原文
            pathologist_report: 病理学分析报告（完整）
            geneticist_report: 遗传学家报告（完整）
            recruiter_report: 临床试验专员报告（完整）

        Returns:
            包含方案和安全警告的字典
        """
        # 构建任务请求 - 使用完整报告，不截断
        task_prompt = f"""
请基于以下完整信息为患者制定治疗方案：

**病历原文**:
{raw_pdf_text}

**病理学分析报告** (完整):
{pathologist_report}

**分子分析报告** (完整):
{geneticist_report}

**临床试验推荐** (完整):
{recruiter_report}

**治疗规划任务**:

1. 首先从病历中提取关键治疗决策信息：
   - 患者基本信息（年龄、性别、肿瘤类型、分期）
   - 器官功能状态（eGFR、肝功能、血象、ECOG PS）
   - 既往治疗史和疗效
   - 合并症
   - 分子特征（基于分子分析报告）

2. 使用 search_nccn 获取标准治疗方案建议

3. 使用 search_fda_labels 获取推荐药物的剂量、禁忌症和剂量调整建议

4. 使用 search_rxnorm 检查药物相互作用（特别关注合并用药）

5. 综合所有信息制定个体化治疗方案

**安全性评估要点**:
- 年龄≥70岁：考虑减量或降低治疗强度
- 多线治疗后：评估骨髓储备和累积毒性
- 合并症管理：考虑药物相互作用
- 器官功能不全：必须查询FDA说明书的剂量调整建议
- 既往严重毒性：避免同类药物或加强监测

**输出格式**:
请输出完整的治疗方案报告，包含:
- 治疗目标和策略
- 推荐的治疗方案（一线/后线）及其证据等级
- 剂量和给药方案（含器官功能调整）
- 安全性注意事项和监测计划
- 可选的临床试验推荐（基于试验专员报告）
- 参考文献/指南引用

请确保报告完整详尽，不要省略任何重要信息。
"""

        result = self.invoke(task_prompt)

        # 提取安全警告
        warnings = self._extract_safety_warnings(result["output"])

        # 生成完整报告（含工具调用详情和引用）
        full_report = self.generate_full_report(
            main_content=result["output"],
            title="Oncologist Treatment Plan"
        )

        return {
            "plan": result["output"],
            "warnings": warnings,
            "full_report_md": full_report
        }

    def _extract_safety_warnings(self, report: str) -> List[str]:
        """提取安全警告"""
        warnings = []

        # 查找警告标记
        warning_markers = ["⚠️", "❌", "警告", "禁忌", "避免", "不建议"]
        lines = report.split("\n")

        for line in lines:
            for marker in warning_markers:
                if marker in line:
                    warnings.append(line.strip())
                    break

        return warnings[:10]  # 限制数量


if __name__ == "__main__":
    print("OncologistAgent 模块加载成功")
