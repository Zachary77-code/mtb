"""
NCCN 指南 RAG (Retrieval Augmented Generation) 模块

基于本地 PDF 文件提供指南检索功能
- NCCNRag: 文本 RAG (ChromaDB + DashScope Embedding)
- NCCNImageRag: 多模态图片 RAG (byaldi + ColQwen2)
"""
from src.tools.rag.nccn_rag import NCCNRag
from src.tools.rag.nccn_image_rag import NCCNImageRag

__all__ = ["NCCNRag", "NCCNImageRag"]
