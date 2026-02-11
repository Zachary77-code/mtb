"""
测试OpenRouter速率限制器

验证：
1. 速率限制器正常工作（10秒内最多20次请求）
2. 超过限制时会等待
3. 多线程环境下线程安全
"""
import threading
import time
from src.agents.base_agent import BaseAgent

def test_rate_limit_basic():
    """测试基本速率限制功能"""
    print("=" * 60)
    print("测试1: 基本速率限制（快速发送25个请求）")
    print("=" * 60)

    start_time = time.time()

    for i in range(25):
        req_start = time.time()
        BaseAgent._check_rate_limit()
        elapsed = time.time() - req_start

        print(f"[{time.time() - start_time:.2f}s] 请求 {i+1}/25 通过速率检查（等待 {elapsed:.2f}s）")

    total_time = time.time() - start_time
    print(f"\n总耗时: {total_time:.2f}s")
    print(f"预期: 前20个立即通过，后5个需等待约10秒")
    print()

def test_rate_limit_concurrent():
    """测试并发请求"""
    print("=" * 60)
    print("测试2: 并发请求（10个线程各发5个请求）")
    print("=" * 60)

    results = []
    lock = threading.Lock()

    def make_requests(thread_id, count):
        for i in range(count):
            req_start = time.time()
            BaseAgent._check_rate_limit()
            elapsed = time.time() - req_start

            with lock:
                results.append({
                    'thread': thread_id,
                    'request': i + 1,
                    'wait_time': elapsed,
                    'timestamp': time.time()
                })

    start_time = time.time()
    threads = []

    # 创建10个线程，每个发送5个请求（总共50个请求）
    for tid in range(10):
        t = threading.Thread(target=make_requests, args=(tid, 5))
        threads.append(t)
        t.start()

    # 等待所有线程完成
    for t in threads:
        t.join()

    total_time = time.time() - start_time

    # 统计结果
    immediate = sum(1 for r in results if r['wait_time'] < 0.1)
    delayed = sum(1 for r in results if r['wait_time'] >= 0.1)

    print(f"\n总耗时: {total_time:.2f}s")
    print(f"立即通过的请求: {immediate}/50")
    print(f"需要等待的请求: {delayed}/50")
    print(f"预期: 大约{50//20 * 10}秒完成（{50}个请求 / 20个每10秒）")
    print()

def test_rate_limit_reset():
    """测试时间窗口重置"""
    print("=" * 60)
    print("测试3: 时间窗口重置（发送20个请求，等待11秒，再发20个）")
    print("=" * 60)

    # 第一批：20个请求
    print("发送第一批20个请求...")
    for i in range(20):
        BaseAgent._check_rate_limit()
    print("✓ 第一批完成")

    # 等待11秒（超过10秒窗口）
    print("\n等待11秒让窗口重置...")
    for i in range(11, 0, -1):
        print(f"  倒计时: {i}秒...", end='\r')
        time.sleep(1)
    print("\n✓ 等待完成")

    # 第二批：20个请求（应该立即通过）
    print("\n发送第二批20个请求...")
    start_time = time.time()
    for i in range(20):
        BaseAgent._check_rate_limit()
    elapsed = time.time() - start_time

    print(f"✓ 第二批完成，耗时 {elapsed:.2f}s")
    print(f"预期: 第二批应该立即通过（<1秒），因为窗口已重置")
    print()

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("OpenRouter 速率限制器测试")
    print("=" * 60)
    print(f"配置: 10秒窗口，最多20个请求")
    print("=" * 60)
    print()

    # 清空时间戳（确保测试环境干净）
    BaseAgent._request_timestamps.clear()

    # 运行测试
    test_rate_limit_basic()

    # 清空时间戳
    BaseAgent._request_timestamps.clear()
    time.sleep(1)

    test_rate_limit_concurrent()

    # 清空时间戳
    BaseAgent._request_timestamps.clear()
    time.sleep(1)

    test_rate_limit_reset()

    print("=" * 60)
    print("✓ 所有测试完成")
    print("=" * 60)
