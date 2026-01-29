"""
全局配置管理
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量 (override=True 确保.env文件覆盖系统环境变量)
load_dotenv(override=True)

# 项目根目录
BASE_DIR = Path(__file__).parent.parent.resolve()

# ==================== API 配置 ====================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-3-pro-preview")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions")

# ==================== 路径配置 ====================
REPORTS_DIR = BASE_DIR / "reports"
PROMPTS_DIR = BASE_DIR / "config" / "prompts"
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"

# 确保关键目录存在
REPORTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# ==================== API 工具配置 ====================
# NCBI (PubMed + ClinVar) - API Key 提高限额至 10次/秒
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "cc2f31026e714a0133f5d535437a486b7907")
NCBI_EMAIL = os.getenv("NCBI_EMAIL", "mtb-workflow@example.com")

# OncoKB Token (如已申请)
ONCOKB_API_TOKEN = os.getenv("ONCOKB_API_TOKEN", "")

# ==================== RAG 配置 ====================
NCCN_PDF_DIR = BASE_DIR / os.getenv("NCCN_PDF_DIR", "NCCN_English")
# 索引存储在用户目录，避免被 git clean 删除
NCCN_VECTOR_DIR = Path(os.getenv("NCCN_VECTOR_DIR", str(Path.home() / ".mtb" / "nccn_vectors")))

# ==================== DashScope Embedding 配置 ====================
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1024"))

# 需要索引的癌症类型（文件名关键词，为空则索引所有）
NCCN_INDEX_CANCER_TYPES = [
    "结肠癌",
    "小肠腺癌",
    "非小细胞肺癌",
    "小细胞肺癌",
]

# ==================== Agent 配置 ====================
AGENT_TEMPERATURE = float(os.getenv("AGENT_TEMPERATURE", "0.2"))
AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "120"))
MAX_RETRY_ITERATIONS = int(os.getenv("MAX_RETRY_ITERATIONS", "2"))

# ==================== DeepEvidence 模型配置 ====================
# Subgraph 内 Agent 使用 flash 模型（Pathologist, Geneticist, Recruiter, Oncologist）
SUBGRAPH_MODEL = os.getenv("SUBGRAPH_MODEL", "google/gemini-3-flash-preview")
# 编排 Agent 使用 pro 模型（PlanAgent, ChairAgent）
ORCHESTRATOR_MODEL = os.getenv("ORCHESTRATOR_MODEL", "google/gemini-3-pro-preview")
# 收敛判断 Agent 使用 pro 模型（ConvergenceJudgeAgent）
CONVERGENCE_JUDGE_MODEL = os.getenv("CONVERGENCE_JUDGE_MODEL", "google/gemini-3-pro-preview")

# ==================== Reasoning 配置 ====================
# 启用 LLM 推理输出（reasoning tokens），用于工具调用报告
# effort: "minimal" / "low" / "medium" / "high" / ""(禁用)
# Pro 模型（PlanAgent, Chair）使用 high，Flash 模型（Research Agents）使用 medium
ORCHESTRATOR_REASONING_EFFORT = os.getenv("ORCHESTRATOR_REASONING_EFFORT", "high")
SUBGRAPH_REASONING_EFFORT = os.getenv("SUBGRAPH_REASONING_EFFORT", "medium")

# ==================== DeepEvidence 收敛配置 ====================
MAX_PHASE1_ITERATIONS = int(os.getenv("MAX_PHASE1_ITERATIONS", "7"))  # 并行分析阶段最大迭代
MAX_PHASE2_ITERATIONS = int(os.getenv("MAX_PHASE2_ITERATIONS", "7"))  # Oncologist 阶段最大迭代
MIN_EVIDENCE_NODES = int(os.getenv("MIN_EVIDENCE_NODES", "10"))       # 最小证据节点数（全局）
MIN_EVIDENCE_PER_DIRECTION = int(os.getenv("MIN_EVIDENCE_PER_DIRECTION", "20"))  # 每个研究方向最小证据数

# ==================== PubMed 搜索配置 ====================
DEFAULT_YEAR_WINDOW = int(os.getenv("DEFAULT_YEAR_WINDOW", "10"))  # 默认搜索最近 N 年
PUBMED_BROAD_SEARCH_COUNT = int(os.getenv("PUBMED_BROAD_SEARCH_COUNT", "200"))  # 宽搜数量
PUBMED_BUCKET_QUOTAS = {
    "guideline": 3,
    "rct": 6,
    "systematic_review": 4,
    "observational": 4,
    "case_report": 2,
    "preclinical": 1,
}

# ==================== 12 个必选模块 ====================
REQUIRED_SECTIONS = [
    "执行摘要",
    "患者概况",
    "分子特征",
    "治疗史回顾",
    "药物/方案对比",
    "器官功能与剂量",
    "治疗路线图",
    "分子复查建议",
    "临床试验推荐",
    "局部治疗建议",
    "核心建议汇总",
    "参考文献"
]

# ==================== 需要证据覆盖的模块（收敛检查用）====================
# 排除：执行摘要（Chair 综合）、患者概况（PDF 提取）、参考文献（汇总）
COVERAGE_REQUIRED_MODULES = [
    "分子特征",
    "治疗史回顾",
    "药物/方案对比",
    "器官功能与剂量",
    "治疗路线图",
    "分子复查建议",
    "临床试验推荐",
    "局部治疗建议",
    "核心建议汇总",
]

# ==================== 全局输出原则文件名 ====================
GLOBAL_PRINCIPLES_FILE = "global_principles.txt"

# Agent 提示词文件名
PATHOLOGIST_PROMPT_FILE = "pathologist_prompt.txt"
GENETICIST_PROMPT_FILE = "geneticist_prompt.txt"
RECRUITER_PROMPT_FILE = "recruiter_prompt.txt"
ONCOLOGIST_PROMPT_FILE = "oncologist_prompt.txt"
CHAIR_PROMPT_FILE = "chair_prompt.txt"
PLAN_AGENT_PROMPT_FILE = "plan_agent_prompt.txt"  # PlanAgent 提示词


# ==================== 多模态图片 RAG 配置 ====================
NCCN_IMAGE_VECTOR_DIR = Path(os.getenv(
    "NCCN_IMAGE_VECTOR_DIR",
    r"C:\Users\Windows11\Desktop\image_vector_store"
))
COLPALI_MODEL = os.getenv("COLPALI_MODEL", "vidore/colqwen2-v1.0")

# 多模态 LLM 读图配置（Image RAG 第二阶段：提取页面图片后由多模态 LLM 分析）
NCCN_IMAGE_READER_MODEL = os.getenv("NCCN_IMAGE_READER_MODEL", ORCHESTRATOR_MODEL)
NCCN_IMAGE_READER_TEMPERATURE = float(os.getenv("NCCN_IMAGE_READER_TEMPERATURE", "0.1"))
NCCN_IMAGE_READER_TIMEOUT = int(os.getenv("NCCN_IMAGE_READER_TIMEOUT", "120"))
NCCN_IMAGE_RENDER_SCALE = float(os.getenv("NCCN_IMAGE_RENDER_SCALE", "2.0"))
NCCN_IMAGE_SCORE_THRESHOLD = float(os.getenv("NCCN_IMAGE_SCORE_THRESHOLD", "0.8"))


def validate_config() -> bool:
    """验证配置有效性"""
    if not OPENROUTER_API_KEY:
        raise ValueError(
            "未设置 OPENROUTER_API_KEY 环境变量。"
            "请在 .env 文件中设置：OPENROUTER_API_KEY=your-api-key"
        )

    # 检查提示词目录是否存在
    if not PROMPTS_DIR.exists():
        raise FileNotFoundError(
            f"提示词目录不存在：{PROMPTS_DIR}。"
            "请运行 mkdir config\\prompts 创建目录。"
        )

    return True


def load_prompt(filename: str) -> str:
    """
    加载提示词文件

    Args:
        filename: 提示词文件名（如 'global_principles.txt'）

    Returns:
        提示词内容
    """
    prompt_path = PROMPTS_DIR / filename

    if not prompt_path.exists():
        raise FileNotFoundError(
            f"提示词文件不存在：{prompt_path}。"
            f"请确保 {filename} 已创建。"
        )

    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


# ==================== 调试信息 ====================
if __name__ == "__main__":
    print("=== MTB 配置信息 ===")
    print(f"项目根目录: {BASE_DIR}")
    print(f"报告目录: {REPORTS_DIR}")
    print(f"提示词目录: {PROMPTS_DIR}")
    print(f"日志目录: {LOGS_DIR}")
    print(f"\nOpenRouter 模型: {OPENROUTER_MODEL}")
    print(f"OpenRouter API URL: {OPENROUTER_BASE_URL}")
    print(f"API Key 已设置: {'是' if OPENROUTER_API_KEY else '否'}")
    print(f"\nAgent 温度: {AGENT_TEMPERATURE}")
    print(f"Agent 超时: {AGENT_TIMEOUT}秒")
    print(f"最大重试次数: {MAX_RETRY_ITERATIONS}")
    print(f"\n必选模块数量: {len(REQUIRED_SECTIONS)}")

    try:
        validate_config()
        print("\n✓ 配置验证通过")
    except Exception as e:
        print(f"\n✗ 配置验证失败: {e}")
