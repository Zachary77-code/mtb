"""
SmartPubMed 3-Layer LLM 递进检索 单元测试

测试目标：
1. _build_layer_query() 各层 LLM 查询构建
2. _fallback_query_cleanup() 正则清理（含中文去除）
3. _extract_best_single_concept() 最佳单概念选择
4. search() 3 层回退链逻辑（Mock）
5. 端到端真实 API 测试（生产报告中的失败查询）

运行方式：
    pytest tests/test_smart_pubmed.py -v
    pytest tests/test_smart_pubmed.py -v -k "not real_api"   # 跳过真实 API 测试
    pytest tests/test_smart_pubmed.py -v -k "real_api"       # 只跑真实 API 测试
"""
import sys
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.smart_pubmed import SmartPubMedSearch, get_smart_pubmed


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def smart_pubmed():
    """创建 SmartPubMedSearch 实例"""
    return SmartPubMedSearch()


# ============================================================
# 生产报告中的真实失败查询（基线测试用例）
# ============================================================

PRODUCTION_FAILED_QUERIES = [
    {
        "query": "KRAS G12C colorectal cancer resistance SHP2 SOS1 inhibitor China",
        "description": "报告中曾降级为仅搜 'KRAS'",
        "expected_min_results": 1,
    },
    {
        "query": "KRAS G12C inhibitor resistance mechanisms colorectal cancer ctDNA monitoring",
        "description": "报告中曾返回 0 结果",
        "expected_min_results": 1,
    },
    {
        "query": "Fulzerasib Cetuximab colorectal cancer KRAS G12C efficacy",
        "description": "新药名，LLM 可能编错别名",
        "expected_min_results": 0,  # Fulzerasib 太新，可能确实搜不到
    },
    {
        "query": "IBI351 Cetuximab colorectal cancer OR GFH925 Cetuximab CRC efficacy",
        "description": "药物开发代号查询",
        "expected_min_results": 0,
    },
]

# 应该能正常返回结果的查询
KNOWN_GOOD_QUERIES = [
    {
        "query": "EGFR L858R osimertinib resistance",
        "description": "经典查询，一定有结果",
        "expected_min_results": 5,
    },
    {
        "query": "KRAS G12C inhibitor colorectal cancer resistance",
        "description": "用户在 PubMed 网页验证有 8 篇结果",
        "expected_min_results": 3,
    },
    {
        "query": "ATM germline mutation colorectal cancer PARP inhibitor sensitivity",
        "description": "报告中搜到 1 篇",
        "expected_min_results": 1,
    },
]

# 用于测试 Boolean 查询在 PubMed API 上是否能工作
BOOLEAN_QUERIES = [
    {
        "query": '"KRAS G12C" AND inhibitor AND "colorectal cancer" AND resistance',
        "description": "简单 Boolean（用户在网页上验证返回 8 篇）",
        "expected_min_results": 3,
    },
    {
        "query": '"KRAS G12C" AND inhibitor AND "colorectal cancer" AND (SHP2 OR MET) AND resistance',
        "description": "带 OR 分组的 Boolean（用户在网页上验证返回 8 篇）",
        "expected_min_results": 3,
    },
    {
        "query": '("Colorectal Neoplasms"[MeSH] OR "colorectal cancer"[TIAB]) AND ("KRAS G12C"[TIAB]) AND ("resistance"[TIAB])',
        "description": "MeSH + TIAB 双保险格式",
        "expected_min_results": 1,
    },
]


# ============================================================
# 1. LLM 分层查询构建测试
# ============================================================

class TestBuildLayerQuery:
    """测试 _build_layer_query() 的 3 层 LLM 查询构建"""

    @pytest.mark.real_api
    def test_layer1_returns_nonempty(self, smart_pubmed):
        """Layer 1 应返回非空查询字符串"""
        result = smart_pubmed._build_layer_query(1, "KRAS G12C colorectal cancer", [])
        assert result and len(result) > 0, "Layer 1 查询不应为空"
        print(f"\n  Layer 1: {result}")

    @pytest.mark.real_api
    def test_layer1_uses_tiab(self, smart_pubmed):
        """Layer 1 应使用 [tiab] 而非 [MeSH]"""
        result = smart_pubmed._build_layer_query(
            1, "KRAS G12C colorectal cancer resistance", []
        )
        has_tiab = "[tiab]" in result.lower()
        has_mesh = "[mesh]" in result.lower()
        print(f"\n  Layer 1: {result}")
        print(f"  含 tiab: {has_tiab}, 含 MeSH: {has_mesh}")
        assert has_tiab, "Layer 1 应使用 [tiab]"
        # Layer 1 不应使用 MeSH（允许但不推荐）

    @pytest.mark.real_api
    def test_layer2_receives_failed_query(self, smart_pubmed):
        """Layer 2 应接收 Layer 1 的失败查询并生成更宽的查询"""
        failed_q1 = '("colorectal cancer"[tiab]) AND ("KRAS G12C"[tiab]) AND ("SHP2"[tiab]) AND ("resistance"[tiab])'
        result = smart_pubmed._build_layer_query(
            2, "KRAS G12C colorectal cancer resistance SHP2", [failed_q1]
        )
        print(f"\n  Layer 1 (failed): {failed_q1[:60]}...")
        print(f"  Layer 2: {result}")
        assert result and len(result) > 0, "Layer 2 查询不应为空"
        assert result != failed_q1, "Layer 2 查询应与 Layer 1 不同"

    @pytest.mark.real_api
    def test_layer3_minimal_query(self, smart_pubmed):
        """Layer 3 应生成最简查询（仅疾病+基因）"""
        failed_q1 = '("colorectal cancer"[tiab]) AND ("KRAS G12C"[tiab]) AND ("SHP2"[tiab])'
        failed_q2 = '("Colorectal Neoplasms"[MeSH] OR "colorectal cancer"[tiab]) AND ("KRAS"[tiab]) AND ("resistance"[tiab])'
        result = smart_pubmed._build_layer_query(
            3, "KRAS G12C colorectal cancer resistance SHP2 inhibitor",
            [failed_q1, failed_q2]
        )
        print(f"\n  Layer 3: {result}")
        assert result and len(result) > 0, "Layer 3 查询不应为空"
        # Layer 3 应比前两层更简短
        assert result.count(" AND ") <= 2, "Layer 3 应最多 2 个 AND"

    @pytest.mark.real_api
    def test_all_layers_for_production_query(self, smart_pubmed):
        """对生产失败查询依次测试 3 层输出"""
        query = "KRAS G12C colorectal cancer resistance SHP2 SOS1 inhibitor China"
        failed = []

        for layer in [1, 2, 3]:
            result = smart_pubmed._build_layer_query(layer, query, failed)
            print(f"\n  Layer {layer}: {result}")
            failed.append(result)
            time.sleep(0.5)


# ============================================================
# 2. 正则清理测试
# ============================================================

class TestFallbackQueryCleanup:
    """测试 _fallback_query_cleanup() 正则清理"""

    def test_remove_numeric_values(self, smart_pubmed):
        """应去除数值+单位"""
        result = smart_pubmed._fallback_query_cleanup("PD-L1 CPS 3 TMB 79 mut/Mb ECOG 1")
        assert "CPS 3" not in result
        assert "79 mut/Mb" not in result
        assert "ECOG 1" not in result
        assert "PD-L1" in result
        print(f"\n  原始: PD-L1 CPS 3 TMB 79 mut/Mb ECOG 1")
        print(f"  清理: {result}")

    def test_variant_notation(self, smart_pubmed):
        """应去掉 p. 前缀"""
        result = smart_pubmed._fallback_query_cleanup("EGFR p.L858R mutation")
        assert "L858R" in result
        assert "p.L858R" not in result
        print(f"\n  原始: EGFR p.L858R mutation")
        print(f"  清理: {result}")

    def test_clean_query_unchanged(self, smart_pubmed):
        """干净查询应不被改变"""
        original = "KRAS G12C colorectal cancer resistance"
        result = smart_pubmed._fallback_query_cleanup(original)
        assert result == original
        print(f"\n  原始: {original}")
        print(f"  清理: {result}")

    def test_chinese_text_removed(self, smart_pubmed):
        """中文字符应被去除"""
        original = "KRAS G12C 结直肠癌 resistance"
        result = smart_pubmed._fallback_query_cleanup(original)
        print(f"\n  原始: {original}")
        print(f"  清理: {result}")
        assert "结直肠癌" not in result
        assert "KRAS" in result
        assert "resistance" in result

    def test_mixed_chinese_english(self, smart_pubmed):
        """混合中英文查询应只保留英文部分"""
        original = "EGFR L858R 非小细胞肺癌 osimertinib 耐药机制"
        result = smart_pubmed._fallback_query_cleanup(original)
        print(f"\n  原始: {original}")
        print(f"  清理: {result}")
        assert "EGFR" in result
        assert "osimertinib" in result
        assert "非小细胞肺癌" not in result


# ============================================================
# 3. 最佳单概念选择测试
# ============================================================

class TestExtractBestSingleConcept:
    """测试 _extract_best_single_concept() 最佳单概念选择"""

    @pytest.mark.parametrize("query,should_not_be", [
        ("high TMB MSS colorectal cancer POLE immunotherapy", "high"),
        ("resistance mechanisms KRAS G12C colorectal cancer", "resistance"),
        ("clinical monitoring ctDNA KRAS G12C", "clinical"),
        ("efficacy safety Fulzerasib cetuximab CRC", "efficacy"),
    ])
    def test_should_not_pick_generic_words(self, smart_pubmed, query, should_not_be):
        """不应选择泛用英语词作为单概念"""
        concept = smart_pubmed._extract_best_single_concept(query)
        print(f"\n  查询: {query}")
        print(f"  选择: {concept}")
        assert concept.strip('"') != should_not_be, (
            f"不应选择 '{should_not_be}'，实际选择: '{concept}'"
        )

    @pytest.mark.parametrize("query,expected_contains", [
        ("KRAS G12C colorectal cancer resistance", "KRAS"),
        ("EGFR L858R NSCLC osimertinib", "EGFR"),
    ])
    def test_should_pick_gene_variant(self, smart_pubmed, query, expected_contains):
        """应优先选择 基因+变异 组合"""
        concept = smart_pubmed._extract_best_single_concept(query)
        print(f"\n  查询: {query}")
        print(f"  选择: {concept}")
        assert expected_contains.lower() in concept.lower(), (
            f"期望包含 '{expected_contains}'，实际: '{concept}'"
        )

    def test_should_pick_drug_name(self, smart_pubmed):
        """无基因+变异时应选择药物名"""
        concept = smart_pubmed._extract_best_single_concept(
            "Fulzerasib cetuximab CRC efficacy"
        )
        print(f"\n  选择: {concept}")
        # Fulzerasib 含 -rasib 后缀，或 cetuximab 含 -ximab
        assert "fulzerasib" in concept.lower() or "cetuximab" in concept.lower(), (
            f"应选择药物名，实际: '{concept}'"
        )

    def test_chinese_query_should_find_english(self, smart_pubmed):
        """含中文的查询应提取英文概念"""
        concept = smart_pubmed._extract_best_single_concept(
            "KRAS G12C 结直肠癌 耐药 SHP2"
        )
        print(f"\n  选择: {concept}")
        assert "KRAS" in concept, f"应提取 KRAS，实际: '{concept}'"


# ============================================================
# 4. 回退链集成测试（Mock）
# ============================================================

class TestSearchLayerFallback:
    """测试 search() 方法的 3 层回退链逻辑"""

    def test_layer1_success_no_fallback(self, smart_pubmed):
        """Layer 1 成功时不触发后续层"""
        api_calls = []

        def mock_build_layer(layer, query, failed):
            return f"layer{layer}_query"

        def mock_api_search(query, max_results=100, year_window=None):
            api_calls.append(query)
            # Layer 1 成功
            return [{"pmid": "1", "title": "test", "abstract": "test", "publication_types": []}]

        with patch.object(smart_pubmed, '_build_layer_query', side_effect=mock_build_layer), \
             patch.object(smart_pubmed.ncbi_client, 'search_pubmed', side_effect=mock_api_search):
            results, query = smart_pubmed.search("KRAS G12C colorectal cancer", skip_filtering=True)

        assert len(api_calls) == 1, f"Layer 1 成功应只调 1 次 API，实际 {len(api_calls)}"
        assert len(results) > 0
        print(f"\n  API 调用: {api_calls}")

    def test_layer1_fail_layer2_success(self, smart_pubmed):
        """Layer 1 失败，Layer 2 成功"""
        api_calls = []

        def mock_build_layer(layer, query, failed):
            return f"layer{layer}_query"

        def mock_api_search(query, max_results=100, year_window=None):
            api_calls.append(query)
            if query == "layer1_query":
                return []  # Layer 1 失败
            return [{"pmid": "1", "title": "test", "abstract": "test", "publication_types": []}]

        with patch.object(smart_pubmed, '_build_layer_query', side_effect=mock_build_layer), \
             patch.object(smart_pubmed.ncbi_client, 'search_pubmed', side_effect=mock_api_search):
            results, query = smart_pubmed.search("test query", skip_filtering=True)

        assert len(api_calls) == 2, f"应调 2 次 API，实际 {len(api_calls)}"
        assert query == "layer2_query"
        assert len(results) > 0
        print(f"\n  API 调用: {api_calls}")

    def test_all_layers_fail_fallback_success(self, smart_pubmed):
        """3 层 LLM 均失败，正则兜底成功"""
        api_calls = []

        def mock_build_layer(layer, query, failed):
            return f"layer{layer}_query"

        def mock_api_search(query, max_results=100, year_window=None):
            api_calls.append(query)
            # 只有正则兜底的查询成功
            if query.startswith("layer"):
                return []
            return [{"pmid": "1", "title": "test", "abstract": "test", "publication_types": []}]

        with patch.object(smart_pubmed, '_build_layer_query', side_effect=mock_build_layer), \
             patch.object(smart_pubmed.ncbi_client, 'search_pubmed', side_effect=mock_api_search):
            results, query = smart_pubmed.search(
                "KRAS G12C colorectal cancer resistance",
                skip_filtering=True
            )

        assert len(api_calls) == 4, f"应调 4 次 API (3 层 + 1 兜底)，实际 {len(api_calls)}"
        assert len(results) > 0
        assert not query.startswith("layer"), "最终查询应来自正则兜底"
        print(f"\n  API 调用: {api_calls}")
        print(f"  最终查询: {query}")

    def test_all_fail_returns_empty(self, smart_pubmed):
        """所有策略均失败时返回空列表"""
        def mock_build_layer(layer, query, failed):
            return f"layer{layer}_query"

        def mock_api_search(query, max_results=100, year_window=None):
            return []  # 全部失败

        with patch.object(smart_pubmed, '_build_layer_query', side_effect=mock_build_layer), \
             patch.object(smart_pubmed.ncbi_client, 'search_pubmed', side_effect=mock_api_search):
            results, query = smart_pubmed.search("nonexistent query", skip_filtering=True)

        assert len(results) == 0
        print(f"\n  最终查询: {query}")

    def test_failed_queries_passed_to_next_layer(self, smart_pubmed):
        """验证失败查询被正确传递到下一层"""
        layer_calls = []

        def mock_build_layer(layer, query, failed):
            layer_calls.append({"layer": layer, "failed": list(failed)})
            return f"layer{layer}_query"

        def mock_api_search(query, max_results=100, year_window=None):
            return []  # 全部失败

        with patch.object(smart_pubmed, '_build_layer_query', side_effect=mock_build_layer), \
             patch.object(smart_pubmed.ncbi_client, 'search_pubmed', side_effect=mock_api_search):
            smart_pubmed.search("test", skip_filtering=True)

        # Layer 1: 无失败查询
        assert layer_calls[0]["layer"] == 1
        assert layer_calls[0]["failed"] == []

        # Layer 2: 收到 Layer 1 的失败查询
        assert layer_calls[1]["layer"] == 2
        assert layer_calls[1]["failed"] == ["layer1_query"]

        # Layer 3: 收到 Layer 1+2 的失败查询
        assert layer_calls[2]["layer"] == 3
        assert layer_calls[2]["failed"] == ["layer1_query", "layer2_query"]

        print("\n  Layer 调用记录:")
        for call in layer_calls:
            print(f"    Layer {call['layer']}: failed={call['failed']}")


# ============================================================
# 5. 端到端搜索测试（真实 API）
# ============================================================

class TestEndToEndSearch:
    """端到端搜索测试，调用真实 PubMed API"""

    @pytest.mark.real_api
    @pytest.mark.parametrize("case", KNOWN_GOOD_QUERIES, ids=[c["description"] for c in KNOWN_GOOD_QUERIES])
    def test_known_good_queries(self, smart_pubmed, case):
        """已知良好查询应返回足够结果"""
        results, optimized_query = smart_pubmed.search(
            case["query"], max_results=20, skip_filtering=True
        )
        print(f"\n  查询: {case['query']}")
        print(f"  优化: {optimized_query}")
        print(f"  结果: {len(results)} 篇")
        assert len(results) >= case["expected_min_results"], (
            f"期望至少 {case['expected_min_results']} 篇，实际 {len(results)} 篇"
        )

    @pytest.mark.real_api
    @pytest.mark.parametrize("case", BOOLEAN_QUERIES, ids=[c["description"] for c in BOOLEAN_QUERIES])
    def test_boolean_queries_directly(self, smart_pubmed, case):
        """验证 Boolean 查询在 PubMed API 上能返回结果"""
        results = smart_pubmed.ncbi_client.search_pubmed(
            case["query"], max_results=20
        )
        print(f"\n  Boolean: {case['query'][:80]}...")
        print(f"  结果: {len(results)} 篇")
        if results:
            for r in results[:3]:
                print(f"    - PMID {r.get('pmid')}: {r.get('title', '')[:60]}...")
        assert len(results) >= case["expected_min_results"], (
            f"期望至少 {case['expected_min_results']} 篇，实际 {len(results)} 篇"
        )

    @pytest.mark.real_api
    @pytest.mark.parametrize("case", PRODUCTION_FAILED_QUERIES, ids=[c["description"] for c in PRODUCTION_FAILED_QUERIES])
    def test_production_failed_queries_improved(self, smart_pubmed, case):
        """生产报告中曾失败的查询：验证新架构是否改善"""
        results, optimized_query = smart_pubmed.search(
            case["query"], max_results=20, skip_filtering=True
        )
        is_first_word_only = optimized_query == case["query"].split()[0]
        print(f"\n  查询: {case['query']}")
        print(f"  优化: {optimized_query}")
        print(f"  结果: {len(results)} 篇")
        print(f"  是否降级到首词: {is_first_word_only}")

        # 新架构不应再降级到首词
        if case["expected_min_results"] > 0:
            assert not is_first_word_only, (
                f"新架构不应降级到首词 '{case['query'].split()[0]}'，应通过某层 LLM 找到结果"
            )

    @pytest.mark.real_api
    def test_mesh_vs_tiab_comparison(self, smart_pubmed):
        """对比 MeSH-only vs MeSH+TIAB vs 简单关键词 的搜索结果数"""
        queries = {
            "简单关键词": '"KRAS G12C" AND inhibitor AND "colorectal cancer" AND resistance',
            "MeSH only": '("Proto-Oncogene Proteins p21(ras)"[MeSH]) AND ("Drug Resistance, Neoplasm"[MeSH]) AND ("Colorectal Neoplasms"[MeSH])',
            "MeSH+TIAB": '("Proto-Oncogene Proteins p21(ras)"[MeSH] OR "KRAS G12C"[TIAB]) AND ("Drug Resistance, Neoplasm"[MeSH] OR "resistance"[TIAB]) AND ("Colorectal Neoplasms"[MeSH] OR "colorectal cancer"[TIAB])',
        }
        print("\n  === MeSH vs TIAB 对比 ===")
        for label, q in queries.items():
            results = smart_pubmed.ncbi_client.search_pubmed(q, max_results=100)
            print(f"  {label}: {len(results)} 篇")
            time.sleep(0.5)


# ============================================================
# 6. 新架构行为验证（真实 API）
# ============================================================

class TestNewArchitectureBehavior:
    """验证 3 层 LLM 递进架构的实际行为"""

    @pytest.mark.real_api
    def test_layer_progression_complex_query(self, smart_pubmed):
        """复杂查询的 3 层递进行为"""
        query = "KRAS G12C colorectal cancer resistance SHP2 SOS1 inhibitor China"
        results, optimized = smart_pubmed.search(query, max_results=20, skip_filtering=True)

        print(f"\n  === 3 层递进测试 ===")
        print(f"  原始: {query}")
        print(f"  实际使用: {optimized}")
        print(f"  结果: {len(results)} 篇")
        # 应该通过某一层找到结果，而非降级到 "KRAS"
        assert len(results) > 0, "3 层架构应能找到结果"
        assert optimized != "KRAS", "不应降级到单个首词 'KRAS'"

    @pytest.mark.real_api
    def test_search_vs_simple_boolean(self, smart_pubmed):
        """对比：新 search() vs 直接用简单 Boolean 查询"""
        query = "KRAS G12C inhibitor resistance colorectal cancer"

        # 新 search() 的结果
        results_search, optimized = smart_pubmed.search(
            query, max_results=20, skip_filtering=True
        )

        time.sleep(1)

        # 直接用简单 Boolean 的结果
        simple_boolean = '"KRAS G12C" AND inhibitor AND "colorectal cancer" AND resistance'
        results_boolean = smart_pubmed.ncbi_client.search_pubmed(simple_boolean, max_results=20)

        print(f"\n  === search() vs 简单 Boolean ===")
        print(f"  search() 优化: {optimized}")
        print(f"  search() 结果: {len(results_search)} 篇")
        print(f"  简单 Boolean: {simple_boolean}")
        print(f"  Boolean 结果: {len(results_boolean)} 篇")

        # 新架构应至少能找到简单 Boolean 能找到的结果
        assert len(results_search) > 0, "search() 应至少返回 1 篇结果"

    @pytest.mark.real_api
    def test_chinese_query_handled(self, smart_pubmed):
        """含中文的查询应能正确处理"""
        query = "KRAS G12C 结直肠癌 耐药 cetuximab"
        results, optimized = smart_pubmed.search(query, max_results=10, skip_filtering=True)

        print(f"\n  查询: {query}")
        print(f"  优化: {optimized}")
        print(f"  结果: {len(results)} 篇")
        # 应能找到结果（中文被清理后搜英文内容）
        assert len(results) > 0, "含中文查询经清理后应能找到结果"


# ============================================================
# 7. 出版类型分桶测试
# ============================================================

class TestPublicationTypeBucketing:
    """测试 _classify_publication_bucket() 映射"""

    @pytest.mark.parametrize("pub_types,expected_bucket", [
        (["Practice Guideline", "Journal Article"], "guideline"),
        (["Randomized Controlled Trial", "Journal Article"], "rct"),
        (["Meta-Analysis", "Journal Article"], "systematic_review"),
        (["Systematic Review"], "systematic_review"),
        (["Observational Study"], "observational"),
        (["Case Reports"], "case_report"),
        (["Clinical Trial, Phase III", "Multicenter Study"], "rct"),  # rct > observational
        (["Guideline", "Systematic Review"], "guideline"),  # guideline > systematic_review
        (["Review", "Journal Article"], "systematic_review"),  # Review → systematic_review
    ])
    def test_bucket_classification(self, smart_pubmed, pub_types, expected_bucket):
        """XML PublicationType 应正确映射到 MTB 桶"""
        article = {"publication_types": pub_types, "title": "", "abstract": ""}
        result = smart_pubmed._classify_publication_bucket(article)
        assert result == expected_bucket, (
            f"PublicationType {pub_types} 应映射到 '{expected_bucket}'，实际: '{result}'"
        )

    def test_journal_article_only_returns_none(self, smart_pubmed):
        """仅 'Journal Article' 应返回 None（待 LLM 二次分类）"""
        article = {
            "publication_types": ["Journal Article"],
            "title": "KRAS G12C in colorectal cancer",
            "abstract": "A retrospective analysis of 200 patients..."
        }
        result = smart_pubmed._classify_publication_bucket(article)
        assert result is None, f"仅 Journal Article 应返回 None，实际: '{result}'"

    def test_empty_pub_types_returns_none(self, smart_pubmed):
        """空 publication_types 应返回 None"""
        article = {"publication_types": [], "title": "test", "abstract": "test"}
        result = smart_pubmed._classify_publication_bucket(article)
        assert result is None

    def test_preclinical_heuristic(self, smart_pubmed):
        """preclinical 启发式：title/abstract 含 'in vitro' 等关键词"""
        article = {
            "publication_types": ["Journal Article"],
            "title": "In vitro study of KRAS G12C inhibitor",
            "abstract": "Cell line experiments with xenograft models showed..."
        }
        result = smart_pubmed._classify_publication_bucket(article)
        assert result == "preclinical", f"应检测为 preclinical，实际: '{result}'"

    def test_xml_takes_priority_over_preclinical_heuristic(self, smart_pubmed):
        """XML 明确分类应优先于 preclinical 启发式"""
        article = {
            "publication_types": ["Randomized Controlled Trial", "Journal Article"],
            "title": "In vitro and clinical study",
            "abstract": "Cell line and patient data..."
        }
        result = smart_pubmed._classify_publication_bucket(article)
        assert result == "rct", "XML 分类应优先于 preclinical 启发式"


# ============================================================
# 8. 分层采样测试
# ============================================================

class TestStratifiedSampling:
    """测试 _stratified_sample() 分层采样"""

    def _make_article(self, pmid, bucket, score):
        """创建测试文章"""
        return {
            "pmid": str(pmid), "title": f"Article {pmid}",
            "abstract": "test", "publication_types": [],
            "mtb_bucket": bucket, "relevance_score": score,
        }

    def test_basic_quota_sampling(self, smart_pubmed):
        """基本配额采样：各桶按配额取文章"""
        articles = []
        # 10 篇 RCT
        for i in range(10):
            articles.append(self._make_article(i, "rct", 8 - i * 0.1))
        # 5 篇 guideline
        for i in range(10, 15):
            articles.append(self._make_article(i, "guideline", 9 - (i - 10) * 0.1))

        result = smart_pubmed._stratified_sample(articles, max_results=9)
        buckets = [a.get("mtb_bucket") for a in result]
        # guideline 配额 3, rct 配额 6
        assert buckets.count("guideline") == 3, f"guideline 应取 3 篇，实际 {buckets.count('guideline')}"
        assert buckets.count("rct") == 6, f"rct 应取 6 篇，实际 {buckets.count('rct')}"

    def test_empty_bucket_redistribution(self, smart_pubmed):
        """空桶配额应重分配给有余量的桶"""
        articles = []
        # 只有 rct 文章，其他桶为空
        for i in range(20):
            articles.append(self._make_article(i, "rct", 8 - i * 0.1))

        result = smart_pubmed._stratified_sample(articles, max_results=10)
        assert len(result) == 10, f"应返回 10 篇，实际 {len(result)}"
        assert all(a.get("mtb_bucket") == "rct" for a in result)

    def test_priority_ordering(self, smart_pubmed):
        """结果应按桶优先级排序（guideline > rct > ...）"""
        articles = [
            self._make_article(1, "case_report", 9),
            self._make_article(2, "guideline", 7),
            self._make_article(3, "rct", 8),
        ]
        result = smart_pubmed._stratified_sample(articles, max_results=3)
        assert result[0]["mtb_bucket"] == "guideline"
        assert result[1]["mtb_bucket"] == "rct"
        assert result[2]["mtb_bucket"] == "case_report"

    def test_within_bucket_sorted_by_score(self, smart_pubmed):
        """桶内应按 relevance_score 降序排列"""
        articles = [
            self._make_article(1, "rct", 5),
            self._make_article(2, "rct", 9),
            self._make_article(3, "rct", 7),
        ]
        result = smart_pubmed._stratified_sample(articles, max_results=3)
        scores = [a["relevance_score"] for a in result]
        assert scores == [9, 7, 5], f"桶内应按分数降序，实际: {scores}"

    def test_unclassified_fallback_to_observational(self, smart_pubmed):
        """未分类文章（mtb_bucket=None）应兜底到 observational"""
        articles = [
            self._make_article(1, None, 8),
            self._make_article(2, None, 7),
        ]
        result = smart_pubmed._stratified_sample(articles, max_results=2)
        assert all(a["mtb_bucket"] == "observational" for a in result)

    def test_fewer_articles_than_max_results(self, smart_pubmed):
        """文章数少于 max_results 时应返回全部"""
        articles = [
            self._make_article(1, "rct", 8),
            self._make_article(2, "guideline", 9),
        ]
        result = smart_pubmed._stratified_sample(articles, max_results=20)
        assert len(result) == 2


# ============================================================
# 9. year_window 透传测试
# ============================================================

class TestYearWindow:
    """测试 year_window 参数透传"""

    def test_year_window_passed_to_ncbi(self, smart_pubmed):
        """year_window 应透传到 ncbi_client.search_pubmed()"""
        api_calls = []

        def mock_build_layer(layer, query, failed):
            return f"layer{layer}_query"

        def mock_api_search(query, max_results=100, year_window=None):
            api_calls.append({"query": query, "year_window": year_window})
            return [{"pmid": "1", "title": "test", "abstract": "test", "publication_types": []}]

        with patch.object(smart_pubmed, '_build_layer_query', side_effect=mock_build_layer), \
             patch.object(smart_pubmed.ncbi_client, 'search_pubmed', side_effect=mock_api_search):
            smart_pubmed.search("KRAS G12C", year_window=15, skip_filtering=True)

        assert api_calls[0]["year_window"] == 15, (
            f"year_window 应为 15，实际: {api_calls[0]['year_window']}"
        )

    def test_default_year_window(self, smart_pubmed):
        """未指定 year_window 时应使用 DEFAULT_YEAR_WINDOW"""
        from config.settings import DEFAULT_YEAR_WINDOW
        api_calls = []

        def mock_build_layer(layer, query, failed):
            return f"layer{layer}_query"

        def mock_api_search(query, max_results=100, year_window=None):
            api_calls.append({"year_window": year_window})
            return [{"pmid": "1", "title": "test", "abstract": "test", "publication_types": []}]

        with patch.object(smart_pubmed, '_build_layer_query', side_effect=mock_build_layer), \
             patch.object(smart_pubmed.ncbi_client, 'search_pubmed', side_effect=mock_api_search):
            smart_pubmed.search("KRAS G12C", skip_filtering=True)

        assert api_calls[0]["year_window"] == DEFAULT_YEAR_WINDOW


# ============================================================
# 10. 真实 API 分桶验证
# ============================================================

class TestBucketingRealAPI:
    """真实 API 测试：验证 publication_types 解析和分桶"""

    @pytest.mark.real_api
    def test_publication_types_parsed(self, smart_pubmed):
        """真实 API: publication_types 字段应被正确解析"""
        results, _ = smart_pubmed.search(
            "EGFR L858R osimertinib", max_results=10, skip_filtering=True
        )
        has_pub_types = any(r.get("publication_types") for r in results)
        assert has_pub_types, "至少部分文章应有 publication_types"
        print("\n  === publication_types 解析验证 ===")
        for r in results[:5]:
            print(f"  PMID {r.get('pmid')}: {r.get('publication_types', [])} -> {r.get('mtb_bucket')}")

    @pytest.mark.real_api
    def test_stratified_results_have_buckets(self, smart_pubmed):
        """真实 API: 分层采样后每篇文章都应有 mtb_bucket"""
        results, _ = smart_pubmed.search(
            "EGFR L858R osimertinib", max_results=10, skip_filtering=True
        )
        for r in results:
            assert r.get("mtb_bucket") is not None, (
                f"PMID {r.get('pmid')} 缺少 mtb_bucket"
            )
        print("\n  === 分桶结果 ===")
        bucket_dist = {}
        for r in results:
            b = r.get("mtb_bucket")
            bucket_dist[b] = bucket_dist.get(b, 0) + 1
        print(f"  分布: {bucket_dist}")


# ============================================================
# 11. _filter_batch() LLM 评估与过滤测试
# ============================================================

class TestFilterBatch:
    """测试 _filter_batch() 的 LLM 评估与过滤逻辑"""

    def _make_article(self, pmid, title="Test", abstract="Test abstract", pub_types=None):
        """创建测试文章"""
        return {
            "pmid": str(pmid),
            "title": title,
            "abstract": abstract,
            "publication_types": pub_types or ["Journal Article"],
        }

    def _mock_llm_response(self, evaluations):
        """构造 LLM 返回的 JSON 字符串"""
        import json
        return json.dumps(evaluations, ensure_ascii=False)

    def test_pass_threshold_score_gte_5(self, smart_pubmed):
        """score=5 + is_relevant=True → 应通过"""
        article = self._make_article("111")
        llm_resp = self._mock_llm_response([{
            "pmid": "111", "is_relevant": True, "relevance_score": 5,
            "study_type": "rct", "matched_criteria": ["KRAS"], "key_findings": "found"
        }])

        with patch.object(smart_pubmed, '_call_llm', return_value=llm_resp):
            result = smart_pubmed._filter_batch("KRAS G12C", [article], 0)

        assert len(result) == 1, f"score=5 应通过，实际返回 {len(result)}"
        assert result[0]["pmid"] == "111"

    def test_reject_score_below_5(self, smart_pubmed):
        """score=4 + is_relevant=True → 应被拒"""
        article = self._make_article("222")
        llm_resp = self._mock_llm_response([{
            "pmid": "222", "is_relevant": True, "relevance_score": 4,
            "study_type": "preclinical", "matched_criteria": [], "key_findings": ""
        }])

        with patch.object(smart_pubmed, '_call_llm', return_value=llm_resp):
            result = smart_pubmed._filter_batch("KRAS G12C", [article], 0)

        assert len(result) == 0, f"score=4 应被拒，实际返回 {len(result)}"

    def test_reject_not_relevant(self, smart_pubmed):
        """score=8 + is_relevant=False → 应被拒"""
        article = self._make_article("333")
        llm_resp = self._mock_llm_response([{
            "pmid": "333", "is_relevant": False, "relevance_score": 8,
            "study_type": "rct", "matched_criteria": [], "key_findings": ""
        }])

        with patch.object(smart_pubmed, '_call_llm', return_value=llm_resp):
            result = smart_pubmed._filter_batch("KRAS G12C", [article], 0)

        assert len(result) == 0, f"is_relevant=False 应被拒，实际返回 {len(result)}"

    def test_fields_assigned_correctly(self, smart_pubmed):
        """通过的文章应被正确赋值 relevance_score、matched_criteria、key_findings、llm_study_type"""
        article = self._make_article("444")
        llm_resp = self._mock_llm_response([{
            "pmid": "444", "is_relevant": True, "relevance_score": 9,
            "study_type": "systematic_review",
            "matched_criteria": ["KRAS G12C", "resistance"],
            "key_findings": "SHP2 inhibition overcomes resistance"
        }])

        with patch.object(smart_pubmed, '_call_llm', return_value=llm_resp):
            result = smart_pubmed._filter_batch("KRAS G12C resistance", [article], 0)

        assert len(result) == 1
        a = result[0]
        assert a["relevance_score"] == 9
        assert a["matched_criteria"] == ["KRAS G12C", "resistance"]
        assert a["key_findings"] == "SHP2 inhibition overcomes resistance"
        assert a["llm_study_type"] == "systematic_review"

    def test_skip_articles_without_abstract(self, smart_pubmed):
        """无摘要文章应被跳过，不参与 LLM 评估"""
        articles = [
            self._make_article("555", abstract="Has abstract"),
            self._make_article("666", abstract=""),  # 无摘要
            self._make_article("777", abstract=None),  # 无摘要
        ]
        # LLM 只会收到 1 篇（PMID 555）
        llm_resp = self._mock_llm_response([{
            "pmid": "555", "is_relevant": True, "relevance_score": 7,
            "study_type": "rct", "matched_criteria": [], "key_findings": ""
        }])

        with patch.object(smart_pubmed, '_call_llm', return_value=llm_resp) as mock:
            result = smart_pubmed._filter_batch("test", articles, 0)

        assert len(result) == 1
        assert result[0]["pmid"] == "555"
        # 验证 LLM 被调用了（说明至少有 1 篇有摘要）
        mock.assert_called_once()

    def test_all_articles_no_abstract_skips_llm(self, smart_pubmed):
        """所有文章都无摘要时应跳过 LLM 调用"""
        articles = [
            self._make_article("888", abstract=""),
            self._make_article("999", abstract=""),
        ]

        with patch.object(smart_pubmed, '_call_llm') as mock:
            result = smart_pubmed._filter_batch("test", articles, 0)

        assert len(result) == 0
        mock.assert_not_called()

    def test_invalid_study_type_not_assigned(self, smart_pubmed):
        """LLM 返回非法 study_type 时不设 llm_study_type"""
        article = self._make_article("100")
        llm_resp = self._mock_llm_response([{
            "pmid": "100", "is_relevant": True, "relevance_score": 7,
            "study_type": "unknown_type",
            "matched_criteria": [], "key_findings": ""
        }])

        with patch.object(smart_pubmed, '_call_llm', return_value=llm_resp):
            result = smart_pubmed._filter_batch("test", [article], 0)

        assert len(result) == 1
        assert "llm_study_type" not in result[0], (
            f"非法 study_type 不应设 llm_study_type，实际: {result[0].get('llm_study_type')}"
        )

    def test_json_parse_error_fallback(self, smart_pubmed):
        """LLM 返回非法 JSON 时的降级处理"""
        article = self._make_article("200")
        # 非法 JSON，但包含 PMID 和 is_relevant: true
        bad_response = 'Invalid JSON but "200" is here and "is_relevant": true somewhere'

        with patch.object(smart_pubmed, '_call_llm', return_value=bad_response):
            result = smart_pubmed._filter_batch("test", [article], 0)

        # 降级逻辑：检测 PMID 和 is_relevant: true → score=5 兜底
        assert len(result) == 1
        assert result[0]["relevance_score"] == 5

    def test_json_parse_error_no_match(self, smart_pubmed):
        """LLM 返回非法 JSON 且无 PMID 匹配时返回空"""
        article = self._make_article("300")
        bad_response = 'Totally invalid response with no useful info'

        with patch.object(smart_pubmed, '_call_llm', return_value=bad_response):
            result = smart_pubmed._filter_batch("test", [article], 0)

        assert len(result) == 0


# ============================================================
# 12. _filter_results() 批次拆分与聚合测试
# ============================================================

class TestFilterResults:
    """测试 _filter_results() 的批次拆分与并行执行"""

    def _make_article(self, pmid, score=7):
        return {
            "pmid": str(pmid), "title": f"Article {pmid}",
            "abstract": f"Abstract {pmid}", "publication_types": [],
            "relevance_score": score,
        }

    def test_batch_splitting(self, smart_pubmed):
        """25 篇文章应被拆为 2 批（20+5），每批都调用 _filter_batch"""
        articles = [self._make_article(i) for i in range(25)]
        call_args = []

        def mock_filter_batch(query, batch, idx):
            call_args.append({"batch_size": len(batch), "idx": idx})
            return batch  # 全部通过

        with patch.object(smart_pubmed, '_filter_batch', side_effect=mock_filter_batch):
            result = smart_pubmed._filter_results("test query", articles)

        assert len(call_args) == 2, f"25 篇应分 2 批，实际 {len(call_args)} 批"
        batch_sizes = sorted([c["batch_size"] for c in call_args])
        assert batch_sizes == [5, 20], f"批次大小应为 [5, 20]，实际 {batch_sizes}"

    def test_results_sorted_by_score(self, smart_pubmed):
        """最终结果应按 relevance_score 降序排序"""
        articles = [
            self._make_article(1, score=3),
            self._make_article(2, score=9),
            self._make_article(3, score=6),
        ]

        def mock_filter_batch(query, batch, idx):
            return batch

        with patch.object(smart_pubmed, '_filter_batch', side_effect=mock_filter_batch):
            result = smart_pubmed._filter_results("test", articles)

        scores = [a["relevance_score"] for a in result]
        assert scores == [9, 6, 3], f"应按分数降序，实际: {scores}"

    def test_empty_input(self, smart_pubmed):
        """空列表输入 → 返回空列表"""
        result = smart_pubmed._filter_results("test", [])
        assert result == []

    def test_batch_exception_handled(self, smart_pubmed):
        """某批次异常时不影响其他批次"""
        articles = [self._make_article(i) for i in range(25)]
        call_count = [0]

        def mock_filter_batch(query, batch, idx):
            call_count[0] += 1
            if idx == 0:
                raise RuntimeError("Batch 0 LLM failure")
            return batch  # 第二批成功

        with patch.object(smart_pubmed, '_filter_batch', side_effect=mock_filter_batch):
            result = smart_pubmed._filter_results("test", articles)

        # 第二批（5 篇）应成功返回
        assert len(result) == 5, f"异常批次不应影响其他批次，期望 5，实际 {len(result)}"


# ============================================================
# 13. LLM 二次分桶与 bucket_source 追踪测试
# ============================================================

class TestLLMSecondaryBucketing:
    """测试 _finalize_results() 中的 LLM 二次分桶逻辑"""

    def _make_article(self, pmid, pub_types=None, abstract="test abstract"):
        return {
            "pmid": str(pmid), "title": f"Article {pmid}",
            "abstract": abstract,
            "publication_types": pub_types or ["Journal Article"],
        }

    def test_xml_bucket_preserved(self, smart_pubmed):
        """XML 已分类的文章 → mtb_bucket 不变，bucket_source='xml'"""
        # RCT 类型文章
        articles = [self._make_article("1", pub_types=["Randomized Controlled Trial", "Journal Article"])]

        def mock_filter(query, results):
            # 不改变文章，直接返回
            return results

        with patch.object(smart_pubmed, '_filter_results', side_effect=mock_filter):
            result, _ = smart_pubmed._finalize_results("test", articles, "q", 20, False)

        assert len(result) == 1
        assert result[0]["mtb_bucket"] == "rct"
        assert result[0]["bucket_source"] == "xml"

    def test_llm_fills_none_bucket(self, smart_pubmed):
        """XML 未分类 + llm_study_type 有效 → bucket_source='llm'"""
        articles = [self._make_article("1")]  # 仅 Journal Article → XML 返回 None

        def mock_filter(query, results):
            # 模拟 LLM 赋值了 llm_study_type
            for a in results:
                a["relevance_score"] = 7
                a["llm_study_type"] = "observational"
            return results

        with patch.object(smart_pubmed, '_filter_results', side_effect=mock_filter):
            result, _ = smart_pubmed._finalize_results("test", articles, "q", 20, False)

        assert len(result) == 1
        assert result[0]["mtb_bucket"] == "observational"
        assert result[0]["bucket_source"] == "llm"

    def test_fallback_to_observational(self, smart_pubmed):
        """XML 未分类 + 无 llm_study_type → 回退到 observational，bucket_source='fallback'"""
        articles = [self._make_article("1")]

        def mock_filter(query, results):
            # LLM 没有设 llm_study_type
            for a in results:
                a["relevance_score"] = 6
            return results

        with patch.object(smart_pubmed, '_filter_results', side_effect=mock_filter):
            result, _ = smart_pubmed._finalize_results("test", articles, "q", 20, False)

        assert len(result) == 1
        assert result[0]["mtb_bucket"] == "observational"
        assert result[0]["bucket_source"] == "fallback"

    def test_invalid_llm_type_falls_back(self, smart_pubmed):
        """llm_study_type='invalid_type' → 回退到 observational"""
        articles = [self._make_article("1")]

        def mock_filter(query, results):
            for a in results:
                a["relevance_score"] = 7
                a["llm_study_type"] = "invalid_type"  # 不在 MTB_EVIDENCE_BUCKETS 中
            return results

        with patch.object(smart_pubmed, '_filter_results', side_effect=mock_filter):
            result, _ = smart_pubmed._finalize_results("test", articles, "q", 20, False)

        assert len(result) == 1
        assert result[0]["mtb_bucket"] == "observational"
        assert result[0]["bucket_source"] == "fallback"

    def test_bucket_source_tracking_mixed(self, smart_pubmed):
        """混合场景：xml/llm/fallback 各有，验证 bucket_source 正确"""
        articles = [
            self._make_article("1", pub_types=["Clinical Trial, Phase III", "Journal Article"]),  # XML → rct
            self._make_article("2"),  # 无 XML → 待 LLM
            self._make_article("3"),  # 无 XML → 待 LLM，但 LLM 也没给 study_type
        ]

        def mock_filter(query, results):
            for a in results:
                a["relevance_score"] = 7
            # 第 2 篇: LLM 补了 study_type
            results[1]["llm_study_type"] = "systematic_review"
            # 第 3 篇: LLM 没给 study_type
            return results

        with patch.object(smart_pubmed, '_filter_results', side_effect=mock_filter):
            result, _ = smart_pubmed._finalize_results("test", articles, "q", 20, False)

        sources = {a["pmid"]: a["bucket_source"] for a in result}
        assert sources["1"] == "xml", f"PMID 1 应为 xml，实际 {sources['1']}"
        assert sources["2"] == "llm", f"PMID 2 应为 llm，实际 {sources['2']}"
        assert sources["3"] == "fallback", f"PMID 3 应为 fallback，实际 {sources['3']}"

        buckets = {a["pmid"]: a["mtb_bucket"] for a in result}
        assert buckets["1"] == "rct"
        assert buckets["2"] == "systematic_review"
        assert buckets["3"] == "observational"


# ============================================================
# 14. _finalize_results() 完整管线集成测试
# ============================================================

class TestFinalizeResultsIntegration:
    """测试 _finalize_results() 完整流程（XML → LLM → 二次分桶 → 采样）"""

    def _make_article(self, pmid, pub_types=None):
        return {
            "pmid": str(pmid), "title": f"Article {pmid}",
            "abstract": f"Abstract for article {pmid}",
            "publication_types": pub_types or ["Journal Article"],
        }

    def test_full_pipeline_fields_propagated(self, smart_pubmed):
        """完整流程后，最终结果应同时包含 mtb_bucket、bucket_source、relevance_score"""
        articles = [
            self._make_article("1", pub_types=["Randomized Controlled Trial"]),
            self._make_article("2"),
        ]

        def mock_filter(query, results):
            for a in results:
                a["relevance_score"] = 8
                a["matched_criteria"] = ["KRAS"]
                a["key_findings"] = "test findings"
            results[1]["llm_study_type"] = "case_report"
            return results

        with patch.object(smart_pubmed, '_filter_results', side_effect=mock_filter):
            result, _ = smart_pubmed._finalize_results("test", articles, "q", 20, False)

        for a in result:
            assert "mtb_bucket" in a, f"PMID {a['pmid']} 缺少 mtb_bucket"
            assert "bucket_source" in a, f"PMID {a['pmid']} 缺少 bucket_source"
            assert "relevance_score" in a, f"PMID {a['pmid']} 缺少 relevance_score"
            assert a["bucket_source"] in ("xml", "llm", "fallback"), (
                f"PMID {a['pmid']} bucket_source 非法: {a['bucket_source']}"
            )

    def test_skip_filtering_true_path(self, smart_pubmed):
        """skip_filtering=True → 未分类文章用 observational 兜底"""
        articles = [
            self._make_article("1", pub_types=["Case Reports"]),  # XML → case_report
            self._make_article("2"),  # 仅 Journal Article → None → fallback
        ]

        result, _ = smart_pubmed._finalize_results("test", articles, "q", 20, True)

        r_dict = {a["pmid"]: a for a in result}
        assert r_dict["1"]["mtb_bucket"] == "case_report"
        assert r_dict["1"]["bucket_source"] == "xml"
        assert r_dict["2"]["mtb_bucket"] == "observational"
        assert r_dict["2"]["bucket_source"] == "fallback"

    def test_all_articles_filtered_out(self, smart_pubmed):
        """LLM 把所有文章都拒了 → 返回空列表"""
        articles = [self._make_article("1"), self._make_article("2")]

        def mock_filter(query, results):
            return []  # 全部被拒

        with patch.object(smart_pubmed, '_filter_results', side_effect=mock_filter):
            result, _ = smart_pubmed._finalize_results("test", articles, "q", 20, False)

        assert result == [], f"所有文章被拒应返回空，实际 {len(result)} 篇"


# ============================================================
# pytest 配置
# ============================================================

def pytest_configure(config):
    """注册自定义 marker"""
    config.addinivalue_line(
        "markers", "real_api: 需要真实 API 调用的测试（PubMed + OpenRouter）"
    )
