"""
API 客户端层

提供对各医学数据库的访问接口
"""
from src.tools.api_clients.ncbi_client import NCBIClient
from src.tools.api_clients.clinicaltrials_client import ClinicalTrialsClient
from src.tools.api_clients.fda_client import FDAClient
from src.tools.api_clients.rxnorm_client import RxNormClient
from src.tools.api_clients.civic_client import CIViCClient
from src.tools.api_clients.gdc_client import GDCClient
from src.tools.api_clients.cbioportal_client import cBioPortalClient  # 向后兼容

__all__ = [
    "NCBIClient",
    "ClinicalTrialsClient",
    "FDAClient",
    "RxNormClient",
    "CIViCClient",
    "GDCClient",
    "cBioPortalClient",  # 向后兼容
]
