"""
Smart PubMed Search - Sandwich Architecture (LLM-API-LLM)

Uses LLM query preprocessing + API broad search + LLM post-filtering to improve search accuracy.

Architecture:
    User Query -> [LLM Optimization] -> API Broad Search -> [LLM Filtering] -> Precise Results
"""
import json
import re
import requests
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.tools.api_clients.ncbi_client import get_ncbi_client
from src.utils.logger import mtb_logger as logger
from config.settings import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    SUBGRAPH_MODEL  # 使用 flash 模型降低成本
)


class SmartPubMedSearch:
    """
    Smart PubMed Search with Sandwich Architecture

    Step 1: LLM Preprocessing - Convert natural language to optimized PubMed Boolean query
    Step 2: API Broad Search - Retrieve more candidate articles (high Recall)
    Step 3: LLM Post-filtering - Read abstracts for precise matching (high Precision)
    """

    QUERY_OPTIMIZATION_PROMPT = """You are a PubMed Search Specialist.

Task: Convert the clinical query into an optimized PubMed Boolean search string.

Rules:
1. Identify key entities: Disease, Drug, Gene, Biomarker
2. Use MeSH terms where possible (e.g., "Colorectal Neoplasms"[MeSH])
3. CRITICAL: Remove specific numeric values like "2+", "CPS 3", "79 mut/Mb", "ECOG 1" - these cause search failures. Only keep the biomarker/score NAME.
4. Expand acronyms (CRC -> Colorectal Cancer, NSCLC -> Non-Small Cell Lung Cancer, mCRC -> metastatic Colorectal Cancer)
5. Keep gene names (KRAS, EGFR, ATM) and drug names (cetuximab, pembrolizumab)
6. Use AND to connect different concepts, OR to connect synonyms
7. Output ONLY the raw query string, no explanation or markdown

User Query: {query}

Optimized PubMed Query:"""

    RELEVANCE_FILTER_PROMPT = """You are a Clinical Literature Reviewer.

Task: Evaluate if this abstract matches the user's specific search criteria.

User's Original Query: {original_query}

Abstract (PMID: {pmid}):
Title: {title}
{abstract}

Evaluate relevance considering:
- Does it discuss the specific disease/cancer type?
- Does it mention the gene/biomarker of interest?
- Does it discuss relevant treatments or clinical outcomes?
- Does it match any specific numeric criteria from the original query (like "2+", "CPS 3", etc.)?

Return ONLY valid JSON (no markdown, no explanation):
{{"is_relevant": true/false, "relevance_score": 0-10, "matched_criteria": ["list"], "key_findings": "brief summary"}}"""

    BATCH_RELEVANCE_FILTER_PROMPT = """You are a Clinical Literature Reviewer.

Task: Evaluate if EACH abstract matches the user's specific search criteria.

User's Original Query: {original_query}

Articles to evaluate (JSON array):
{articles_json}

For EACH article, evaluate:
- Does it discuss the specific disease/cancer type?
- Does it mention the gene/biomarker of interest?
- Does it discuss relevant treatments or clinical outcomes?
- Does it match any specific numeric criteria from the original query?

Return ONLY a valid JSON array (no markdown, no explanation):
[{{"pmid": "...", "is_relevant": true/false, "relevance_score": 0-10, "matched_criteria": ["..."], "key_findings": "..."}}]

IMPORTANT: Return evaluation for ALL articles in the input, maintaining the same order."""

    def __init__(self):
        self.ncbi_client = get_ncbi_client()
        self.model = SUBGRAPH_MODEL

    def _call_llm(self, prompt: str, max_tokens: int = 500) -> str:
        """Call LLM (using flash model to reduce cost)"""
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.1  # 低温度确保稳定输出
        }
        try:
            response = requests.post(
                OPENROUTER_BASE_URL,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()
            # Clean potential markdown code blocks
            if content.startswith("```"):
                content = re.sub(r'^```\w*\n?', '', content)
                content = re.sub(r'\n?```$', '', content)
            return content
        except Exception as e:
            logger.error(f"[SmartPubMed] LLM 调用失败: {e}")
            return ""

    def _optimize_query(self, query: str) -> str:
        """
        Step 1: LLM Query Optimization

        Convert natural language query to PubMed Boolean search string,
        removing special characters and numeric values that cause search failures.
        """
        prompt = self.QUERY_OPTIMIZATION_PROMPT.format(query=query)
        optimized = self._call_llm(prompt, max_tokens=300)

        if not optimized:
            # 回退：简单正则清理
            optimized = self._fallback_query_cleanup(query)

        logger.info(f"[SmartPubMed] 查询优化: '{query[:40]}...' -> '{optimized[:60]}...'")
        return optimized

    def _fallback_query_cleanup(self, query: str) -> str:
        """回退的简单查询清理"""
        # 移除数值和特殊符号
        cleaned = re.sub(r'\b\d+\.?\d*\s*(\+|%|mut/Mb|ng/ml|U/ml)\b', '', query, flags=re.IGNORECASE)
        cleaned = re.sub(r'\b(ECOG|CPS|PS|TPS)\s*\d+\b', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bp\.([A-Z]\d+[A-Z])\b', r'\1', cleaned)  # p.G12C -> G12C
        cleaned = ' '.join(cleaned.split())
        return cleaned

    def _filter_batch(self, original_query: str, batch: List[Dict], batch_idx: int) -> List[Dict]:
        """
        评估一批文章的相关性（单次 LLM 调用评估多篇）

        Args:
            original_query: 用户原始查询
            batch: 文章列表（最多 20 篇）
            batch_idx: 批次索引（用于日志）

        Returns:
            相关文章列表（带相关性评分）
        """
        # 过滤无摘要的文章，构建精简的文章 JSON
        articles_for_eval = []
        pmid_to_article = {}
        for article in batch:
            pmid = article.get("pmid", "")
            abstract = article.get("abstract", "")
            if not abstract:
                continue
            pmid_to_article[pmid] = article
            articles_for_eval.append({
                "pmid": pmid,
                "title": article.get("title", ""),
                "abstract": abstract
            })

        if not articles_for_eval:
            return []

        # 构建批量评估 prompt
        prompt = self.BATCH_RELEVANCE_FILTER_PROMPT.format(
            original_query=original_query,
            articles_json=json.dumps(articles_for_eval, ensure_ascii=False)
        )

        # 调用 LLM（增加 max_tokens 以容纳批量输出）
        response = self._call_llm(prompt, max_tokens=2000)

        # 解析返回的 JSON 数组
        filtered = []
        try:
            evaluations = json.loads(response)
            if not isinstance(evaluations, list):
                evaluations = [evaluations]

            for eval_result in evaluations:
                pmid = str(eval_result.get("pmid", ""))
                is_relevant = eval_result.get("is_relevant", False)
                score = eval_result.get("relevance_score", 0)

                if pmid in pmid_to_article and is_relevant and score >= 5:
                    article = pmid_to_article[pmid]
                    article["relevance_score"] = score
                    article["matched_criteria"] = eval_result.get("matched_criteria", [])
                    article["key_findings"] = eval_result.get("key_findings", "")
                    filtered.append(article)

            logger.debug(f"[SmartPubMed] 批次 {batch_idx}: {len(articles_for_eval)} -> {len(filtered)} 篇相关")

        except json.JSONDecodeError as e:
            logger.warning(f"[SmartPubMed] 批次 {batch_idx} JSON 解析失败: {e}")
            # 回退：尝试提取 is_relevant: true 的 PMID
            for pmid, article in pmid_to_article.items():
                if f'"{pmid}"' in response and '"is_relevant": true' in response.lower():
                    article["relevance_score"] = 5
                    filtered.append(article)

        return filtered

    def _filter_results(self, original_query: str, results: List[Dict]) -> List[Dict]:
        """
        Step 3: LLM 筛选结果（并行 + 批量策略）

        策略:
        - 将文章分批，每批 20 篇
        - 使用 ThreadPoolExecutor 并行执行多个批次
        - 合并结果并按相关性排序
        """
        if not results:
            return []

        BATCH_SIZE = 20
        MAX_WORKERS = 5

        # 分批
        batches = [results[i:i + BATCH_SIZE] for i in range(0, len(results), BATCH_SIZE)]
        logger.info(f"[SmartPubMed] 开始筛选: {len(results)} 篇分为 {len(batches)} 批 (并行={MAX_WORKERS})")

        # 并行执行
        filtered = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(self._filter_batch, original_query, batch, idx): idx
                for idx, batch in enumerate(batches)
            }
            for future in as_completed(futures):
                batch_idx = futures[future]
                try:
                    batch_results = future.result()
                    filtered.extend(batch_results)
                except Exception as e:
                    logger.error(f"[SmartPubMed] 批次 {batch_idx} 执行失败: {e}")

        # 按相关性排序
        filtered.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        logger.info(f"[SmartPubMed] 筛选完成: {len(results)} -> {len(filtered)} 篇")
        return filtered

    def search(
        self,
        query: str,
        max_results: int = 20,
        broad_search_count: int = 100,
        skip_filtering: bool = False
    ) -> List[Dict]:
        """
        智能搜索主流程

        Args:
            query: 用户原始查询（自然语言）
            max_results: 最终返回结果数
            broad_search_count: API 宽搜数量（用于后筛选池）
            skip_filtering: 跳过 LLM 筛选（用于简单查询）

        Returns:
            筛选后的高相关性文献列表
        """
        logger.info(f"[SmartPubMed] 开始搜索: {query[:50]}...")

        # Step 1: LLM 优化查询
        optimized_query = self._optimize_query(query)

        # Step 2: API 宽搜
        results = self.ncbi_client.search_pubmed(optimized_query, max_results=broad_search_count)

        if not results:
            # 回退策略 1: 尝试简化后的原始查询
            logger.warning(f"[SmartPubMed] 优化查询无结果，尝试回退查询")
            fallback_query = self._fallback_query_cleanup(query)
            results = self.ncbi_client.search_pubmed(fallback_query, max_results=broad_search_count)

        if not results:
            # 回退策略 2: 只用第一个词（通常是基因名或癌症类型）
            first_term = query.split()[0] if query else ""
            if first_term:
                logger.warning(f"[SmartPubMed] 回退查询无结果，尝试单词查询: {first_term}")
                results = self.ncbi_client.search_pubmed(first_term, max_results=broad_search_count)

        if not results:
            logger.warning(f"[SmartPubMed] 所有查询策略均无结果")
            return []

        logger.info(f"[SmartPubMed] API 返回 {len(results)} 篇文献")

        # Step 3: LLM 筛选（可选）
        if skip_filtering:
            return results[:max_results]

        filtered = self._filter_results(query, results)
        return filtered[:max_results]


# ==================== 全局单例 ====================
_smart_pubmed_instance: SmartPubMedSearch = None


def get_smart_pubmed() -> SmartPubMedSearch:
    """获取智能 PubMed 搜索单例"""
    global _smart_pubmed_instance
    if _smart_pubmed_instance is None:
        _smart_pubmed_instance = SmartPubMedSearch()
        logger.info("[SmartPubMed] 初始化智能搜索单例")
    return _smart_pubmed_instance


if __name__ == "__main__":
    # 测试
    search = get_smart_pubmed()

    print("=== 智能 PubMed 搜索测试 ===\n")

    test_queries = [
        "KRAS G12C colorectal cancer cetuximab response",
        "EGFR 2+ IHC colorectal cancer PD-L1 CPS 3 MSS immunotherapy",
        "ATM germline mutation PARP inhibitor solid tumor"
    ]

    for q in test_queries:
        print(f"查询: {q}")
        results = search.search(q, max_results=3)
        print(f"结果: {len(results)} 篇\n")
        for r in results:
            print(f"  - PMID {r.get('pmid')}: {r.get('title', '')[:60]}...")
            if r.get('matched_criteria'):
                print(f"    匹配: {r.get('matched_criteria')}")
        print()
