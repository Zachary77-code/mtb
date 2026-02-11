"""
PageIndex RAG — 基于语义树结构的 NCCN 指南检索

替换 byaldi + ColQwen2 的 Image RAG，使用 PageIndex 的
Tree Search + Expert Preference 实现结构化章节检索。

工具函数从 PageIndex/pageindex/utils.py 复制，无外部依赖。
"""
import json
import re
import copy
import time
import requests
from pathlib import Path
from typing import Dict, Any, Optional

import tiktoken
import PyPDF2

from config.settings import (
    OPENROUTER_API_KEY,
    NCCN_PAGEINDEX_DIR,
    NCCN_PAGEINDEX_TREE_SEARCH_MODEL,
    NCCN_PAGEINDEX_REASONING_EFFORT,
    AGENT_TIMEOUT,
)
from src.utils.logger import mtb_logger as logger


# ============================================================
# PDF / Tree 工具函数（从 PageIndex utils.py 复制）
# ============================================================

def get_page_tokens(pdf_path, model="gpt-4o-2024-11-20"):
    """PDF 页面文本提取 + token 计数"""
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("o200k_base")
    pdf_reader = PyPDF2.PdfReader(pdf_path)
    page_list = []
    for page in pdf_reader.pages:
        page_text = page.extract_text() or ""
        token_length = len(enc.encode(page_text))
        page_list.append((page_text, token_length))
    return page_list


def get_text_of_pdf_pages(pdf_pages, start_page, end_page):
    """按页码范围取文本（1-indexed）"""
    text = ""
    for page_num in range(start_page - 1, end_page):
        text += pdf_pages[page_num][0]
    return text


def add_node_text(node, pdf_pages):
    """递归给 tree 节点填充 PDF 文本"""
    if isinstance(node, dict):
        start_page = node.get("start_index")
        end_page = node.get("end_index")
        node["text"] = get_text_of_pdf_pages(pdf_pages, start_page, end_page)
        if "nodes" in node:
            add_node_text(node["nodes"], pdf_pages)
    elif isinstance(node, list):
        for item in node:
            add_node_text(item, pdf_pages)


def get_nodes(structure):
    """扁平化 tree 为节点列表（不含 children）"""
    if isinstance(structure, dict):
        node = copy.deepcopy(structure)
        node.pop("nodes", None)
        nodes = [node]
        if "nodes" in structure:
            nodes.extend(get_nodes(structure["nodes"]))
        return nodes
    elif isinstance(structure, list):
        nodes = []
        for item in structure:
            nodes.extend(get_nodes(item))
        return nodes
    return []


def remove_fields(data, fields=("text",)):
    """递归移除指定字段"""
    if isinstance(data, dict):
        return {k: remove_fields(v, fields) for k, v in data.items() if k not in fields}
    elif isinstance(data, list):
        return [remove_fields(item, fields) for item in data]
    return data


# ============================================================
# 流程图过滤
# ============================================================

def is_flowchart_node(node):
    """判断是否为流程图节点 (COL-1 ~ COL-15 等)"""
    title = node.get("title", "")
    return bool(re.search(r'\(COL-\d+\)', title))


def filter_tree(tree):
    """递归移除流程图节点"""
    filtered = []
    for node in tree:
        if is_flowchart_node(node):
            continue
        new_node = dict(node)
        if "nodes" in new_node:
            new_node["nodes"] = filter_tree(new_node["nodes"])
        filtered.append(new_node)
    return filtered


# ============================================================
# Expert Preference
# ============================================================

EXPERT_PREFERENCE = """
NCCN 指南检索规则:
- 免疫治疗/靶向治疗 → 优先查 Discussion 中的 dMMR/MSI-H 相关章节 + 系统治疗原则
- 手术相关 → 优先查手术原则 + Discussion 中的 Surgical Management
- 分子检测/基因突变 → 优先查病理和分子检测原则 + Discussion 中的 Biomarkers
- 辅助化疗 → 优先查 Discussion 中的 Adjuvant Chemotherapy + 辅助治疗原则
- 所有流程图节点已被排除，其内容完整包含在 Discussion 和 Principles 章节中
"""


# ============================================================
# PageIndexRAG 类
# ============================================================

class PageIndexRAG:
    """基于 PageIndex Tree Search 的 NCCN 指南 RAG"""

    def __init__(self):
        self._indices: Dict[str, Dict[str, Any]] = {}

    def _load_index(self, cancer_type: str):
        """延迟加载指定癌种的 tree structure + PDF"""
        if cancer_type in self._indices:
            return

        cancer_dir = NCCN_PAGEINDEX_DIR / cancer_type
        structure_path = cancer_dir / "structure.json"
        pdf_path = cancer_dir / "guideline.pdf"

        if not structure_path.exists():
            raise FileNotFoundError(f"未找到 {cancer_type} 的 tree structure: {structure_path}")
        if not pdf_path.exists():
            raise FileNotFoundError(f"未找到 {cancer_type} 的 PDF: {pdf_path}")

        logger.info(f"[PageIndexRAG] 加载 {cancer_type} 索引...")

        # 读取 tree structure
        with open(structure_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        tree = data["structure"]

        # 过滤流程图节点
        original_count = len(get_nodes({"nodes": tree}))
        tree = filter_tree(tree)
        filtered_count = len(get_nodes({"nodes": tree}))
        logger.info(f"[PageIndexRAG] {cancer_type}: 过滤流程图节点 {original_count} → {filtered_count}")

        # 从 PDF 提取文本填充到节点
        pdf_pages = get_page_tokens(str(pdf_path))
        for node in tree:
            add_node_text(node, pdf_pages)

        # 构建 node_id -> node 映射
        all_nodes = []
        for node in tree:
            all_nodes.extend(get_nodes(node))
        node_map = {n["node_id"]: n for n in all_nodes if "node_id" in n}

        # 准备无文本的 tree（用于 search prompt，节省 token）
        tree_no_text = [remove_fields(n, fields=("text",)) for n in tree]

        self._indices[cancer_type] = {
            "tree": tree,
            "tree_no_text": tree_no_text,
            "node_map": node_map,
        }
        logger.info(f"[PageIndexRAG] {cancer_type}: 索引加载完成，{len(node_map)} 个节点")

    def _tree_search(self, query: str, cancer_type: str) -> Dict[str, Any]:
        """LLM Tree Search + Expert Preference → 返回 {thinking, node_list}"""
        # ========== 全局速率限制检查 ==========
        from src.agents.base_agent import BaseAgent
        BaseAgent._check_rate_limit()

        index = self._indices[cancer_type]
        tree_no_text = index["tree_no_text"]

        prompt = f"""You are given a question and a tree structure of a clinical guideline document.
Each node contains a node_id, title, and a corresponding summary.
Your task is to find all nodes that are likely to contain the answer to the question.

Question: {query}

Document tree structure:
{json.dumps(tree_no_text, indent=2, ensure_ascii=False)}

Expert Knowledge of relevant sections: {EXPERT_PREFERENCE}

Please reply in the following JSON format:
{{
    "thinking": "<Your reasoning about which nodes are relevant>",
    "node_list": ["node_id_1", "node_id_2"]
}}
Directly return the final JSON structure. Do not output anything else."""

        # 调用 OpenRouter API（与 base_agent.py 同一模式）
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": NCCN_PAGEINDEX_TREE_SEARCH_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        if NCCN_PAGEINDEX_REASONING_EFFORT:
            payload["reasoning"] = {"effort": NCCN_PAGEINDEX_REASONING_EFFORT}

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    data=json.dumps(payload, ensure_ascii=False),
                    timeout=AGENT_TIMEOUT,
                )
                if response.status_code != 200:
                    raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")

                result = response.json()
                if "error" in result:
                    raise Exception(f"API error: {result['error']}")

                content = result["choices"][0]["message"]["content"]

                # 解析 JSON（处理可能的 markdown 包裹）
                text = content.strip()
                if text.startswith("```"):
                    text = re.sub(r'^```(?:json)?\s*', '', text)
                    text = re.sub(r'\s*```$', '', text)

                parsed = json.loads(text)
                node_ids = parsed.get("node_list", [])
                thinking = parsed.get("thinking", "")
                logger.info(f"[PageIndexRAG] Tree search: {len(node_ids)} 节点, reasoning: {thinking[:100]}...")
                return {"thinking": thinking, "node_list": node_ids}

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"[PageIndexRAG] Tree search 重试 ({attempt + 1}/{max_retries - 1}): {e}")
                    time.sleep(2)
                else:
                    logger.error(f"[PageIndexRAG] Tree search 失败: {e}")
                    return {"thinking": "", "node_list": []}

    def retrieve(self, query: str, cancer_type: str = "结肠癌") -> str:
        """
        完整 RAG 检索流程

        Args:
            query: 自然语言查询
            cancer_type: 癌种名（对应 data/pageindex/ 下的目录名）

        Returns:
            格式化的检索结果文本
        """
        if not query.strip():
            return "未提供查询内容"

        try:
            self._load_index(cancer_type)
        except FileNotFoundError as e:
            logger.error(f"[PageIndexRAG] {e}")
            return f"NCCN PageIndex 索引未找到: {e}"

        # Tree Search
        search_result = self._tree_search(query, cancer_type)
        thinking = search_result["thinking"]
        node_ids = search_result["node_list"]
        if not node_ids:
            return f"未检索到与 '{query}' 相关的 NCCN 指南章节"

        # 提取节点文本
        node_map = self._indices[cancer_type]["node_map"]

        # 构建输出：检索推理 + 节点列表 + 章节内容
        output_parts = [f"**NCCN {cancer_type}指南检索结果**\n"]

        # 检索推理
        output_parts.append(f"**检索推理**: {thinking}\n")

        # 节点列表
        valid_ids = [nid for nid in node_ids if nid in node_map]
        output_parts.append(f"**检索到 {len(valid_ids)} 个相关章节**:")
        for nid in valid_ids:
            node = node_map[nid]
            title = node.get("title", "未知章节")
            pages = f"p.{node.get('start_index', '?')}-{node.get('end_index', '?')}"
            output_parts.append(f"  - [{nid}] {title} ({pages})")
        output_parts.append("")

        # 章节内容
        sections = []
        for nid in valid_ids:
            node = node_map[nid]
            title = node.get("title", "未知章节")
            pages = f"p.{node.get('start_index', '?')}-{node.get('end_index', '?')}"
            text = node.get("text", "")
            sections.append(f"### {title} ({pages})\n\n{text}")

        if not sections:
            return f"检索到 {len(node_ids)} 个节点 ID 但无法提取文本"

        output_parts.append("\n---\n\n".join(sections))
        return "\n".join(output_parts)


# ============================================================
# 单例工厂
# ============================================================

_instance: Optional[PageIndexRAG] = None


def get_pageindex_rag() -> PageIndexRAG:
    """获取 PageIndexRAG 单例"""
    global _instance
    if _instance is None:
        _instance = PageIndexRAG()
    return _instance
