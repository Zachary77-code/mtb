"""
Chair Agent & HTML Generator 功能测试

测试覆盖:
- HTML 渲染管道 (B1-B6 bug 修复 + 核心功能)
- Chair 证据格式化和引用注入
- 格式验证器
- 真实报告集成测试
"""
import re
import sys
from pathlib import Path

import pytest

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.renderers.html_generator import HtmlReportGenerator
from src.agents.chair import ChairAgent
from src.validators.format_checker import FormatChecker
from src.models.evidence_graph import (
    EvidenceGraph, Entity, Edge, Observation,
    EntityType, Predicate, EvidenceGrade, CivicEvidenceType,
)


# ==================== Fixtures ====================

@pytest.fixture
def gen():
    """HtmlReportGenerator instance."""
    return HtmlReportGenerator()


@pytest.fixture
def chair():
    """ChairAgent instance (no API call in tests)."""
    return ChairAgent()


@pytest.fixture
def format_checker():
    return FormatChecker()


@pytest.fixture
def evidence_graph():
    """Populated EvidenceGraph with entities, edges, and observations."""
    g = EvidenceGraph()

    # Entities
    g.get_or_create_entity("GENE:EGFR", EntityType.GENE, "EGFR", "test")
    g.get_or_create_entity("EGFR_L858R", EntityType.VARIANT, "L858R", "test")
    g.get_or_create_entity("DRUG:OSIMERTINIB", EntityType.DRUG, "Osimertinib", "test")
    g.get_or_create_entity("DISEASE:NSCLC", EntityType.DISEASE, "NSCLC", "test")
    g.get_or_create_entity("NCT:NCT04487080", EntityType.TRIAL, "NCT04487080", "test")

    # Observations on entities
    obs1 = Observation(
        id="obs_test0001",
        statement="EGFR L858R 对奥希替尼敏感，ORR 72% (Phase III, n=347)",
        source_agent="Geneticist",
        source_tool="PubMed",
        provenance="PMID:28854312",
        source_url="https://pubmed.ncbi.nlm.nih.gov/28854312/",
        evidence_grade=EvidenceGrade.A,
        civic_type=CivicEvidenceType.PREDICTIVE,
        iteration=1,
    )
    g.add_observation_to_entity("EGFR_L858R", obs1)

    obs2 = Observation(
        id="obs_test0002",
        statement="奥希替尼一线治疗 EGFR+ NSCLC，PFS 18.9个月",
        source_agent="Oncologist",
        source_tool="PubMed",
        provenance="PMID:29151359",
        source_url="https://pubmed.ncbi.nlm.nih.gov/29151359/",
        evidence_grade=EvidenceGrade.B,
        civic_type=CivicEvidenceType.PREDICTIVE,
        iteration=2,
    )
    g.add_observation_to_entity("DRUG:OSIMERTINIB", obs2)

    obs3 = Observation(
        id="obs_test0003",
        statement="NCT04487080 评估奥希替尼联合化疗",
        source_agent="Recruiter",
        source_tool="ClinicalTrials",
        provenance="NCT04487080",
        source_url="https://clinicaltrials.gov/study/NCT04487080",
        evidence_grade=EvidenceGrade.C,
        iteration=1,
    )
    g.add_observation_to_entity("NCT:NCT04487080", obs3)

    # Edge with observation
    edge_obs = Observation(
        id="obs_test0004",
        statement="EGFR L858R sensitizes to osimertinib",
        source_agent="Geneticist",
        source_tool="CIViC",
        provenance="PMID:28854312",
        source_url="https://pubmed.ncbi.nlm.nih.gov/28854312/",
        evidence_grade=EvidenceGrade.A,
        iteration=1,
    )
    g.add_edge("EGFR_L858R", "DRUG:OSIMERTINIB", Predicate.SENSITIZES,
               observation=edge_obs, confidence=0.95)

    return g


REAL_REPORT_PATH = Path("reports/20260204_102106_unknown/5_chair_final_report.md")


@pytest.fixture
def real_chair_md():
    """Load real 5_chair_final_report.md if available."""
    if not REAL_REPORT_PATH.exists():
        pytest.skip("Real report not available")
    return REAL_REPORT_PATH.read_text(encoding="utf-8")


# ==================== Class 1: HTML Rendering ====================

class TestHtmlRendering:
    """HTML 渲染管道测试 — 覆盖 B1-B6 bug 修复 + 核心功能"""

    # --- B1: Bold in table cells ---
    def test_bold_in_table_cells(self, gen):
        md = (
            "| 项目 | 结果 |\n"
            "|------|------|\n"
            "| **年龄** | 65岁 |\n"
            "| **性别** | 男 |\n"
        )
        html = gen._markdown_to_html(md)
        assert "<strong>年龄</strong>" in html
        assert "<strong>性别</strong>" in html
        assert "**年龄**" not in html, "Raw ** should not appear in output"

    # --- B2: Heading inside div ---
    def test_heading_inside_div(self, gen):
        md = (
            '<div class="section">\n\n'
            "### 基本信息\n\n"
            "患者男性，65岁\n\n"
            "</div>"
        )
        html = gen._markdown_to_html(md)
        assert "<h3>" in html, "### should render as <h3> inside <div>"
        assert "### 基本信息" not in html, "Raw ### should not appear"

    # --- B3: Refs in table cells ---
    def test_ref_in_table_no_breakage(self, gen):
        md = (
            "| 证据 | 来源 |\n"
            "|------|------|\n"
            "| FLAURA研究 | [[ref:P1;;PMID:28854312;;https://pubmed.ncbi.nlm.nih.gov/28854312/]] |\n"
        )
        html = gen._markdown_to_html(md)
        assert '[[ref:' not in html, "Raw [[ref:]] should be converted"
        assert '<table>' in html or '<table' in html
        # No broken HTML tags
        assert '...]]' not in html
        assert 'ref-tooltip' in html or 'cite' in html

    def test_multiple_refs_in_same_row(self, gen):
        """Two [[ref:...]] in adjacent cells should both parse correctly (B3 greedy regex fix)."""
        md = (
            "| 研究A | 研究B |\n"
            "|-------|-------|\n"
            "| [[ref:P6;;PMID:38336371;;https://pubmed.ncbi.nlm.nih.gov/38336371/]] "
            "| [[ref:P7;;PMID:37133585;;https://pubmed.ncbi.nlm.nih.gov/37133585/]] |\n"
        )
        html = gen._markdown_to_html(md)
        assert '[[ref:' not in html, "All refs should be converted"
        # Both PMIDs should appear as citations
        assert '38336371' in html
        assert '37133585' in html

    # --- B4: Roadmap dict actions ---
    def test_roadmap_dict_actions(self, gen):
        roadmap_yaml = (
            ":::roadmap\n"
            "- title: 一线方案\n"
            "  status: current\n"
            "  regimen: 奥希替尼\n"
            "  actions:\n"
            "    - 若 POLE(+): 双免疫治疗\n"
            "    - 若 MSS: 化疗联合靶向\n"
            ":::\n"
        )
        html = gen._markdown_to_html(roadmap_yaml)
        assert "{'若 POLE(+)'" not in html, "Dict syntax should not appear"
        assert "若 POLE(+)" in html or "POLE" in html

    # --- B5: No nested tooltips ---
    def test_no_nested_tooltips(self, gen):
        # Simulate HTML with an existing ref-tooltip containing a bare [PMID:xxx]
        html_input = (
            '<span class="ref-tooltip">'
            '<a class="cite" href="https://pubmed.ncbi.nlm.nih.gov/28854312/">[PMID: 28854312]</a>'
            '<span class="ref-text">PMID: 28854312 - FLAURA study</span>'
            '</span>'
        )
        result = gen._add_reference_links(html_input)
        # Count ref-tooltip spans - should be exactly 1 (the original)
        tooltip_count = result.count('class="ref-tooltip"')
        assert tooltip_count == 1, f"Expected 1 ref-tooltip, got {tooltip_count}"

    # --- B6: Markdown after table section ---
    def test_markdown_after_table(self, gen):
        md = (
            "| 项目 | 结果 |\n"
            "|------|------|\n"
            "| 基因 | EGFR |\n\n"
            "## 6. 下一节标题\n\n"
            "**重要内容**在这里。\n"
        )
        html = gen._markdown_to_html(md)
        assert "<h2>" in html, "## heading after table should render"
        assert "<strong>重要内容</strong>" in html
        assert "## 6." not in html, "Raw ## should not appear"

    # --- Custom blocks ---
    def test_exec_summary_block(self, gen):
        md = ":::exec-summary\n关键发现：EGFR L858R 突变阳性\n:::\n"
        html = gen._markdown_to_html(md)
        assert 'exec-summary' in html
        assert 'EGFR L858R' in html

    def test_timeline_block_yaml(self, gen):
        md = (
            ":::timeline\n"
            "- type: surgery\n"
            "  date: 2024-01\n"
            "  regimen: 右肺上叶切除\n"
            "  response: CR\n"
            "  line: 手术\n"
            ":::\n"
        )
        html = gen._markdown_to_html(md)
        assert 'treatment-timeline' in html
        assert '右肺上叶切除' in html

    # --- B7: Custom block HTML not escaped ---
    def test_timeline_not_escaped(self, gen):
        """Timeline HTML should NOT be escaped by markdown processor (B7)."""
        md = (
            "## 3. 治疗史\n\n"
            ":::timeline\n"
            "- type: surgery\n"
            "  date: 2024-01\n"
            "  regimen: 手术切除\n"
            "  response: CR\n"
            "  line: 手术\n"
            ":::\n\n"
            "## 4. 下一节\n\n"
            "正常内容\n"
        )
        html = gen._markdown_to_html(md)
        assert '&lt;div' not in html, "Timeline divs should NOT be HTML-escaped"
        assert '<pre><code>' not in html or 'treatment-' not in html.split('<pre>')[0] if '<pre>' in html else True
        assert 'treatment-timeline' in html
        assert 'treatment-item' in html

    def test_roadmap_not_escaped(self, gen):
        """Roadmap HTML should NOT be escaped by markdown processor (B7)."""
        md = (
            "### 4.4 治疗决策\n\n"
            ":::roadmap\n"
            "- title: 当前方案\n"
            "  status: current\n"
            "  regimen: 奥希替尼\n"
            "  actions:\n"
            "    - 每3周评估\n"
            ":::\n\n"
            "## 5. 下一节\n"
        )
        html = gen._markdown_to_html(md)
        assert '&lt;div' not in html, "Roadmap divs should NOT be HTML-escaped"
        assert 'card-grid' in html
        assert 'card-header' in html

    def test_roadmap_block(self, gen):
        md = (
            ":::roadmap\n"
            "- title: 一线方案\n"
            "  status: current\n"
            "  regimen: 奥希替尼 80mg QD\n"
            "  actions:\n"
            "    - 每3周评估\n"
            "    - 监测QTc\n"
            ":::\n"
        )
        html = gen._markdown_to_html(md)
        assert 'card-grid' in html
        assert '奥希替尼 80mg QD' in html
        assert '每3周评估' in html

    # --- Inline refs ---
    def test_ref_4field(self, gen):
        md = "研究发现 [[ref:P1;;FLAURA Study;;https://pubmed.ncbi.nlm.nih.gov/28854312/;;奥希替尼一线]] 支持此结论"
        html = gen._markdown_to_html(md)
        assert '[[ref:' not in html
        assert '28854312' in html
        assert 'ref-tooltip' in html or 'cite' in html

    def test_ref_3field(self, gen):
        md = "证据 [[ref:P2;;AURA3;;https://pubmed.ncbi.nlm.nih.gov/27959700/]] 显示"
        html = gen._markdown_to_html(md)
        assert '[[ref:' not in html
        assert '27959700' in html

    def test_ref_legacy_pipe(self, gen):
        md = "参考 [[ref:P3|Legacy Title|https://pubmed.ncbi.nlm.nih.gov/12345678/|旧格式]] 说明"
        html = gen._markdown_to_html(md)
        assert '[[ref:' not in html
        assert '12345678' in html

    # --- Bare reference conversion ---
    def test_pmid_bare_reference(self, gen):
        html_input = "证据来源 [PMID: 28854312] 支持此方案"
        result = gen._add_reference_links(html_input)
        assert 'ref-tooltip' in result or 'cite' in result
        assert '28854312' in result

    def test_nct_bare_reference(self, gen):
        html_input = "推荐临床试验 [NCT04487080] 正在招募"
        result = gen._add_reference_links(html_input)
        assert 'ref-tooltip' in result or 'cite' in result
        assert 'NCT04487080' in result

    # --- _inject_markdown_attr_to_divs ---
    def test_inject_markdown_attr(self, gen):
        md = '<div class="section">\ncontent\n</div>'
        result = gen._inject_markdown_attr_to_divs(md)
        assert 'markdown="1"' in result

    def test_inject_markdown_attr_no_double(self, gen):
        md = '<div class="section" markdown="1">\ncontent\n</div>'
        result = gen._inject_markdown_attr_to_divs(md)
        assert result.count('markdown=') == 1


# ==================== Class 2: Chair Evidence Formatting ====================

class TestChairEvidenceFormatting:
    """Chair 证据格式化和引用注入测试"""

    def test_grade_sort_key(self, chair):
        assert chair._grade_sort_key(EvidenceGrade.A) == 0
        assert chair._grade_sort_key(EvidenceGrade.B) == 1
        assert chair._grade_sort_key(EvidenceGrade.C) == 2
        assert chair._grade_sort_key(EvidenceGrade.D) == 3
        assert chair._grade_sort_key(EvidenceGrade.E) == 4
        assert chair._grade_sort_key(None) == 5
        # A < B < C < D < E < None
        assert chair._grade_sort_key(EvidenceGrade.A) < chair._grade_sort_key(EvidenceGrade.E)

    def test_format_observation(self, chair):
        obs = Observation(
            id="obs_fmt01",
            statement="EGFR L858R shows 72% ORR to osimertinib",
            source_agent="Geneticist",
            source_tool="PubMed",
            provenance="PMID:28854312",
            source_url="https://pubmed.ncbi.nlm.nih.gov/28854312/",
            evidence_grade=EvidenceGrade.A,
            civic_type=CivicEvidenceType.PREDICTIVE,
            iteration=1,
        )
        text = chair._format_observation(obs)
        assert "[A]" in text
        assert "EGFR L858R" in text
        assert "PMID:28854312" in text
        assert "Geneticist" in text
        assert "PubMed" in text

    def test_inject_missing_citations_adds_table(self, chair, evidence_graph):
        # Markdown that does NOT cite PMID:29151359 or NCT04487080
        md = "## 报告\n引用了 [PMID: 28854312] 但没有其他引用。\n"
        result = chair._inject_missing_citations(md, evidence_graph)
        assert "完整证据引用列表" in result
        # Should contain the missing provenances
        assert "29151359" in result or "NCT04487080" in result

    def test_inject_missing_citations_no_duplicates(self, chair, evidence_graph):
        # Markdown that already cites ALL provenances
        md = (
            "## 报告\n"
            "引用了 [PMID: 28854312] 和 [PMID: 29151359]。\n"
            "临床试验 [NCT04487080] 也已纳入。\n"
        )
        result = chair._inject_missing_citations(md, evidence_graph)
        assert "完整证据引用列表" not in result, "No missing citations should be appended"

    def test_inject_missing_citations_empty_graph(self, chair):
        empty_graph = EvidenceGraph()
        md = "## 报告\n内容\n"
        result = chair._inject_missing_citations(md, empty_graph)
        assert result == md, "Empty graph should return markdown unchanged"

    def test_inject_missing_citations_none_graph(self, chair):
        md = "## 报告\n内容\n"
        result = chair._inject_missing_citations(md, None)
        assert result == md

    def test_inject_missing_nct(self, chair, evidence_graph):
        # Cite PMIDs but not NCT
        md = "引用了 [PMID: 28854312] 和 [PMID: 29151359]。\n"
        result = chair._inject_missing_citations(md, evidence_graph)
        assert "NCT04487080" in result

    def test_format_evidence_for_chair_sections(self, chair, evidence_graph):
        text = chair._format_evidence_for_chair(evidence_graph)
        assert "分子特征证据" in text
        assert "治疗方案证据" in text
        assert "临床试验证据" in text

    def test_format_evidence_for_chair_stats(self, chair, evidence_graph):
        text = chair._format_evidence_for_chair(evidence_graph)
        assert "证据图统计" in text
        assert "总实体数" in text


# ==================== Class 3: Format Validation ====================

class TestFormatValidation:
    """FormatChecker 格式验证测试"""

    def _make_full_report(self):
        """Generate a report with all required sections."""
        from config.settings import REQUIRED_SECTIONS
        lines = []
        for i, section in enumerate(REQUIRED_SECTIONS, 1):
            lines.append(f"## {i}. {section}\n内容\n")
        return "\n".join(lines)

    def test_all_sections_present(self, format_checker):
        report = self._make_full_report()
        is_valid, missing = format_checker.validate(report)
        assert is_valid, f"Full report should pass, missing: {missing}"
        assert len(missing) == 0

    def test_missing_section(self, format_checker):
        report = self._make_full_report()
        # Remove 执行摘要
        report = report.replace("## 1. 执行摘要", "## 1. 删除的段落")
        is_valid, missing = format_checker.validate(report)
        assert not is_valid
        assert "执行摘要" in missing

    def test_english_alias_match(self, format_checker):
        report = "## Executive Summary\ncontent\n"
        # Should match "执行摘要"
        assert format_checker._section_exists("执行摘要", report)

    def test_markdown_heading_match(self, format_checker):
        report = "## 1. 执行摘要\n内容\n"
        assert format_checker._section_exists("执行摘要", report)

    def test_empty_report(self, format_checker):
        is_valid, missing = format_checker.validate("")
        assert not is_valid
        assert len(missing) > 0

    def test_generate_feedback_missing(self, format_checker):
        feedback = format_checker.generate_feedback(["执行摘要", "患者概况"])
        assert "执行摘要" in feedback
        assert "患者概况" in feedback
        assert "验证失败" in feedback

    def test_generate_feedback_none(self, format_checker):
        feedback = format_checker.generate_feedback([])
        assert "验证通过" in feedback

    def test_check_references(self, format_checker):
        report = "内容 [PMID: 28854312] 和 [NCT04487080] 引用 [PMID: 29151359]"
        has_refs, count = format_checker.check_references(report)
        assert has_refs
        assert count == 3


# ==================== Class 4: Real Report Integration ====================

class TestRealReportRendering:
    """真实报告集成测试 — 需要 reports/ 目录中存在实际报告文件"""

    def test_real_report_no_raw_bold(self, gen, real_chair_md):
        html = gen._markdown_to_html(real_chair_md)
        # Find raw **text** patterns not inside code blocks
        raw_bold = re.findall(r'(?<!</code>)\*\*[^*]+\*\*', html)
        # Filter out any that might be in code/pre blocks or timeline YAML values
        raw_bold = [b for b in raw_bold if '<code>' not in b]
        # Allow <=2 residual: timeline YAML note values contain raw markdown
        # that is rendered as text (not processed through markdown pipeline)
        assert len(raw_bold) <= 2, f"Found {len(raw_bold)} raw **bold** patterns in HTML: {raw_bold[:5]}"

    def test_real_report_bold_rendered(self, gen, real_chair_md):
        html = gen._markdown_to_html(real_chair_md)
        strong_count = html.count("<strong>")
        assert strong_count > 0, "Should have <strong> tags in rendered HTML"

    def test_real_report_headings_rendered(self, gen, real_chair_md):
        html = gen._markdown_to_html(real_chair_md)
        h2_count = html.count("<h2>") + html.count("<h2 ")
        h3_count = html.count("<h3>") + html.count("<h3 ")
        assert h2_count + h3_count > 0, "Should have heading tags"

    def test_real_report_tables_rendered(self, gen, real_chair_md):
        html = gen._markdown_to_html(real_chair_md)
        assert "<table>" in html or "<table " in html, "Should have <table> tags"

    def test_real_report_refs_valid(self, gen, real_chair_md):
        html = gen._markdown_to_html(real_chair_md)
        broken_refs = re.findall(r'<a\s+href="[^"]*\]\]', html)
        assert len(broken_refs) == 0, f"Found {len(broken_refs)} broken ref tags"

    def test_real_report_no_dict_syntax(self, gen, real_chair_md):
        html = gen._markdown_to_html(real_chair_md)
        dict_patterns = re.findall(r"\{'[^']+'\s*:", html)
        assert len(dict_patterns) == 0, f"Found dict syntax in HTML: {dict_patterns}"

    def test_real_report_format_validation(self, format_checker, real_chair_md):
        is_valid, missing = format_checker.validate(real_chair_md)
        assert is_valid, f"Real report should pass validation, missing: {missing}"
