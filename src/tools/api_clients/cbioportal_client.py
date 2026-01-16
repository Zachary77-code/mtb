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
        hugo_symbol = gene_info.get("hugoGeneSymbol", gene)

        result = {
            "gene": hugo_symbol,
            "entrez_id": entrez_id,
            "studies_analyzed": 0,
            "mutations": [],
            "by_cancer_type": {},
            "common_mutations": {},
            "top_mutations": []
        }

        # 使用 MSK-IMPACT 等大型研究直接获取突变
        major_study_ids = [
            "msk_impact_2017",      # MSK-IMPACT Clinical Sequencing
            "tcga_pan_can_atlas_2018",  # TCGA Pan-Cancer Atlas
            "genie_public"          # AACR GENIE
        ]

        all_mutations = []
        for study_id in major_study_ids:
            mutations = self._get_study_mutations(study_id, entrez_id)
            if mutations:
                result["studies_analyzed"] += 1
                all_mutations.extend(mutations)

        if not all_mutations:
            # 尝试获取更多研究
            studies = self._get_major_studies(cancer_type)
            for study in studies[:5]:
                study_id = study.get("studyId")
                mutations = self._get_study_mutations(study_id, entrez_id)
                if mutations:
                    result["studies_analyzed"] += 1
                    all_mutations.extend(mutations)

        # 统计突变
        for mut in all_mutations:
            # cBioPortal 使用 proteinChange 字段
            aa_change = mut.get("proteinChange") or mut.get("aminoAcidChange", "")
            if aa_change:
                result["common_mutations"][aa_change] = result["common_mutations"].get(aa_change, 0) + 1

            # 按癌症类型统计
            cancer = mut.get("studyId", "").split("_")[0] if mut.get("studyId") else "unknown"
            if cancer not in result["by_cancer_type"]:
                result["by_cancer_type"][cancer] = {"mutation_count": 0}
            result["by_cancer_type"][cancer]["mutation_count"] += 1

        # 排序常见突变
        sorted_mutations = sorted(
            result["common_mutations"].items(),
            key=lambda x: x[1],
            reverse=True
        )
        result["top_mutations"] = [{"mutation": m[0], "count": m[1]} for m in sorted_mutations[:10]]
        result["total_mutations"] = len(all_mutations)

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
        # 使用 POST 端点查询突变
        url = f"{self.BASE_URL}/molecular-profiles/{study_id}_mutations/mutations/fetch"

        # POST body - 查询特定基因
        body = {
            "entrezGeneIds": [entrez_gene_id],
            "sampleListId": f"{study_id}_all"  # 使用 all samples
        }

        try:
            response = self.session.post(
                url,
                json=body,
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            if response.status_code == 404:
                return []

            response.raise_for_status()
            mutations = response.json()

            # 添加 studyId 到每个突变
            for mut in mutations:
                mut["studyId"] = study_id

            return mutations

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

        # 查找特定变异 (支持多种格式: L858R, p.L858R, L858)
        variant_upper = variant.upper()
        variant_count = 0
        total_mutations = mutation_data.get("total_mutations", 0)

        for mut, count in mutation_data.get("common_mutations", {}).items():
            mut_upper = mut.upper()
            # 精确匹配或包含匹配
            if (variant_upper == mut_upper or
                variant_upper in mut_upper or
                f"P.{variant_upper}" == mut_upper):
                variant_count += count

        return {
            "gene": mutation_data.get("gene", gene),
            "variant": variant,
            "variant_count": variant_count,
            "total_gene_mutations": total_mutations,
            "frequency_percentage": round(variant_count / total_mutations * 100, 2) if total_mutations > 0 else 0,
            "studies_analyzed": mutation_data.get("studies_analyzed", 0),
            "top_mutations": mutation_data.get("top_mutations", []),
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
