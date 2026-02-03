"""
NCCN 多模态图片 RAG

基于 byaldi + ColQwen2.5 的多模态文档检索
PDF 每页转为图片，生成多向量嵌入，MaxSim 晚交互检索
检索后由多模态 LLM（Gemini）读取页面图片，生成结构化分析
"""
import base64
import gzip
import json
import requests
from typing import Dict, List, Any, Optional
from pathlib import Path
from src.utils.logger import mtb_logger as logger

try:
    from byaldi import RAGMultiModalModel
    HAS_BYALDI = True
except (ImportError, RuntimeError) as e:
    HAS_BYALDI = False
    if "flash_attn" in str(e):
        logger.warning(f"[ImageRAG] flash_attn 组件导入失败 (可能与 Torch 版本不兼容)，已禁用多模态 RAG。错误: {e}")
    else:
        logger.warning(f"[ImageRAG] byaldi 未安装或导入失败 ({e})，请运行: pip install byaldi colpali-engine --no-deps")

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    logger.warning("[ImageRAG] PyMuPDF 未安装，多模态读图功能不可用。请运行: pip install PyMuPDF")

try:
    from transformers.utils.import_utils import is_flash_attn_2_available
    HAS_FLASH_ATTN = is_flash_attn_2_available()
except ImportError:
    HAS_FLASH_ATTN = False


class NCCNImageRag:
    """NCCN 指南多模态图片 RAG 系统 (byaldi + ColQwen2 + MaxSim + 多模态 LLM 读图)"""

    DEFAULT_INDEX_NAME = "nccn_colon"

    def __init__(
        self,
        index_root: str = None,
        model_name: str = None,
        device: str = "cuda",
        enable_multimodal_reading: bool = True
    ):
        """
        初始化多模态 RAG 系统

        Args:
            index_root: 索引存储根目录
            model_name: ColPali/ColQwen 模型名称
            device: 推理设备 ("cuda" 或 "cpu")
            enable_multimodal_reading: 是否启用多模态 LLM 读图（False 则仅返回页码）
        """
        from config.settings import (
            NCCN_IMAGE_VECTOR_DIR, COLPALI_MODEL,
            NCCN_IMAGE_READER_MODEL, NCCN_IMAGE_READER_TEMPERATURE,
            NCCN_IMAGE_READER_TIMEOUT, NCCN_IMAGE_RENDER_SCALE,
            NCCN_IMAGE_SCORE_THRESHOLD,
            OPENROUTER_API_KEY, OPENROUTER_BASE_URL, NCCN_PDF_DIR
        )

        self.index_root = Path(index_root) if index_root else NCCN_IMAGE_VECTOR_DIR
        self.model_name = model_name or COLPALI_MODEL
        self.device = device
        self.model = None
        self._initialized = False

        # 多模态读图配置
        self.enable_multimodal_reading = enable_multimodal_reading
        self.reader_model = NCCN_IMAGE_READER_MODEL
        self.reader_temperature = NCCN_IMAGE_READER_TEMPERATURE
        self.reader_timeout = NCCN_IMAGE_READER_TIMEOUT
        self.render_scale = NCCN_IMAGE_RENDER_SCALE
        self.score_threshold = NCCN_IMAGE_SCORE_THRESHOLD
        self.api_key = OPENROUTER_API_KEY
        self.api_url = OPENROUTER_BASE_URL
        self.nccn_pdf_dir = NCCN_PDF_DIR

        # PDF 路径缓存 (doc_id -> Path)
        self._doc_id_to_pdf: Dict[int, Path] = {}

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
        2. ColQwen2 生成多向量嵌入
        3. 持久化索引到 index_root

        Args:
            pdf_path: PDF 文件路径
            index_name: 索引名称
            overwrite: 是否覆盖已有索引
        """
        if not HAS_BYALDI:
            raise ImportError("byaldi 未安装或不可用，请检查日志中的导入错误或运行: pip install byaldi colpali-engine --no-deps")

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
            index_root=str(self.index_root),
            device=self.device
        )

        logger.info(f"[ImageRAG] 开始构建索引: {pdf_path.name}")
        logger.info(f"[ImageRAG] 索引位置: {self.index_root / index_name}")

        self.model.index(
            input_path=str(pdf_path),
            index_name=index_name,
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
            raise ImportError("byaldi 未安装或不可用，请检查日志中的导入错误或运行: pip install byaldi colpali-engine --no-deps")

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
        查询并返回分析结果

        Pipeline:
        1. byaldi MaxSim 检索 -> top-K 候选页面
        2. 分数阈值过滤（保留 >= 最高分 × threshold 的结果）
        3. PyMuPDF 从 PDF 提取页面图片
        4. 多模态 LLM (Gemini) 分析图片内容
        5. 返回结构化分析

        失败时 fallback 到仅返回页码。

        Args:
            question: 查询问题
            top_k: 初始检索候选数（过滤前）

        Returns:
            多模态 LLM 分析结果，或 fallback 的页码列表
        """
        if not self._initialized:
            self.load_index()

        results = self.search(question, top_k)

        if not results:
            return self._no_results_response(question)

        # 分数阈值过滤：只保留 >= 最高分 × threshold 的结果
        max_score = results[0]["score"]  # byaldi 结果已按分数降序
        threshold = max_score * self.score_threshold
        filtered = [r for r in results if r["score"] >= threshold]
        logger.info(
            f"[ImageRAG] 分数过滤: 最高分={max_score:.2f}, "
            f"阈值={threshold:.2f} ({self.score_threshold:.0%}), "
            f"保留 {len(filtered)}/{len(results)} 页"
        )
        results = filtered

        # 多模态读图
        if self.enable_multimodal_reading and HAS_PYMUPDF:
            llm_analysis = self._multimodal_read(question, results)
            if llm_analysis:
                return self._format_multimodal_results(question, results, llm_analysis)

        # Fallback: 仅返回页码
        return self._format_results(question, results)

    def retrieve(self, question: str, top_k: int = 5) -> Dict[str, Any]:
        """
        检索 NCCN 指南页面并返回原始图片（不经过多模态 LLM 读图）

        Pipeline:
        1. byaldi MaxSim 检索 → top-K 候选页面
        2. 分数阈值过滤（保留 >= 最高分 × threshold 的结果）
        3. PyMuPDF 从 PDF 提取页面图片
        4. 返回 {text: 元数据摘要, images: [{page_num, base64}]}

        供 agent 直接读图使用，跳过 Gemini reader 中间层。

        Args:
            question: 查询问题
            top_k: 初始检索候选数（过滤前）

        Returns:
            {"text": str, "images": List[Dict[str, Any]]}
        """
        if not self._initialized:
            self.load_index()

        if not HAS_PYMUPDF:
            logger.error("[ImageRAG] PyMuPDF 未安装，无法提取页面图片")
            return {"text": "错误: PyMuPDF 未安装，无法提取 NCCN 指南页面图片", "images": []}

        results = self.search(question, top_k)

        if not results:
            return {"text": "未找到相关 NCCN 指南页面", "images": []}

        # 分数阈值过滤：只保留 >= 最高分 × threshold 的结果
        max_score = results[0]["score"]  # byaldi 结果已按分数降序
        threshold = max_score * self.score_threshold
        filtered = [r for r in results if r["score"] >= threshold]
        logger.info(
            f"[ImageRAG] retrieve 分数过滤: 最高分={max_score:.2f}, "
            f"阈值={threshold:.2f} ({self.score_threshold:.0%}), "
            f"保留 {len(filtered)}/{len(results)} 页"
        )

        # 按 doc_id 分组页码
        pages_by_doc: Dict[int, List[int]] = {}
        for r in filtered:
            doc_id = r.get("doc_id", 0)
            page_num = r.get("page_num", 0)
            pages_by_doc.setdefault(doc_id, []).append(page_num)

        # 从各 PDF 提取图片
        all_images = []
        for doc_id, page_nums in pages_by_doc.items():
            pdf_path = self._get_pdf_path(doc_id)
            if not pdf_path:
                logger.warning(f"[ImageRAG] 无法解析 doc_id={doc_id} 对应的 PDF 路径")
                continue
            all_images.extend(self._extract_page_images(pdf_path, page_nums))

        # 按检索分数排序对齐
        page_to_image = {img["page_num"]: img for img in all_images}
        ordered_images = []
        for r in filtered:
            page_num = r.get("page_num", 0)
            if page_num in page_to_image:
                ordered_images.append(page_to_image[page_num])

        # 构建文本摘要
        page_info = ", ".join([
            f"第{r['page_num']}页(相关度:{r['score']:.4f})"
            for r in filtered if r.get("page_num", 0) in page_to_image
        ])
        text = f"NCCN 指南检索结果: 找到 {len(ordered_images)} 个相关页面 — {page_info}"

        logger.info(f"[ImageRAG] retrieve 完成: {len(ordered_images)} 页图片")
        return {"text": text, "images": ordered_images}

    # ==================== 多模态读图管线 ====================

    def _multimodal_read(
        self,
        question: str,
        search_results: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        多模态读图：提取页面图片 + 调用多模态 LLM

        Args:
            question: 用户问题
            search_results: byaldi 检索结果 [{doc_id, page_num, score, ...}]

        Returns:
            LLM 分析文本，失败时返回 None
        """
        # 按 doc_id 分组页码
        pages_by_doc: Dict[int, List[int]] = {}
        for r in search_results:
            doc_id = r.get("doc_id", 0)
            page_num = r.get("page_num", 0)
            if doc_id not in pages_by_doc:
                pages_by_doc[doc_id] = []
            pages_by_doc[doc_id].append(page_num)

        # 从各 PDF 提取图片
        all_images = []
        for doc_id, page_nums in pages_by_doc.items():
            pdf_path = self._get_pdf_path(doc_id)
            if not pdf_path:
                logger.warning(f"[ImageRAG] 无法解析 doc_id={doc_id} 对应的 PDF 路径")
                continue

            images = self._extract_page_images(pdf_path, page_nums)
            all_images.extend(images)

        if not all_images:
            logger.warning("[ImageRAG] 未提取到页面图片，fallback 到仅页码模式")
            return None

        # 按检索排序对齐图片
        page_to_image = {img["page_num"]: img for img in all_images}
        ordered_images = []
        ordered_results = []
        for r in search_results:
            page_num = r.get("page_num", 0)
            if page_num in page_to_image:
                ordered_images.append(page_to_image[page_num])
                ordered_results.append(r)

        # 调用多模态 LLM
        return self._call_multimodal_llm(question, ordered_images, ordered_results)

    def _load_doc_id_mapping(self, index_name: str = None) -> Dict[int, Path]:
        """
        从 byaldi 索引加载 doc_id -> PDF 路径映射

        读取索引目录下的 doc_ids_to_file_names.json.gz。
        若失败则 fallback 到扫描 NCCN_PDF_DIR。

        Returns:
            {doc_id(int): Path} 映射
        """
        index_name = index_name or self.DEFAULT_INDEX_NAME
        mapping_file = self.index_root / index_name / "doc_ids_to_file_names.json.gz"

        mapping = {}

        if mapping_file.exists():
            try:
                with gzip.open(str(mapping_file), "rb") as f:
                    raw = f.read()
                    data = json.loads(raw.decode("utf-8"))
                    for str_id, path_str in data.items():
                        pdf_path = Path(path_str)
                        if pdf_path.exists():
                            mapping[int(str_id)] = pdf_path
                        else:
                            logger.warning(
                                f"[ImageRAG] doc_id={str_id} 对应 PDF 不存在: {path_str}"
                            )
            except Exception as e:
                logger.warning(f"[ImageRAG] 加载 doc_id 映射失败: {e}")

        # Fallback: 扫描 NCCN_PDF_DIR
        if not mapping and self.nccn_pdf_dir.exists():
            logger.info(f"[ImageRAG] 使用 fallback: 扫描 {self.nccn_pdf_dir} 中的 PDF")
            pdfs = sorted(self.nccn_pdf_dir.glob("*.pdf"))
            for i, pdf in enumerate(pdfs):
                mapping[i] = pdf
                logger.debug(f"[ImageRAG] Fallback 映射: doc_id={i} -> {pdf.name}")

        return mapping

    def _get_pdf_path(self, doc_id: int) -> Optional[Path]:
        """
        解析 doc_id 对应的 PDF 文件路径

        Args:
            doc_id: byaldi 检索结果中的文档 ID

        Returns:
            PDF 路径，未找到时返回 None
        """
        if not self._doc_id_to_pdf:
            self._doc_id_to_pdf = self._load_doc_id_mapping()

        return self._doc_id_to_pdf.get(doc_id)

    def _extract_page_images(
        self,
        pdf_path: Path,
        page_nums: List[int]
    ) -> List[Dict[str, Any]]:
        """
        用 PyMuPDF 从 PDF 提取指定页面为 base64 PNG

        Args:
            pdf_path: PDF 文件路径
            page_nums: 页码列表 (1-indexed，与 byaldi 一致)

        Returns:
            [{"page_num": int, "base64": str}]
        """
        images = []
        try:
            doc = fitz.open(str(pdf_path))
            total_pages = len(doc)
            mat = fitz.Matrix(self.render_scale, self.render_scale)

            for page_num in page_nums:
                # byaldi page_num 1-indexed → PyMuPDF 0-indexed
                page_index = page_num - 1
                if page_index < 0 or page_index >= total_pages:
                    logger.warning(
                        f"[ImageRAG] 页码 {page_num} 超出范围 "
                        f"(总页数: {total_pages})，跳过"
                    )
                    continue

                page = doc[page_index]
                pix = page.get_pixmap(matrix=mat)
                png_bytes = pix.tobytes("png")
                b64_str = base64.b64encode(png_bytes).decode("utf-8")

                images.append({
                    "page_num": page_num,
                    "base64": b64_str
                })

                logger.debug(
                    f"[ImageRAG] 提取页面 {page_num}: "
                    f"{pix.width}x{pix.height}, {len(png_bytes)/1024:.0f} KB"
                )

            doc.close()

        except Exception as e:
            logger.error(f"[ImageRAG] 页面图片提取失败: {e}")

        return images

    def _build_reader_prompt(self) -> str:
        """构建多模态 LLM 的 system prompt"""
        return """You are a clinical guideline analysis expert. You are reading pages from NCCN (National Comprehensive Cancer Network) clinical practice guidelines.

Your task:
1. Carefully examine each provided guideline page image
2. Extract ALL relevant information that answers the user's question
3. Pay special attention to: treatment algorithms, decision trees, footnotes, category of evidence ratings, and specific drug regimens
4. Preserve exact drug names, dosages, and evidence categories from the guidelines
5. Note which page each piece of information comes from

Output format:
- Use clear markdown with headers
- Cite page numbers as [Page N] for each piece of extracted information
- Include treatment algorithms as structured lists when applicable
- Preserve NCCN category of evidence and consensus ratings (e.g., "Category 1", "Category 2A")
- If tables are present, reproduce their key content in markdown table format
- If the pages do not contain information relevant to the question, state that clearly

Language: Respond in the same language as the user's question."""

    def _call_multimodal_llm(
        self,
        question: str,
        images: List[Dict[str, Any]],
        search_results: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        调用多模态 LLM 分析页面图片

        Args:
            question: 用户问题
            images: _extract_page_images() 返回的图片列表
            search_results: 对应的 byaldi 检索结果

        Returns:
            LLM 分析文本，失败时返回 None
        """
        if not self.api_key:
            logger.error("[ImageRAG] OPENROUTER_API_KEY 未设置，无法调用多模态 LLM")
            return None

        if not images:
            logger.warning("[ImageRAG] 无图片可发送给多模态 LLM")
            return None

        # 构建用户消息的 content 数组（text + images）
        page_info = ", ".join([
            f"Page {img['page_num']} (score: {sr.get('score', 0):.4f})"
            for img, sr in zip(images, search_results)
        ])

        content_parts = [
            {
                "type": "text",
                "text": (
                    f"Question: {question}\n\n"
                    f"Below are {len(images)} pages retrieved from NCCN guidelines "
                    f"as most relevant. Pages: {page_info}\n\n"
                    f"Please analyze these pages and provide a comprehensive answer."
                )
            }
        ]

        for img_data in images:
            content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_data['base64']}"
                }
            })

        # 构建 API 请求
        messages = [
            {"role": "system", "content": self._build_reader_prompt()},
            {"role": "user", "content": content_parts}
        ]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.reader_model,
            "messages": messages,
            "temperature": self.reader_temperature,
            "max_tokens": 8192,
        }

        logger.info(
            f"[ImageRAG] 调用多模态 LLM: {self.reader_model}, "
            f"{len(images)} 页图片"
        )

        # 重试逻辑
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url=self.api_url,
                    headers=headers,
                    data=json.dumps(payload, ensure_ascii=False),
                    timeout=self.reader_timeout
                )

                if response.status_code != 200:
                    raise Exception(f"HTTP {response.status_code}: {response.text[:300]}")

                result = response.json()

                if "choices" not in result or len(result["choices"]) == 0:
                    raise Exception(f"API 响应格式异常: {result}")

                content = result["choices"][0].get("message", {}).get("content", "")

                # 记录 token 用量
                usage = result.get("usage", {})
                if usage:
                    logger.info(
                        f"[ImageRAG] 多模态 LLM token 用量 - "
                        f"prompt: {usage.get('prompt_tokens', '?')}, "
                        f"completion: {usage.get('completion_tokens', '?')}"
                    )

                logger.info(f"[ImageRAG] 多模态 LLM 响应: {len(content)} 字符")
                return content

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"[ImageRAG] LLM 请求失败 ({type(e).__name__})，重试 ({attempt + 1}/{max_retries - 1})...")
                else:
                    logger.error(f"[ImageRAG] LLM 请求失败，重试已用尽: {e}")
                    return None
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"[ImageRAG] LLM 调用失败，重试 ({attempt + 1}/{max_retries - 1}): {e}")
                else:
                    logger.error(f"[ImageRAG] LLM 调用失败，重试已用尽: {e}")
                    return None

    # ==================== 结果格式化 ====================

    def _format_multimodal_results(
        self,
        question: str,
        search_results: List[Dict],
        llm_analysis: str
    ) -> str:
        """格式化多模态读图结果"""
        output_parts = [
            "**NCCN 指南多模态分析结果**\n",
            f"**查询**: {question}\n",
            f"**分析页数**: {len(search_results)} 页\n",
            "---\n\n",
            llm_analysis,
            "\n\n---\n",
            "**来源页面**:\n"
        ]

        for result in search_results:
            page_num = result.get("page_num", 0)
            score = result.get("score", 0)
            output_parts.append(f"- 第 {page_num} 页 (相关度: {score:.4f})\n")

        return "".join(output_parts)

    def _format_results(self, question: str, results: List[Dict]) -> str:
        """格式化查询结果（仅页码，fallback 模式）"""
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

    # 解析参数
    no_multimodal = "--no-multimodal" in sys.argv

    rag = NCCNImageRag(enable_multimodal_reading=not no_multimodal)

    # 检查命令行参数
    if "--build" in sys.argv:
        from config.settings import NCCN_PDF_DIR
        pdf_path = NCCN_PDF_DIR / "（2025.V1）NCCN临床实践指南：结肠癌.pdf"
        print(f"构建索引: {pdf_path}")
        rag.build_index(pdf_path)
    else:
        rag.load_index()

    mode = "多模态读图 (PyMuPDF + Gemini)" if not no_multimodal else "仅页码"
    print(f"模式: {mode}")
    print(f"读图模型: {rag.reader_model}")

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
