"""
文献工具（占位符实现）
"""
from src.tools.base_tool import BaseMockTool
from typing import Dict, Any


class PubMedTool(BaseMockTool):
    """PubMed 文献搜索工具"""

    def __init__(self):
        super().__init__(
            name="search_pubmed",
            description="搜索 PubMed 获取相关文献。输入关键词如：'EGFR L858R osimertinib clinical trial'"
        )

    def _generate_mock_response(self, query: str = "", **kwargs) -> str:
        return f"""
**PubMed 搜索结果（模拟数据）**

**搜索关键词**: {query}
**找到文献**: 342 篇

**Top 3 相关文献**:

1. **FLAURA Trial: Osimertinib vs Standard EGFR TKIs**
   - PMID: 29151359
   - Ramalingam SS, et al. N Engl J Med. 2020.
   - 结果: Osimertinib组 mPFS 18.9个月 vs 对照组 10.2个月 (HR=0.46, P<0.001)
   - 链接: https://pubmed.ncbi.nlm.nih.gov/29151359/

2. **ADAURA Trial: Adjuvant Osimertinib in EGFR+ NSCLC**
   - PMID: 33277505
   - Wu YL, et al. N Engl J Med. 2020.
   - 结果: 辅助治疗显著改善 DFS (HR=0.20, P<0.001)
   - 链接: https://pubmed.ncbi.nlm.nih.gov/33277505/

3. **Real-World Evidence of Osimertinib in Chinese Patients**
   - PMID: 35123456 (模拟)
   - Liu X, et al. Lung Cancer. 2023.
   - 结果: 中国真实世界数据显示 mPFS 16.2个月，与临床试验一致
   - 链接: https://pubmed.ncbi.nlm.nih.gov/35123456/
"""

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词，支持布尔运算符 (AND, OR)"
                }
            },
            "required": ["query"]
        }
