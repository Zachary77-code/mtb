"""
Oncologist Agent（肿瘤学家）- 三模式设计

Phase 1: Analysis 模式 - 过往治疗分析 (3.1)
Phase 2a: Mapping 模式 - 全身治疗手段 Mapping (5×4矩阵)
Phase 3: Integration 模式 - 方案整合 + L1-L5 证据分层
"""
from typing import Dict, Any, List

from src.agents.base_agent import BaseAgent
from src.tools.guideline_tools import NCCNTool, FDALabelTool, RxNormTool
from src.tools.literature_tools import PubMedTool
from config.settings import ONCOLOGIST_PROMPT_FILE


class OncologistAgent(BaseAgent):
    """
    肿瘤学家 Agent - 三模式

    Phase 1 (Analysis): 过往治疗和当前治疗方案的分析评价
    Phase 2a (Mapping): 全身治疗手段 Mapping (4审批×5手段=20格矩阵)
    Phase 3 (Integration): 方案整合 + L1-L5 证据分层 + 路径排序
    """

    def __init__(self):
        tools = [
            NCCNTool(),
            FDALabelTool(),
            RxNormTool(),
            PubMedTool()
        ]

        super().__init__(
            role="Oncologist",
            prompt_file=ONCOLOGIST_PROMPT_FILE,
            tools=tools,
            temperature=0.2
        )

    def analyze_past_treatment(
        self,
        raw_pdf_text: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Phase 1 Analysis 模式: 过往治疗和当前治疗方案的分析评价

        输出 3.1: 每线治疗的疗效评估、方案合理性分析、耐药机制推断、关键决策点回顾

        Args:
            raw_pdf_text: PDF 解析后的完整病历原文

        Returns:
            包含分析报告的字典
        """
        task_prompt = f"""
请基于以下病历原文，对患者的过往治疗和当前治疗方案进行全面分析评价。

**病历原文**:
{raw_pdf_text}

**分析任务** (3.1 过往治疗分析):

对每一线治疗进行以下分析：
1. **疗效评估**: ORR/PFS/影像变化/标志物趋势
2. **方案合理性分析**: 是否符合当时的标准治疗指南
3. **耐药机制推断**: 可能的耐药原因（分子层面+临床层面）
4. **关键决策点回顾**: 治疗转换时机是否合理、是否有更优选择
5. **副作用评估**: 累积毒性、器官功能影响

使用 search_nccn 核实各线治疗的指南推荐等级。
使用 search_pubmed 查找相关疗效数据和耐药机制文献。

**输出格式**:
请输出完整的 Markdown 格式分析报告，每线治疗独立章节。
"""

        result = self.invoke(task_prompt)

        full_report = self.generate_full_report(
            main_content=result["output"],
            title="Oncologist Past Treatment Analysis (Phase 1)"
        )

        return {
            "report": result["output"],
            "full_report_md": full_report
        }

    def create_plan(
        self,
        raw_pdf_text: str,
        pathologist_report: str = "",
        geneticist_report: str = "",
        recruiter_report: str = "",
        pharmacist_report: str = "",
        oncologist_analysis_report: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Phase 2a Mapping 模式: 全身治疗手段 Mapping

        输出 4审批分类 × 5治疗手段 = 20格矩阵
        核心原则: 只罗列可用手段并逐一分析，不做推荐判断

        Args:
            raw_pdf_text: PDF 解析后的完整病历原文
            pathologist_report: 病理学分析报告
            geneticist_report: 遗传学家报告
            recruiter_report: 临床试验专员报告
            pharmacist_report: 药师 Phase1 报告
            oncologist_analysis_report: Phase1 过往治疗分析

        Returns:
            包含 Mapping 报告和安全警告的字典
        """
        task_prompt = f"""
请基于以下完整信息，进行全身治疗手段 Mapping。

**病历原文**:
{raw_pdf_text}

**Phase 1 报告汇总**:

**病理学分析报告**:
{pathologist_report}

**分子分析报告**:
{geneticist_report}

**药师报告（合并症/用药/过敏）**:
{pharmacist_report}

**过往治疗分析 (3.1)**:
{oncologist_analysis_report}

**临床试验推荐**:
{recruiter_report}

**Mapping 任务 (Phase 2a)**:

请按以下 4审批分类 × 5治疗手段 = 20格矩阵 进行全身治疗手段 Mapping:

**5大治疗手段类别**:
1. 小分子 (化疗+靶向): 铂类/紫杉/吉西他滨, EGFR-TKI/ALK-TKI/BRAF-TKI等
2. 大分子 (抗体+ICI+双抗+ADC): 曲妥珠/贝伐珠, PD-1/PD-L1/CTLA-4, 双抗, T-DXd/EV等
3. 生物类 (疫苗+细胞治疗+溶瘤病毒): mRNA疫苗/DC疫苗, CAR-T/TIL/NK, T-VEC等
4. 内分泌治疗: AI/他莫昔芬/氟维司群, 恩扎卢胺/阿比特龙, TSH抑制等
5. 核素治疗: Lu-177 PSMA/DOTATATE, I-131, Ra-223等

**4大审批分类**:
a. 适应症获批: 该适应症已获批的药物/方案
b. 超适应症: 有数据但未获批的药物
c. 有试验可入组: 活跃临床试验中的药物
d. 无试验/临床阶段: 早期研究阶段药物

每格内容须包含: 药物/方案名称、适用条件、关键证据(PMID/NCT)、获益数据(ORR/PFS/OS)

**核心原则**: 只罗列分析，不做推荐判断。推荐将在 Phase 3 进行。

使用工具:
- search_nccn: 获取标准治疗方案
- search_fda_labels: 获取已获批适应症和剂量
- search_rxnorm: 检查药物相互作用
- search_pubmed: 查找证据数据

**输出格式**:
请输出完整的 Markdown 格式 Mapping 报告。
"""

        result = self.invoke(task_prompt)
        warnings = self._extract_safety_warnings(result["output"])

        full_report = self.generate_full_report(
            main_content=result["output"],
            title="Oncologist Treatment Mapping (Phase 2a)"
        )

        return {
            "plan": result["output"],
            "warnings": warnings,
            "full_report_md": full_report
        }

    def integrate_treatment_plan(
        self,
        raw_pdf_text: str,
        all_phase1_reports: Dict[str, str] = None,
        all_phase2a_reports: Dict[str, str] = None,
        pharmacist_review_report: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Phase 3 Integration 模式: 方案整合 + L1-L5 证据分层

        输出:
        - 3.3 治疗方案制定 (含 L1-L5 证据分层标注)
        - 3.4 治疗路径规划 (含排序逻辑)
        - 5.1 常规复查时间线 (To-Do)
        - 5.2 分子复查补充
        注: 3.1 已在 Phase 1 完成

        Args:
            raw_pdf_text: 完整病历原文
            all_phase1_reports: Phase 1 全部报告 dict
            all_phase2a_reports: Phase 2a 全部报告 dict
            pharmacist_review_report: Phase 2b 药学审查报告

        Returns:
            包含整合报告的字典
        """
        phase1 = all_phase1_reports or {}
        phase2a = all_phase2a_reports or {}

        task_prompt = f"""
请基于所有前序阶段的完整报告，进行治疗方案整合。

**病历原文**:
{raw_pdf_text}

**Phase 1 报告**:

**病理学报告**: {phase1.get('pathologist_report', '暂无')}

**遗传学报告**: {phase1.get('geneticist_report', '暂无')}

**药师报告(合并症/用药)**: {phase1.get('pharmacist_report', '暂无')}

**过往治疗分析(3.1)**: {phase1.get('oncologist_analysis_report', '暂无')}

**Phase 2a 报告**:

**全身治疗Mapping**: {phase2a.get('oncologist_mapping_report', '暂无')}

**局部治疗评估**: {phase2a.get('local_therapist_report', '暂无')}

**临床试验推荐**: {phase2a.get('recruiter_report', '暂无')}

**营养学方案**: {phase2a.get('nutritionist_report', '暂无')}

**替代疗法评估**: {phase2a.get('integrative_med_report', '暂无')}

**Phase 2b 药学审查报告**:
{pharmacist_review_report}

**整合任务 (Phase 3)**:

1. **3.3 治疗方案制定** - 每个方案必须执行 L1-L5 证据分层:
   - L1 直接循证: 有该组合的 RCT/Meta-analysis
   - L2 指南推荐: NCCN/CSCO/ESMO 指南推荐
   - L3 间接外推: 类似情境的证据外推
   - L4 机制推断: 基于生物学机制推断
   - L5 经验性: 无证据，纯临床经验

   证据分层寻证逻辑（每个治疗方案必须执行）:
   有直接证据? -> YES -> L1 | NO -> 有指南推荐? -> YES -> L2 | NO -> 有间接证据? -> YES -> L3 | NO -> 有机制合理性? -> YES -> L4 | NO -> L5

2. **3.4 治疗路径规划** - 排序打分维度:
   - 证据层级 (L1 > L2 > L3 > L4 > L5)
   - 获益预期 (ORR/PFS 数据)
   - 安全性 (Pharmacist Phase2b 标签)
   - 可及性 (中国获批 > 超适应证 > 临床试验 > 不可及)
   - 患者因素 (ECOG、年龄、合并症)

3. **5.1 常规复查时间线** (To-Do format)

4. **5.2 分子复查补充** (补充遗传学家 Phase1 的初稿)

**规则**:
- 引用 LocalTherapist 建议时，不修改局部治疗技术参数（放疗剂量/消融范围等），只判断在整体路径中的位置
- 无证据时不跳过，标注 L4/L5 + 推断逻辑 + 风险 + 建议 MDT

使用工具查证:
- search_nccn: 核实指南推荐
- search_fda_labels: 核实适应症和剂量
- search_pubmed: 查找证据
- search_rxnorm: 药物相互作用

**输出格式**:
请输出完整的 Markdown 格式整合报告。
"""

        result = self.invoke(task_prompt)
        warnings = self._extract_safety_warnings(result["output"])

        full_report = self.generate_full_report(
            main_content=result["output"],
            title="Oncologist Treatment Integration (Phase 3)"
        )

        return {
            "report": result["output"],
            "warnings": warnings,
            "full_report_md": full_report
        }

    def _extract_safety_warnings(self, report: str) -> List[str]:
        """提取安全警告"""
        warnings = []
        warning_markers = ["\u26a0\ufe0f", "\u274c", "警告", "禁忌", "避免", "不建议"]
        lines = report.split("\n")

        for line in lines:
            for marker in warning_markers:
                if marker in line:
                    warnings.append(line.strip())
                    break

        return warnings[:10]


if __name__ == "__main__":
    print("OncologistAgent 模块加载成功 (三模式: Analysis/Mapping/Integration)")
