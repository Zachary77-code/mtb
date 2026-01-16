"""
工具库
"""
from src.tools.base_tool import BaseTool
from src.tools.molecular_tools import CIViCTool, ClinVarTool, cBioPortalTool
from src.tools.literature_tools import PubMedTool
from src.tools.trial_tools import ClinicalTrialsTool
from src.tools.guideline_tools import NCCNTool, FDALabelTool, RxNormTool

# 保留旧名称作为别名（向后兼容）
OncoKBTool = CIViCTool
CosmicTool = cBioPortalTool
DrugBankTool = RxNormTool

__all__ = [
    "BaseTool",
    # 新名称（推荐使用）
    "CIViCTool",
    "ClinVarTool",
    "cBioPortalTool",
    "PubMedTool",
    "ClinicalTrialsTool",
    "NCCNTool",
    "FDALabelTool",
    "RxNormTool",
    # 旧名称别名（向后兼容）
    "OncoKBTool",
    "CosmicTool",
    "DrugBankTool"
]
