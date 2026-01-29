"""
Smart PubMed Search - 3-Layer LLM Progressive Architecture

Each layer uses LLM to build progressively broader PubMed queries,
with later layers receiving previous failures as context.

Architecture:
    User Query
        → [Layer 1 LLM] High-precision tiab-only query → API search
        → [Layer 2 LLM] Expanded MeSH+tiab+synonyms (receives Layer 1 failure) → API search
        → [Layer 3 LLM] Minimal disease+gene only (receives Layer 1+2 failures) → API search
        → [Regex Fallback] Best single concept → API search
        → [LLM Post-filtering] Relevance scoring → Precise Results
"""
import json
import re
import requests
from typing import Dict, List, Any, Optional, Tuple
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
    Smart PubMed Search with 3-Layer LLM Progressive Architecture

    Layer 1: High-precision [tiab]-only query (no MeSH, avoids LLM MeSH errors)
    Layer 2: Expanded recall with MeSH+TIAB dual insurance + synonym expansion
    Layer 3: Minimal fallback with only disease + gene/variant
    Fallback: Regex-based best single concept (no LLM)
    Post-filter: LLM batch relevance scoring on retrieved articles
    """

    LAYER1_PROMPT = """You are a PubMed Search Specialist.

Task: Convert the clinical query into a HIGH-PRECISION PubMed Boolean search string.

Strategy:
1. Extract key concepts: Disease, Gene/Variant, Drug, Mechanism/Outcome
2. Use ONLY [tiab] field tag (title/abstract search) — do NOT use [MeSH]
3. Within each concept, use OR to connect synonyms (wrap each synonym in quotes)
4. Between different concepts, use AND
5. Remove: numeric values (2+, CPS 3, ECOG 1, 79 mut/Mb), staging info, non-English characters
6. Expand common acronyms: CRC → "colorectal cancer", NSCLC → "non-small cell lung cancer", mCRC → "metastatic colorectal cancer"
7. Keep gene names (KRAS, EGFR), variant names (G12C, L858R), and drug names (cetuximab, osimertinib)
8. Combine gene+variant as a single phrase when possible: "KRAS G12C"[tiab]

Example:
  Input: KRAS G12C colorectal cancer resistance SHP2 SOS1 inhibitor
  Output: ("colorectal cancer"[tiab] OR "colorectal neoplasm"[tiab]) AND ("KRAS G12C"[tiab]) AND ("resistance"[tiab] OR "resistant"[tiab]) AND ("SHP2"[tiab] OR "SOS1"[tiab] OR "inhibitor"[tiab])

Output ONLY the raw PubMed query string. No explanation, no markdown.

User Query: {query}

PubMed Query:"""

    LAYER2_PROMPT = """You are a PubMed Search Specialist.

Task: The previous search query returned ZERO results on PubMed. Build a BROADER query with higher recall.

Previous failed query (returned 0 results):
{failed_queries}

Strategy — use MeSH + TIAB dual insurance for each concept:
1. For each concept, use BOTH MeSH and free text: ("MeSH Term"[MeSH] OR "free text"[tiab])
2. Expand drug synonyms: generic name + brand name + development code
   e.g., (osimertinib[tiab] OR Tagrisso[tiab] OR AZD9291[tiab])
3. Expand variant notations: L858R OR "exon 21" OR "p.L858R"
4. Expand disease terms with MeSH: ("Colorectal Neoplasms"[MeSH] OR "colorectal cancer"[tiab])
5. Be more inclusive within each concept group (more OR synonyms)
6. Remove overly specific terms that may have caused the previous query to fail

Example:
  Input: KRAS G12C colorectal cancer inhibitor resistance
  Output: ("Colorectal Neoplasms"[MeSH] OR "colorectal cancer"[tiab] OR "CRC"[tiab]) AND ("KRAS"[tiab] OR "KRAS G12C"[tiab]) AND ("drug resistance"[MeSH] OR "resistance"[tiab] OR "inhibitor"[tiab])

Output ONLY the raw PubMed query string. No explanation, no markdown.

Original User Query: {query}

Broader PubMed Query:"""

    LAYER3_PROMPT = """You are a PubMed Search Specialist.

Task: ALL previous queries returned ZERO results. Build a MINIMAL fallback query using only the 2 most essential concepts.

Previous failed queries (all returned 0 results):
{failed_queries}

Strategy:
1. Identify the 2 MOST IMPORTANT concepts from the original query (usually: disease + gene/variant)
2. DROP all drug names, interventions, mechanisms, and modifiers
3. Use simple [tiab] search only — do NOT use [MeSH]
4. Each concept can have 2-3 synonyms connected by OR
5. Connect the 2 concepts with a single AND

Example:
  Input: KRAS G12C colorectal cancer cetuximab resistance SHP2 inhibitor
  Output: ("colorectal cancer"[tiab] OR "CRC"[tiab]) AND ("KRAS G12C"[tiab] OR "KRAS"[tiab])

Output ONLY the raw PubMed query string. No explanation, no markdown.

Original User Query: {query}

Minimal PubMed Query:"""

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

    def _build_layer_query(self, layer: int, query: str, failed_queries: List[str]) -> str:
        """
        Use LLM to build a PubMed query at a specific layer.

        Args:
            layer: Layer number (1=high precision, 2=expanded recall, 3=minimal fallback)
            query: Original user query
            failed_queries: List of previously failed query strings

        Returns:
            Optimized PubMed query string
        """
        prompts = {
            1: self.LAYER1_PROMPT,
            2: self.LAYER2_PROMPT,
            3: self.LAYER3_PROMPT,
        }

        prompt_template = prompts.get(layer, self.LAYER1_PROMPT)
        failed_str = "\n".join(f"  - {q}" for q in failed_queries) if failed_queries else "(none)"

        prompt = prompt_template.format(query=query, failed_queries=failed_str)
        result = self._call_llm(prompt, max_tokens=400)

        if not result:
            result = self._fallback_query_cleanup(query)

        logger.info(f"[SmartPubMed] Layer {layer} 查询: '{query[:40]}...' -> '{result[:80]}...'")
        return result

    def _fallback_query_cleanup(self, query: str) -> str:
        """回退的简单查询清理"""
        # 移除中文字符
        cleaned = re.sub(r'[\u4e00-\u9fff]+', '', query)
        # 移除数值和特殊符号
        cleaned = re.sub(r'\b\d+\.?\d*\s*(\+|%|mut/Mb|ng/ml|U/ml)\b', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\b(ECOG|CPS|PS|TPS)\s*\d+\b', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bp\.([A-Z]\d+[A-Z])\b', r'\1', cleaned)  # p.G12C -> G12C
        cleaned = ' '.join(cleaned.split())
        return cleaned

    def _extract_best_single_concept(self, query: str) -> str:
        """
        最后的纯正则兜底（无 LLM 调用），从查询中提取最佳单概念。

        优先级：基因+变异 > 药物名 > 基因名 > 疾病名
        不选泛用词（high, resistance, mechanisms, response, treatment 等）
        """
        # 先清理中文和数值
        cleaned = self._fallback_query_cleanup(query)
        tokens = cleaned.split()

        # 泛用词排除表
        generic_words = {
            "high", "low", "resistance", "resistant", "mechanisms", "mechanism",
            "response", "treatment", "therapy", "clinical", "monitoring",
            "efficacy", "safety", "analysis", "study", "review", "outcomes",
            "prognosis", "diagnosis", "sensitivity", "inhibitor", "inhibitors",
            "mutation", "mutations", "expression", "pathway", "signaling",
            "China", "patients", "cancer", "tumor", "tumour",
        }

        # 1. 基因+变异 (e.g., "KRAS G12C", "EGFR L858R")
        gene_variant_pattern = re.compile(
            r'\b([A-Z][A-Z0-9]{1,6})\s+([A-Z]\d+[A-Z])\b'
        )
        match = gene_variant_pattern.search(cleaned)
        if match:
            concept = f'"{match.group(1)} {match.group(2)}"'
            logger.info(f"[SmartPubMed] 最佳单概念（基因+变异）: {concept}")
            return concept

        # 2. 药物名 (-ib, -mab, -nib, -lib, -sib 后缀)
        drug_pattern = re.compile(r'\b(\w*(?:inib|tinib|ertinib|umab|izumab|ximab|rasib|clib|lisib|parib))\b', re.IGNORECASE)
        drug_match = drug_pattern.search(cleaned)
        if drug_match:
            drug = drug_match.group(1)
            logger.info(f"[SmartPubMed] 最佳单概念（药物）: {drug}")
            return drug

        # 3. 基因名 (2-6 大写字母+数字)
        gene_pattern = re.compile(r'\b([A-Z][A-Z0-9]{1,5})\b')
        for match in gene_pattern.finditer(cleaned):
            candidate = match.group(1)
            if candidate.lower() not in generic_words and len(candidate) >= 2:
                # 排除常见非基因缩写
                non_gene = {"AND", "OR", "NOT", "MeSH", "TIAB", "CRC", "MSS", "MSI", "TMB", "IHC", "CPS", "TPS", "ECOG"}
                if candidate not in non_gene:
                    logger.info(f"[SmartPubMed] 最佳单概念（基因）: {candidate}")
                    return candidate

        # 4. 疾病名（多词短语）
        disease_patterns = [
            r'"?(colorectal cancer|colorectal neoplasm|colon cancer|rectal cancer)"?',
            r'"?(non-small cell lung cancer|NSCLC|lung adenocarcinoma|lung cancer)"?',
            r'"?(breast cancer|pancreatic cancer|gastric cancer|ovarian cancer)"?',
            r'"?(hepatocellular carcinoma|prostate cancer|melanoma|glioblastoma)"?',
        ]
        for dp in disease_patterns:
            dm = re.search(dp, cleaned, re.IGNORECASE)
            if dm:
                disease = dm.group(0).strip('"')
                logger.info(f"[SmartPubMed] 最佳单概念（疾病）: {disease}")
                return f'"{disease}"'

        # 5. 兜底：第一个非泛用词 token
        for token in tokens:
            if token.lower() not in generic_words and len(token) >= 3:
                logger.info(f"[SmartPubMed] 最佳单概念（首非泛用词）: {token}")
                return token

        # 最终兜底
        fallback = tokens[0] if tokens else query.split()[0] if query else ""
        logger.info(f"[SmartPubMed] 最佳单概念（兜底）: {fallback}")
        return fallback

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
    ) -> Tuple[List[Dict], str]:
        """
        智能搜索主流程：3 层 LLM 递进检索 + 正则兜底

        每层由 LLM 构建查询，后一层收到前一层失败的查询作为上下文，逐步放宽策略。

        Args:
            query: 用户原始查询（自然语言）
            max_results: 最终返回结果数
            broad_search_count: API 宽搜数量（用于后筛选池）
            skip_filtering: 跳过 LLM 筛选（用于简单查询）

        Returns:
            (筛选后的高相关性文献列表, 实际使用的查询字符串)
        """
        logger.info(f"[SmartPubMed] 开始搜索: {query[:80]}...")

        failed_queries = []

        # Layer 1: 高精度 [tiab]-only 查询
        q1 = self._build_layer_query(1, query, failed_queries)
        results = self.ncbi_client.search_pubmed(q1, max_results=broad_search_count)
        if results:
            logger.info(f"[SmartPubMed] Layer 1 命中 {len(results)} 篇")
            return self._finalize_results(query, results, q1, max_results, skip_filtering)
        failed_queries.append(q1)

        # Layer 2: 扩召回 MeSH+TIAB+同义词
        q2 = self._build_layer_query(2, query, failed_queries)
        results = self.ncbi_client.search_pubmed(q2, max_results=broad_search_count)
        if results:
            logger.info(f"[SmartPubMed] Layer 2 命中 {len(results)} 篇")
            return self._finalize_results(query, results, q2, max_results, skip_filtering)
        failed_queries.append(q2)

        # Layer 3: 兜底 疾病+基因 only
        q3 = self._build_layer_query(3, query, failed_queries)
        results = self.ncbi_client.search_pubmed(q3, max_results=broad_search_count)
        if results:
            logger.info(f"[SmartPubMed] Layer 3 命中 {len(results)} 篇")
            return self._finalize_results(query, results, q3, max_results, skip_filtering)

        # Fallback: 最佳单概念（纯正则，无 LLM）
        best_concept = self._extract_best_single_concept(query)
        logger.warning(f"[SmartPubMed] 3 层 LLM 均无结果，正则兜底: {best_concept}")
        results = self.ncbi_client.search_pubmed(best_concept, max_results=broad_search_count)
        if results:
            logger.info(f"[SmartPubMed] Fallback 命中 {len(results)} 篇")
            return self._finalize_results(query, results, best_concept, max_results, skip_filtering)

        logger.warning(f"[SmartPubMed] 所有查询策略均无结果")
        return [], best_concept

    def _finalize_results(
        self,
        original_query: str,
        results: List[Dict],
        used_query: str,
        max_results: int,
        skip_filtering: bool
    ) -> Tuple[List[Dict], str]:
        """对搜索结果进行 LLM 筛选（可选）并返回"""
        logger.info(f"[SmartPubMed] API 返回 {len(results)} 篇文献")

        if skip_filtering:
            return results[:max_results], used_query

        filtered = self._filter_results(original_query, results)
        return filtered[:max_results], used_query


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
