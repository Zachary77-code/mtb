"""
SmartPubMed Pipeline 逐步诊断报告生成器

对单个查询运行 SmartPubMed 完整 pipeline，生成 6 步诊断报告：
  STEP 1: LLM Query Build (Layer 1/2/3 + fallback)
  STEP 2: PubMed API broad search
  STEP 3: XML Metadata Bucketing
  STEP 4: LLM Batch Evaluation (PASS/REJECT for ALL articles)
  STEP 5: XML vs LLM Bucket Comparison
  STEP 6: Stratified Sampling

Usage:
  python tests/test_reports/generate_pipeline_report.py "KRAS G12C colorectal cancer resistance SHP2 SOS1 inhibitor China"
"""
import sys
import os
import json
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.tools.smart_pubmed import SmartPubMedSearch, get_smart_pubmed
from config.settings import PUBMED_BUCKET_QUOTAS

REPORT_DIR = os.path.dirname(os.path.abspath(__file__))
BATCH_SIZE = 20
SEP = "=" * 100


def evaluate_batch_full(search, original_query, batch, batch_idx, total_batches):
    """
    对一批文章进行 LLM 评估，返回 ALL 评估结果（包括 PASS 和 REJECT）。

    Returns:
        (all_evals, raw_response, passed_articles, report_lines)
    """
    lines = []

    # 准备评估数据（与 _filter_batch 逻辑一致）
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
        lines.append(f"--- Batch {batch_idx + 1}/{total_batches} (0 articles with abstracts, skipped) ---")
        return [], "", [], lines

    batch_pmids = [a["pmid"] for a in articles_for_eval]
    lines.append(f"--- Batch {batch_idx + 1}/{total_batches} ({len(articles_for_eval)} articles) ---")
    lines.append(f"PMIDs: {batch_pmids}")

    # 构建 prompt 并调用 LLM
    prompt = SmartPubMedSearch.BATCH_RELEVANCE_FILTER_PROMPT.format(
        original_query=original_query,
        articles_json=json.dumps(articles_for_eval, ensure_ascii=False),
    )
    raw_response = search._call_llm(prompt, max_tokens=2000)
    lines.append(f"LLM raw response (len={len(raw_response)}):")

    # 解析 JSON 响应
    all_evals = []
    passed = []
    try:
        evaluations = json.loads(raw_response)
        if not isinstance(evaluations, list):
            evaluations = [evaluations]

        for eval_result in evaluations:
            pmid = str(eval_result.get("pmid", ""))
            is_relevant = eval_result.get("is_relevant", False)
            score = eval_result.get("relevance_score", 0)
            study_type = eval_result.get("study_type", "")
            matched_criteria = eval_result.get("matched_criteria", [])
            key_findings = eval_result.get("key_findings", "")

            eval_entry = {
                "pmid": pmid,
                "is_relevant": is_relevant,
                "relevance_score": score,
                "study_type": study_type,
                "matched_criteria": matched_criteria,
                "key_findings": key_findings,
            }
            all_evals.append(eval_entry)

            # 格式化输出
            is_pass = is_relevant and score >= 5
            tag = "PASS  " if is_pass else "REJECT"
            criteria_str = ", ".join(f"'{c}'" for c in matched_criteria) if matched_criteria else ""
            findings_trunc = key_findings[:100] if key_findings else ""

            lines.append(
                f"  [{tag}] PMID {pmid:<12} | score={score:>2} "
                f"| study_type={study_type:<20} | criteria=[{criteria_str}]"
            )
            lines.append(f"           findings: {findings_trunc}")

            # 标注原始文章
            if pmid in pmid_to_article:
                article = pmid_to_article[pmid]
                article["relevance_score"] = score
                article["matched_criteria"] = matched_criteria
                article["key_findings"] = key_findings
                if study_type in SmartPubMedSearch.MTB_EVIDENCE_BUCKETS:
                    article["llm_study_type"] = study_type
                if is_pass:
                    passed.append(article)

    except json.JSONDecodeError as e:
        lines.append(f"  [JSON PARSE ERROR] {e}")
        lines.append(f"  Raw response: {raw_response[:500]}")

    return all_evals, raw_response, passed, lines


def run_pipeline_diagnostic(search, query):
    """运行完整 pipeline 并生成诊断报告文本。"""
    lines = []
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines.append(SEP)
    lines.append("SmartPubMed Pipeline Detailed Report")
    lines.append(SEP)
    lines.append(f"Query: {query}")
    lines.append(f"Time: {timestamp}")
    lines.append("")

    # ================================================================
    # STEP 1 + STEP 2: Layer fallback loop
    # ================================================================
    failed_queries = []
    optimized_query = None
    raw_results = []
    hit_layer = None

    for layer in [1, 2, 3]:
        q = search._build_layer_query(layer, query, failed_queries)

        lines.append(SEP)
        lines.append(f"STEP 1: LLM Query Build (Layer {layer})")
        lines.append(SEP)
        lines.append(f"Generated: {q}")
        lines.append("")

        print(f"[STEP 1] Layer {layer} query built, searching PubMed...")
        results = search.ncbi_client.search_pubmed(q, max_results=200, year_window=10)

        lines.append(SEP)
        lines.append(f"STEP 2: PubMed API broad search (broad=200, year_window=10)")
        lines.append(SEP)
        lines.append(f"API returned: {len(results)} articles")
        lines.append("")

        print(f"[STEP 2] API returned: {len(results)} articles")

        if results:
            optimized_query = q
            raw_results = results
            hit_layer = layer
            break
        failed_queries.append(q)
        print(f"[STEP 1] Layer {layer} returned 0 results, trying next layer...")

    if not raw_results:
        # Regex fallback
        best_concept = search._extract_best_single_concept(query)
        lines.append(f"[Regex fallback]: {best_concept}")
        print(f"[STEP 1] All LLM layers failed, regex fallback: {best_concept}")

        raw_results = search.ncbi_client.search_pubmed(best_concept, max_results=200, year_window=10)
        optimized_query = best_concept
        hit_layer = "fallback"

        lines.append(f"Fallback API returned: {len(raw_results)} articles")
        lines.append("")

    if not raw_results:
        lines.append("NO RESULTS from any layer. Report ends here.")
        return "\n".join(lines)

    # ================================================================
    # STEP 3: XML Metadata Bucketing
    # ================================================================
    lines.append(SEP)
    lines.append("STEP 3: XML Metadata Bucketing")
    lines.append(SEP)

    print(f"[STEP 3] XML bucketing {len(raw_results)} articles...")

    for article in raw_results:
        bucket = search._classify_publication_bucket(article)
        article["mtb_bucket"] = bucket
        article["bucket_source"] = "xml" if bucket else None
        # 保存原始 XML bucket 用于 STEP 5 比较
        article["xml_bucket"] = bucket

    for idx, article in enumerate(raw_results, 1):
        pmid = article.get("pmid", "N/A")
        xml_bucket = article.get("mtb_bucket")
        bucket_display = xml_bucket if xml_bucket else "None(need LLM)"
        pub_types = article.get("publication_types", [])
        title = (article.get("title") or "(no title)")[:80]
        lines.append(
            f"   {idx:>3}. PMID {pmid:<12} | XML: {bucket_display:<20} "
            f"| PubTypes: {pub_types}"
        )
        lines.append(f"      Title: {title}")
        journal = article.get("journal", "")
        year = article.get("year", "")
        abstract = article.get("abstract") or "(no abstract)"
        lines.append(f"      Journal: {journal} ({year})")
        lines.append(f"      Abstract: {abstract[:200]}{'...' if len(abstract) > 200 else ''}")

    xml_count = sum(1 for a in raw_results if a["mtb_bucket"] is not None)
    lines.append(f"  Summary: XML classified {xml_count}/{len(raw_results)}")
    lines.append("")

    # ================================================================
    # STEP 4: LLM Batch Evaluation
    # ================================================================
    lines.append(SEP)
    lines.append("STEP 4: LLM Batch Evaluation (raw JSON responses)")
    lines.append(SEP)

    batches = [raw_results[i:i + BATCH_SIZE] for i in range(0, len(raw_results), BATCH_SIZE)]
    all_passed = []
    total_evaluated = 0

    print(f"[STEP 4] LLM evaluation: {len(raw_results)} articles in {len(batches)} batches...")

    for batch_idx, batch in enumerate(batches):
        all_evals, raw_response, passed, batch_lines = evaluate_batch_full(
            search, query, batch, batch_idx, len(batches)
        )
        lines.extend(batch_lines)
        all_passed.extend(passed)
        total_evaluated += len(all_evals)
        lines.append("")
        print(f"  Batch {batch_idx + 1}/{len(batches)}: {len(all_evals)} evaluated, {len(passed)} passed")

    lines.append(f"LLM filter summary: {len(raw_results)} -> {len(all_passed)} (score >= 5)")
    lines.append("")

    print(f"[STEP 4] Filter complete: {len(raw_results)} -> {len(all_passed)}")

    if not all_passed:
        lines.append("No articles passed LLM filter. Report ends here.")
        return "\n".join(lines)

    # ================================================================
    # STEP 5: XML vs LLM Bucket Comparison
    # ================================================================
    lines.append(SEP)
    lines.append("STEP 5: XML vs LLM Bucket Comparison (Manual Verification Table)")
    lines.append(SEP)

    print(f"[STEP 5] Building comparison table for {len(all_passed)} passed articles...")

    # 应用最终分桶逻辑
    for article in all_passed:
        if article.get("mtb_bucket") is None:
            llm_type = article.get("llm_study_type")
            if llm_type and llm_type in SmartPubMedSearch.MTB_EVIDENCE_BUCKETS:
                article["mtb_bucket"] = llm_type
                article["bucket_source"] = "llm"
            else:
                article["mtb_bucket"] = "observational"
                article["bucket_source"] = "fallback"

    header = (
        f" {'No':>3} | {'PMID':>10}   | {'XML Bucket':>16} | {'LLM study_type':>20} "
        f"| {'Final Bucket':>16} | {'Source':>8} | {'Score':>5} | Title"
    )
    separator = "-" * 140
    lines.append(header)
    lines.append(separator)

    for idx, article in enumerate(all_passed, 1):
        pmid = article.get("pmid", "")
        xml_b = article.get("xml_bucket")
        xml_display = xml_b if xml_b else "None"
        llm_t = article.get("llm_study_type", "")
        final_b = article.get("mtb_bucket", "")
        src = article.get("bucket_source", "")
        score = article.get("relevance_score", "")
        title = (article.get("title") or "")[:50]
        lines.append(
            f" {idx:>3} | {pmid:>10}   | {xml_display:>16} | {llm_t:>20} "
            f"| {final_b:>16} | {src:>8} | {score:>5} | {title}"
        )

    lines.append("")

    # ================================================================
    # STEP 6: Stratified Sampling
    # ================================================================
    lines.append(SEP)
    lines.append("STEP 6: Stratified Sampling")
    lines.append(SEP)

    print(f"[STEP 6] Stratified sampling from {len(all_passed)} articles...")

    lines.append(f"Quotas: {json.dumps(PUBMED_BUCKET_QUOTAS)}")
    lines.append(f"Input: {len(all_passed)} articles, max_results=20")

    # Pre-sample distribution
    pre_dist = {}
    for a in all_passed:
        b = a.get("mtb_bucket", "unknown")
        pre_dist[b] = pre_dist.get(b, 0) + 1
    lines.append(f"  Pre-sample dist:  {json.dumps(pre_dist)}")

    sampled = search._stratified_sample(all_passed, max_results=20)

    # Post-sample distribution
    post_dist = {}
    for a in sampled:
        b = a.get("mtb_bucket", "unknown")
        post_dist[b] = post_dist.get(b, 0) + 1
    lines.append(f"  Post-sample dist: {json.dumps(post_dist)}")
    lines.append(f"  Sampled: {len(all_passed)} -> {len(sampled)}")
    lines.append("")

    lines.append("Final results:")
    for idx, a in enumerate(sampled, 1):
        bucket = a.get("mtb_bucket", "?")
        src = a.get("bucket_source", "?")
        score = a.get("relevance_score", "?")
        pmid = a.get("pmid", "?")
        title = (a.get("title") or "")[:80]
        journal = a.get("journal", "")
        year = a.get("year", "")
        authors = a.get("authors", [])
        abstract = a.get("abstract") or "(no abstract)"
        matched = a.get("matched_criteria", [])
        findings = a.get("key_findings", "")

        lines.append(
            f"   {idx:>2}. [{bucket:<18}] (src={src:<8}, score={score}) "
            f"PMID {pmid}: {title}"
        )
        author_str = ", ".join(authors[:5]) + (" et al." if len(authors) > 5 else "")
        lines.append(f"       Journal: {journal} ({year})")
        lines.append(f"       Authors: {author_str}")
        if matched:
            lines.append(f"       Matched: {matched}")
        if findings:
            lines.append(f"       Findings: {findings}")
        lines.append(f"       Abstract: {abstract}")
        lines.append(f"       Link: https://pubmed.ncbi.nlm.nih.gov/{pmid}/")

    lines.append("")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/test_reports/generate_pipeline_report.py \"<query>\"")
        print()
        print("Example:")
        print('  python tests/test_reports/generate_pipeline_report.py "KRAS G12C colorectal cancer resistance SHP2 SOS1 inhibitor China"')
        sys.exit(1)

    query = sys.argv[1]
    print(f"\n{'=' * 60}")
    print(f"SmartPubMed Pipeline Diagnostic")
    print(f"Query: {query}")
    print(f"{'=' * 60}\n")

    search = get_smart_pubmed()

    report_text = run_pipeline_diagnostic(search, query)

    # 保存报告文件
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_query = query.replace(" ", "_")[:40]
    # 移除不安全的文件名字符
    safe_query = "".join(c for c in safe_query if c.isalnum() or c in "_-")
    filename = f"pipeline_report_{safe_query}_{timestamp}.txt"
    filepath = os.path.join(REPORT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"\n{'=' * 60}")
    print(f"Report saved: {filepath}")
    print(f"{'=' * 60}")

    # 同时输出到 stdout（处理 Windows GBK 终端编码问题）
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("\n" + report_text)


if __name__ == "__main__":
    main()
