"""测试Rate Limiter是否真的在工作"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# 设置DEBUG级别logger
from src.utils.logger import setup_logger
logger = setup_logger(log_level="DEBUG", log_file="rate_limiter_test.log")

from src.agents.base_agent import BaseAgent
import time

print("=" * 60)
print("测试Rate Limiter（DEBUG模式）")
print("=" * 60)

# 快速发送25个请求
for i in range(25):
    print(f"\n[{i+1}/25] 调用 _check_rate_limit()...")
    start = time.time()
    BaseAgent._check_rate_limit()
    elapsed = time.time() - start
    print(f"  耗时: {elapsed:.2f}s")

print("\n" + "=" * 60)
print("测试完成！检查日志: logs/rate_limiter_test.log")
print("=" * 60)
