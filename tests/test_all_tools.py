"""
MTB 工具测试脚本

测试所有 API 工具的连接和基本功能
"""
import sys
import time
from pathlib import Path

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent))


def print_header(title: str):
    """打印测试标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(success: bool, message: str = ""):
    """打印测试结果"""
    status = "[PASS]" if success else "[FAIL]"
    print(f"\nResult: {status}")
    if message:
        print(f"Note: {message}")


def test_pubmed():
    """测试 PubMed 文献搜索"""
    print_header("1. PubMed 文献搜索测试")

    from src.tools.literature_tools import PubMedTool

    tool = PubMedTool()
    print("查询: EGFR L858R osimertinib")

    start = time.time()
    result = tool.invoke(query="EGFR L858R osimertinib", max_results=3)
    elapsed = time.time() - start

    print(f"耗时: {elapsed:.2f}s")
    print("-" * 40)
    print(result[:1000] if result else "无结果")

    success = result is not None and ("PubMed" in result or "PMID" in result)
    print_result(success)
    return success


def test_clinical_trials():
    """测试 ClinicalTrials.gov 搜索"""
    print_header("2. ClinicalTrials.gov 临床试验搜索测试")

    from src.tools.trial_tools import ClinicalTrialsTool

    tool = ClinicalTrialsTool()
    print("查询: NSCLC + EGFR mutation + osimertinib (中国)")

    start = time.time()
    result = tool.invoke(
        cancer_type="NSCLC",
        biomarker="EGFR mutation",
        intervention="osimertinib",
        max_results=3
    )
    elapsed = time.time() - start

    print(f"耗时: {elapsed:.2f}s")
    print("-" * 40)
    print(result[:1500] if result else "无结果")

    success = result is not None and "ClinicalTrials" in result
    print_result(success)
    return success


def test_civic():
    """测试 CIViC 变异证据查询"""
    print_header("3. CIViC 变异证据查询测试")

    from src.tools.molecular_tools import CIViCTool

    tool = CIViCTool()
    print("查询: EGFR L858R NSCLC")

    start = time.time()
    result = tool.invoke(gene="EGFR", variant="L858R", cancer_type="NSCLC")
    elapsed = time.time() - start

    print(f"耗时: {elapsed:.2f}s")
    print("-" * 40)
    print(result[:1200] if result else "无结果")

    success = result is not None and "CIViC" in result
    print_result(success)
    return success


def test_clinvar():
    """测试 ClinVar 致病性分类查询"""
    print_header("4. ClinVar 致病性分类测试")

    from src.tools.molecular_tools import ClinVarTool

    tool = ClinVarTool()
    print("查询: BRCA1 基因变异")

    start = time.time()
    result = tool.invoke(gene="BRCA1", variant="")
    elapsed = time.time() - start

    print(f"耗时: {elapsed:.2f}s")
    print("-" * 40)
    print(result[:1200] if result else "无结果")

    success = result is not None and "ClinVar" in result
    print_result(success)
    return success


def test_cbioportal():
    """测试 cBioPortal 突变频率查询"""
    print_header("5. cBioPortal 突变频率测试")

    from src.tools.molecular_tools import cBioPortalTool

    tool = cBioPortalTool()
    print("查询: EGFR 基因突变频率")

    start = time.time()
    result = tool.invoke(gene="EGFR", variant="L858R")
    elapsed = time.time() - start

    print(f"耗时: {elapsed:.2f}s")
    print("-" * 40)
    print(result[:1200] if result else "无结果")

    success = result is not None and "cBioPortal" in result
    print_result(success)
    return success


def test_fda_label():
    """测试 FDA 药品说明书查询"""
    print_header("6. FDA 药品说明书测试")

    from src.tools.guideline_tools import FDALabelTool

    tool = FDALabelTool()
    print("查询: osimertinib (奥希替尼)")

    start = time.time()
    result = tool.invoke(drug_name="osimertinib")
    elapsed = time.time() - start

    print(f"耗时: {elapsed:.2f}s")
    print("-" * 40)
    print(result[:1500] if result else "无结果")

    success = result is not None and "FDA" in result
    print_result(success)
    return success


def test_rxnorm():
    """测试 RxNorm 药物相互作用查询"""
    print_header("7. RxNorm 药物相互作用测试")

    from src.tools.guideline_tools import RxNormTool

    tool = RxNormTool()
    print("查询: osimertinib 药物信息")

    start = time.time()
    result = tool.invoke(drug_name="osimertinib")
    elapsed = time.time() - start

    print(f"耗时: {elapsed:.2f}s")
    print("-" * 40)
    print(result[:1200] if result else "无结果")

    success = result is not None and "RxNorm" in result
    print_result(success)
    return success


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("       MTB 工具测试套件")
    print("       Testing All API Tools")
    print("=" * 60)

    tests = [
        ("PubMed", test_pubmed),
        ("ClinicalTrials", test_clinical_trials),
        ("CIViC", test_civic),
        ("ClinVar", test_clinvar),
        ("cBioPortal", test_cbioportal),
        ("FDA Label", test_fda_label),
        ("RxNorm", test_rxnorm),
    ]

    results = {}

    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n错误: {e}")
            results[name] = False

    # 汇总
    print("\n" + "=" * 60)
    print("       测试汇总")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, success in results.items():
        status = "[OK]" if success else "[X]"
        print(f"  {status} {name}")

    print("-" * 40)
    print(f"  通过: {passed}/{total}")

    if passed == total:
        print("\n  所有测试通过!")
    else:
        print(f"\n  {total - passed} 个测试失败")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
