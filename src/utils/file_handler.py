"""
文件处理工具
"""
from pathlib import Path
from typing import Optional


def read_case_file(file_path: str, encoding: str = "utf-8") -> str:
    """
    读取病例文件

    Args:
        file_path: 文件路径
        encoding: 文件编码（默认 UTF-8）

    Returns:
        文件内容

    Raises:
        FileNotFoundError: 文件不存在
        UnicodeDecodeError: 编码错误
    """
    path = Path(file_path).resolve()

    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")

    if not path.is_file():
        raise ValueError(f"路径不是文件: {path}")

    with open(path, "r", encoding=encoding) as f:
        return f.read()


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
