"""
NCCN RAG (Retrieval Augmented Generation) 工具

整合 PDF 处理和向量检索，提供指南查询接口
"""
from typing import Dict, List, Any, Optional
from pathlib import Path
from src.utils.logger import mtb_logger as logger


class NCCNRag:
    """NCCN 指南 RAG 系统"""

    def __init__(self, auto_init: bool = False):
        """
        初始化 RAG 系统

        Args:
            auto_init: 是否自动初始化 (加载模型)
        """
        from src.tools.rag.pdf_processor import NCCNPdfProcessor
        from src.tools.rag.vector_store import NCCNVectorStore

        self.processor = NCCNPdfProcessor()
        self.vector_store = NCCNVectorStore()

        self._initialized = False

        if auto_init:
            self.initialize()

    def initialize(self):
        """初始化 RAG 系统 (加载模型和索引)"""
        if self._initialized:
            return

        logger.info("[NCCN-RAG] 初始化中...")
        self.vector_store.initialize()

        # 检查是否需要构建索引
        if self.vector_store.collection.count() == 0:
            logger.info("[NCCN-RAG] 索引为空，尝试构建...")
            self.build_index()

        self._initialized = True
        logger.info("[NCCN-RAG] 初始化完成")

    def build_index(self, force: bool = False):
        """
        构建或重建索引

        Args:
            force: 是否强制重建 (即使索引已存在)
        """
        if not self.vector_store._initialized:
            self.vector_store.initialize()

        current_count = self.vector_store.collection.count()

        if current_count > 0 and not force:
            logger.info(f"[NCCN-RAG] 索引已存在 ({current_count} 个文档)，跳过构建")
            return

        logger.info("[NCCN-RAG] 开始处理 PDF 并构建索引...")

        # 处理所有 PDF
        documents = self.processor.process_all_pdfs()

        if not documents:
            logger.warning("[NCCN-RAG] 没有可处理的 PDF 文件")
            return

        # 构建索引
        self.vector_store.build_index(documents)
        logger.info(f"[NCCN-RAG] 索引构建完成: {len(documents)} 个文档块")

    def query(
        self,
        question: str,
        cancer_type: str = None,
        top_k: int = 30
    ) -> str:
        """
        查询 NCCN 指南

        Args:
            question: 查询问题
            cancer_type: 癌症类型 (可选，用于过滤)
            top_k: 返回结果数量

        Returns:
            格式化的查询结果
        """
        if not self._initialized:
            self.initialize()

        logger.debug(f"[NCCN-RAG] 查询: {question[:50]}...")

        # 检查索引状态
        if self.vector_store.collection.count() == 0:
            return self._no_index_response()

        # 执行搜索
        if cancer_type:
            results = self.vector_store.search_by_cancer_type(
                query=question,
                cancer_type=cancer_type,
                top_k=top_k
            )
        else:
            results = self.vector_store.search(
                query=question,
                top_k=top_k
            )

        if not results:
            return self._no_results_response(question)

        return self._format_results(question, results)

    def _format_results(self, question: str, results: List[Dict]) -> str:
        """格式化查询结果"""
        output_parts = [
            f"**NCCN 指南检索结果**\n",
            f"**查询**: {question}\n",
            f"**找到 {len(results)} 条相关内容**:\n",
            "---\n"
        ]

        for i, result in enumerate(results, 1):
            metadata = result.get("metadata", {})
            score = result.get("score", 0)
            text = result.get("text", "")

            source = metadata.get("filename", "Unknown")
            cancer_type = metadata.get("cancer_type", "")
            chunk_info = f"({metadata.get('chunk_index', 0)+1}/{metadata.get('total_chunks', 1)})"

            output_parts.append(f"### {i}. {source} {chunk_info}\n")
            if cancer_type:
                output_parts.append(f"**癌症类型**: {cancer_type}\n")
            output_parts.append(f"**相关度**: {score:.2%}\n\n")

            # 输出完整文本
            output_parts.append(f"{text}\n")

            output_parts.append("\n---\n")

        output_parts.append(
            "\n**注意**: 以上内容来自 NCCN 指南 PDF，"
            "具体治疗方案请结合最新版指南和患者具体情况。\n"
        )

        return "".join(output_parts)

    def _no_index_response(self) -> str:
        """索引为空时的响应"""
        return """**NCCN 指南检索**

⚠️ **索引未建立**

NCCN 指南向量索引尚未建立。请确保:
1. NCCN PDF 文件已放置在 `NCCN_English` 目录
2. 运行 `python -m src.tools.rag.nccn_rag` 构建索引

**当前状态**: 将使用通用知识回答 NCCN 相关问题。
"""

    def _no_results_response(self, question: str) -> str:
        """无结果时的响应"""
        return f"""**NCCN 指南检索**

**查询**: {question}

未找到与查询相关的指南内容。可能原因:
1. 查询关键词与指南内容不匹配
2. 相关指南尚未索引

建议:
- 尝试使用更具体的医学术语
- 检查癌症类型拼写是否正确
"""

    def get_available_guidelines(self) -> List[str]:
        """获取已索引的指南列表"""
        if not self._initialized:
            self.initialize()

        stats = self.vector_store.get_stats()
        return list(stats.get("cancer_types", {}).keys())

    def get_stats(self) -> Dict[str, Any]:
        """获取 RAG 系统统计信息"""
        if not self._initialized:
            self.initialize()

        return {
            "initialized": self._initialized,
            "pdf_dir": str(self.processor.pdf_dir),
            "vector_store": self.vector_store.get_stats()
        }


# 全局实例 (延迟初始化)
_global_nccn_rag: Optional[NCCNRag] = None


def get_nccn_rag() -> NCCNRag:
    """获取全局 NCCN RAG 实例"""
    global _global_nccn_rag
    if _global_nccn_rag is None:
        _global_nccn_rag = NCCNRag(auto_init=False)
    return _global_nccn_rag


if __name__ == "__main__":
    import sys

    print("=== NCCN RAG 系统 ===\n")

    rag = NCCNRag()

    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--build":
        print("强制重建索引...")
        rag.build_index(force=True)
    else:
        rag.initialize()

    # 显示统计
    stats = rag.get_stats()
    print(f"PDF 目录: {stats['pdf_dir']}")
    print(f"文档总数: {stats['vector_store']['total_documents']}")
    print(f"癌症类型: {stats['vector_store']['cancer_types']}")

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
