"""
文献工具

提供 PubMed 文献检索功能
"""
from typing import Dict, Any, Optional, List
from src.tools.base_tool import BaseTool
from src.tools.api_clients.ncbi_client import NCBIClient
from config.settings import NCBI_API_KEY, NCBI_EMAIL
from src.utils.logger import mtb_logger as logger


class PubMedTool(BaseTool):
    """PubMed 文献搜索工具"""

    def __init__(self):
        super().__init__(
            name="search_pubmed",
            description="搜索 PubMed 获取相关文献。输入关键词如：'EGFR L858R osimertinib clinical trial'"
        )
        self.client = NCBIClient(api_key=NCBI_API_KEY, email=NCBI_EMAIL)

    def _call_real_api(self, query: str = "", max_results: int = 5, **kwargs) -> Optional[str]:
        """
        调用 NCBI E-utilities 搜索 PubMed

        Args:
            query: 搜索关键词
            max_results: 最大结果数

        Returns:
            格式化的搜索结果
        """
        if not query:
            return None

        results = self.client.search_pubmed(query, max_results=max_results)

        if not results:
            return f"**PubMed 搜索结果**\n\n**搜索关键词**: {query}\n\n未找到相关文献。"

        return self._format_results(query, results)

    def _format_results(self, query: str, results: List[Dict]) -> str:
        """格式化搜索结果"""
        output = [
            f"**PubMed 搜索结果**\n",
            f"**搜索关键词**: {query}",
            f"**找到文献**: {len(results)} 篇\n",
            "---\n"
        ]

        for i, article in enumerate(results, 1):
            pmid = article.get("pmid", "N/A")
            title = article.get("title", "无标题")
            authors = article.get("authors", [])
            journal = article.get("journal", "")
            year = article.get("year", "")
            abstract = article.get("abstract", "")

            # 作者格式化
            author_str = ", ".join(authors[:3])
            if len(authors) > 3:
                author_str += ", et al."

            output.append(f"### {i}. {title}\n")
            output.append(f"- **PMID**: {pmid}")
            output.append(f"- **作者**: {author_str}")
            output.append(f"- **期刊**: {journal} ({year})")

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
