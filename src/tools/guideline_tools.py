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

    def _generate_mock_response(
        self,
        cancer_type: str = "",
        biomarker: str = "",
        line: str = "",
        **kwargs
    ) -> str:
        """生成模拟响应"""
        return f"""**NCCN 指南建议（模拟数据）**

**肿瘤类型**: {cancer_type}
**生物标志物**: {biomarker}
**治疗线**: {line}

**推荐方案**:

### Category 1 (一级推荐)
1. **Osimertinib** 80mg PO daily
   - 适应症: EGFR敏感突变 (Exon 19del 或 L858R) 一线治疗
   - 证据等级: Phase III RCT (FLAURA)
   - 优势: 更好的PFS和OS，脑转移控制优越

### Category 2A (二级推荐A)
2. **Afatinib** 40mg PO daily
   - 适应症: EGFR突变一线治疗
   - 证据等级: Phase III RCT (LUX-Lung 3/6)

3. **Erlotinib** 150mg PO daily + Bevacizumab IV
   - 适应症: EGFR突变一线治疗（尤其伴脑转移）
   - 证据等级: Phase III RCT (NEJ026)

### Category 2B (二级推荐B)
4. **Gefitinib** 250mg PO daily (中国常用)
   - 适应症: EGFR突变一线治疗
   - 备注: 疗效略逊于Osimertinib，但价格更低

**不推荐**:
- 单药化疗（在EGFR突变阳性患者中）
- 免疫单药治疗（EGFR突变通常PD-L1低表达）

**参考**: NCCN Guidelines for NSCLC Version 5.2024
"""

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
            output.append(indications[:800])
            if len(indications) > 800:
                output.append("...(截断)")
            output.append("")

        # 剂量
        dosage = label.get("dosage", "")
        if dosage:
            output.append("### 剂量与用法")
            output.append(dosage[:800])
            if len(dosage) > 800:
                output.append("...(截断)")
            output.append("")

        # 黑框警告
        boxed = label.get("boxed_warning", "")
        if boxed:
            output.append("### ⚠️ 黑框警告")
            output.append(boxed[:500])
            output.append("")

        # 警告
        warnings = label.get("warnings", "")
        if warnings:
            output.append("### 警告与注意事项")
            output.append(warnings[:600])
            if len(warnings) > 600:
                output.append("...(截断)")
            output.append("")

        # 禁忌症
        contraindications = label.get("contraindications", "")
        if contraindications:
            output.append("### 禁忌症")
            output.append(contraindications[:400])
            output.append("")

        # 药物相互作用
        interactions = label.get("drug_interactions", "")
        if interactions:
            output.append("### 药物相互作用")
            output.append(interactions[:500])
            if len(interactions) > 500:
                output.append("...(截断)")
            output.append("")

        # 不良反应
        adverse = label.get("adverse_reactions", "")
        if adverse:
            output.append("### 不良反应")
            output.append(adverse[:500])
            if len(adverse) > 500:
                output.append("...(截断)")

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

    def _generate_mock_response(self, drug_name: str = "", **kwargs) -> str:
        """生成模拟响应"""
        return f"""**FDA 药品说明书（模拟数据）**

**药物**: {drug_name} (Osimertinib)

### 适应症
- 转移性NSCLC，EGFR Exon 19缺失或L858R突变
- 辅助治疗：术后EGFR突变阳性NSCLC

### 剂量与用法
- **标准剂量**: 80 mg 口服，每日一次
- **给药时间**: 无需考虑进食时间

### 剂量调整
**肝功能不全**:
- 轻度 (Child-Pugh A): 无需调整
- 中度 (Child-Pugh B): 无需调整，但密切监测
- 重度 (Child-Pugh C): 未进行研究，慎用

**肾功能不全**:
- CrCl ≥30 mL/min: 无需调整
- CrCl <30 mL/min: 未进行研究，慎用

### 警告与注意事项
⚠️ **间质性肺病 (ILD)**: 发生率3.3%，可能致命。出现呼吸困难/咳嗽加重应立即评估。

⚠️ **QTc延长**: 发生率0.9%。基线QTc>500ms禁用。治疗中QTc>500ms需暂停用药。

⚠️ **心肌病**: LVEF下降发生率2.7%。基线及治疗中定期监测LVEF。

### 禁忌症
- 对Osimertinib或任何赋形剂过敏

### 药物相互作用
- **CYP3A4诱导剂** (如利福平、苯妥英钠): 避免联用，可能降低Osimertinib血药浓度
- **质子泵抑制剂** (如奥美拉唑): 可能降低吸收，建议间隔给药

### 不良反应 (≥20%)
- 腹泻 (58%)
- 皮疹 (57%)
- 皮肤干燥 (36%)
- 甲沟炎 (35%)

**参考**: https://www.accessdata.fda.gov/drugsatfda_docs/label/2020/208065s014lbl.pdf
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
                output.append(f"- 说明: {description[:200]}{'...' if len(description) > 200 else ''}")
                output.append("")
        elif fda_interactions:
            # 使用 FDA 说明书数据作为补充
            output.append("### 药物相互作用 (FDA 说明书)\n")
            output.append("*注: RxNorm 无数据，以下信息来自 FDA 药品说明书*\n")
            # 限制长度并格式化
            fda_text = fda_interactions[:1500]
            if len(fda_interactions) > 1500:
                fda_text += "\n...(更多信息请查阅完整说明书)"
            output.append(fda_text)
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

    def _generate_mock_response(self, drug_name: str = "", **kwargs) -> str:
        """生成模拟响应"""
        return f"""**RxNorm 查询结果（模拟数据）**

**药物**: {drug_name}

### 代谢
- **主要代谢酶**: CYP3A4, CYP3A5
- **代谢产物**: AZ5104 (活性代谢物)

### 药物相互作用
**主要相互作用** (>20种已知):
1. **Rifampin (利福平)** - CYP3A4强诱导剂
   - 影响: 降低Osimertinib血药浓度约78%
   - 建议: 避免联用，考虑替代药物

2. **Ketoconazole (酮康唑)** - CYP3A4强抑制剂
   - 影响: 升高Osimertinib血药浓度约24%
   - 建议: 密切监测不良反应

3. **Warfarin (华法林)**
   - 影响: Osimertinib可能影响INR
   - 建议: 联用时每周监测INR

### 肾清除
- 肾排泄: <15%
- 主要通过肝脏代谢和胆汁排泄

**参考**: https://go.drugbank.com/drugs/DB09330
"""

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
