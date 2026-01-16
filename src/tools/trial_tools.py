"""
临床试验工具

提供 ClinicalTrials.gov 搜索功能
"""
from typing import Dict, Any, Optional, List
from src.tools.base_tool import BaseTool
from src.tools.api_clients.clinicaltrials_client import ClinicalTrialsClient
from src.utils.logger import mtb_logger as logger


class ClinicalTrialsTool(BaseTool):
    """ClinicalTrials.gov 搜索工具"""

    def __init__(self):
        super().__init__(
            name="search_clinical_trials",
            description="搜索 ClinicalTrials.gov 中国招募中的试验。输入肿瘤类型、生物标志物、干预措施"
        )
        self.client = ClinicalTrialsClient()

    def _call_real_api(
        self,
        cancer_type: str = "",
        biomarker: str = "",
        intervention: str = "",
        location: str = "China",
        max_results: int = 5,
        **kwargs
    ) -> Optional[str]:
        """
        调用 ClinicalTrials.gov API v2

        Args:
            cancer_type: 肿瘤类型
            biomarker: 生物标志物
            intervention: 干预措施/药物
            location: 地点
            max_results: 最大结果数

        Returns:
            格式化的搜索结果
        """
        # 构建条件查询
        condition_parts = []
        if cancer_type:
            condition_parts.append(cancer_type)
        if biomarker:
            condition_parts.append(biomarker)

        condition = " ".join(condition_parts) if condition_parts else "cancer"

        results = self.client.search_trials(
            condition=condition,
            intervention=intervention if intervention else None,
            location=location,
            status="RECRUITING",
            max_results=max_results
        )

        if not results:
            return self._no_results_response(cancer_type, biomarker, intervention)

        return self._format_results(cancer_type, biomarker, intervention, results)

    def _format_results(
        self,
        cancer_type: str,
        biomarker: str,
        intervention: str,
        results: List[Dict]
    ) -> str:
        """格式化搜索结果"""
        output = [
            "**ClinicalTrials.gov 搜索结果**\n",
            "**搜索条件**:",
            f"- 肿瘤类型: {cancer_type or 'N/A'}",
            f"- 生物标志物: {biomarker or 'N/A'}",
            f"- 干预措施: {intervention or 'N/A'}",
            "- 地区: 中国",
            "- 状态: Recruiting\n",
            f"**匹配试验（共{len(results)}项）**:\n",
            "---\n"
        ]

        for i, trial in enumerate(results, 1):
            nct_id = trial.get("nct_id", "N/A")
            title = trial.get("brief_title", "无标题")
            phase = trial.get("phase", "N/A")
            status = trial.get("status", "N/A")
            enrollment = trial.get("enrollment", 0)
            sponsor = trial.get("sponsor", "")
            interventions = trial.get("interventions", [])
            locations = trial.get("locations", [])
            eligibility = trial.get("eligibility_criteria", "")

            output.append(f"### {i}. {nct_id} - {title[:80]}{'...' if len(title) > 80 else ''}\n")
            output.append(f"**Phase**: {phase}")
            output.append(f"**状态**: {status}")
            output.append(f"**入组人数**: {enrollment} patients")
            output.append(f"**资助方**: {sponsor}")

            # 干预措施
            if interventions:
                drug_list = [f"{intr.get('name', '')} ({intr.get('type', '')})" for intr in interventions[:3]]
                output.append(f"**药物**: {', '.join(drug_list)}")

            # 入选标准 (截取)
            if eligibility:
                eligibility_preview = eligibility[:400] + "..." if len(eligibility) > 400 else eligibility
                output.append(f"\n**关键入组标准**:\n{eligibility_preview}")

            # 中国中心
            if locations:
                china_sites = [f"{loc.get('facility', '')} ({loc.get('city', '')})" for loc in locations[:5]]
                output.append(f"\n**中国中心**:")
                for site in china_sites:
                    output.append(f"- {site}")

            output.append(f"\n**参考**: {trial.get('url', '')}")
            output.append("\n---\n")

        output.append("\n**备注**: 以上为实时数据，实际试验入组需联系各中心PI确认资格。")

        return "\n".join(output)

    def _no_results_response(self, cancer_type: str, biomarker: str, intervention: str) -> str:
        """无结果响应"""
        return f"""**ClinicalTrials.gov 搜索结果**

**搜索条件**:
- 肿瘤类型: {cancer_type or 'N/A'}
- 生物标志物: {biomarker or 'N/A'}
- 干预措施: {intervention or 'N/A'}
- 地区: 中国
- 状态: Recruiting

**未找到匹配的临床试验。**

建议:
1. 尝试放宽搜索条件
2. 使用英文搜索 (如 "NSCLC" 而非 "非小细胞肺癌")
3. 检查其他试验状态 (如 NOT_YET_RECRUITING)
"""

    def _generate_mock_response(
        self,
        cancer_type: str = "",
        biomarker: str = "",
        intervention: str = "",
        **kwargs
    ) -> str:
        """生成模拟响应"""
        return f"""**ClinicalTrials.gov 搜索结果（模拟数据）**

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
                "cancer_type": {"type": "string", "description": "肿瘤类型，如 NSCLC, 乳腺癌"},
                "biomarker": {"type": "string", "description": "生物标志物，如 EGFR mutation"},
                "intervention": {"type": "string", "description": "干预措施/药物，如 osimertinib"},
                "max_results": {"type": "integer", "description": "最大结果数，默认 5", "default": 5}
            },
            "required": []
        }


if __name__ == "__main__":
    # 测试
    tool = ClinicalTrialsTool()

    print("=== 临床试验搜索测试 ===")
    result = tool.invoke(
        cancer_type="NSCLC",
        biomarker="EGFR mutation",
        intervention="osimertinib",
        max_results=3
    )
    print(result)
