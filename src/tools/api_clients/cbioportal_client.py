"""
cBioPortal API 客户端

提供突变频率和癌症基因组数据查询 (替代 COSMIC)
API 文档: https://www.cbioportal.org/api/swagger-ui/index.html
"""
import requests
from typing import Dict, List, Any, Optional
from src.utils.logger import mtb_logger as logger


class cBioPortalClient:
    """cBioPortal API 客户端"""

    BASE_URL = "https://www.cbioportal.org/api"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json"
        })
        self._cancer_types_cache = None

    def get_cancer_types(self) -> List[Dict]:
        """获取所有癌症类型"""
        if self._cancer_types_cache:
            return self._cancer_types_cache

        url = f"{self.BASE_URL}/cancer-types"

        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            self._cancer_types_cache = response.json()
            return self._cancer_types_cache
        except Exception as e:
            logger.error(f"[cBioPortal] 获取癌症类型失败: {e}")
            return []

    def search_gene(self, gene_name: str) -> Optional[Dict]:
        """
        搜索基因信息

        Args:
            gene_name: 基因名称 (如 EGFR)

        Returns:
            基因信息 {entrezGeneId, hugoGeneSymbol}
        """
        url = f"{self.BASE_URL}/genes/{gene_name}"

        try:
            logger.debug(f"[cBioPortal] 搜索基因: {gene_name}")
            response = self.session.get(url, timeout=15)

            if response.status_code == 404:
                logger.info(f"[cBioPortal] 未找到基因: {gene_name}")
                return None

            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"[cBioPortal] 搜索基因失败: {e}")
            return None

    def get_mutation_frequency(self, gene: str, cancer_type: str = None) -> Dict:
        """
        获取基因突变频率

        Args:
            gene: 基因名称
            cancer_type: 癌症类型 ID (可选)

        Returns:
            突变频率数据 {gene, overall_frequency, by_cancer_type, common_mutations}
        """
        gene_info = self.search_gene(gene)
        if not gene_info:
            return {"gene": gene, "error": "Gene not found"}

        entrez_id = gene_info.get("entrezGeneId")

        # 获取所有研究中的突变数据
        url = f"{self.BASE_URL}/mutations"

        # 使用 POST 查询多个研究
        # 先获取一些主要研究的 ID
        studies = self._get_major_studies(cancer_type)

        if not studies:
            return {"gene": gene, "error": "No studies found"}

        result = {
            "gene": gene,
            "entrez_id": entrez_id,
            "studies_analyzed": len(studies),
            "mutations": [],
            "by_cancer_type": {},
            "common_mutations": {}
        }

        # 查询每个研究的突变
        for study in studies[:10]:  # 限制研究数量
            study_id = study.get("studyId")
            mutations = self._get_study_mutations(study_id, entrez_id)

            cancer_type_id = study.get("cancerTypeId", "Unknown")

            if cancer_type_id not in result["by_cancer_type"]:
                result["by_cancer_type"][cancer_type_id] = {
                    "study_count": 0,
                    "mutation_count": 0,
                    "sample_count": 0
                }

            result["by_cancer_type"][cancer_type_id]["study_count"] += 1
            result["by_cancer_type"][cancer_type_id]["mutation_count"] += len(mutations)

            # 统计常见突变
            for mut in mutations:
                aa_change = mut.get("aminoAcidChange", "")
                if aa_change:
                    result["common_mutations"][aa_change] = result["common_mutations"].get(aa_change, 0) + 1

        # 排序常见突变
        sorted_mutations = sorted(
            result["common_mutations"].items(),
            key=lambda x: x[1],
            reverse=True
        )
        result["top_mutations"] = [{"mutation": m[0], "count": m[1]} for m in sorted_mutations[:10]]

        return result

    def _get_major_studies(self, cancer_type: str = None) -> List[Dict]:
        """获取主要研究列表"""
        url = f"{self.BASE_URL}/studies"
        params = {"pageSize": 50, "sortBy": "studyId"}

        if cancer_type:
            params["keyword"] = cancer_type

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            studies = response.json()

            # 过滤一些大型研究
            major_studies = [
                s for s in studies
                if s.get("allSampleCount", 0) > 100
            ]

            return major_studies[:20]

        except Exception as e:
            logger.error(f"[cBioPortal] 获取研究列表失败: {e}")
            return []

    def _get_study_mutations(self, study_id: str, entrez_gene_id: int) -> List[Dict]:
        """获取特定研究中基因的突变"""
        url = f"{self.BASE_URL}/molecular-profiles/{study_id}_mutations/mutations"
        params = {
            "entrezGeneId": entrez_gene_id,
            "projection": "SUMMARY"
        }

        try:
            response = self.session.get(url, params=params, timeout=30)

            if response.status_code == 404:
                return []

            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.debug(f"[cBioPortal] 获取 {study_id} 突变失败: {e}")
            return []

    def get_gene_mutations(self, gene: str, study_id: str = "msk_impact_2017") -> List[Dict]:
        """
        获取特定研究中基因的所有突变

        Args:
            gene: 基因名称
            study_id: 研究 ID (默认 MSK-IMPACT)

        Returns:
            突变列表
        """
        gene_info = self.search_gene(gene)
        if not gene_info:
            return []

        entrez_id = gene_info.get("entrezGeneId")
        mutations = self._get_study_mutations(study_id, entrez_id)

        # 简化返回数据
        results = []
        for mut in mutations:
            results.append({
                "sample_id": mut.get("sampleId"),
                "mutation_type": mut.get("mutationType"),
                "amino_acid_change": mut.get("aminoAcidChange"),
                "chromosome": mut.get("chr"),
                "start_position": mut.get("startPosition"),
                "ref_allele": mut.get("referenceAllele"),
                "var_allele": mut.get("variantAllele")
            })

        return results

    def get_variant_frequency_summary(self, gene: str, variant: str) -> Dict:
        """
        获取特定变异的频率摘要

        Args:
            gene: 基因名称
            variant: 变异 (如 L858R)

        Returns:
            频率摘要
        """
        mutation_data = self.get_mutation_frequency(gene)

        if "error" in mutation_data:
            return mutation_data

        # 查找特定变异
        variant_upper = variant.upper()
        variant_count = 0
        total_mutations = sum(mutation_data.get("common_mutations", {}).values())

        for mut, count in mutation_data.get("common_mutations", {}).items():
            if variant_upper in mut.upper():
                variant_count += count

        return {
            "gene": gene,
            "variant": variant,
            "variant_count": variant_count,
            "total_gene_mutations": total_mutations,
            "frequency_percentage": round(variant_count / total_mutations * 100, 2) if total_mutations > 0 else 0,
            "studies_analyzed": mutation_data.get("studies_analyzed", 0),
            "by_cancer_type": mutation_data.get("by_cancer_type", {}),
            "cbioportal_url": f"https://www.cbioportal.org/results/mutations?gene_list={gene}"
        }


if __name__ == "__main__":
    # 测试
    client = cBioPortalClient()

    print("=== cBioPortal 基因搜索: EGFR ===")
    gene = client.search_gene("EGFR")
    if gene:
        print(f"Entrez ID: {gene.get('entrezGeneId')}")
        print(f"Hugo Symbol: {gene.get('hugoGeneSymbol')}")

    print("\n=== 变异频率查询: EGFR L858R ===")
    freq = client.get_variant_frequency_summary("EGFR", "L858R")
    print(f"变异计数: {freq.get('variant_count')}")
    print(f"总突变数: {freq.get('total_gene_mutations')}")
    print(f"频率: {freq.get('frequency_percentage')}%")

    print("\n=== 常见突变 ===")
    mutations = client.get_mutation_frequency("EGFR")
    for m in mutations.get("top_mutations", [])[:5]:
        print(f"- {m['mutation']}: {m['count']}")
