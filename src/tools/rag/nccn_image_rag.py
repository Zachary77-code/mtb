"""
NCCN 多模态图片 RAG

基于 byaldi + ColQwen2.5 的多模态文档检索
PDF 每页转为图片，生成多向量嵌入，MaxSim 晚交互检索
"""
from typing import Dict, List, Any, Optional
from pathlib import Path
from src.utils.logger import mtb_logger as logger

try:
    from byaldi import RAGMultiModalModel
    HAS_BYALDI = True
except ImportError:
    HAS_BYALDI = False
    logger.warning("[ImageRAG] byaldi 未安装，请运行: pip install byaldi colpali-engine")

try:
    from transformers.utils.import_utils import is_flash_attn_2_available
    HAS_FLASH_ATTN = is_flash_attn_2_available()
except ImportError:
    HAS_FLASH_ATTN = False


class NCCNImageRag:
    """NCCN 指南多模态图片 RAG 系统 (byaldi + ColQwen2.5 + MaxSim)"""

    DEFAULT_INDEX_NAME = "nccn_colon"

    def __init__(
        self,
        index_root: str = None,
        model_name: str = None,
        device: str = "cuda"
    ):
        """
        初始化多模态 RAG 系统

        Args:
            index_root: 索引存储根目录
            model_name: ColPali/ColQwen 模型名称
            device: 推理设备 ("cuda" 或 "cpu")
        """
        from config.settings import NCCN_IMAGE_VECTOR_DIR, COLPALI_MODEL

        self.index_root = Path(index_root) if index_root else NCCN_IMAGE_VECTOR_DIR
        self.model_name = model_name or COLPALI_MODEL
        self.device = device
        self.model = None
        self._initialized = False

    def build_index(
        self,
        pdf_path: Path,
        index_name: str = None,
        overwrite: bool = True
    ) -> None:
        """
        构建图片索引

        byaldi 自动完成:
        1. PDF 每页转为图片 (pdf2image)
        2. ColQwen2.5 生成多向量嵌入
        3. 持久化索引到 index_root

        Args:
            pdf_path: PDF 文件路径
            index_name: 索引名称
            overwrite: 是否覆盖已有索引
        """
        if not HAS_BYALDI:
            raise ImportError("byaldi 未安装，请运行: pip install byaldi colpali-engine")

        index_name = index_name or self.DEFAULT_INDEX_NAME
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")

        # 确保索引目录存在
        self.index_root.mkdir(parents=True, exist_ok=True)

        attn_impl = "flash_attention_2" if HAS_FLASH_ATTN else "sdpa"
        logger.info(
            f"[ImageRAG] 加载模型: {self.model_name} "
            f"(device={self.device}, attn={attn_impl})"
        )
        self.model = RAGMultiModalModel.from_pretrained(
            self.model_name,
            device=self.device
        )

        logger.info(f"[ImageRAG] 开始构建索引: {pdf_path.name}")
        logger.info(f"[ImageRAG] 索引位置: {self.index_root / index_name}")

        self.model.index(
            input_path=str(pdf_path),
            index_name=index_name,
            index_root=str(self.index_root),
            store_collection_with_index=False,
            overwrite=overwrite
        )

        self._initialized = True
        logger.info(f"[ImageRAG] 索引构建完成: {index_name}")

    def load_index(self, index_name: str = None) -> None:
        """
        从磁盘加载已有索引

        Args:
            index_name: 索引名称
        """
        if not HAS_BYALDI:
            raise ImportError("byaldi 未安装，请运行: pip install byaldi colpali-engine")

        index_name = index_name or self.DEFAULT_INDEX_NAME
        index_path = self.index_root / index_name

        if not index_path.exists():
            raise FileNotFoundError(
                f"索引不存在: {index_path}\n"
                f"请先运行: python -m src.tools.rag.build_image_index"
            )

        attn_impl = "flash_attention_2" if HAS_FLASH_ATTN else "sdpa"
        logger.info(f"[ImageRAG] 加载索引: {index_path} (attn={attn_impl})")
        self.model = RAGMultiModalModel.from_index(
            index_name,
            index_root=str(self.index_root)
        )
        self._initialized = True
        logger.info(f"[ImageRAG] 索引加载完成")

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        MaxSim 检索

        Args:
            query: 查询文本
            top_k: 返回结果数

        Returns:
            结果列表 [{doc_id, page_num, score, metadata}]
        """
        if not self._initialized:
            self.load_index()

        logger.debug(f"[ImageRAG] 检索: {query[:50]}...")

        results = self.model.search(query, k=top_k)

        formatted = []
        for r in results:
            formatted.append({
                "doc_id": r.doc_id,
                "page_num": r.page_num,
                "score": r.score,
                "metadata": r.metadata if hasattr(r, "metadata") else {}
            })

        logger.debug(f"[ImageRAG] 返回 {len(formatted)} 个结果")
        return formatted

    def query(self, question: str, top_k: int = 5) -> str:
        """
        查询并格式化结果

        Args:
            question: 查询问题
            top_k: 返回结果数

        Returns:
            格式化的查询结果文本
        """
        if not self._initialized:
            self.load_index()

        results = self.search(question, top_k)

        if not results:
            return self._no_results_response(question)

        return self._format_results(question, results)

    def _format_results(self, question: str, results: List[Dict]) -> str:
        """格式化查询结果"""
        output_parts = [
            "**NCCN 指南多模态检索结果**\n",
            f"**查询**: {question}\n",
            f"**找到 {len(results)} 个相关页面**:\n",
            "---\n"
        ]

        for i, result in enumerate(results, 1):
            page_num = result.get("page_num", 0)
            score = result.get("score", 0)
            doc_id = result.get("doc_id", 0)

            output_parts.append(f"### {i}. 第 {page_num} 页 (文档 {doc_id})\n")
            output_parts.append(f"**相关度评分**: {score:.4f}\n")
            output_parts.append("---\n")

        output_parts.append(
            "\n**注意**: 以上结果基于页面视觉内容的多模态检索，"
            "返回的是最相关的页码。请参阅对应页面获取详细内容。\n"
        )

        return "".join(output_parts)

    def _no_results_response(self, question: str) -> str:
        """无结果时的响应"""
        return f"""**NCCN 指南多模态检索**

**查询**: {question}

未找到相关页面。可能原因:
1. 索引尚未构建
2. 查询内容与指南内容不匹配

建议:
- 运行 `python -m src.tools.rag.build_image_index` 构建索引
- 尝试使用更具体的医学术语
"""


# 全局实例 (延迟初始化)
_global_image_rag: Optional[NCCNImageRag] = None


def get_nccn_image_rag() -> NCCNImageRag:
    """获取全局多模态 RAG 实例"""
    global _global_image_rag
    if _global_image_rag is None:
        _global_image_rag = NCCNImageRag()
    return _global_image_rag


if __name__ == "__main__":
    import sys

    print("=== NCCN 多模态图片 RAG ===\n")

    rag = NCCNImageRag()

    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--build":
        from config.settings import NCCN_PDF_DIR
        pdf_path = NCCN_PDF_DIR / "（2025.V1）NCCN临床实践指南：结肠癌.pdf"
        print(f"构建索引: {pdf_path}")
        rag.build_index(pdf_path)
    else:
        rag.load_index()

    # 交互式查询
    print("\n输入查询 (输入 'quit' 退出):")
    while True:
        try:
            query = input("\n> ").strip()
            if query.lower() in ('quit', 'exit', 'q'):
                break
            if not query:
                continue

            result = rag.query(query)
            print(result)

        except KeyboardInterrupt:
            break

    print("\n再见！")
