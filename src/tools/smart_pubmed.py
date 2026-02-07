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
    SUBGRAPH_MODEL,  # 使用 flash 模型降低成本
    MAX_TOKENS_SUBGRAPH,
    DEFAULT_YEAR_WINDOW,
    PUBMED_BROAD_SEARCH_COUNT,
    PUBMED_BUCKET_QUOTAS,
)


class SmartPubMedSearch:
    """
    Smart PubMed Search with 3-Layer LLM Progressive Architecture

    Layer 1: High-precision [tiab]-only query (no MeSH, avoids LLM MeSH errors)
    Layer 2: Expanded recall with MeSH+TIAB dual insurance + synonym expansion
    Layer 3: Minimal fallback with only disease + gene/variant
    Fallback: Regex-based best single concept (no LLM)
    Post-filter: LLM batch relevance scoring + study type classification
    Sampling: Stratified sampling by MTB evidence bucket quotas
    """

    # MTB 证据桶（按优先级排序，索引越小优先级越高）
    MTB_EVIDENCE_BUCKETS = [
        "guideline", "rct", "systematic_review",
        "observational", "case_report", "preclinical",
    ]

    # PubMed PublicationType → MTB 桶映射
    PUBTYPE_TO_BUCKET = {
        # 指南
        "Practice Guideline": "guideline",
        "Guideline": "guideline",
        "Consensus Development Conference": "guideline",
        "Consensus Development Conference, NIH": "guideline",
        # RCT / 临床试验
        "Randomized Controlled Trial": "rct",
        "Clinical Trial": "rct",
        "Clinical Trial, Phase I": "rct",
        "Clinical Trial, Phase II": "rct",
        "Clinical Trial, Phase III": "rct",
        "Clinical Trial, Phase IV": "rct",
        "Controlled Clinical Trial": "rct",
        "Pragmatic Clinical Trial": "rct",
        # 系统综述 / 荟萃分析 / 综述
        "Systematic Review": "systematic_review",
        "Meta-Analysis": "systematic_review",
        "Review": "systematic_review",
        # 观察性研究
        "Observational Study": "observational",
        "Multicenter Study": "observational",
        "Comparative Study": "observational",
        # 病例报告
        "Case Reports": "case_report",
    }

    # Preclinical 启发式关键词
    PRECLINICAL_MARKERS = [
        "in vitro", "cell line", "xenograft", "mouse model",
        "animal model", "preclinical", "cell culture",
    ]

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
9. IMPORTANT: Use AT MOST 4 AND groups. Prioritize concepts in this order:
   (1) Disease/cancer type — ALWAYS include
   (2) Gene/variant — ALWAYS include if present
   (3) Drug name — include if it is the primary focus of the query
   (4) Mechanism/outcome (resistance, efficacy, prognosis) — include only if ≤3 AND groups so far
   DROP these from AND groups: geographic terms (China, Japan, etc.), staging info, secondary modifiers,
   general terms like "inhibitor" when specific drug names already exist, biomarker subtypes (MSS, TMB-H)
10. When multiple related concepts exist (e.g., SHP2 + SOS1 + inhibitor), merge them into ONE OR group rather than separate AND groups

Example:
  Input: KRAS G12C colorectal cancer resistance SHP2 SOS1 inhibitor China
  Output: ("colorectal cancer"[tiab] OR "colorectal neoplasm"[tiab]) AND ("KRAS G12C"[tiab]) AND ("SHP2"[tiab] OR "SOS1"[tiab] OR "resistance"[tiab])

Output ONLY the raw PubMed query string. No explanation, no markdown.

User Query: {query}

PubMed Query:"""

    LAYER2_PROMPT = """You are a PubMed Search Specialist.

Task: The previous search query returned ZERO results on PubMed. Build a BROADER query with higher recall.

Previous failed query (returned 0 results):
{failed_queries}

Strategy — use MeSH + TIAB dual insurance, AND reduce AND groups:
1. For each concept, use BOTH MeSH and free text: ("MeSH Term"[MeSH] OR "free text"[tiab])
2. Expand drug synonyms: generic name + brand name + development code
   e.g., (osimertinib[tiab] OR Tagrisso[tiab] OR AZD9291[tiab])
3. Expand variant notations: L858R OR "exon 21" OR "p.L858R"
4. Expand disease terms with MeSH: ("Colorectal Neoplasms"[MeSH] OR "colorectal cancer"[tiab])
5. Be more inclusive within each concept group (more OR synonyms)
6. CRITICAL: You MUST use FEWER AND groups than the failed query. Maximum 3 AND groups total.
   - Analyze the failed query: identify which AND group likely caused zero results
   - DROP geographic terms (China, Japan, etc.), mechanism modifiers, biomarker subtypes (MSS, TMB-H), general terms
   - Keep only: Disease + Gene/Drug (primary) + one optional modifier
   - Merge related concepts into OR groups instead of separate AND groups
7. If the query involves a rare/new drug name, drop the combination partner drug and keep only the rare drug + disease

Example:
  Input: KRAS G12C colorectal cancer inhibitor resistance China
  Failed: ... AND ("China"[tiab]) — too restrictive
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

    BATCH_RELEVANCE_FILTER_PROMPT = """You are a Clinical Literature Reviewer for a Molecular Tumor Board.

Task: Evaluate EACH abstract for relevance, evidence quality, and study type.

User's Original Query: {original_query}

Articles to evaluate (JSON array with title, abstract, and PubMed publication types):
{articles_json}

For EACH article, evaluate:
1. Relevance: Does it discuss the specific disease, gene/biomarker, treatment, or clinical outcomes?
2. Evidence quality: Consider study design strength (Phase III RCT > Phase II > Phase I > prospective cohort > retrospective > case series > preclinical), sample size, and whether it reports primary endpoints.
3. Study type classification: Classify into ONE of the following categories based on the study methodology described in the abstract.

IMPORTANT: Use the "publication_types" field as a strong signal for study_type classification.
If publication_types contains "Review", classify as "systematic_review" (not "preclinical").
If publication_types contains "Randomized Controlled Trial", classify as "rct".

study_type categories:
- "guideline": Clinical practice guidelines, consensus statements, expert panel recommendations
- "rct": Randomized controlled trials, clinical trials (any phase), interventional studies
- "systematic_review": Systematic reviews, meta-analyses, pooled analyses, narrative reviews, literature reviews
- "observational": Cohort studies, cross-sectional studies, retrospective analyses, real-world data, registry studies
- "case_report": Case reports, case series (typically < 10 patients)
- "preclinical": In vitro studies, cell line experiments, animal models, xenograft studies.
  A review article that DISCUSSES preclinical data is NOT preclinical — classify it as "systematic_review".
  Only classify as "preclinical" if the article reports ORIGINAL preclinical experimental results.

Return ONLY a valid JSON array (no markdown, no explanation):
[{{"pmid": "...", "is_relevant": true/false, "relevance_score": 0-10, "study_type": "rct|systematic_review|observational|case_report|preclinical|guideline", "matched_criteria": ["..."], "key_findings": "..."}}]

Scoring guideline for relevance_score:
- 9-10: Directly relevant + high-quality evidence (large RCT, guideline, pivotal study)
- 7-8: Directly relevant + moderate evidence (Phase I/II, prospective cohort)
- 5-6: Partially relevant or lower evidence quality (retrospective, case series)
- 1-4: Tangentially relevant or preclinical only
- 0: Not relevant

IMPORTANT: Return evaluation for ALL articles in the input, maintaining the same order."""

    def __init__(self):
        self.ncbi_client = get_ncbi_client()
        self.model = SUBGRAPH_MODEL

    def _call_llm(self, prompt: str, max_tokens: int = MAX_TOKENS_SUBGRAPH) -> str:
        """Call LLM (using flash model to reduce cost)"""
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,  # 低温度确保稳定输出
            "max_tokens": max_tokens,
        }

        # 重试逻辑
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    OPENROUTER_BASE_URL,
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                response.raise_for_status()
                result = response.json()

                # 检查响应格式
                if "choices" not in result:
                    raise ValueError(f"API 错误: {result.get('error', result)}")

                finish_reason = result["choices"][0].get("finish_reason", "unknown")
                if finish_reason == "length":
                    logger.warning(f"[SmartPubMed] LLM 响应被截断 (finish_reason=length, max_tokens={max_tokens})")
                content = result["choices"][0]["message"]["content"].strip()
                # Clean potential markdown code blocks
                if content.startswith("```"):
                    content = re.sub(r'^```\w*\n?', '', content)
                    content = re.sub(r'\n?```$', '', content)
                return content

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"[SmartPubMed] LLM 请求失败 ({type(e).__name__})，重试 ({attempt + 1}/{max_retries - 1})...")
                else:
                    logger.error(f"[SmartPubMed] LLM 请求失败，重试已用尽: {e}")
                    raise
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"[SmartPubMed] LLM 调用失败，重试 ({attempt + 1}/{max_retries - 1}): {e}")
                else:
                    logger.error(f"[SmartPubMed] LLM 调用失败，重试已用尽: {e}")
                    raise

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
        result = self._call_llm(prompt)

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

    def _classify_publication_bucket(self, article: Dict) -> Optional[str]:
        """
        基于 PubMed PublicationType XML 元数据对文章分桶。

        Returns:
            桶名（如 "rct", "guideline"）或 None（仅 "Journal Article"，需 LLM 二次分类）
        """
        pub_types = article.get("publication_types", [])

        # 查映射表，取最高优先级桶
        best_bucket = None
        best_priority = len(self.MTB_EVIDENCE_BUCKETS)

        for pt in pub_types:
            bucket = self.PUBTYPE_TO_BUCKET.get(pt)
            if bucket:
                priority = self.MTB_EVIDENCE_BUCKETS.index(bucket)
                if priority < best_priority:
                    best_priority = priority
                    best_bucket = bucket

        # Preclinical 启发式：无映射匹配时检查 title/abstract 关键词
        if best_bucket is None:
            text = ((article.get("title") or "") + " " + (article.get("abstract") or "")).lower()
            if any(marker in text for marker in self.PRECLINICAL_MARKERS):
                best_bucket = "preclinical"

        return best_bucket

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
                "title": article.get("title") or "",
                "abstract": abstract,
                "publication_types": article.get("publication_types", []),
            })

        if not articles_for_eval:
            return []

        # 构建批量评估 prompt
        prompt = self.BATCH_RELEVANCE_FILTER_PROMPT.format(
            original_query=original_query,
            articles_json=json.dumps(articles_for_eval, ensure_ascii=False)
        )

        response = self._call_llm(prompt)

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
                    # LLM 研究类型分类（用于 XML 未分类文章的二次分桶）
                    llm_study_type = eval_result.get("study_type", "")
                    if llm_study_type in self.MTB_EVIDENCE_BUCKETS:
                        article["llm_study_type"] = llm_study_type
                    filtered.append(article)

            logger.debug(f"[SmartPubMed] 批次 {batch_idx}: {len(articles_for_eval)} -> {len(filtered)} 篇相关")

        except json.JSONDecodeError as e:
            logger.warning(f"[SmartPubMed] 批次 {batch_idx} JSON 解析失败，尝试部分解析: {e}")
            # 尝试截取到最后一个完整对象，挽救已评估的文章
            last_complete = response.rfind("}")
            if last_complete > 0:
                truncated = response[:last_complete + 1].rstrip(",\n\r\t ") + "]"
                try:
                    evaluations = json.loads(truncated)
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
                            llm_study_type = eval_result.get("study_type", "")
                            if llm_study_type in self.MTB_EVIDENCE_BUCKETS:
                                article["llm_study_type"] = llm_study_type
                            filtered.append(article)
                    logger.info(f"[SmartPubMed] 批次 {batch_idx} 部分解析成功: 挽救 {len(filtered)} 篇")
                except json.JSONDecodeError:
                    logger.error(f"[SmartPubMed] 批次 {batch_idx} 部分解析也失败")
                    logger.error(f"[SmartPubMed] 原始响应: {response[:500]}...")
            else:
                logger.error(f"[SmartPubMed] 批次 {batch_idx} 无法部分解析")
                logger.error(f"[SmartPubMed] 原始响应: {response[:500]}...")

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
                    raise

        # 按相关性排序
        filtered.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        logger.info(f"[SmartPubMed] 筛选完成: {len(results)} -> {len(filtered)} 篇")
        return filtered

    def _stratified_sample(self, articles: List[Dict], max_results: int) -> List[Dict]:
        """
        从已分桶的文章中按 MTB 证据配额进行分层采样。

        策略:
        1. 各桶内按 relevance_score 降序排列
        2. 按 PUBMED_BUCKET_QUOTAS 配额取文章
        3. 空桶剩余配额按优先级顺序重新分配给有余量的桶
        4. 最终按 (桶优先级, -relevance_score) 排序返回
        """
        # Step 1: 分桶
        buckets: Dict[str, List[Dict]] = {b: [] for b in self.MTB_EVIDENCE_BUCKETS}

        for article in articles:
            bucket = article.get("mtb_bucket")
            if bucket and bucket in buckets:
                buckets[bucket].append(article)
            else:
                # 兜底：未分类文章归入 observational
                article["mtb_bucket"] = "observational"
                buckets["observational"].append(article)

        # Step 2: 各桶内按 relevance_score 降序排列
        for bucket_name in buckets:
            buckets[bucket_name].sort(
                key=lambda x: x.get("relevance_score", 0), reverse=True
            )

        # 日志：分桶分布
        dist = {b: len(arts) for b, arts in buckets.items() if arts}
        logger.info(f"[SmartPubMed] 证据分桶: {dist}")

        # Step 3: 按配额取文章
        selected = []
        remaining_by_bucket: Dict[str, List[Dict]] = {}

        for bucket_name in self.MTB_EVIDENCE_BUCKETS:
            quota = PUBMED_BUCKET_QUOTAS.get(bucket_name, 0)
            available = buckets[bucket_name]
            take = min(quota, len(available))
            selected.extend(available[:take])
            remaining_by_bucket[bucket_name] = available[take:]

        # Step 4: 空桶剩余配额重分配
        shortfall = max_results - len(selected)
        if shortfall > 0:
            for bucket_name in self.MTB_EVIDENCE_BUCKETS:
                if shortfall <= 0:
                    break
                surplus = remaining_by_bucket.get(bucket_name, [])
                take = min(shortfall, len(surplus))
                if take > 0:
                    selected.extend(surplus[:take])
                    shortfall -= take

        # Step 5: 按 (桶优先级, -relevance_score) 排序
        def sort_key(article):
            bucket = article.get("mtb_bucket", "observational")
            try:
                bucket_priority = self.MTB_EVIDENCE_BUCKETS.index(bucket)
            except ValueError:
                bucket_priority = len(self.MTB_EVIDENCE_BUCKETS)
            relevance = article.get("relevance_score", 0)
            return (bucket_priority, -relevance)

        selected.sort(key=sort_key)

        logger.info(f"[SmartPubMed] 分层采样: {len(articles)} -> {len(selected[:max_results])} 篇")
        return selected[:max_results]

    def search(
        self,
        query: str,
        max_results: int = 20,
        broad_search_count: int = None,
        skip_filtering: bool = False,
        year_window: int = None,
    ) -> Tuple[List[Dict], str]:
        """
        智能搜索主流程：3 层 LLM 递进检索 + 正则兜底 + 分层采样

        每层由 LLM 构建查询，后一层收到前一层失败的查询作为上下文，逐步放宽策略。
        检索结果经 LLM 相关性+证据质量评分后，按 MTB 证据桶配额分层采样。

        Args:
            query: 用户原始查询（自然语言）
            max_results: 最终返回结果数
            broad_search_count: API 宽搜数量（用于后筛选池），默认 PUBMED_BROAD_SEARCH_COUNT
            skip_filtering: 跳过 LLM 筛选（用于简单查询）
            year_window: 搜索时间窗口（年数），默认 DEFAULT_YEAR_WINDOW

        Returns:
            (筛选后的高相关性文献列表, 实际使用的查询字符串)
        """
        if broad_search_count is None:
            broad_search_count = PUBMED_BROAD_SEARCH_COUNT
        if year_window is None:
            year_window = DEFAULT_YEAR_WINDOW

        logger.info(f"[SmartPubMed] 开始搜索: {query[:80]}... (year_window={year_window})")

        failed_queries = []

        # Layer 1: 高精度 [tiab]-only 查询
        q1 = self._build_layer_query(1, query, failed_queries)
        results = self.ncbi_client.search_pubmed(q1, max_results=broad_search_count, year_window=year_window)
        if results:
            logger.info(f"[SmartPubMed] Layer 1 命中 {len(results)} 篇")
            return self._finalize_results(query, results, q1, max_results, skip_filtering)
        failed_queries.append(q1)

        # Layer 2: 扩召回 MeSH+TIAB+同义词
        q2 = self._build_layer_query(2, query, failed_queries)
        results = self.ncbi_client.search_pubmed(q2, max_results=broad_search_count, year_window=year_window)
        if results:
            logger.info(f"[SmartPubMed] Layer 2 命中 {len(results)} 篇")
            return self._finalize_results(query, results, q2, max_results, skip_filtering)
        failed_queries.append(q2)

        # Layer 3: 兜底 疾病+基因 only
        q3 = self._build_layer_query(3, query, failed_queries)
        results = self.ncbi_client.search_pubmed(q3, max_results=broad_search_count, year_window=year_window)
        if results:
            logger.info(f"[SmartPubMed] Layer 3 命中 {len(results)} 篇")
            return self._finalize_results(query, results, q3, max_results, skip_filtering)

        # Fallback: 最佳单概念（纯正则，无 LLM）
        best_concept = self._extract_best_single_concept(query)
        logger.warning(f"[SmartPubMed] 3 层 LLM 均无结果，正则兜底: {best_concept}")
        results = self.ncbi_client.search_pubmed(best_concept, max_results=broad_search_count, year_window=year_window)
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
        """对搜索结果进行 XML 分桶 + LLM 筛选 + LLM 二次分桶 + 分层采样"""
        logger.info(f"[SmartPubMed] API 返回 {len(results)} 篇文献")

        # 第一阶段：XML 元数据分桶
        for article in results:
            article["mtb_bucket"] = self._classify_publication_bucket(article)
            article["bucket_source"] = "xml" if article["mtb_bucket"] else None

        xml_classified = sum(1 for a in results if a["mtb_bucket"] is not None)
        logger.info(f"[SmartPubMed] XML 分桶: {xml_classified}/{len(results)} 篇已分类")

        if skip_filtering:
            # 无 LLM 可用：未分类文章用 observational 兜底
            for article in results:
                if article["mtb_bucket"] is None:
                    article["mtb_bucket"] = "observational"
                    article["bucket_source"] = "fallback"
            return self._stratified_sample(results, max_results), used_query

        # 第二阶段：LLM 相关性+证据质量打分 + study_type 分类
        filtered = self._filter_results(original_query, results)

        # 合并分桶：XML 优先，None 的用 LLM study_type 补全
        for article in filtered:
            if article.get("mtb_bucket") is None:
                llm_type = article.get("llm_study_type")
                if llm_type and llm_type in self.MTB_EVIDENCE_BUCKETS:
                    article["mtb_bucket"] = llm_type
                    article["bucket_source"] = "llm"
                else:
                    article["mtb_bucket"] = "observational"
                    article["bucket_source"] = "fallback"

        llm_classified = sum(1 for a in filtered if a.get("bucket_source") == "llm")
        logger.info(f"[SmartPubMed] LLM 二次分桶: {llm_classified} 篇补全")

        # 第三阶段：分层采样
        return self._stratified_sample(filtered, max_results), used_query


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
