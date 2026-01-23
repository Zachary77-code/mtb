"""
NCCN PDF 处理器

负责提取 PDF 文本并进行分块
"""
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.utils.logger import mtb_logger as logger

# 尝试导入 PyMuPDF
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    logger.warning("[PDF] PyMuPDF 未安装，请运行: pip install PyMuPDF")


class NCCNPdfProcessor:
    """NCCN PDF 文本提取和分块处理器"""

    def __init__(self, pdf_dir: str = None):
        """
        初始化处理器

        Args:
            pdf_dir: PDF 文件目录路径
        """
        from config.settings import NCCN_PDF_DIR
        self.pdf_dir = Path(pdf_dir) if pdf_dir else NCCN_PDF_DIR

        if not self.pdf_dir.exists():
            logger.warning(f"[PDF] 目录不存在: {self.pdf_dir}")

    def list_pdfs(self, filter_types: List[str] = None) -> List[Path]:
        """
        列出 PDF 文件

        Args:
            filter_types: 癌症类型过滤列表（文件名关键词），为空则返回所有

        Returns:
            PDF 文件路径列表
        """
        if not self.pdf_dir.exists():
            return []

        all_pdfs = list(self.pdf_dir.glob("*.pdf"))

        # 如果有过滤条件，只保留匹配的文件
        if filter_types:
            filtered_pdfs = []
            for pdf in all_pdfs:
                filename = pdf.name
                for cancer_type in filter_types:
                    if cancer_type in filename:
                        filtered_pdfs.append(pdf)
                        break
            logger.info(f"[PDF] 找到 {len(all_pdfs)} 个 PDF，过滤后保留 {len(filtered_pdfs)} 个")
            return filtered_pdfs

        logger.info(f"[PDF] 找到 {len(all_pdfs)} 个 PDF 文件")
        return all_pdfs

    def extract_text(self, pdf_path: Path) -> str:
        """
        从 PDF 提取文本

        Args:
            pdf_path: PDF 文件路径

        Returns:
            提取的文本内容
        """
        if not HAS_PYMUPDF:
            logger.error("[PDF] PyMuPDF 未安装")
            return ""

        try:
            doc = fitz.open(pdf_path)
            text_parts = []
            page_count = len(doc)  # 在关闭前保存页数

            for page_num, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"[Page {page_num + 1}]\n{text}")

            doc.close()

            full_text = "\n\n".join(text_parts)
            logger.debug(f"[PDF] 提取 {pdf_path.name}: {len(full_text)} 字符, {page_count} 页")

            return full_text

        except Exception as e:
            logger.error(f"[PDF] 提取失败 {pdf_path.name}: {e}")
            return ""

    def chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[str]:
        """
        将文本分块

        Args:
            text: 原始文本
            chunk_size: 块大小 (字符数)
            chunk_overlap: 块之间的重叠

        Returns:
            文本块列表
        """
        if not text:
            return []

        # 按段落分割
        paragraphs = re.split(r'\n\s*\n', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            # 如果当前段落本身就超过 chunk_size，需要进一步分割
            if len(para) > chunk_size:
                # 先保存当前累积的内容
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""

                # 按句子分割大段落
                sentences = re.split(r'(?<=[.!?。！？])\s+', para)
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) > chunk_size:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = sentence
                    else:
                        current_chunk += " " + sentence if current_chunk else sentence

            elif len(current_chunk) + len(para) > chunk_size:
                # 当前块已满，保存并开始新块
                chunks.append(current_chunk)
                # 保留重叠部分
                overlap_start = max(0, len(current_chunk) - chunk_overlap)
                current_chunk = current_chunk[overlap_start:] + "\n\n" + para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        # 保存最后一个块
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def extract_metadata(self, pdf_path: Path, text: str = None) -> Dict[str, Any]:
        """
        提取 PDF 元数据

        Args:
            pdf_path: PDF 文件路径
            text: 已提取的文本 (可选，用于推断内容)

        Returns:
            元数据字典
        """
        filename = pdf_path.stem

        # 从文件名推断信息
        metadata = {
            "source": str(pdf_path),
            "filename": filename,
            "guideline_name": "",
            "version": "",
            "cancer_type": ""
        }

        # 尝试解析文件名
        # 示例: "非小细胞肺癌 2025 V1" 或 "NSCLC_2025_V2"
        version_match = re.search(r'(V\d+|v\d+|\d{4})', filename)
        if version_match:
            metadata["version"] = version_match.group(1)

        # 常见癌症类型关键词
        cancer_keywords = {
            "肺癌": "Lung Cancer",
            "非小细胞肺癌": "NSCLC",
            "小细胞肺癌": "SCLC",
            "乳腺癌": "Breast Cancer",
            "结直肠癌": "Colorectal Cancer",
            "结肠癌": "Colon Cancer",
            "小肠腺癌": "Small Intestine Adenocarcinoma",
            "胃癌": "Gastric Cancer",
            "肝癌": "Liver Cancer",
            "胰腺癌": "Pancreatic Cancer",
            "前列腺癌": "Prostate Cancer",
            "膀胱癌": "Bladder Cancer",
            "肾癌": "Kidney Cancer",
            "黑色素瘤": "Melanoma",
            "淋巴瘤": "Lymphoma",
            "白血病": "Leukemia",
            "lung": "Lung Cancer",
            "breast": "Breast Cancer",
            "colon": "Colorectal Cancer",
            "nsclc": "NSCLC",
            "sclc": "SCLC"
        }

        filename_lower = filename.lower()
        for keyword, cancer_type in cancer_keywords.items():
            if keyword.lower() in filename_lower:
                metadata["cancer_type"] = cancer_type
                break

        metadata["guideline_name"] = filename

        return metadata

    def process_single_pdf(
        self,
        pdf_path: Path,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[Dict[str, Any]]:
        """
        处理单个 PDF 文件

        Args:
            pdf_path: PDF 文件路径
            chunk_size: 块大小
            chunk_overlap: 重叠大小

        Returns:
            文档块列表 [{text, metadata}]
        """
        logger.info(f"[PDF] 处理: {pdf_path.name}")

        text = self.extract_text(pdf_path)
        if not text:
            return []

        metadata = self.extract_metadata(pdf_path, text)
        chunks = self.chunk_text(text, chunk_size, chunk_overlap)

        documents = []
        for i, chunk in enumerate(chunks):
            doc = {
                "text": chunk,
                "metadata": {
                    **metadata,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
            }
            documents.append(doc)

        logger.info(f"[PDF] {pdf_path.name}: {len(chunks)} 个文档块")
        return documents

    def process_all_pdfs(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        filter_types: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        处理目录中所有 PDF 文件

        Args:
            chunk_size: 块大小
            chunk_overlap: 重叠大小
            filter_types: 癌症类型过滤（为空则使用配置文件中的设置）

        Returns:
            所有文档块列表
        """
        # 如果未指定过滤条件，使用配置文件中的设置
        if filter_types is None:
            from config.settings import NCCN_INDEX_CANCER_TYPES
            filter_types = NCCN_INDEX_CANCER_TYPES if NCCN_INDEX_CANCER_TYPES else None

        pdfs = self.list_pdfs(filter_types=filter_types)
        if not pdfs:
            logger.warning(f"[PDF] 目录中没有匹配的 PDF 文件: {self.pdf_dir}")
            return []

        all_documents = []

        for pdf_path in pdfs:
            try:
                docs = self.process_single_pdf(pdf_path, chunk_size, chunk_overlap)
                all_documents.extend(docs)
            except Exception as e:
                logger.error(f"[PDF] 处理失败 {pdf_path.name}: {e}")
                continue

        logger.info(f"[PDF] 总计处理 {len(pdfs)} 个 PDF，生成 {len(all_documents)} 个文档块")
        return all_documents


if __name__ == "__main__":
    # 测试
    processor = NCCNPdfProcessor()

    print("=== PDF 文件列表 ===")
    pdfs = processor.list_pdfs()
    for pdf in pdfs[:5]:
        print(f"- {pdf.name}")

    if pdfs:
        print(f"\n=== 处理第一个 PDF: {pdfs[0].name} ===")
        docs = processor.process_single_pdf(pdfs[0])
        print(f"生成 {len(docs)} 个文档块")

        if docs:
            print(f"\n第一个块元数据: {docs[0]['metadata']}")
            print(f"文本预览: {docs[0]['text'][:200]}...")
