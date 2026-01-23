"""
CIViC (Clinical Interpretation of Variants in Cancer) API 客户端

使用 GraphQL API (v2)
API 文档: https://griffithlab.github.io/civic-v2/
GraphiQL: https://civicdb.org/api/graphiql
许可证: CC0 (公共领域)
"""
import requests
from typing import Dict, List, Any, Optional
from src.utils.logger import mtb_logger as logger


class CIViCClient:
    """CIViC GraphQL API 客户端"""

    GRAPHQL_URL = "https://civicdb.org/api/graphql"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })

    def _execute_query(self, query: str, variables: Dict = None) -> Optional[Dict]:
        """执行 GraphQL 查询"""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = self.session.post(
                self.GRAPHQL_URL,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                logger.error(f"[CIViC] GraphQL 错误: {data['errors']}")
                return None

            return data.get("data")

        except Exception as e:
            logger.error(f"[CIViC] GraphQL 查询失败: {e}")
            return None

    def search_gene(self, gene_name: str) -> Optional[Dict]:
        """
        搜索基因

        Args:
            gene_name: 基因名称 (如 EGFR)

        Returns:
            基因信息 {id, name, description}
        """
        query = """
        query GeneSearch($name: String!) {
            genes(name: $name) {
                nodes {
                    id
                    name
                    description
                    entrezId
                }
            }
        }
        """

        logger.debug(f"[CIViC] 搜索基因: {gene_name}")
        data = self._execute_query(query, {"name": gene_name})

        if not data:
            return None

        nodes = data.get("genes", {}).get("nodes", [])
        if not nodes:
            logger.info(f"[CIViC] 未找到基因: {gene_name}")
            return None

        gene = nodes[0]
        return {
            "id": gene.get("id"),
            "name": gene.get("name"),
            "entrez_id": gene.get("entrezId"),
            "description": gene.get("description") or ""
        }

    def search_variant(self, gene: str, variant: str) -> Optional[Dict]:
        """
        搜索变异 (通过 Molecular Profile)

        Args:
            gene: 基因名称 (如 EGFR)
            variant: 变异名称 (如 L858R)

        Returns:
            变异信息
        """
        # CIViC v2 使用 Molecular Profile 模型
        # 搜索格式: "EGFR L858R"
        mp_name = f"{gene} {variant}"

        query = """
        query MolecularProfileSearch($name: String!) {
            molecularProfiles(name: $name) {
                nodes {
                    id
                    name
                    description
                    link
                    variants {
                        id
                        name
                        variantTypes {
                            name
                        }
                    }
                    evidenceItems(first: 20) {
                        totalCount
                        nodes {
                            id
                            status
                            evidenceType
                            evidenceLevel
                            evidenceDirection
                            significance
                            disease {
                                name
                                doid
                            }
                            therapies {
                                name
                                ncitId
                            }
                            source {
                                sourceType
                                citationId
                            }
                        }
                    }
                }
            }
        }
        """

        logger.debug(f"[CIViC] 搜索 Molecular Profile: {mp_name}")
        data = self._execute_query(query, {"name": mp_name})

        if not data:
            return None

        nodes = data.get("molecularProfiles", {}).get("nodes", [])

        # 查找精确匹配或包含匹配
        target_mp = None
        for mp in nodes:
            mp_name_upper = mp.get("name", "").upper()
            if mp_name_upper == f"{gene} {variant}".upper():
                target_mp = mp
                break
            elif gene.upper() in mp_name_upper and variant.upper() in mp_name_upper:
                target_mp = mp
                break

        if not target_mp:
            logger.info(f"[CIViC] 未找到 Molecular Profile: {mp_name}")
            return None

        return self._format_molecular_profile(target_mp)

    def _format_molecular_profile(self, mp: Dict) -> Dict:
        """格式化 Molecular Profile 数据"""
        evidence_data = mp.get("evidenceItems", {})
        evidence_items = evidence_data.get("nodes", [])
        evidence_count = evidence_data.get("totalCount", len(evidence_items))

        # 只处理已接受的证据
        accepted_evidence = [e for e in evidence_items if e.get("status") == "ACCEPTED"]

        # 汇总证据
        evidence_summary = self._get_evidence_summary(accepted_evidence)

        return {
            "id": mp.get("id"),
            "name": mp.get("name"),
            "description": mp.get("description") or "",
            "variants": [
                {
                    "id": v.get("id"),
                    "name": v.get("name"),
                    "types": [vt.get("name") for vt in v.get("variantTypes", [])]
                }
                for v in mp.get("variants", [])
            ],
            "evidence_count": evidence_count,
            "evidence_items": evidence_summary,
            "civic_url": mp.get("link") or f"https://civicdb.org/molecular-profiles/{mp.get('id')}"
        }

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
            etype = item.get("evidenceType", "Unknown")
            summary["by_type"][etype] = summary["by_type"].get(etype, 0) + 1

            # 按等级统计
            level = item.get("evidenceLevel", "Unknown")
            summary["by_level"][level] = summary["by_level"].get(level, 0) + 1

            # 提取疾病和治疗信息
            disease = item.get("disease", {})
            disease_name = disease.get("name", "") if disease else ""
            therapies = item.get("therapies", []) or []
            drug_names = [t.get("name") for t in therapies if t]
            significance = item.get("significance", "")
            direction = item.get("evidenceDirection", "")

            # 获取 PubMed ID
            source = item.get("source", {})
            pmid = None
            if source and source.get("sourceType") == "PUBMED":
                pmid = source.get("citationId")

            evidence_entry = {
                "drugs": drug_names,
                "disease": disease_name,
                "clinical_significance": significance,
                "evidence_level": level,
                "evidence_direction": direction,
                "pubmed_id": pmid
            }

            # 分类存储
            if etype == "PREDICTIVE":
                summary["therapeutic"].append(evidence_entry)
            elif etype == "DIAGNOSTIC":
                summary["diagnostic"].append(evidence_entry)
            elif etype == "PROGNOSTIC":
                summary["prognostic"].append(evidence_entry)

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
                "message": "No therapeutic evidence found in CIViC",
                "civic_url": variant_info.get("civic_url")
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
        print(f"基因名称: {gene['name']}")

    print("\n=== CIViC 变异搜索: EGFR L858R ===")
    variant = client.search_variant("EGFR", "L858R")
    if variant:
        print(f"Molecular Profile: {variant['name']}")
        print(f"证据数量: {variant['evidence_count']}")
        print(f"证据等级: {variant['evidence_items']['by_level']}")
        print(f"URL: {variant['civic_url']}")

    print("\n=== 治疗意义查询 ===")
    implications = client.get_therapeutic_implications("EGFR", "L858R")
    if implications:
        print(f"有治疗证据: {implications.get('has_therapeutic_evidence')}")
        if implications.get("has_therapeutic_evidence"):
            print(f"证据等级分布: {implications['evidence_by_level']}")
            for e in implications.get("top_therapeutic_evidence", [])[:3]:
                print(f"- {e['drugs']}: {e['clinical_significance']} (Level {e['evidence_level']})")
