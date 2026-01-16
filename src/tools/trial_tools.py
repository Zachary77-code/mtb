"""
临床试验工具（占位符实现）
"""
from src.tools.base_tool import BaseMockTool
from typing import Dict, Any


class ClinicalTrialsTool(BaseMockTool):
    """ClinicalTrials.gov 搜索工具"""

    def __init__(self):
        super().__init__(
            name="search_clinical_trials",
            description="搜索 ClinicalTrials.gov 中国招募中的试验。输入肿瘤类型、生物标志物、干预措施"
        )

    def _generate_mock_response(self, cancer_type: str = "", biomarker: str = "", intervention: str = "", **kwargs) -> str:
        return f"""
**ClinicalTrials.gov 搜索结果（模拟数据）**

**搜索条件**:
- 肿瘤类型: {cancer_type}
- 生物标志物: {biomarker}
- 干预措施: {intervention}
- 地区: 中国
- 状态: Recruiting

**匹配试验（共3项）**:

---

### 1. NCT04532463 - BPI-7711 vs Osimertinib in EGFR+ NSCLC

**Phase**: III
**状态**: Recruiting (招募中)
**入组人数**: 440 patients
**药物**: BPI-7711 (新型 EGFR TKI) vs Osimertinib

**关键入组标准**:
- EGFR敏感突变 (Exon 19del 或 L858R)
- 既往未接受 EGFR TKI 治疗
- ECOG PS 0-1
- 可测量病灶

**中国中心**:
- 北京协和医院
- 上海市胸科医院
- 广东省人民医院
- 四川大学华西医院

**PI**: 吴一龙教授（广东省人民医院）
**预计完成日期**: 2025年12月

**参考**: https://clinicaltrials.gov/study/NCT04532463

---

### 2. NCT05123456 - Amivantamab + Lazertinib in EGFR Ex20ins NSCLC

**Phase**: II
**状态**: Recruiting (招募中)
**入组人数**: 80 patients
**药物**: Amivantamab (双特异性抗体) + Lazertinib (EGFR TKI)

**关键入组标准**:
- EGFR Exon 20 插入突变
- 既往接受≤2线治疗
- ECOG PS 0-2

**中国中心**:
- 中山大学肿瘤防治中心
- 复旦大学附属肿瘤医院
- 浙江省肿瘤医院

**预期疗效**: 基于 CHRYSALIS 研究，ORR约40%

**参考**: https://clinicaltrials.gov/study/NCT05123456

---

### 3. NCT03915158 - KEYNOTE-158: Pembrolizumab in TMB-High Solid Tumors

**Phase**: II
**状态**: Recruiting (招募中)
**入组人数**: 1000 patients (多个队列)
**药物**: Pembrolizumab (帕博利珠单抗)

**关键入组标准**:
- TMB-High (≥10 mutations/Mb)
- 既往标准治疗失败
- 任何实体瘤类型

**中国中心**: 多中心（>20家三甲医院）

**已发表数据**: TMB-H队列 ORR 29%, mPFS 4.1 months [PMID: 32628872]

**参考**: https://clinicaltrials.gov/study/NCT03915158

---

**备注**: 以上为模拟数据，实际试验入组需联系各中心PI确认资格。
"""

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "cancer_type": {"type": "string", "description": "肿瘤类型"},
                "biomarker": {"type": "string", "description": "生物标志物"},
                "intervention": {"type": "string", "description": "干预措施/药物"}
            },
            "required": []
        }
