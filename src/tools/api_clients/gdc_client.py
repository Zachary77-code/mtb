"""
NCI GDC (Genomic Data Commons) API 客户端

提供基因突变频率和癌症基因组数据查询（替代 cBioPortal）
基于 TCGA + ICGC 数据
API 文档: https://docs.gdc.cancer.gov/API/Users_Guide/Data_Analysis/
"""
import json
import threading
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, List, Any, Optional
from src.utils.logger import mtb_logger as logger


class GDCClient:
    """NCI GDC API 客户端"""

    BASE_URL = "https://api.gdc.cancer.gov"

    # 类级别基因 ID 缓存（symbol → ensembl_id，跨实例共享）
    _gene_cache: Dict[str, Optional[str]] = {}
    _gene_cache_lock = threading.Lock()

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,  # 1s → 2s → 4s
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _get_ensembl_id(self, gene_symbol: str) -> Optional[str]:
        """
        HUGO 基因符号 → Ensembl ID（带缓存）

        Args:
            gene_symbol: 基因名称（如 EGFR）

        Returns:
            Ensembl ID（如 ENSG00000146648），未找到返回 None
        """
        cache_key = gene_symbol.upper()
        with GDCClient._gene_cache_lock:
            if cache_key in GDCClient._gene_cache:
                logger.debug(f"[GDC] 基因缓存命中: {gene_symbol}")
                return GDCClient._gene_cache[cache_key]

        url = f"{self.BASE_URL}/genes"
        filters = {
            "op": "in",
            "content": {
                "field": "symbol",
                "value": [gene_symbol.upper()]
            }
        }
        params = {
            "filters": json.dumps(filters),
            "fields": "gene_id,symbol,name",
            "size": 1,
        }

        try:
            logger.debug(f"[GDC] 查询基因 ID: {gene_symbol}")
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            hits = data.get("data", {}).get("hits", [])
            if not hits:
                logger.info(f"[GDC] 未找到基因: {gene_symbol}")
                with GDCClient._gene_cache_lock:
                    GDCClient._gene_cache[cache_key] = None
                return None

            ensembl_id = hits[0].get("gene_id")
            with GDCClient._gene_cache_lock:
                GDCClient._gene_cache[cache_key] = ensembl_id
            logger.debug(f"[GDC] {gene_symbol} → {ensembl_id}")
            return ensembl_id

        except Exception as e:
            logger.error(f"[GDC] 查询基因 ID 失败: {e}")
            return None

    def get_mutation_frequency(self, gene: str, cancer_type: str = None) -> Dict:
        """
        获取基因突变频率（按癌种/项目分布）

        Args:
            gene: 基因名称（如 EGFR）
            cancer_type: 癌症类型过滤（可选，如 "lung"）

        Returns:
            突变频率数据 {gene, by_cancer_type, top_mutations, ...}
        """
        ensembl_id = self._get_ensembl_id(gene)
        if not ensembl_id:
            return {"gene": gene, "error": "Gene not found in GDC"}

        result = {
            "gene": gene,
            "ensembl_id": ensembl_id,
            "studies_analyzed": 0,
            "by_cancer_type": {},
            "top_mutations": [],
            "total_mutations": 0,
            "common_mutations": {},
            "gdc_url": f"https://portal.gdc.cancer.gov/genes/{ensembl_id}",
        }

        # 1. 获取各癌种的突变病例数
        case_counts = self._get_cases_by_gene(ensembl_id)
        if case_counts:
            for project_id, count in case_counts.items():
                if cancer_type and cancer_type.lower() not in project_id.lower():
                    continue
                result["by_cancer_type"][project_id] = {
                    "mutation_count": count,
                }
            result["studies_analyzed"] = len(result["by_cancer_type"])

        # 2. 获取高频突变列表
        mutations = self._get_ssm_for_gene(gene)
        if mutations:
            # 统计氨基酸变化频率
            aa_counts: Dict[str, int] = {}
            for mut in mutations:
                aa_changes = self._extract_aa_changes(mut)
                for aa in aa_changes:
                    aa_counts[aa] = aa_counts.get(aa, 0) + 1

            sorted_mutations = sorted(aa_counts.items(), key=lambda x: x[1], reverse=True)
            result["top_mutations"] = [
                {"mutation": m[0], "count": m[1]} for m in sorted_mutations[:50]
            ]
            result["common_mutations"] = aa_counts
            result["total_mutations"] = len(mutations)

        return result

    def get_variant_frequency_summary(self, gene: str, variant: str) -> Dict:
        """
        获取特定变异的频率摘要

        通过 SSM 的 occurrence 字段统计该变异在各项目中的出现次数（病例数）。

        Args:
            gene: 基因名称
            variant: 变异（如 L858R）

        Returns:
            频率摘要
        """
        ensembl_id = self._get_ensembl_id(gene)
        if not ensembl_id:
            return {"gene": gene, "error": "Gene not found in GDC"}

        # 1. 获取基因的整体突变病例数（按项目分布）
        case_counts = self._get_cases_by_gene(ensembl_id)
        total_gene_cases = sum(case_counts.values()) if case_counts else 0

        # 2. 查询特定变异的 SSM 及其 occurrence（病例分布）
        variant_count, variant_by_project = self._get_variant_occurrences(
            gene, variant
        )

        # 3. 获取该基因的高频突变列表
        mutations = self._get_ssm_for_gene(gene, size=500)
        aa_counts: Dict[str, int] = {}
        for mut in mutations:
            for aa in self._extract_aa_changes(mut):
                aa_counts[aa] = aa_counts.get(aa, 0) + 1
        sorted_mutations = sorted(aa_counts.items(), key=lambda x: x[1], reverse=True)
        top_mutations = [{"mutation": m[0], "count": m[1]} for m in sorted_mutations[:50]]

        return {
            "gene": gene,
            "variant": variant,
            "variant_count": variant_count,
            "total_gene_mutations": total_gene_cases,
            "frequency_percentage": round(
                variant_count / total_gene_cases * 100, 2
            ) if total_gene_cases > 0 else 0,
            "studies_analyzed": len(case_counts),
            "top_mutations": top_mutations,
            "by_cancer_type": {
                p: {"mutation_count": c} for p, c in case_counts.items()
            },
            "variant_by_project": variant_by_project,
            "gdc_url": f"https://portal.gdc.cancer.gov/genes/{ensembl_id}",
        }

    def _get_variant_occurrences(
        self, gene_symbol: str, variant: str
    ) -> tuple:
        """
        查询特定变异的病例数和项目分布

        通过 SSM 过滤 aa_change 并统计 occurrence。

        Args:
            gene_symbol: 基因名称
            variant: 氨基酸变化（如 L858R）

        Returns:
            (total_cases, {project_id: case_count})
        """
        url = f"{self.BASE_URL}/ssms"

        # 支持多种变异格式匹配
        variant_values = [variant]
        if not variant.startswith("p."):
            variant_values.append(f"p.{variant}")

        filters = {
            "op": "and",
            "content": [
                {
                    "op": "in",
                    "content": {
                        "field": "consequence.transcript.gene.symbol",
                        "value": [gene_symbol.upper()]
                    }
                },
                {
                    "op": "in",
                    "content": {
                        "field": "consequence.transcript.aa_change",
                        "value": variant_values
                    }
                }
            ]
        }

        params = {
            "filters": json.dumps(filters),
            "fields": "ssm_id,occurrence.case.project.project_id",
            "size": 10,
        }

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            hits = data.get("data", {}).get("hits", [])
            project_counts: Dict[str, int] = {}

            for hit in hits:
                for occ in hit.get("occurrence", []):
                    project_id = (
                        occ.get("case", {})
                        .get("project", {})
                        .get("project_id", "")
                    )
                    if project_id:
                        project_counts[project_id] = (
                            project_counts.get(project_id, 0) + 1
                        )

            total_cases = sum(project_counts.values())
            return total_cases, project_counts

        except Exception as e:
            logger.error(f"[GDC] 查询变异 {gene_symbol} {variant} 失败: {e}")
            return 0, {}

    def _get_cases_by_gene(self, ensembl_id: str) -> Dict[str, int]:
        """
        获取各项目中基因突变的病例数

        Args:
            ensembl_id: Ensembl 基因 ID

        Returns:
            {project_id: case_count} 字典
        """
        url = f"{self.BASE_URL}/analysis/top_cases_counts_by_genes"
        params = {"gene_ids": ensembl_id}

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            project_counts: Dict[str, int] = {}
            # top_cases_counts_by_genes 返回顶层 aggregations（非嵌套在 data 下）
            projects = data.get("aggregations", {}).get(
                "projects", {}
            ).get("buckets", [])

            for project in projects:
                project_id = project.get("key", "")
                # 从嵌套 aggregation 提取基因的突变病例数
                gene_buckets = (
                    project.get("genes", {})
                    .get("my_genes", {})
                    .get("gene_id", {})
                    .get("buckets", [])
                )
                for gene_bucket in gene_buckets:
                    if gene_bucket.get("key") == ensembl_id:
                        count = gene_bucket.get("doc_count", 0)
                        if count > 0:
                            project_counts[project_id] = count

            return project_counts

        except Exception as e:
            logger.error(f"[GDC] 获取病例计数失败: {e}")
            return {}

    def _get_ssm_for_gene(self, gene_symbol: str, size: int = 500) -> List[Dict]:
        """
        获取基因的 SSM（Simple Somatic Mutations）列表

        Args:
            gene_symbol: 基因名称
            size: 返回结果数量

        Returns:
            SSM 列表
        """
        url = f"{self.BASE_URL}/ssms"
        filters = {
            "op": "and",
            "content": [
                {
                    "op": "in",
                    "content": {
                        "field": "consequence.transcript.gene.symbol",
                        "value": [gene_symbol.upper()]
                    }
                }
            ]
        }
        params = {
            "filters": json.dumps(filters),
            "fields": "ssm_id,genomic_dna_change,consequence.transcript.aa_change,consequence.transcript.gene.symbol",
            "size": size,
        }

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("data", {}).get("hits", [])

        except Exception as e:
            logger.error(f"[GDC] 获取 SSM 失败: {e}")
            return []

    def _extract_aa_changes(self, ssm: Dict) -> List[str]:
        """
        从 SSM 记录中提取氨基酸变化

        Args:
            ssm: SSM 记录

        Returns:
            氨基酸变化列表（去重）
        """
        aa_changes = set()
        consequences = ssm.get("consequence", [])
        for consequence in consequences:
            transcript = consequence.get("transcript", {})
            aa_change = transcript.get("aa_change")
            if aa_change and aa_change != "":
                aa_changes.add(aa_change)
        return list(aa_changes)


# ==================== 全局单例 ====================
_gdc_client_instance: GDCClient = None
_gdc_client_lock = threading.Lock()


def get_gdc_client() -> GDCClient:
    """
    获取全局 GDCClient 单例

    所有 Agent 共享同一个实例和缓存。
    """
    global _gdc_client_instance
    if _gdc_client_instance is None:
        with _gdc_client_lock:
            if _gdc_client_instance is None:
                _gdc_client_instance = GDCClient()
                logger.info("[GDC] 初始化全局单例")
    return _gdc_client_instance


if __name__ == "__main__":
    # 测试
    client = GDCClient()

    print("=== GDC 基因查询: EGFR ===")
    ensembl_id = client._get_ensembl_id("EGFR")
    print(f"Ensembl ID: {ensembl_id}")

    print("\n=== 突变频率查询: EGFR ===")
    freq = client.get_mutation_frequency("EGFR")
    print(f"分析项目数: {freq.get('studies_analyzed')}")
    print(f"总突变数: {freq.get('total_mutations')}")
    print(f"\n按癌种分布 (Top 10):")
    for project, data in list(freq.get("by_cancer_type", {}).items())[:10]:
        print(f"  {project}: {data.get('mutation_count')} 例")
    print(f"\n常见突变 (Top 5):")
    for m in freq.get("top_mutations", [])[:5]:
        print(f"  {m['mutation']}: {m['count']}")

    print("\n=== 变异频率查询: EGFR L858R ===")
    summary = client.get_variant_frequency_summary("EGFR", "L858R")
    print(f"变异计数: {summary.get('variant_count')}")
    print(f"总突变数: {summary.get('total_gene_mutations')}")
    print(f"频率: {summary.get('frequency_percentage')}%")
