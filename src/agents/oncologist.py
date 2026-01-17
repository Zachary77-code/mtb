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

        # 新增：提取患者基本信息
        age = structured_case.get("age", "?")
        sex = structured_case.get("sex", "?")
        stage = structured_case.get("stage", "?")
        metastatic_sites = structured_case.get("metastatic_sites", [])

        # 新增：提取合并症和肿瘤标志物
        comorbidities = structured_case.get("comorbidities", [])
        tumor_markers = structured_case.get("tumor_markers", {})

        # 安全性预检
        safety_concerns = self._check_safety_concerns(organ_function, treatment_lines)

        # 计算实际治疗线数
        max_line = max((t.get('line_number', 0) for t in treatment_lines), default=0)

        # 新增：分析累积毒性风险
        cumulative_toxicity_risk = self._assess_cumulative_toxicity(treatment_lines)

        # 构建任务请求
        task_prompt = f"""
请为以下患者制定治疗方案：

**患者基本信息**:
- 年龄: {age}岁
- 性别: {sex}
- 肿瘤类型: {cancer_type}
- 分期: {stage}
- 转移部位: {', '.join(metastatic_sites) if metastatic_sites else '无'}

**既往治疗线数**: {max_line}（共{len(treatment_lines)}条记录）

**详细治疗记录**:
{self._format_treatment_history(treatment_lines)}

**器官功能评估**:
{self._format_organ_function(organ_function)}

**合并症**: {', '.join(comorbidities) if comorbidities else '无'}

**肿瘤标志物**:
{self._format_tumor_markers(tumor_markers)}

**累积毒性风险评估**:
{cumulative_toxicity_risk if cumulative_toxicity_risk else "未发现显著累积毒性风险"}

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

**特别注意**:
1. 年龄≥70岁：考虑减量或降低治疗强度
2. 多线治疗后：评估骨髓储备和累积毒性
3. 合并症管理：考虑药物相互作用
4. 器官功能不全：必须查询FDA说明书的剂量调整建议

**警告**: 如果你跳过任何一个工具调用，患者安全将无法保障！

请现在开始执行第1步，调用 search_nccn。
"""

        result = self.invoke(task_prompt, context={
            "organ_function": organ_function,
            "prior_lines": max_line,
            "age": age,
            "comorbidities": comorbidities
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

    def _format_tumor_markers(self, tumor_markers: Dict[str, float]) -> str:
        """格式化肿瘤标志物"""
        if not tumor_markers:
            return "无肿瘤标志物数据"

        lines = []
        for marker, value in tumor_markers.items():
            # 标准化标记物名称
            marker_name = marker.replace('_', ' ').upper()
            lines.append(f"- {marker_name}: {value}")

        return "\n".join(lines)

    def _assess_cumulative_toxicity(self, treatment_lines: List[Dict[str, Any]]) -> str:
        """评估累积毒性风险"""
        concerns = []

        # 统计化疗程数
        chemo_cycles = 0
        anthracycline_use = False
        platinum_use = False

        for line in treatment_lines:
            regimen = line.get('regimen', '').lower()
            cycles = line.get('cycles', 0)

            # 累积化疗程数
            if any(drug in regimen for drug in ['化疗', 'chemo', '奥沙利铂', 'oxaliplatin',
                                                   '顺铂', 'cisplatin', '卡铂', 'carboplatin',
                                                   '紫杉醇', 'paclitaxel', '多西他赛', 'docetaxel']):
                chemo_cycles += cycles if cycles else 4  # 默认4程

            # 蒽环类药物（心脏毒性）
            if '表柔比星' in regimen or 'epirubicin' in regimen or '多柔比星' in regimen or 'doxorubicin' in regimen:
                anthracycline_use = True

            # 铂类药物（肾毒性、神经毒性）
            if '铂' in regimen or 'platin' in regimen:
                platinum_use = True

        # 风险评估
        if chemo_cycles >= 12:
            concerns.append(f"⚠️ 累积化疗≥{chemo_cycles}程 - 骨髓储备可能减少，考虑减量或延长给药间隔")

        if anthracycline_use:
            concerns.append("⚠️ 既往蒽环类药物史 - 监测LVEF，避免进一步心脏毒性药物")

        if platinum_use:
            concerns.append("⚠️ 既往铂类药物史 - 评估肾功能和周围神经病变，考虑非铂方案")

        return "\n".join(concerns) if concerns else ""

    def _format_treatment_history(self, treatment_lines: List[Dict[str, Any]]) -> str:
        """格式化治疗史为完整明细（用于制定后线治疗方案）"""
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

        return "\n".join(lines)


if __name__ == "__main__":
    print("OncologistAgent 模块加载成功")
