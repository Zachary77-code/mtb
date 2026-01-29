"""
文献工具

提供 PubMed 文献检索功能（使用智能三明治架构）
"""
from typing import Dict, Any, Optional, List
from src.tools.base_tool import BaseTool
from src.tools.smart_pubmed import get_smart_pubmed


class PubMedTool(BaseTool):
    """PubMed 文献搜索工具（智能搜索版）"""

    def __init__(self):
        super().__init__(
            name="search_pubmed",
            description="搜索 PubMed 获取相关文献。支持自然语言查询，如：'KRAS G12C colorectal cancer treatment resistance'"
        )
        self.smart_search = get_smart_pubmed()

    def _call_real_api(self, query: str = "", max_results: int = 20, year_window: int = None, **kwargs) -> Optional[str]:
        """
        Search PubMed using smart sandwich architecture (LLM-API-LLM)

        Flow: LLM query optimization -> API broad search (200) -> LLM filtering + bucketing -> stratified sampling

        Args:
            query: Search keywords (supports natural language)
            max_results: Maximum results to return (default 20)
            year_window: Search time window in years (default 10)

        Returns:
            Formatted search results
        """
        if not query:
            return None

        results, optimized_query = self.smart_search.search(
            query,
            max_results=max_results,
            year_window=year_window,
        )

        if not results:
            return f"**PubMed 搜索结果**\n\n**搜索关键词**: {query}\n**优化查询**: {optimized_query}\n\n未找到相关文献。"

        return self._format_results(query, results, optimized_query=optimized_query)

    # 桶名中文映射
    BUCKET_LABELS = {
        "guideline": "指南", "rct": "RCT", "systematic_review": "系统综述",
        "observational": "观察性", "case_report": "病例报告",
        "preclinical": "临床前",
    }

    def _format_results(self, query: str, results: List[Dict], optimized_query: str = "") -> str:
        """格式化搜索结果（包含相关性评分 + 证据分桶）"""
        output = [
            f"**PubMed 搜索结果**\n",
            f"**搜索关键词**: {query}",
        ]
        if optimized_query and optimized_query != query:
            output.append(f"**优化查询**: {optimized_query}")
        output.append(f"**找到文献**: {len(results)} 篇")

        # 证据分布汇总
        bucket_counts: Dict[str, int] = {}
        for article in results:
            bucket = article.get("mtb_bucket", "")
            if bucket:
                bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
        if bucket_counts:
            dist_str = ", ".join(
                f"{self.BUCKET_LABELS.get(b, b)}:{c}"
                for b, c in bucket_counts.items()
            )
            output.append(f"**证据分布**: {dist_str}")

        output.extend(["\n", "---\n"])

        for i, article in enumerate(results, 1):
            pmid = article.get("pmid", "N/A")
            title = article.get("title", "无标题")
            authors = article.get("authors", [])
            journal = article.get("journal", "")
            year = article.get("year", "")
            abstract = article.get("abstract", "")
            relevance_score = article.get("relevance_score")
            matched_criteria = article.get("matched_criteria", [])
            key_findings = article.get("key_findings", "")

            # 作者格式化 (显示所有作者)
            author_str = ", ".join(authors)

            output.append(f"### {i}. {title}\n")
            output.append(f"- **PMID**: {pmid}")
            output.append(f"- **作者**: {author_str}")
            output.append(f"- **期刊**: {journal} ({year})")

            # 显示相关性评分（如果有）
            if relevance_score is not None:
                output.append(f"- **相关性评分**: {relevance_score}/10")
            if matched_criteria:
                output.append(f"- **匹配条件**: {', '.join(matched_criteria)}")
            if key_findings:
                output.append(f"- **关键发现**: {key_findings}")

            # 出版类型与证据分桶
            pub_types = article.get("publication_types", [])
            mtb_bucket = article.get("mtb_bucket", "")
            bucket_source = article.get("bucket_source", "")
            if pub_types:
                output.append(f"- **出版类型**: {', '.join(pub_types)}")
            if mtb_bucket:
                label = self.BUCKET_LABELS.get(mtb_bucket, mtb_bucket)
                source_tag = f" ({bucket_source})" if bucket_source else ""
                output.append(f"- **证据分类**: {label}{source_tag}")

            if abstract:
                output.append(f"- **摘要**: {abstract}")

            output.append(f"- **链接**: https://pubmed.ncbi.nlm.nih.gov/{pmid}/\n")
            output.append("---\n")

        return "\n".join(output)

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词，支持布尔运算符 (AND, OR)"
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大结果数，默认 5",
                    "default": 5
                },
                "year_window": {
                    "type": "integer",
                    "description": "搜索时间窗口（年数），默认 10 年。罕见变异/疾病可设置更大值（如 20）",
                    "default": 10
                }
            },
            "required": ["query"]
        }


if __name__ == "__main__":
    # 测试
    tool = PubMedTool()

    print("=== PubMed 搜索测试 ===")
    result = tool.invoke(query="EGFR L858R osimertinib", max_results=3)
    print(result)
