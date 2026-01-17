"""
病例数据模型（Pydantic）
"""
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class MolecularAlteration(BaseModel):
    """分子变异"""

    gene: str = Field(..., description="基因名称，如 EGFR")
    alteration_type: str = Field(
        ...,
        description="变异类型：SNV（点突变）、CNV（拷贝数变异）、Fusion（融合）等"
    )
    variant: Optional[str] = Field(None, description="具体变异，如 L858R")
    vaf: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="变异等位基因频率（Variant Allele Frequency）"
    )
    evidence_level: Optional[str] = Field(
        None,
        description="证据等级，如 OncoKB Level 1-4"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "gene": "EGFR",
                "alteration_type": "SNV",
                "variant": "L858R",
                "vaf": 0.45,
                "evidence_level": "Level 1"
            }
        }


class TreatmentLine(BaseModel):
    """治疗线"""

    line_number: int = Field(..., ge=1, description="治疗线数（1、2、3...）")
    regimen: str = Field(..., description="治疗方案名称")
    duration_months: Optional[float] = Field(
        None,
        ge=0.0,
        description="治疗持续时间（月）"
    )
    best_response: Optional[str] = Field(
        None,
        description="最佳疗效：CR（完全缓解）、PR（部分缓解）、SD（疾病稳定）、PD（疾病进展）"
    )
    discontinuation_reason: Optional[str] = Field(
        None,
        description="停药原因：如疾病进展、不良反应等"
    )
    grade3_plus_toxicities: Optional[List[str]] = Field(
        default_factory=list,
        description="3级及以上不良反应"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "line_number": 1,
                "regimen": "吉非替尼（Gefitinib）",
                "duration_months": 12.0,
                "best_response": "PR",
                "discontinuation_reason": "疾病进展",
                "grade3_plus_toxicities": []
            }
        }


class OrganFunction(BaseModel):
    """器官功能参数"""

    # 肾功能
    egfr_ml_min: Optional[float] = Field(
        None,
        ge=0.0,
        description="肾小球滤过率（eGFR），mL/min"
    )
    creatinine_clearance: Optional[float] = Field(
        None,
        ge=0.0,
        description="肌酐清除率（CrCl），mL/min"
    )
    creatinine: Optional[float] = Field(
        None,
        ge=0.0,
        description="血肌酐，umol/L 或 mg/dL"
    )

    # 肝功能
    alt_u_l: Optional[float] = Field(
        None,
        ge=0.0,
        description="丙氨酸转氨酶（ALT），U/L"
    )
    ast_u_l: Optional[float] = Field(
        None,
        ge=0.0,
        description="天冬氨酸转氨酶（AST），U/L"
    )
    bilirubin_mg_dl: Optional[float] = Field(
        None,
        ge=0.0,
        description="总胆红素，mg/dL"
    )

    # 骨髓功能
    platelet_count: Optional[float] = Field(
        None,
        ge=0.0,
        description="血小板计数，×10^9/L"
    )
    neutrophil_count: Optional[float] = Field(
        None,
        ge=0.0,
        description="中性粒细胞计数，×10^9/L"
    )
    hemoglobin_g_dl: Optional[float] = Field(
        None,
        ge=0.0,
        description="血红蛋白，g/dL"
    )

    # 心功能
    lvef_percent: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="左室射血分数（LVEF），%"
    )

    # 体能状态
    ecog_ps: Optional[int] = Field(
        None,
        ge=0,
        le=4,
        description="ECOG 体能状态评分（0-4）"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "egfr_ml_min": 85.0,
                "alt_u_l": 45.0,
                "ast_u_l": 38.0,
                "bilirubin_mg_dl": 0.8,
                "platelet_count": 200.0,
                "neutrophil_count": 3.5,
                "lvef_percent": 60.0,
                "ecog_ps": 1
            }
        }


class CaseData(BaseModel):
    """结构化病例数据"""

    # ==================== 基本信息 ====================
    patient_id: Optional[str] = Field(None, description="患者编号")
    age: Optional[int] = Field(None, ge=0, le=120, description="年龄")
    sex: Optional[str] = Field(None, description="性别：男/女")

    # ==================== 肿瘤信息 ====================
    primary_cancer: str = Field(..., description="原发肿瘤类型，如非小细胞肺癌")
    histology: Optional[str] = Field(None, description="病理类型，如腺癌")
    stage: Optional[str] = Field(None, description="分期，如 IV 期")
    metastatic_sites: Optional[List[str]] = Field(
        default_factory=list,
        description="转移部位列表，如 ['骨', '肝', '肺']"
    )

    # ==================== 分子特征 ====================
    molecular_profile: List[MolecularAlteration] = Field(
        default_factory=list,
        description="分子变异列表"
    )
    msi_status: Optional[str] = Field(
        None,
        description="微卫星不稳定性状态：MSI-H（高）、MSS（稳定）"
    )
    tmb_score: Optional[float] = Field(
        None,
        ge=0.0,
        description="肿瘤突变负荷（TMB），mut/Mb"
    )
    pd_l1_tps: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="PD-L1 TPS（肿瘤比例得分），%"
    )
    pd_l1_cps: Optional[float] = Field(
        None,
        ge=0.0,
        description="PD-L1 CPS（联合阳性评分）"
    )

    # ==================== 治疗史 ====================
    treatment_lines: List[TreatmentLine] = Field(
        default_factory=list,
        description="治疗线列表"
    )
    current_status: str = Field(
        ...,
        description="当前状态：ongoing（治疗中）、progressed（进展）、stable（稳定）等"
    )

    # ==================== 器官功能 ====================
    organ_function: OrganFunction = Field(
        default_factory=OrganFunction,
        description="器官功能参数"
    )

    # ==================== 合并症 ====================
    comorbidities: Optional[List[str]] = Field(
        default_factory=list,
        description="合并症列表，如 ['高血压', '糖尿病', '肾损伤']"
    )

    # ==================== 肿瘤标志物 ====================
    tumor_markers: Optional[Dict[str, float]] = Field(
        default_factory=dict,
        description="肿瘤标志物，如 {'cea_ng_ml': 112, 'ca199_u_ml': 145}"
    )

    # ==================== 原始文本（用于调试） ====================
    raw_text: str = Field(..., description="原始病历文本")

    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "P001",
                "age": 65,
                "sex": "男",
                "primary_cancer": "非小细胞肺癌",
                "histology": "腺癌",
                "stage": "IV期",
                "metastatic_sites": ["骨", "肝"],
                "molecular_profile": [
                    {
                        "gene": "EGFR",
                        "alteration_type": "SNV",
                        "variant": "L858R",
                        "vaf": 0.45
                    }
                ],
                "msi_status": "MSS",
                "tmb_score": 5.2,
                "pd_l1_tps": 10.0,
                "pd_l1_cps": 15.0,
                "treatment_lines": [
                    {
                        "line_number": 1,
                        "regimen": "吉非替尼",
                        "duration_months": 12.0,
                        "best_response": "PR",
                        "discontinuation_reason": "疾病进展"
                    }
                ],
                "current_status": "progressed",
                "organ_function": {
                    "ecog_ps": 1,
                    "egfr_ml_min": 85.0,
                    "creatinine": 80.0
                },
                "comorbidities": ["高血压", "糖尿病"],
                "tumor_markers": {"cea_ng_ml": 5.2, "ca199_u_ml": 25.0},
                "raw_text": "患者男性，65岁，诊断为非小细胞肺癌..."
            }
        }


if __name__ == "__main__":
    # 测试数据模型
    test_case = CaseData(
        primary_cancer="非小细胞肺癌",
        current_status="progressed",
        raw_text="测试文本"
    )
    print("CaseData 模型测试成功:")
    print(test_case.model_dump_json(indent=2, exclude={"raw_text"}))
