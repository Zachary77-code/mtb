"""
NCCN 多模态图片索引构建脚本

将 NCCN 指南 PDF 每页转为图片，使用 ColQwen2 生成多向量嵌入，
通过 byaldi 索引引擎持久化存储。

用法:
    python -m src.tools.rag.build_image_index
    python -m src.tools.rag.build_image_index --pdf "path/to/custom.pdf"
    python -m src.tools.rag.build_image_index --rebuild
"""
import argparse
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="构建 NCCN 多模态图片索引")
    parser.add_argument(
        "--pdf",
        type=str,
        default=None,
        help="指定 PDF 文件路径 (默认: NCCN 结肠癌指南)"
    )
    parser.add_argument(
        "--index-name",
        type=str,
        default="nccn_colon",
        help="索引名称 (默认: nccn_colon)"
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="强制重建索引 (覆盖已有)"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda",
        help="推理设备 (默认: cuda)"
    )
    args = parser.parse_args()

    from config.settings import NCCN_PDF_DIR, NCCN_IMAGE_VECTOR_DIR, COLPALI_MODEL
    from src.tools.rag.nccn_image_rag import NCCNImageRag

    # 确定 PDF 路径
    if args.pdf:
        pdf_path = Path(args.pdf)
    else:
        pdf_path = NCCN_PDF_DIR / "（2025.V1）NCCN临床实践指南：结肠癌.pdf"

    if not pdf_path.exists():
        print(f"错误: PDF 文件不存在: {pdf_path}")
        return

    # 检查索引是否已存在
    index_path = NCCN_IMAGE_VECTOR_DIR / args.index_name
    if index_path.exists() and not args.rebuild:
        print(f"索引已存在: {index_path}")
        print("使用 --rebuild 参数强制重建")
        return

    print("=" * 60)
    print("NCCN 多模态图片索引构建")
    print("=" * 60)
    print(f"PDF 文件:   {pdf_path}")
    print(f"PDF 大小:   {pdf_path.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"模型:       {COLPALI_MODEL}")
    print(f"索引目录:   {NCCN_IMAGE_VECTOR_DIR}")
    print(f"索引名称:   {args.index_name}")
    print(f"设备:       {args.device}")
    print("=" * 60)

    # 构建索引
    rag = NCCNImageRag(
        index_root=str(NCCN_IMAGE_VECTOR_DIR),
        model_name=COLPALI_MODEL,
        device=args.device
    )

    start_time = time.time()

    try:
        rag.build_index(
            pdf_path=pdf_path,
            index_name=args.index_name,
            overwrite=args.rebuild
        )
    except Exception as e:
        print(f"\n错误: 索引构建失败 - {e}")
        raise

    elapsed = time.time() - start_time

    # 打印统计
    print("\n" + "=" * 60)
    print("索引构建完成!")
    print("=" * 60)
    print(f"耗时:       {elapsed:.1f} 秒")
    print(f"索引位置:   {NCCN_IMAGE_VECTOR_DIR / args.index_name}")

    # 显示索引目录大小
    index_dir = NCCN_IMAGE_VECTOR_DIR / args.index_name
    if index_dir.exists():
        total_size = sum(f.stat().st_size for f in index_dir.rglob("*") if f.is_file())
        print(f"索引大小:   {total_size / 1024 / 1024:.1f} MB")

    # 快速测试检索
    print("\n--- 快速检索测试 ---")
    test_queries = [
        "结肠癌一线治疗方案",
        "KRAS突变治疗选择",
        "MSI-H免疫治疗"
    ]

    for q in test_queries:
        results = rag.search(q, top_k=3)
        pages = [str(r["page_num"]) for r in results]
        scores = [f"{r['score']:.4f}" for r in results]
        print(f"  查询: {q}")
        print(f"    页码: {', '.join(pages)} | 分数: {', '.join(scores)}")


if __name__ == "__main__":
    main()
