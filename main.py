"""
MTB 多智能体工作流系统 - 主入口

使用方法:
    python main.py <病例PDF文件路径>

示例:
    python main.py tests/fixtures/sample_case.pdf
"""
import sys
import time
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from config.settings import validate_config, REPORTS_DIR
from src.utils.logger import mtb_logger as logger
from src.utils.file_handler import read_case_file
from src.graph.state_graph import run_mtb_workflow


def main(case_file_path: str):
    """
    主函数

    Args:
        case_file_path: 病例文件路径
    """
    logger.info("=" * 60)
    logger.info("MTB 多智能体工作流系统启动")
    logger.info("=" * 60)

    # 验证配置
    try:
        validate_config()
        logger.info("配置验证通过")
    except Exception as e:
        logger.error(f"配置验证失败: {e}")
        print(f"\n[ERROR] 配置错误: {e}")
        sys.exit(1)

    # 读取病例文件
    try:
        logger.info(f"读取病例文件: {case_file_path}")
        input_text = read_case_file(case_file_path)
        logger.info(f"病例文本长度: {len(input_text)} 字符")
    except FileNotFoundError:
        logger.error(f"文件不存在: {case_file_path}")
        print(f"\n[ERROR] 文件不存在: {case_file_path}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"读取文件失败: {e}")
        print(f"\n[ERROR] 读取文件失败: {e}")
        sys.exit(1)

    # 执行工作流
    print("\n" + "=" * 60)
    print("开始处理病例...")
    print("=" * 60)

    start_time = time.time()

    try:
        # 运行工作流
        logger.info("开始执行工作流")
        print("\n[1/5] 解析病例文本...")

        final_state = run_mtb_workflow(input_text)

        # 检查结果
        if "output_path" in final_state and final_state["output_path"]:
            elapsed = time.time() - start_time
            output_path = final_state["output_path"]

            logger.info(f"报告生成成功: {output_path}")
            logger.info(f"执行时间: {elapsed:.2f}秒")

            print("\n" + "=" * 60)
            print("[OK] MTB 报告生成成功!")
            print("=" * 60)
            print(f"\n报告路径: {output_path}")
            print(f"执行时间: {elapsed:.2f}秒")

            # 验证状态
            if final_state.get("is_compliant"):
                print("[PASS] 格式验证: 通过（包含全部 12 个必选模块）")
            else:
                missing = final_state.get("missing_sections", [])
                print(f"[WARN] 格式验证: 部分模块可能缺失 ({len(missing)} 个)")

            # 解析错误
            if final_state.get("parsing_errors"):
                print(f"[WARN] 解析警告: {final_state['parsing_errors']}")

            print("\n提示: 使用浏览器打开 HTML 文件查看完整报告")

        else:
            logger.error("报告生成失败")
            errors = final_state.get("workflow_errors", ["未知错误"])
            print(f"\n[ERROR] 报告生成失败")
            for err in errors:
                print(f"   - {err}")

    except Exception as e:
        logger.exception(f"工作流执行失败: {e}")
        print(f"\n[ERROR] 执行失败: {e}")
        sys.exit(1)


def print_usage():
    """打印使用说明"""
    print("""
MTB 多智能体工作流系统
======================

使用方法:
    python main.py <病例PDF文件路径>

示例:
    python main.py tests/fixtures/sample_case.pdf

输入格式:
    仅支持 PDF 格式的病例报告

输出:
    生成的 HTML 报告保存在 reports/ 目录

环境变量 (.env 文件):
    OPENAI_API_KEY=<你的 OpenAI API Key>
    OPENAI_MODEL=gpt-5.2

更多信息请参阅 README.md
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    case_path = sys.argv[1]

    if case_path in ["-h", "--help"]:
        print_usage()
        sys.exit(0)

    main(case_path)
