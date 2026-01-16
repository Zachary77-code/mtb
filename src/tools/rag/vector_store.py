"""
NCCN 向量存储

使用 ChromaDB 存储和检索文档向量
"""
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.utils.logger import mtb_logger as logger

# 尝试导入依赖
try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False
    logger.warning("[VectorStore] ChromaDB 未安装，请运行: pip install chromadb")

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False
    logger.warning("[VectorStore] sentence-transformers 未安装，请运行: pip install sentence-transformers")


class NCCNVectorStore:
    """NCCN 指南向量存储"""

    COLLECTION_NAME = "nccn_guidelines"

    def __init__(self, persist_dir: str = None, embedding_model: str = None):
        """
        初始化向量存储

        Args:
            persist_dir: 持久化目录
            embedding_model: 嵌入模型名称
        """
        from config.settings import NCCN_VECTOR_DIR, EMBEDDING_MODEL

        self.persist_dir = Path(persist_dir) if persist_dir else NCCN_VECTOR_DIR
        self.embedding_model_name = embedding_model or EMBEDDING_MODEL

        self.client = None
        self.collection = None
        self.embedding_model = None

        self._initialized = False

    def initialize(self):
        """初始化存储 (延迟加载)"""
        if self._initialized:
            return

        if not HAS_CHROMADB:
            raise ImportError("ChromaDB 未安装")

        if not HAS_SENTENCE_TRANSFORMERS:
            raise ImportError("sentence-transformers 未安装")

        # 确保目录存在
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # 初始化 ChromaDB
        logger.info(f"[VectorStore] 初始化 ChromaDB: {self.persist_dir}")
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False)
        )

        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"description": "NCCN Guidelines for MTB"}
        )

        # 加载嵌入模型
        logger.info(f"[VectorStore] 加载嵌入模型: {self.embedding_model_name}")
        self.embedding_model = SentenceTransformer(self.embedding_model_name)

        self._initialized = True
        logger.info(f"[VectorStore] 初始化完成，现有文档数: {self.collection.count()}")

    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """生成文本嵌入"""
        if not self._initialized:
            self.initialize()

        embeddings = self.embedding_model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()

    def build_index(self, documents: List[Dict[str, Any]], batch_size: int = 100):
        """
        构建索引

        Args:
            documents: 文档列表 [{text, metadata}]
            batch_size: 批处理大小
        """
        if not self._initialized:
            self.initialize()

        if not documents:
            logger.warning("[VectorStore] 没有文档需要索引")
            return

        logger.info(f"[VectorStore] 开始构建索引: {len(documents)} 个文档")

        # 清空现有集合
        existing_count = self.collection.count()
        if existing_count > 0:
            logger.info(f"[VectorStore] 清空现有 {existing_count} 个文档")
            # ChromaDB 需要通过 ID 删除
            all_ids = self.collection.get()["ids"]
            if all_ids:
                self.collection.delete(ids=all_ids)

        # 分批处理
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]

            texts = [doc["text"] for doc in batch]
            metadatas = [doc["metadata"] for doc in batch]
            ids = [f"doc_{i + j}" for j in range(len(batch))]

            # 生成嵌入
            embeddings = self._get_embeddings(texts)

            # 添加到集合
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )

            logger.debug(f"[VectorStore] 已索引 {min(i + batch_size, len(documents))}/{len(documents)}")

        logger.info(f"[VectorStore] 索引构建完成，总计 {self.collection.count()} 个文档")

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索相关文档

        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_metadata: 元数据过滤条件

        Returns:
            结果列表 [{text, metadata, score}]
        """
        if not self._initialized:
            self.initialize()

        if self.collection.count() == 0:
            logger.warning("[VectorStore] 索引为空，请先构建索引")
            return []

        # 生成查询嵌入
        query_embedding = self._get_embeddings([query])[0]

        # 执行搜索
        where_filter = filter_metadata if filter_metadata else None

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        # 格式化结果
        formatted_results = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                formatted_results.append({
                    "text": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "score": 1 - results["distances"][0][i] if results["distances"] else 0  # 距离转相似度
                })

        logger.debug(f"[VectorStore] 搜索 '{query[:30]}...' 返回 {len(formatted_results)} 个结果")
        return formatted_results

    def search_by_cancer_type(
        self,
        query: str,
        cancer_type: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        按癌症类型搜索

        Args:
            query: 查询文本
            cancer_type: 癌症类型
            top_k: 返回结果数量

        Returns:
            结果列表
        """
        return self.search(
            query=query,
            top_k=top_k,
            filter_metadata={"cancer_type": cancer_type}
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        if not self._initialized:
            self.initialize()

        count = self.collection.count()

        # 获取所有元数据以统计
        all_data = self.collection.get(include=["metadatas"])

        cancer_types = {}
        sources = set()

        for metadata in all_data.get("metadatas", []):
            if metadata:
                ct = metadata.get("cancer_type", "Unknown")
                cancer_types[ct] = cancer_types.get(ct, 0) + 1
                sources.add(metadata.get("filename", ""))

        return {
            "total_documents": count,
            "unique_sources": len(sources),
            "cancer_types": cancer_types,
            "persist_dir": str(self.persist_dir)
        }


if __name__ == "__main__":
    # 测试
    from src.tools.rag.pdf_processor import NCCNPdfProcessor

    print("=== 向量存储测试 ===")

    # 初始化
    store = NCCNVectorStore()
    store.initialize()

    print(f"当前统计: {store.get_stats()}")

    # 如果索引为空，构建索引
    if store.collection.count() == 0:
        print("\n索引为空，开始构建...")
        processor = NCCNPdfProcessor()
        docs = processor.process_all_pdfs()

        if docs:
            store.build_index(docs)
        else:
            print("没有可处理的 PDF 文件")

    # 测试搜索
    print("\n=== 搜索测试 ===")
    results = store.search("EGFR mutation treatment", top_k=3)
    for i, r in enumerate(results):
        print(f"\n{i+1}. Score: {r['score']:.3f}")
        print(f"   Source: {r['metadata'].get('filename', 'N/A')}")
        print(f"   Text: {r['text'][:150]}...")
