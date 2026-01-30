"""
NCBI E-utilities 客户端

支持 PubMed 文献检索和 ClinVar 变异查询
API 文档: https://www.ncbi.nlm.nih.gov/books/NBK25500/
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
from src.utils.logger import mtb_logger as logger


class NCBIClient:
    """NCBI E-utilities API 客户端"""

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, api_key: str = None, email: str = None):
        """
        初始化 NCBI 客户端

        Args:
            api_key: NCBI API Key (可选，提高请求限额至 10/秒)
            email: 联系邮箱 (NCBI 建议提供)
        """
        self.api_key = api_key
        self.email = email
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "MTB-Workflow/1.0 (Medical Tumor Board)"
        })
        # 重试策略：处理瞬态 SSL/网络错误和服务端限流
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,           # 1s → 2s → 4s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        # 请求间隔 (无 API Key 限制 3/秒)
        self._last_request_time = 0
        self._min_interval = 0.34 if not api_key else 0.1

    def _rate_limit(self):
        """速率限制"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    def _build_params(self, params: Dict) -> Dict:
        """构建请求参数"""
        if self.api_key:
            params["api_key"] = self.api_key
        if self.email:
            params["email"] = self.email
        return params

    # ==================== PubMed 相关 ====================

    def search_pubmed(self, query: str, max_results: int = 20, year_window: int = None) -> List[Dict]:
        """
        搜索 PubMed 文献

        Args:
            query: 搜索关键词 (支持布尔运算符)
            max_results: 最大结果数
            year_window: 搜索时间窗口（年数），如 10 表示最近 10 年

        Returns:
            文献列表 [{pmid, title, authors, journal, year, abstract, publication_types}]
        """
        self._rate_limit()

        # Step 1: esearch 获取 PMID 列表
        search_url = f"{self.BASE_URL}/esearch.fcgi"
        params = self._build_params({
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance"
        })

        # 日期范围过滤
        if year_window and year_window > 0:
            import datetime
            current_year = datetime.datetime.now().year
            params["datetype"] = "pdat"
            params["mindate"] = str(current_year - year_window)
            params["maxdate"] = str(current_year)

        try:
            logger.debug(f"[NCBI] PubMed 搜索: {query}")
            response = self.session.get(search_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            pmids = data.get("esearchresult", {}).get("idlist", [])
            if not pmids:
                logger.info(f"[NCBI] PubMed 无结果: {query}")
                return []

            logger.debug(f"[NCBI] 找到 {len(pmids)} 篇文献")

            # Step 2: efetch 获取详细信息
            return self.fetch_abstracts(pmids)

        except Exception as e:
            logger.error(f"[NCBI] PubMed 搜索失败: {e}")
            return []

    def fetch_abstracts(self, pmids: List[str]) -> List[Dict]:
        """
        获取文献详细信息

        Args:
            pmids: PMID 列表

        Returns:
            文献详细信息列表
        """
        if not pmids:
            return []

        self._rate_limit()

        fetch_url = f"{self.BASE_URL}/efetch.fcgi"
        params = self._build_params({
            "db": "pubmed",
            "id": ",".join(pmids),
            "rettype": "xml",
            "retmode": "xml"
        })

        try:
            response = self.session.get(fetch_url, params=params, timeout=60)
            response.raise_for_status()

            return self._parse_pubmed_xml(response.text)

        except Exception as e:
            logger.error(f"[NCBI] 获取摘要失败: {e}")
            return []

    def _parse_pubmed_xml(self, xml_text: str) -> List[Dict]:
        """解析 PubMed XML 响应"""
        results = []
        try:
            root = ET.fromstring(xml_text)

            for article in root.findall(".//PubmedArticle"):
                citation = article.find(".//MedlineCitation")
                if citation is None:
                    continue

                pmid_elem = citation.find("PMID")
                pmid = pmid_elem.text if pmid_elem is not None else ""

                article_elem = citation.find("Article")
                if article_elem is None:
                    continue

                # 标题 — 使用 itertext() 处理内联标签（如 <sup>, <i>）
                title_elem = article_elem.find("ArticleTitle")
                title = ''.join(title_elem.itertext()) if title_elem is not None else ""

                # 作者
                authors = []
                author_list = article_elem.find("AuthorList")
                if author_list is not None:
                    for author in author_list.findall("Author"):
                        last_name = author.find("LastName")
                        initials = author.find("Initials")
                        if last_name is not None:
                            name = last_name.text
                            if initials is not None:
                                name += f" {initials.text}"
                            authors.append(name)

                # 期刊
                journal_elem = article_elem.find(".//Journal/Title")
                journal = journal_elem.text if journal_elem is not None else ""

                # 年份
                year_elem = article_elem.find(".//PubDate/Year")
                year = year_elem.text if year_elem is not None else ""

                # 摘要 — 处理内联标签（如 <sup>, <i>）和结构化摘要（多个 AbstractText）
                abstract_sections = article_elem.findall(".//Abstract/AbstractText")
                abstract = ""
                if abstract_sections:
                    parts = []
                    for section in abstract_sections:
                        section_text = ''.join(section.itertext()).strip()
                        if not section_text:
                            continue
                        label = section.get("Label")
                        if label:
                            parts.append(f"{label}: {section_text}")
                        else:
                            parts.append(section_text)
                    abstract = " ".join(parts)

                # 出版类型
                publication_types = []
                pub_type_list = article_elem.find("PublicationTypeList")
                if pub_type_list is not None:
                    for pt in pub_type_list.findall("PublicationType"):
                        if pt.text:
                            publication_types.append(pt.text)

                results.append({
                    "pmid": pmid,
                    "title": title,
                    "authors": authors,  # 返回完整作者列表
                    "journal": journal,
                    "year": year,
                    "abstract": abstract,  # 返回完整摘要
                    "publication_types": publication_types,  # PubMed 出版类型
                })

        except ET.ParseError as e:
            logger.error(f"[NCBI] XML 解析失败: {e}")

        return results

    # ==================== ClinVar 相关 ====================

    def search_clinvar(self, gene: str, variant: str = None) -> List[Dict]:
        """
        搜索 ClinVar 变异

        Args:
            gene: 基因名称 (如 EGFR)
            variant: 变异 (如 L858R)，可选

        Returns:
            变异列表 [{variation_id, gene, variant, classification, review_status}]
        """
        self._rate_limit()

        # 构建更精确的查询
        # 使用 gene symbol 精确匹配
        query_parts = [f'"{gene}"[gene]']
        if variant:
            # 变异名可能是 L858R 或 p.L858R 格式
            query_parts.append(f'("{variant}" OR "p.{variant}")')

        query = " AND ".join(query_parts)

        search_url = f"{self.BASE_URL}/esearch.fcgi"
        params = self._build_params({
            "db": "clinvar",
            "term": query,
            "retmax": 20,  # 增加结果数以便过滤
            "retmode": "json",
            "sort": "clinical_significance"  # 按临床意义排序
        })

        try:
            logger.debug(f"[NCBI] ClinVar 搜索: {query}")
            response = self.session.get(search_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            ids = data.get("esearchresult", {}).get("idlist", [])
            if not ids:
                logger.info(f"[NCBI] ClinVar 无结果: {query}")
                return []

            # 获取详细信息并过滤
            results = self._fetch_clinvar_details(ids)

            # 过滤确保基因匹配
            filtered = [r for r in results if r.get("gene", "").upper() == gene.upper()]

            # 如果过滤后没有结果，返回原始结果
            return filtered if filtered else results[:5]

        except Exception as e:
            logger.error(f"[NCBI] ClinVar 搜索失败: {e}")
            return []

    def _fetch_clinvar_details(self, variation_ids: List[str]) -> List[Dict]:
        """获取 ClinVar 变异详细信息"""
        if not variation_ids:
            return []

        self._rate_limit()

        fetch_url = f"{self.BASE_URL}/efetch.fcgi"
        params = self._build_params({
            "db": "clinvar",
            "id": ",".join(variation_ids),
            "rettype": "vcv",
            "retmode": "xml"
        })

        try:
            response = self.session.get(fetch_url, params=params, timeout=60)
            response.raise_for_status()

            return self._parse_clinvar_xml(response.text)

        except Exception as e:
            logger.error(f"[NCBI] ClinVar 详情获取失败: {e}")
            return []

    def _parse_clinvar_xml(self, xml_text: str) -> List[Dict]:
        """解析 ClinVar XML 响应"""
        results = []
        try:
            root = ET.fromstring(xml_text)

            for record in root.findall(".//VariationArchive"):
                variation_id = record.get("VariationID", "")
                variation_name = record.get("VariationName", "")

                # 临床意义
                classification_elem = record.find(".//ClassifiedRecord/Classifications/GermlineClassification/Description")
                classification = classification_elem.text if classification_elem is not None else "Unknown"

                # 审查状态
                review_elem = record.find(".//ClassifiedRecord/Classifications/GermlineClassification/ReviewStatus")
                review_status = review_elem.text if review_elem is not None else "Unknown"

                # 基因
                gene_elem = record.find(".//Gene")
                gene = gene_elem.get("Symbol", "") if gene_elem is not None else ""

                results.append({
                    "variation_id": variation_id,
                    "variation_name": variation_name,
                    "gene": gene,
                    "classification": classification,
                    "review_status": review_status,
                    "url": f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{variation_id}/"
                })

        except ET.ParseError as e:
            logger.error(f"[NCBI] ClinVar XML 解析失败: {e}")

        return results


# ==================== 全局单例 ====================
_ncbi_client_instance: NCBIClient = None


def get_ncbi_client() -> NCBIClient:
    """
    获取全局 NCBIClient 单例

    所有 Agent 共享同一个限速器，避免并行请求超出 NCBI 限制。
    """
    global _ncbi_client_instance
    if _ncbi_client_instance is None:
        from config.settings import NCBI_API_KEY, NCBI_EMAIL
        _ncbi_client_instance = NCBIClient(api_key=NCBI_API_KEY, email=NCBI_EMAIL)
        logger.info(f"[NCBI] 初始化全局单例 (API Key: {'已配置' if NCBI_API_KEY else '未配置'})")
    return _ncbi_client_instance


if __name__ == "__main__":
    # 测试
    client = get_ncbi_client()

    print("=== PubMed 搜索测试 ===")
    results = client.search_pubmed("EGFR L858R osimertinib", max_results=3)
    for r in results:
        print(f"- PMID {r['pmid']}: {r['title'][:60]}...")

    print("\n=== ClinVar 搜索测试 ===")
    results = client.search_clinvar("EGFR", "L858R")
    for r in results:
        print(f"- {r['gene']} {r['variation_name']}: {r['classification']}")
