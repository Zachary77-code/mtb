"""
RxNorm API 客户端

提供药物标准化和药物相互作用查询 (替代 DrugBank)
API 文档: https://lhncbc.nlm.nih.gov/RxNav/APIs/
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, List, Any, Optional
from src.utils.logger import mtb_logger as logger


class RxNormClient:
    """RxNorm API 客户端"""

    BASE_URL = "https://rxnav.nlm.nih.gov/REST"
    INTERACTION_URL = "https://rxnav.nlm.nih.gov/REST/interaction"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json"
        })
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

    def get_rxcui(self, drug_name: str) -> Optional[str]:
        """
        获取药物的 RxCUI (RxNorm Concept Unique Identifier)

        Args:
            drug_name: 药物名称

        Returns:
            RxCUI 字符串，未找到返回 None
        """
        url = f"{self.BASE_URL}/rxcui.json"
        params = {"name": drug_name}

        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            id_group = data.get("idGroup", {})
            rxnorm_id = id_group.get("rxnormId", [])

            if rxnorm_id:
                return rxnorm_id[0]

            # 尝试近似搜索
            return self._approximate_search(drug_name)

        except Exception as e:
            logger.error(f"[RxNorm] 获取 RxCUI 失败: {e}")
            return None

    def _approximate_search(self, drug_name: str) -> Optional[str]:
        """近似搜索药物"""
        url = f"{self.BASE_URL}/approximateTerm.json"
        params = {"term": drug_name, "maxEntries": 1}

        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            candidates = data.get("approximateGroup", {}).get("candidate", [])
            if candidates:
                return candidates[0].get("rxcui")
            return None

        except Exception as e:
            logger.debug(f"[RxNorm] 近似搜索失败: {e}")
            return None

    def get_drug_info(self, drug_name: str) -> Optional[Dict]:
        """
        获取药物基本信息

        Args:
            drug_name: 药物名称

        Returns:
            药物信息 {rxcui, name, tty, drug_class}
        """
        rxcui = self.get_rxcui(drug_name)
        if not rxcui:
            logger.info(f"[RxNorm] 未找到药物: {drug_name}")
            return None

        # 获取属性
        url = f"{self.BASE_URL}/rxcui/{rxcui}/allProperties.json"
        params = {"prop": "names"}

        try:
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            props = data.get("propConceptGroup", {}).get("propConcept", [])

            result = {
                "rxcui": rxcui,
                "name": drug_name,
                "properties": {}
            }

            for prop in props:
                prop_name = prop.get("propName", "")
                prop_value = prop.get("propValue", "")
                result["properties"][prop_name] = prop_value

            # 获取药物分类
            result["drug_class"] = self.get_drug_class(rxcui)

            return result

        except Exception as e:
            logger.error(f"[RxNorm] 获取药物信息失败: {e}")
            return None

    def get_drug_class(self, rxcui: str) -> List[str]:
        """
        获取药物分类

        Args:
            rxcui: 药物 RxCUI

        Returns:
            药物分类列表
        """
        url = f"{self.BASE_URL}/rxcui/{rxcui}/class.json"

        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()

            classes = []
            concept_groups = data.get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", [])

            for group in concept_groups:
                class_name = group.get("rxclassMinConceptItem", {}).get("className", "")
                if class_name and class_name not in classes:
                    classes.append(class_name)

            return classes[:50]  # 限制数量

        except Exception as e:
            logger.debug(f"[RxNorm] 获取药物分类失败: {e}")
            return []

    def get_drug_interactions(self, drug_name: str) -> List[Dict]:
        """
        获取单个药物的已知相互作用

        Args:
            drug_name: 药物名称

        Returns:
            相互作用列表 [{drug, description, severity}]
        """
        rxcui = self.get_rxcui(drug_name)
        if not rxcui:
            return []

        url = f"{self.INTERACTION_URL}/interaction.json"
        params = {"rxcui": rxcui}

        try:
            logger.debug(f"[RxNorm] 查询 {drug_name} 的药物相互作用")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            interactions = []
            groups = data.get("interactionTypeGroup", [])

            for group in groups:
                for itype in group.get("interactionType", []):
                    for pair in itype.get("interactionPair", []):
                        description = pair.get("description", "")
                        severity = pair.get("severity", "N/A")

                        # 获取相互作用的药物
                        concepts = pair.get("interactionConcept", [])
                        drugs_involved = []
                        for concept in concepts:
                            drug = concept.get("minConceptItem", {}).get("name", "")
                            if drug:
                                drugs_involved.append(drug)

                        interactions.append({
                            "drugs": drugs_involved,
                            "description": description,
                            "severity": severity
                        })

            logger.debug(f"[RxNorm] 找到 {len(interactions)} 个相互作用")
            return interactions

        except Exception as e:
            logger.error(f"[RxNorm] 查询相互作用失败: {e}")
            return []

    def check_interaction(self, drug_names: List[str]) -> List[Dict]:
        """
        检查多个药物之间的相互作用

        Args:
            drug_names: 药物名称列表

        Returns:
            相互作用列表
        """
        # 获取所有药物的 RxCUI
        rxcuis = []
        for name in drug_names:
            rxcui = self.get_rxcui(name)
            if rxcui:
                rxcuis.append(rxcui)

        if len(rxcuis) < 2:
            logger.info("[RxNorm] 需要至少2个有效药物才能检查相互作用")
            return []

        url = f"{self.INTERACTION_URL}/list.json"
        params = {"rxcuis": "+".join(rxcuis)}

        try:
            logger.debug(f"[RxNorm] 检查 {len(rxcuis)} 个药物间的相互作用")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            interactions = []
            full_results = data.get("fullInteractionTypeGroup", [])

            for group in full_results:
                for itype in group.get("fullInteractionType", []):
                    for pair in itype.get("interactionPair", []):
                        description = pair.get("description", "")
                        severity = pair.get("severity", "N/A")

                        concepts = pair.get("interactionConcept", [])
                        drugs_involved = []
                        for concept in concepts:
                            drug = concept.get("minConceptItem", {}).get("name", "")
                            if drug:
                                drugs_involved.append(drug)

                        interactions.append({
                            "drugs": drugs_involved,
                            "description": description,
                            "severity": severity
                        })

            return interactions

        except Exception as e:
            logger.error(f"[RxNorm] 检查相互作用失败: {e}")
            return []


if __name__ == "__main__":
    # 测试
    client = RxNormClient()

    print("=== RxNorm 药物查询: Osimertinib ===")
    info = client.get_drug_info("osimertinib")
    if info:
        print(f"RxCUI: {info['rxcui']}")
        print(f"药物分类: {info['drug_class']}")

    print("\n=== 药物相互作用查询 ===")
    interactions = client.get_drug_interactions("osimertinib")
    for i, intr in enumerate(interactions[:3]):
        print(f"{i+1}. {intr['drugs']}: {intr['description'][:100]}...")

    print("\n=== 多药相互作用检查 ===")
    interactions = client.check_interaction(["osimertinib", "rifampin", "ketoconazole"])
    for intr in interactions[:3]:
        print(f"- {intr['drugs']}: {intr['severity']}")
