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
        structured_case: Dict[str, Any],
        geneticist_report: str,
        recruiter_report: str
    ) -> Dict[str, Any]:
        """
        制定治疗方案

        Args:
            structured_case: 结构化病例数据
            geneticist_report: 遗传学家报告
            recruiter_report: 临床试验专员报告

        Returns:
            包含方案和安全警告的字典
        """
        # 提取器官功能信息
        organ_function = structured_case.get("organ_function", {})
        treatment_lines = structured_case.get("treatment_lines", [])
        cancer_type = structured_case.get("primary_cancer", "未知肿瘤")

        # 安全性预检
        safety_concerns = self._check_safety_concerns(organ_function, treatment_lines)

        # 构建任务请求
        task_prompt = f"""
请为以下患者制定治疗方案：

**肿瘤类型**: {cancer_type}
**既往治疗线数**: {len(treatment_lines)}

**器官功能评估**:
{self._format_organ_function(organ_function)}

**预检安全问题**:
{safety_concerns if safety_concerns else "未发现明显安全问题"}

**遗传学家报告摘要**:
{geneticist_report[:1500]}...

**临床试验专员报告摘要**:
{recruiter_report[:1500]}...

**工具调用清单** (必须全部执行):

☐ 第1步: 调用 search_nccn(cancer_type="{cancer_type}") 获取标准治疗方案
☐ 第2步: 调用 search_fda_labels(drug_name="推荐药物名") 获取剂量和禁忌症
☐ 第3步: 调用 search_rxnorm(drug_name="推荐药物名") 检查药物相互作用

**警告**: 如果你跳过任何一个工具调用，患者安全将无法保障！

请现在开始执行第1步，调用 search_nccn。
"""

        result = self.invoke(task_prompt, context={
            "organ_function": organ_function,
            "prior_lines": len(treatment_lines)
        })

        # 提取安全警告
        warnings = self._extract_safety_warnings(result["output"])

        return {
            "plan": result["output"],
            "warnings": warnings
        }

    def _format_organ_function(self, organ_function: Dict[str, Any]) -> str:
        """格式化器官功能信息"""
        if not organ_function:
            return "无器官功能数据"

        lines = []

        # 肾功能
        egfr = organ_function.get("egfr_ml_min") or organ_function.get("creatinine_clearance")
        if egfr:
            status = "正常" if egfr >= 60 else ("减低" if egfr >= 30 else "严重减低")
            lines.append(f"- 肾功能 (eGFR): {egfr} mL/min - {status}")

        # 肝功能
        alt = organ_function.get("alt_u_l")
        ast = organ_function.get("ast_u_l")
        bili = organ_function.get("bilirubin_mg_dl")
        if alt or ast:
            lines.append(f"- 肝功能: ALT {alt or '?'} U/L, AST {ast or '?'} U/L")
        if bili:
            lines.append(f"- 胆红素: {bili} mg/dL")

        # 骨髓功能
        plt = organ_function.get("platelet_count")
        anc = organ_function.get("neutrophil_count")
        if plt:
            lines.append(f"- 血小板: {plt} × 10^9/L")
        if anc:
            lines.append(f"- ANC: {anc} × 10^9/L")

        # 心功能
        lvef = organ_function.get("lvef_percent")
        if lvef:
            lines.append(f"- LVEF: {lvef}%")

        # ECOG PS
        ecog = organ_function.get("ecog_ps")
        if ecog is not None:
            lines.append(f"- ECOG PS: {ecog}")

        return "\n".join(lines) if lines else "无器官功能数据"

    def _check_safety_concerns(
        self,
        organ_function: Dict[str, Any],
        treatment_lines: List[Dict[str, Any]]
    ) -> str:
        """预检安全问题"""
        concerns = []

        # 肾功能检查
        egfr = organ_function.get("egfr_ml_min") or organ_function.get("creatinine_clearance")
        if egfr and egfr < 30:
            concerns.append("⚠️ 严重肾功能不全 (eGFR <30) - 避免肾毒性药物")

        # ECOG PS 检查
        ecog = organ_function.get("ecog_ps")
        if ecog and ecog >= 3:
            concerns.append("⚠️ 体能状态差 (ECOG PS ≥3) - 考虑姑息治疗")

        # 既往严重毒性检查
        for line in treatment_lines:
            toxicities = line.get("grade3_plus_toxicities", [])
            for tox in toxicities:
                if "心脏" in tox or "cardiac" in tox.lower():
                    concerns.append(f"⚠️ 既往心脏毒性 ({tox}) - 避免心脏毒性药物")
                if "肝" in tox or "hepatic" in tox.lower():
                    concerns.append(f"⚠️ 既往肝毒性 ({tox}) - 监测肝功能")

        return "\n".join(concerns) if concerns else ""

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
