"""
openFDA API 客户端

提供药物说明书查询
API 文档: https://open.fda.gov/apis/drug/label/
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, List, Any, Optional
from src.utils.logger import mtb_logger as logger


class FDAClient:
    """openFDA API 客户端"""

    BASE_URL = "https://api.fda.gov/drug/label.json"

    def __init__(self, api_key: str = None):
        """
        初始化 FDA 客户端

        Args:
            api_key: openFDA API Key (可选，提高请求限额)
        """
        self.api_key = api_key
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def search_drug_label(self, drug_name: str) -> Optional[Dict]:
        """
        搜索药物说明书

        Args:
            drug_name: 药物名称 (通用名或商品名)

        Returns:
            说明书内容 {drug_name, indications, dosage, warnings, contraindications,
                       adverse_reactions, drug_interactions}
        """
        # 搜索通用名或商品名
        search_query = f'openfda.generic_name:"{drug_name}" OR openfda.brand_name:"{drug_name}"'

        params = {
            "search": search_query,
            "limit": 1
        }

        if self.api_key:
            params["api_key"] = self.api_key

        try:
            logger.debug(f"[FDA] 搜索药物: {drug_name}")
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            if not results:
                logger.info(f"[FDA] 未找到药物: {drug_name}")
                return None

            return self._parse_label(results[0])

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"[FDA] 未找到药物: {drug_name}")
            else:
                logger.error(f"[FDA] 请求失败: {e}")
            return None
        except Exception as e:
            logger.error(f"[FDA] 搜索失败: {e}")
            return None

    def _parse_label(self, label: Dict) -> Dict:
        """解析药物说明书"""
        openfda = label.get("openfda", {})

        # 药物名称
        generic_names = openfda.get("generic_name", [])
        brand_names = openfda.get("brand_name", [])

        # 各部分内容 (FDA API 返回数组)
        def get_section(key: str) -> str:
            content = label.get(key, [])
            if isinstance(content, list) and content:
                return content[0]
            return ""

        return {
            "generic_name": generic_names[0] if generic_names else "",
            "brand_name": brand_names[0] if brand_names else "",
            "manufacturer": openfda.get("manufacturer_name", [""])[0],
            "indications": get_section("indications_and_usage"),
            "dosage": get_section("dosage_and_administration"),
            "warnings": get_section("warnings_and_cautions") or get_section("warnings"),
            "boxed_warning": get_section("boxed_warning"),
            "contraindications": get_section("contraindications"),
            "adverse_reactions": get_section("adverse_reactions"),
            "drug_interactions": get_section("drug_interactions"),
            "use_in_pregnancy": get_section("pregnancy") or get_section("use_in_specific_populations"),
            "pharmacology": get_section("clinical_pharmacology"),
        }

    def get_indications(self, drug_name: str) -> str:
        """获取适应症"""
        label = self.search_drug_label(drug_name)
        return label.get("indications", "") if label else ""

    def get_warnings(self, drug_name: str) -> str:
        """获取警告信息"""
        label = self.search_drug_label(drug_name)
        if not label:
            return ""

        warnings = []
        if label.get("boxed_warning"):
            warnings.append(f"[黑框警告] {label['boxed_warning']}")
        if label.get("warnings"):
            warnings.append(label["warnings"])

        return "\n\n".join(warnings)

    def get_dosage(self, drug_name: str) -> str:
        """获取剂量信息"""
        label = self.search_drug_label(drug_name)
        return label.get("dosage", "") if label else ""

    def get_interactions(self, drug_name: str) -> str:
        """获取药物相互作用"""
        label = self.search_drug_label(drug_name)
        return label.get("drug_interactions", "") if label else ""


if __name__ == "__main__":
    # 测试
    client = FDAClient()

    print("=== FDA 药物说明书查询: Osimertinib ===")
    label = client.search_drug_label("osimertinib")

    if label:
        print(f"通用名: {label['generic_name']}")
        print(f"商品名: {label['brand_name']}")
        print(f"生产商: {label['manufacturer']}")
        print(f"\n适应症: {label['indications'][:300]}...")
        print(f"\n剂量: {label['dosage'][:300]}...")
        print(f"\n警告: {label['warnings'][:300]}...")
    else:
        print("未找到")
