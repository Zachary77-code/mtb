"""
SmartPubMed 分桶诊断报告生成器

生成两部分报告：
  Part 1: API 原始返回 + XML 分桶（200 篇，展示每篇完整字段）
  Part 2: 完整 search() 流程（LLM 过滤 + 二次分桶 + 分层采样，展示最终结果）

运行: python tests/test_reports/generate_bucketing_report.py
"""
import sys
import os
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.tools.smart_pubmed import get_smart_pubmed

QUERIES = [
    "KRAS G12C colorectal cancer treatment",
]
REPORT_DIR = os.path.dirname(os.path.abspath(__file__))


def format_article_full(idx: int, article: dict, show_llm_fields: bool = False) -> list:
    """格式化单篇文章的完整信息"""
    lines = []
    pmid = article.get("pmid", "N/A")
    title = article.get("title") or "(无标题)"
    journal = article.get("journal", "")
    year = article.get("year", "")
    authors = article.get("authors", [])
    pub_types = article.get("publication_types", [])
    abstract = article.get("abstract") or "(无摘要)"
    mtb_bucket = article.get("mtb_bucket", "")
    bucket_source = article.get("bucket_source", "")

    # 标题行
    if show_llm_fields:
        score = article.get("relevance_score", "N/A")
        lines.append(f"### {idx}. [PMID: {pmid}] {title} (relevance_score: {score}/10)")
    else:
        lines.append(f"### {idx}. [PMID: {pmid}] {title}")

    # 基本字段
    lines.append(f"- **期刊**: {journal} ({year})")
    author_str = ", ".join(authors) if authors else "(无作者信息)"
    lines.append(f"- **作者**: {author_str}")
    lines.append(f"- **PubMed 出版类型**: {', '.join(pub_types) if pub_types else '(无)'}")

    # 分桶信息
    if show_llm_fields:
        source_tag = f" ({bucket_source})" if bucket_source else ""
        lines.append(f"- **最终分桶**: {mtb_bucket}{source_tag}")
        llm_type = article.get("llm_study_type", "")
        if llm_type:
            lines.append(f"- **LLM study_type**: {llm_type}")
        matched = article.get("matched_criteria", [])
        if matched:
            lines.append(f"- **匹配条件**: {', '.join(matched)}")
        findings = article.get("key_findings", "")
        if findings:
            lines.append(f"- **关键发现**: {findings}")
    else:
        lines.append(f"- **XML 分桶**: {mtb_bucket if mtb_bucket else '(未分类 → 待 LLM)'}")

    # 完整摘要
    lines.append(f"- **摘要**: {abstract}")
    lines.append(f"- **链接**: https://pubmed.ncbi.nlm.nih.gov/{pmid}/")
    lines.append("")
    return lines


def generate_report():
    search = get_smart_pubmed()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    for query in QUERIES:
        report = []
        report.append(f"# SmartPubMed 分桶诊断报告")
        report.append(f"")
        report.append(f"- **生成时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"- **查询**: `{query}`")
        report.append(f"")

        # ============================================================
        # Part 1: API 原始返回 + XML 分桶
        # ============================================================
        report.append(f"---")
        report.append(f"")
        report.append(f"## Part 1: API 原始返回 + XML 分桶")
        report.append(f"")

        print(f"[Part 1] 正在从 PubMed API 获取原始结果...")
        raw_results = search.ncbi_client.search_pubmed(query, max_results=200, year_window=10)
        print(f"[Part 1] 获取到 {len(raw_results)} 篇文献")

        # XML 分桶
        for article in raw_results:
            article["mtb_bucket"] = search._classify_publication_bucket(article)
            article["bucket_source"] = "xml" if article["mtb_bucket"] else None

        xml_classified = sum(1 for a in raw_results if a["mtb_bucket"] is not None)
        xml_unclassified = len(raw_results) - xml_classified

        report.append(f"- **API 返回总数**: {len(raw_results)} 篇")
        report.append(f"- **XML 已分类**: {xml_classified} 篇")
        report.append(f"- **XML 未分类**: {xml_unclassified} 篇 (待 LLM 二次分类)")
        report.append(f"")

        # XML 分桶分布
        xml_dist = {}
        for a in raw_results:
            b = a.get("mtb_bucket") or "(未分类)"
            xml_dist[b] = xml_dist.get(b, 0) + 1
        report.append(f"**XML 分桶分布**:")
        report.append(f"")
        for bucket, count in sorted(xml_dist.items(), key=lambda x: -x[1]):
            report.append(f"| {bucket} | {count} |")
        report.append(f"")

        # 每篇文章详情
        report.append(f"### 文章详情 ({len(raw_results)} 篇)")
        report.append(f"")
        for idx, article in enumerate(raw_results, 1):
            report.extend(format_article_full(idx, article, show_llm_fields=False))

        # ============================================================
        # Part 2: 完整 search() 流程
        # ============================================================
        report.append(f"---")
        report.append(f"")
        report.append(f"## Part 2: 完整 search() 流程 (LLM 过滤 + 二次分桶 + 分层采样)")
        report.append(f"")

        print(f"[Part 2] 正在运行完整 search() 流程 (含 LLM 过滤)...")
        final_results, optimized_query = search.search(query, max_results=20)
        print(f"[Part 2] 最终返回 {len(final_results)} 篇文献")

        report.append(f"- **优化查询**: `{optimized_query}`")
        report.append(f"- **最终返回**: {len(final_results)} 篇")
        report.append(f"")

        # 最终分桶分布
        final_dist = {}
        for a in final_results:
            b = a.get("mtb_bucket", "unknown")
            src = a.get("bucket_source", "unknown")
            key = f"{b}({src})"
            final_dist[key] = final_dist.get(key, 0) + 1
        report.append(f"**最终分桶分布 (bucket_source)**:")
        report.append(f"")
        report.append(f"| 分桶 | 数量 |")
        report.append(f"|------|------|")
        for bucket, count in sorted(final_dist.items(), key=lambda x: -x[1]):
            report.append(f"| {bucket} | {count} |")
        report.append(f"")

        # 每篇文章详情
        report.append(f"### 最终结果详情 ({len(final_results)} 篇)")
        report.append(f"")
        for idx, article in enumerate(final_results, 1):
            report.extend(format_article_full(idx, article, show_llm_fields=True))

        # 写入报告文件
        safe_query = query.replace(" ", "_")[:30]
        filename = f"bucketing_report_{safe_query}_{timestamp}.md"
        filepath = os.path.join(REPORT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(report))

        print(f"\n报告已保存: {filepath}")


if __name__ == "__main__":
    generate_report()
