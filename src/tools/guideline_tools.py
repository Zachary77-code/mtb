"""
指南工具

提供临床指南、药物说明书和药物相互作用查询
- NCCNTool: NCCN 指南 (基于 RAG)
- FDALabelTool: FDA 药品说明书
- RxNormTool: 药物相互作用 (替代 DrugBank)
"""
from typing import Dict, Any, Optional, List
from src.tools.base_tool import BaseTool
from src.tools.api_clients.fda_client import FDAClient
from src.tools.api_clients.rxnorm_client import RxNormClient
from src.utils.logger import mtb_logger as logger


class NCCNTool(BaseTool):
    """
    NCCN 指南查询工具

    基于本地 PDF 的 RAG (Retrieval Augmented Generation) 实现
    """

    def __init__(self):
        super().__init__(
            name="search_nccn",
            description="查询 NCCN 指南获取标准治疗建议"
        )
        self._rag = None  # 延迟加载

    @property
    def rag(self):
        """延迟加载 RAG 系统"""
        if self._rag is None:
            from src.tools.rag.nccn_rag import get_nccn_rag
            self._rag = get_nccn_rag()
        return self._rag

    def _call_real_api(
        self,
        cancer_type: str = "",
        biomarker: str = "",
        line: str = "",
        **kwargs
    ) -> Optional[str]:
        """
        调用 NCCN RAG 系统

        Args:
            cancer_type: 肿瘤类型
            biomarker: 生物标志物
            line: 治疗线

        Returns:
            指南检索结果
        """
        # 构建查询
        query_parts = []
        if cancer_type:
            query_parts.append(cancer_type)
        if biomarker:
            query_parts.append(biomarker)
        if line:
            query_parts.append(f"{line} treatment")

        if not query_parts:
            query_parts.append("cancer treatment guidelines")

        query = " ".join(query_parts)

        try:
            result = self.rag.query(query, cancer_type=cancer_type if cancer_type else None)
            return result
        except Exception as e:
            logger.error(f"[NCCNTool] RAG 查询失败: {e}")
            return None

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "cancer_type": {"type": "string", "description": "肿瘤类型"},
                "biomarker": {"type": "string", "description": "生物标志物"},
                "line": {"type": "string", "description": "治疗线：first-line, second-line等"}
            },
            "required": ["cancer_type"]
        }


class FDALabelTool(BaseTool):
    """FDA 药品说明书查询工具"""

    def __init__(self):
        super().__init__(
            name="search_fda_labels",
            description="查询 FDA 药品说明书获取剂量、禁忌症、警告信息"
        )
        self.client = FDAClient()

    def _call_real_api(self, drug_name: str = "", **kwargs) -> Optional[str]:
        """调用 openFDA API"""
        if not drug_name:
            return None

        label = self.client.search_drug_label(drug_name)

        if not label:
            return self._no_results_response(drug_name)

        return self._format_results(drug_name, label)

    def _format_results(self, drug_name: str, label: Dict) -> str:
        """格式化结果"""
        generic_name = label.get("generic_name", drug_name)
        brand_name = label.get("brand_name", "")
        manufacturer = label.get("manufacturer", "")

        output = [
            "**FDA 药品说明书**\n",
            f"**药物**: {generic_name}",
        ]

        if brand_name:
            output.append(f"**商品名**: {brand_name}")
        if manufacturer:
            output.append(f"**生产商**: {manufacturer}")

        output.append("")

        # 适应症
        indications = label.get("indications", "")
        if indications:
            output.append("### 适应症")
            output.append(indications)
            output.append("")

        # 剂量
        dosage = label.get("dosage", "")
        if dosage:
            output.append("### 剂量与用法")
            output.append(dosage)
            output.append("")

        # 黑框警告
        boxed = label.get("boxed_warning", "")
        if boxed:
            output.append("### ⚠️ 黑框警告")
            output.append(boxed)
            output.append("")

        # 警告
        warnings = label.get("warnings", "")
        if warnings:
            output.append("### 警告与注意事项")
            output.append(warnings)
            output.append("")

        # 禁忌症
        contraindications = label.get("contraindications", "")
        if contraindications:
            output.append("### 禁忌症")
            output.append(contraindications)
            output.append("")

        # 药物相互作用
        interactions = label.get("drug_interactions", "")
        if interactions:
            output.append("### 药物相互作用")
            output.append(interactions)
            output.append("")

        # 不良反应
        adverse = label.get("adverse_reactions", "")
        if adverse:
            output.append("### 不良反应")
            output.append(adverse)

        output.append(f"\n**参考**: https://labels.fda.gov (搜索 {generic_name})")

        return "\n".join(output)

    def _no_results_response(self, drug_name: str) -> str:
        """无结果响应"""
        return f"""**FDA 药品说明书**

**药物**: {drug_name}

未找到该药物的 FDA 说明书。

可能原因:
1. 药物名称拼写错误
2. 该药物未在美国 FDA 批准
3. 尝试使用通用名或商品名搜索

建议:
- 访问 https://labels.fda.gov 直接搜索
- 使用英文药物名称
"""

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "drug_name": {"type": "string", "description": "药物名称"}
            },
            "required": ["drug_name"]
        }


class RxNormTool(BaseTool):
    """
    RxNorm 药物相互作用查询工具 (替代 DrugBank)

    提供药物代谢和相互作用信息
    """

    def __init__(self):
        super().__init__(
            name="search_rxnorm",
            description="查询 RxNorm 获取药物代谢、相互作用信息"
        )
        self.client = RxNormClient()

    def _call_real_api(
        self,
        drug_name: str = "",
        check_interactions: List[str] = None,
        **kwargs
    ) -> Optional[str]:
        """
        调用 RxNorm API

        Args:
            drug_name: 主要药物名称
            check_interactions: 要检查相互作用的其他药物列表

        Returns:
            药物相互作用信息
        """
        if not drug_name:
            return None

        # 获取药物基本信息
        drug_info = self.client.get_drug_info(drug_name)

        # 获取相互作用
        interactions = self.client.get_drug_interactions(drug_name)

        # 如果提供了其他药物，检查多药相互作用
        multi_interactions = []
        if check_interactions:
            all_drugs = [drug_name] + check_interactions
            multi_interactions = self.client.check_interaction(all_drugs)

        # 如果 RxNorm 无相互作用数据，尝试从 FDA 说明书获取
        fda_interactions = None
        if not interactions:
            fda_client = FDAClient()
            label = fda_client.search_drug_label(drug_name)
            if label:
                fda_interactions = label.get("drug_interactions", "")
                logger.info(f"[RxNormTool] RxNorm 无数据，使用 FDA 说明书补充")

        return self._format_results(drug_name, drug_info, interactions, multi_interactions, fda_interactions)

    def _format_results(
        self,
        drug_name: str,
        drug_info: Optional[Dict],
        interactions: List[Dict],
        multi_interactions: List[Dict],
        fda_interactions: Optional[str] = None
    ) -> str:
        """格式化结果"""
        output = [
            "**RxNorm 药物查询结果**\n",
            f"**药物**: {drug_name}",
        ]

        if drug_info:
            rxcui = drug_info.get("rxcui", "")
            drug_class = drug_info.get("drug_class", [])

            output.append(f"**RxCUI**: {rxcui}")
            if drug_class:
                output.append(f"**药物分类**: {', '.join(drug_class[:5])}")

        output.append("")

        # 已知相互作用 (RxNorm)
        if interactions:
            output.append("### 主要药物相互作用 (RxNorm)\n")
            for i, intr in enumerate(interactions[:8], 1):
                drugs = ", ".join(intr.get("drugs", []))
                description = intr.get("description", "")
                severity = intr.get("severity", "N/A")

                output.append(f"**{i}. {drugs}**")
                output.append(f"- 严重程度: {severity}")
                output.append(f"- 说明: {description}")
                output.append("")
        elif fda_interactions:
            # 使用 FDA 说明书数据作为补充
            output.append("### 药物相互作用 (FDA 说明书)\n")
            output.append("*注: RxNorm 无数据，以下信息来自 FDA 药品说明书*\n")
            output.append(fda_interactions)
            output.append("")
        else:
            output.append("未找到药物相互作用记录。\n")

        # 多药相互作用
        if multi_interactions:
            output.append("### 多药相互作用检查\n")
            for intr in multi_interactions[:5]:
                drugs = ", ".join(intr.get("drugs", []))
                severity = intr.get("severity", "N/A")
                output.append(f"- **{drugs}**: {severity}")
            output.append("")

        output.append(f"**参考**: https://rxnav.nlm.nih.gov")

        return "\n".join(output)

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "drug_name": {"type": "string", "description": "药物名称"},
                "check_interactions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要检查相互作用的其他药物列表"
                }
            },
            "required": ["drug_name"]
        }


# 保留旧名称以兼容
DrugBankTool = RxNormTool


if __name__ == "__main__":
    # 测试
    print("=== NCCN 工具测试 ===")
    nccn_tool = NCCNTool()
    result = nccn_tool.invoke(cancer_type="NSCLC", biomarker="EGFR mutation", line="first-line")
    print(result)

    print("\n=== FDA 说明书测试 ===")
    fda_tool = FDALabelTool()
    result = fda_tool.invoke(drug_name="osimertinib")
    print(result)

    print("\n=== RxNorm 工具测试 ===")
    rxnorm_tool = RxNormTool()
    result = rxnorm_tool.invoke(drug_name="osimertinib")
    print(result)
