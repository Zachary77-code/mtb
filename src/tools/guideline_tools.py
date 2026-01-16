"""
指南工具（占位符实现）
"""
from src.tools.base_tool import BaseMockTool
from typing import Dict, Any


class NCCNTool(BaseMockTool):
    """NCCN 指南查询工具"""

    def __init__(self):
        super().__init__(
            name="search_nccn",
            description="查询 NCCN 指南获取标准治疗建议"
        )

    def _generate_mock_response(self, cancer_type: str = "", biomarker: str = "", line: str = "", **kwargs) -> str:
        return f"""
**NCCN 指南建议（模拟数据）**

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
                "cancer_type": {"type": "string"},
                "biomarker": {"type": "string"},
                "line": {"type": "string", "description": "治疗线：first-line, second-line等"}
            },
            "required": ["cancer_type"]
        }


class FDALabelTool(BaseMockTool):
    """FDA 药品说明书查询工具"""

    def __init__(self):
        super().__init__(
            name="search_fda_labels",
            description="查询 FDA 药品说明书获取剂量、禁忌症、警告信息"
        )

    def _generate_mock_response(self, drug_name: str = "", **kwargs) -> str:
        return f"""
**FDA 药品说明书（模拟数据）**

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


class DrugBankTool(BaseMockTool):
    """DrugBank 药物数据库查询工具"""

    def __init__(self):
        super().__init__(
            name="search_drugbank",
            description="查询 DrugBank 获取药物代谢、相互作用信息"
        )

    def _generate_mock_response(self, drug_name: str = "", **kwargs) -> str:
        return f"""
**DrugBank 查询结果（模拟数据）**

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
                "drug_name": {"type": "string"}
            },
            "required": ["drug_name"]
        }
