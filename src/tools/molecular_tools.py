"""
分子工具（占位符实现）
"""
from src.tools.base_tool import BaseMockTool
from typing import Dict, Any


class OncoKBTool(BaseMockTool):
    """OncoKB 数据库查询工具"""

    def __init__(self):
        super().__init__(
            name="search_oncokb",
            description="查询 OncoKB 数据库获取变异的证据等级和治疗建议。输入格式：基因名-变异-肿瘤类型（如 EGFR-L858R-NSCLC）"
        )

    def _generate_mock_response(self, gene: str = "", variant: str = "", cancer_type: str = "", **kwargs) -> str:
        return f"""
**OncoKB 查询结果（模拟数据）**

**变异**: {gene} {variant}
**肿瘤类型**: {cancer_type}
**证据等级**: Level 1 (FDA-approved biomarker)
**治疗推荐**:
- Osimertinib (奥希替尼/泰瑞沙) - FDA approved, NMPA approved
- Dacomitinib (达克替尼) - FDA approved (second-line)

**临床试验**:
- FLAURA Trial: 71% ORR, 18.9 months mPFS [PMID: 29151359]

**参考**: https://www.oncokb.org/gene/{gene}/{variant}
"""

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "gene": {"type": "string", "description": "基因名称，如 EGFR"},
                "variant": {"type": "string", "description": "变异，如 L858R"},
                "cancer_type": {"type": "string", "description": "肿瘤类型，如 NSCLC"}
            },
            "required": ["gene"]
        }


class ClinVarTool(BaseMockTool):
    """ClinVar 数据库查询工具"""

    def __init__(self):
        super().__init__(
            name="search_clinvar",
            description="查询 ClinVar 数据库获取变异的致病性分类"
        )

    def _generate_mock_response(self, gene: str = "", variant: str = "", **kwargs) -> str:
        return f"""
**ClinVar 查询结果（模拟数据）**

**变异**: {gene} {variant}
**致病性分类**: Pathogenic (★★★★)
**审查状态**: Reviewed by expert panel
**临床意义**: 该变异与癌症易感性相关

**参考**: https://www.ncbi.nlm.nih.gov/clinvar/?term={gene}[gene]+AND+{variant}
"""

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "gene": {"type": "string"},
                "variant": {"type": "string"}
            },
            "required": ["gene", "variant"]
        }


class CosmicTool(BaseMockTool):
    """COSMIC 数据库查询工具"""

    def __init__(self):
        super().__init__(
            name="search_cosmic",
            description="查询 COSMIC 数据库获取变异在特定肿瘤类型的频率"
        )

    def _generate_mock_response(self, gene: str = "", variant: str = "", cancer_type: str = "", **kwargs) -> str:
        return f"""
**COSMIC 查询结果（模拟数据）**

**变异**: {gene} {variant}
**肿瘤类型**: {cancer_type}
**突变频率**: 15.3% (n=2,405 samples)
**突变类型分布**:
- 替代突变 (Substitution): 98%
- 缺失 (Deletion): 2%

**参考**: https://cancer.sanger.ac.uk/cosmic/gene/analysis?ln={gene}
"""

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "gene": {"type": "string"},
                "variant": {"type": "string"},
                "cancer_type": {"type": "string"}
            },
            "required": ["gene"]
        }
