"""
CIViC (Clinical Interpretation of Variants in Cancer) API 客户端

提供变异证据等级和治疗意义查询 (替代 OncoKB)
API 文档: https://docs.civicdb.org/en/latest/api.html
许可证: CC0 (公共领域)
"""
import requests
from typing import Dict, List, Any, Optional
from src.utils.logger import mtb_logger as logger


class CIViCClient:
    """CIViC API 客户端"""

    BASE_URL = "https://civicdb.org/api"
    GRAPHQL_URL = "https://civicdb.org/api/graphql"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })

    def search_gene(self, gene_name: str) -> Optional[Dict]:
        """
        搜索基因

        Args:
            gene_name: 基因名称 (如 EGFR)

        Returns:
            基因信息 {id, name, description, variants_count}
        """
        url = f"{self.BASE_URL}/genes/{gene_name}"

        try:
            logger.debug(f"[CIViC] 搜索基因: {gene_name}")
            response = self.session.get(url, timeout=15)

            if response.status_code == 404:
                logger.info(f"[CIViC] 未找到基因: {gene_name}")
                return None

            response.raise_for_status()
            data = response.json()

            return {
                "id": data.get("id"),
                "name": data.get("name"),
                "entrez_id": data.get("entrez_id"),
                "description": data.get("description", "")[:500],
                "variants_count": len(data.get("variants", []))
            }

        except Exception as e:
            logger.error(f"[CIViC] 搜索基因失败: {e}")
            return None

    def search_variant(self, gene: str, variant: str) -> Optional[Dict]:
        """
        搜索变异

        Args:
            gene: 基因名称 (如 EGFR)
            variant: 变异名称 (如 L858R)

        Returns:
            变异信息 {id, name, gene, variant_types, evidence_items_count}
        """
        # 先获取基因的所有变异
        url = f"{self.BASE_URL}/genes/{gene}"

        try:
            logger.debug(f"[CIViC] 搜索变异: {gene} {variant}")
            response = self.session.get(url, timeout=15)

            if response.status_code == 404:
                logger.info(f"[CIViC] 未找到基因: {gene}")
                return None

            response.raise_for_status()
            data = response.json()

            # 在变异列表中查找匹配的变异
            variants = data.get("variants", [])
            variant_upper = variant.upper()

            for v in variants:
                v_name = v.get("name", "").upper()
                # 精确匹配或包含匹配
                if v_name == variant_upper or variant_upper in v_name:
                    return self.get_variant_details(v.get("id"))

            logger.info(f"[CIViC] 未找到变异: {gene} {variant}")
            return None

        except Exception as e:
            logger.error(f"[CIViC] 搜索变异失败: {e}")
            return None

    def get_variant_details(self, variant_id: int) -> Optional[Dict]:
        """
        获取变异详细信息

        Args:
            variant_id: CIViC 变异 ID

        Returns:
            变异详细信息
        """
        url = f"{self.BASE_URL}/variants/{variant_id}"

        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()

            return {
                "id": data.get("id"),
                "name": data.get("name"),
                "gene": data.get("gene", {}).get("name", ""),
                "description": data.get("description", "")[:500],
                "variant_types": [vt.get("display_name") for vt in data.get("variant_types", [])],
                "evidence_items": self._get_evidence_summary(data.get("evidence_items", [])),
                "coordinates": {
                    "chromosome": data.get("coordinates", {}).get("chromosome"),
                    "start": data.get("coordinates", {}).get("start"),
                    "reference_bases": data.get("coordinates", {}).get("reference_bases"),
                    "variant_bases": data.get("coordinates", {}).get("variant_bases")
                },
                "civic_url": f"https://civicdb.org/variants/{variant_id}"
            }

        except Exception as e:
            logger.error(f"[CIViC] 获取变异详情失败: {e}")
            return None

    def _get_evidence_summary(self, evidence_items: List[Dict]) -> Dict:
        """汇总证据项"""
        summary = {
            "total_count": len(evidence_items),
            "by_type": {},
            "by_level": {},
            "therapeutic": [],
            "diagnostic": [],
            "prognostic": []
        }

        for item in evidence_items:
            # 按类型统计
            etype = item.get("evidence_type", "Unknown")
            summary["by_type"][etype] = summary["by_type"].get(etype, 0) + 1

            # 按等级统计
            level = item.get("evidence_level", "Unknown")
            summary["by_level"][level] = summary["by_level"].get(level, 0) + 1

            # 提取治疗相关证据
            if etype == "Predictive":
                drugs = [d.get("name") for d in item.get("drugs", [])]
                clinical_significance = item.get("clinical_significance", "")
                disease = item.get("disease", {}).get("display_name", "")

                summary["therapeutic"].append({
                    "drugs": drugs,
                    "disease": disease,
                    "clinical_significance": clinical_significance,
                    "evidence_level": level,
                    "evidence_direction": item.get("evidence_direction", ""),
                    "pubmed_id": item.get("source", {}).get("pubmed_id")
                })

            elif etype == "Diagnostic":
                summary["diagnostic"].append({
                    "disease": item.get("disease", {}).get("display_name", ""),
                    "clinical_significance": item.get("clinical_significance", ""),
                    "evidence_level": level
                })

            elif etype == "Prognostic":
                summary["prognostic"].append({
                    "disease": item.get("disease", {}).get("display_name", ""),
                    "clinical_significance": item.get("clinical_significance", ""),
                    "evidence_level": level
                })

        # 限制数量
        summary["therapeutic"] = summary["therapeutic"][:5]
        summary["diagnostic"] = summary["diagnostic"][:3]
        summary["prognostic"] = summary["prognostic"][:3]

        return summary

    def get_therapeutic_implications(self, gene: str, variant: str) -> Optional[Dict]:
        """
        获取变异的治疗意义 (类似 OncoKB 功能)

        Args:
            gene: 基因名称
            variant: 变异名称

        Returns:
            治疗意义摘要
        """
        variant_info = self.search_variant(gene, variant)
        if not variant_info:
            return None

        evidence = variant_info.get("evidence_items", {})
        therapeutic = evidence.get("therapeutic", [])

        if not therapeutic:
            return {
                "gene": gene,
                "variant": variant,
                "has_therapeutic_evidence": False,
                "message": "No therapeutic evidence found in CIViC"
            }

        # 按证据等级排序
        level_order = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}
        therapeutic.sort(key=lambda x: level_order.get(x.get("evidence_level", "E"), 4))

        return {
            "gene": gene,
            "variant": variant,
            "has_therapeutic_evidence": True,
            "total_evidence_count": evidence.get("total_count", 0),
            "evidence_by_level": evidence.get("by_level", {}),
            "top_therapeutic_evidence": therapeutic[:5],
            "civic_url": variant_info.get("civic_url")
        }


if __name__ == "__main__":
    # 测试
    client = CIViCClient()

    print("=== CIViC 基因搜索: EGFR ===")
    gene = client.search_gene("EGFR")
    if gene:
        print(f"基因 ID: {gene['id']}")
        print(f"变异数量: {gene['variants_count']}")

    print("\n=== CIViC 变异搜索: EGFR L858R ===")
    variant = client.search_variant("EGFR", "L858R")
    if variant:
        print(f"变异 ID: {variant['id']}")
        print(f"变异类型: {variant['variant_types']}")
        print(f"证据项数量: {variant['evidence_items']['total_count']}")
        print(f"按等级: {variant['evidence_items']['by_level']}")

    print("\n=== 治疗意义查询 ===")
    implications = client.get_therapeutic_implications("EGFR", "L858R")
    if implications and implications.get("has_therapeutic_evidence"):
        print(f"证据等级分布: {implications['evidence_by_level']}")
        for e in implications["top_therapeutic_evidence"][:3]:
            print(f"- {e['drugs']}: {e['clinical_significance']} (Level {e['evidence_level']})")
