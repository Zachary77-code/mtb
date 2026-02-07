"""
分子工具

提供变异证据、致病性分类和突变频率查询
- CIViCTool: 变异证据等级 (替代 OncoKB)
- ClinVarTool: 变异致病性分类
- cBioPortalTool: 突变频率统计 (替代 COSMIC)
"""
from typing import Dict, Any, Optional, List
from src.tools.base_tool import BaseTool
from src.tools.api_clients.civic_client import CIViCClient
from src.tools.api_clients.ncbi_client import get_ncbi_client
from src.tools.api_clients.cbioportal_client import get_cbioportal_client
from src.utils.logger import mtb_logger as logger


class CIViCTool(BaseTool):
    """
    CIViC 数据库查询工具 (替代 OncoKB)

    提供变异的临床证据等级和治疗意义
    """

    def __init__(self):
        super().__init__(
            name="search_civic",
            description="查询 CIViC 数据库获取变异的证据等级和治疗建议。输入格式：基因名-变异-肿瘤类型（如 EGFR-L858R-NSCLC）"
        )
        self.client = CIViCClient()

    def _call_real_api(
        self,
        gene: str = "",
        variant: str = "",
        cancer_type: str = "",
        **kwargs
    ) -> Optional[str]:
        """调用 CIViC API"""
        if not gene:
            return None

        # 获取治疗意义
        implications = self.client.get_therapeutic_implications(gene, variant)

        if not implications:
            return self._no_results_response(gene, variant, cancer_type)

        return self._format_results(gene, variant, cancer_type, implications)

    def _format_results(
        self,
        gene: str,
        variant: str,
        cancer_type: str,
        implications: Dict
    ) -> str:
        """格式化结果"""
        output = [
            "**CIViC 查询结果**\n",
            f"**变异**: {gene} {variant}",
            f"**肿瘤类型**: {cancer_type or 'All'}\n"
        ]

        if not implications.get("has_therapeutic_evidence"):
            output.append("未找到该变异的治疗相关证据。\n")
            return "\n".join(output)

        # 证据等级分布
        by_level = implications.get("evidence_by_level", {})
        output.append("**证据等级分布**:")
        for level, count in sorted(by_level.items()):
            level_desc = {
                "A": "已验证 (Validated)",
                "B": "临床 (Clinical)",
                "C": "案例研究 (Case Study)",
                "D": "临床前 (Preclinical)",
                "E": "推断 (Inferential)"
            }.get(level, level)
            output.append(f"- Level {level} ({level_desc}): {count} 条")

        output.append("")

        # 治疗相关证据
        therapeutic = implications.get("top_therapeutic_evidence", [])
        if therapeutic:
            output.append("**治疗相关证据**:\n")
            for i, evidence in enumerate(therapeutic, 1):  # CIViC API 已限制
                drugs = ", ".join(evidence.get("drugs", []))
                disease = evidence.get("disease", "")
                significance = evidence.get("clinical_significance", "")
                level = evidence.get("evidence_level", "")
                direction = evidence.get("evidence_direction", "")
                pmid = evidence.get("pubmed_id")

                output.append(f"{i}. **{drugs}**")
                output.append(f"   - 疾病: {disease}")
                output.append(f"   - 临床意义: {significance} ({direction})")
                output.append(f"   - 证据等级: Level {level}")
                if pmid:
                    output.append(f"   - 参考: PMID {pmid}")
                output.append("")

        output.append(f"**CIViC 链接**: {implications.get('civic_url', '')}")
        output.append("\n**注意**: CIViC 为开放数据库，证据需结合最新指南使用。")

        return "\n".join(output)

    def _no_results_response(self, gene: str, variant: str, cancer_type: str) -> str:
        """无结果响应"""
        return f"""**CIViC 查询结果**

**变异**: {gene} {variant}
**肿瘤类型**: {cancer_type or 'All'}

未找到该变异在 CIViC 数据库中的记录。

可能原因:
1. 变异命名不一致（尝试标准 HGVS 格式）
2. 该变异尚未被 CIViC 收录
3. 基因名称拼写错误

建议搜索: https://civicdb.org/genes/{gene}
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


class ClinVarTool(BaseTool):
    """ClinVar 数据库查询工具"""

    def __init__(self):
        super().__init__(
            name="search_clinvar",
            description="查询 ClinVar 数据库获取变异的致病性分类"
        )
        self.client = get_ncbi_client()  # 使用全局单例

    def _call_real_api(
        self,
        gene: str = "",
        variant: str = "",
        **kwargs
    ) -> Optional[str]:
        """调用 ClinVar API"""
        if not gene:
            return None

        results = self.client.search_clinvar(gene, variant)

        if not results:
            return self._no_results_response(gene, variant)

        return self._format_results(gene, variant, results)

    def _format_results(self, gene: str, variant: str, results: List[Dict]) -> str:
        """格式化结果"""
        output = [
            "**ClinVar 查询结果**\n",
            f"**查询**: {gene} {variant}",
            f"**找到 {len(results)} 条记录**\n",
            "---\n"
        ]

        for i, result in enumerate(results, 1):  # ClinVar retmax:20 已限制
            variation_name = result.get("variation_name", "N/A")
            classification = result.get("classification", "N/A")
            review_status = result.get("review_status", "N/A")
            url = result.get("url", "")

            # 致病性评级星标
            stars = {
                "criteria provided, single submitter": "★★",
                "criteria provided, multiple submitters, no conflicts": "★★★",
                "reviewed by expert panel": "★★★★",
                "practice guideline": "★★★★★"
            }.get(review_status.lower(), "★")

            output.append(f"### {i}. {variation_name}\n")
            output.append(f"**致病性分类**: {classification} ({stars})")
            output.append(f"**审查状态**: {review_status}")
            output.append(f"**链接**: {url}\n")
            output.append("---\n")

        output.append("\n**说明**: 星标表示审查等级，★★★★★ 为最高 (Practice Guideline)")

        return "\n".join(output)

    def _no_results_response(self, gene: str, variant: str) -> str:
        """无结果响应"""
        return f"""**ClinVar 查询结果**

**查询**: {gene} {variant}

未找到该变异在 ClinVar 数据库中的记录。

建议:
1. 检查变异命名是否正确
2. 尝试使用 HGVS 格式 (如 NM_005228.5:c.2573T>G)
3. 直接搜索: https://www.ncbi.nlm.nih.gov/clinvar/?term={gene}
"""

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "gene": {"type": "string", "description": "基因名称"},
                "variant": {"type": "string", "description": "变异"}
            },
            "required": ["gene", "variant"]
        }


class cBioPortalTool(BaseTool):
    """
    cBioPortal 数据库查询工具 (替代 COSMIC)

    提供突变频率和癌症基因组数据
    """

    def __init__(self):
        super().__init__(
            name="search_cbioportal",
            description="查询 cBioPortal 获取变异在特定肿瘤类型的频率"
        )
        self.client = get_cbioportal_client()

    def _call_real_api(
        self,
        gene: str = "",
        variant: str = "",
        cancer_type: str = "",
        **kwargs
    ) -> Optional[str]:
        """调用 cBioPortal API"""
        if not gene:
            return None

        if variant:
            # 查询特定变异频率
            result = self.client.get_variant_frequency_summary(gene, variant)
        else:
            # 查询基因整体突变情况
            result = self.client.get_mutation_frequency(gene, cancer_type)

        if not result or "error" in result:
            return self._no_results_response(gene, variant, cancer_type)

        return self._format_results(gene, variant, cancer_type, result)

    def _format_results(
        self,
        gene: str,
        variant: str,
        cancer_type: str,
        result: Dict
    ) -> str:
        """格式化结果"""
        output = [
            "**cBioPortal 查询结果**\n",
            f"**基因**: {gene}",
        ]

        if variant:
            output.append(f"**变异**: {variant}")
            output.append(f"**变异计数**: {result.get('variant_count', 0)}")
            output.append(f"**总突变数**: {result.get('total_gene_mutations', 0)}")
            output.append(f"**频率**: {result.get('frequency_percentage', 0)}%")
        else:
            output.append(f"**分析研究数**: {result.get('studies_analyzed', 0)}")

        output.append(f"**肿瘤类型**: {cancer_type or 'All'}\n")

        # 按癌症类型分布
        by_cancer = result.get("by_cancer_type", {})
        if by_cancer:
            output.append("**按癌症类型分布**:")
            for ct, data in list(by_cancer.items())[:10]:
                count = data.get("mutation_count", 0) if isinstance(data, dict) else data
                output.append(f"- {ct}: {count} mutations")

        # 常见突变
        top_mutations = result.get("top_mutations", [])
        if top_mutations:
            output.append("\n**常见突变 (Top 10)**:")
            for mut in top_mutations[:10]:
                output.append(f"- {mut['mutation']}: {mut['count']}")

        output.append(f"\n**参考**: {result.get('cbioportal_url', 'https://www.cbioportal.org')}")

        return "\n".join(output)

    def _no_results_response(self, gene: str, variant: str, cancer_type: str) -> str:
        """无结果响应"""
        return f"""**cBioPortal 查询结果**

**基因**: {gene}
**变异**: {variant or 'All'}
**肿瘤类型**: {cancer_type or 'All'}

未找到相关数据。

建议:
1. 检查基因名称是否正确
2. 直接访问: https://www.cbioportal.org/results/mutations?gene_list={gene}
"""

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "gene": {"type": "string", "description": "基因名称"},
                "variant": {"type": "string", "description": "变异（可选）"},
                "cancer_type": {"type": "string", "description": "肿瘤类型（可选）"}
            },
            "required": ["gene"]
        }


# 保留旧名称以兼容
OncoKBTool = CIViCTool  # CIViC 替代 OncoKB
CosmicTool = cBioPortalTool  # cBioPortal 替代 COSMIC


if __name__ == "__main__":
    # 测试
    print("=== CIViC 工具测试 ===")
    civic_tool = CIViCTool()
    result = civic_tool.invoke(gene="EGFR", variant="L858R", cancer_type="NSCLC")
    print(result)

    print("\n=== ClinVar 工具测试 ===")
    clinvar_tool = ClinVarTool()
    result = clinvar_tool.invoke(gene="EGFR", variant="L858R")
    print(result)

    print("\n=== cBioPortal 工具测试 ===")
    cbio_tool = cBioPortalTool()
    result = cbio_tool.invoke(gene="EGFR", variant="L858R")
    print(result)
