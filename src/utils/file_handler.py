"""
文件处理工具
"""
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF


def read_pdf_file(file_path: str) -> str:
    """
    读取 PDF 文件并提取文本

    Args:
        file_path: PDF 文件路径

    Returns:
        提取的文本内容

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 文件格式错误或无法提取文本
    """
    path = Path(file_path).resolve()

    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"仅支持 PDF 文件格式，当前: {path.suffix}")

    # 使用 PyMuPDF 提取文本
    doc = fitz.open(str(path))
    text_parts = []

    for page_num, page in enumerate(doc, 1):
        text = page.get_text()
        if text.strip():
            text_parts.append(f"=== 第 {page_num} 页 ===\n{text}")

    doc.close()

    if not text_parts:
        raise ValueError(f"PDF 文件为空或无法提取文本: {path}")

    return "\n\n".join(text_parts)


def read_case_file(file_path: str) -> str:
    """
    读取病例文件（仅支持 PDF 格式）

    Args:
        file_path: PDF 文件路径

    Returns:
        提取的文本内容

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 文件格式不是 PDF
    """
    path = Path(file_path).resolve()

    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")

    if not path.is_file():
        raise ValueError(f"路径不是文件: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(
            f"仅支持 PDF 文件格式。当前文件: {path.name} ({path.suffix})"
        )

    return read_pdf_file(str(path))


def write_file(file_path: str, content: str, encoding: str = "utf-8") -> str:
    """
    写入文件

    Args:
        file_path: 文件路径
        content: 文件内容
        encoding: 文件编码

    Returns:
        写入的文件路径
    """
    path = Path(file_path).resolve()

    # 确保父目录存在
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding=encoding) as f:
        f.write(content)

    return str(path)


def ensure_directory(dir_path: str) -> Path:
    """
    确保目录存在

    Args:
        dir_path: 目录路径

    Returns:
        目录 Path 对象
    """
    path = Path(dir_path).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_size(file_path: str) -> int:
    """
    获取文件大小

    Args:
        file_path: 文件路径

    Returns:
        文件大小（字节）
    """
    path = Path(file_path).resolve()
    return path.stat().st_size if path.exists() else 0


if __name__ == "__main__":
    print("文件处理模块加载成功")
