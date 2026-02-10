"""
Chair Agent（MTB 主席）
"""
from typing import Dict, Any, List, Optional

from src.agents.base_agent import BaseAgent
from src.tools.guideline_tools import NCCNTool, FDALabelTool
from src.tools.literature_tools import PubMedTool
from src.models.evidence_graph import EvidenceGraph, EntityType, Predicate, EvidenceGrade
from src.models.evidence_graph import construct_provenance_url
from config.settings import CHAIR_PROMPT_FILE, REQUIRED_SECTIONS


class ChairAgent(BaseAgent):
    """
    MTB 主席 Agent

    汇总所有专家意见，生成最终的 6 章节+附录报告。
    负责仲裁冲突（安全优先）和确保引用完整性。
    """

    def __init__(self):
        tools = [
            NCCNTool(),
            FDALabelTool(),
            PubMedTool()
        ]

        super().__init__(
            role="Chair",
            prompt_file=CHAIR_PROMPT_FILE,
            tools=tools,
            temperature=0.3  # 稍高温度以增加综合能力
        )

    @staticmethod
    def _grade_sort_key(grade) -> int:
        """证据等级排序键（A=0 最高, E=4 最低, None=5）"""
        if grade is None:
            return 5
        order = {EvidenceGrade.A: 0, EvidenceGrade.B: 1, EvidenceGrade.C: 2,
                 EvidenceGrade.D: 3, EvidenceGrade.E: 4}
        return order.get(grade, 5)

    def _format_observation(self, obs) -> str:
        """格式化单条 Observation 为文本（输出所有字段）"""
        grade_str = f"[{obs.evidence_grade.value}]" if obs.evidence_grade else "[?]"
        civic_str = obs.civic_type.value if obs.civic_type else "-"
        return (
            f"  - {grade_str} {obs.statement}\n"
            f"    id: {obs.id} | agent: {obs.source_agent or '-'} | "
            f"tool: {obs.source_tool or '-'} | provenance: {obs.provenance or '-'} | "
            f"url: {obs.source_url or '-'} | civic_type: {civic_str} | "
            f"iteration: {obs.iteration}"
        )

    def _generate_evidence_reference_list(self, evidence_graph: Optional[EvidenceGraph]) -> str:
        """
        从 evidence graph 中按 obs.id 去重，生成完整证据引用列表（Module 12）。

        Args:
            evidence_graph: 完整证据图

        Returns:
            Markdown 格式的完整证据引用列表
        """
        if not evidence_graph or not evidence_graph.entities:
            return "\n\n---\n\n## 12. 完整证据引用列表\n\n暂无证据数据。\n"

        # 1. 收集所有 observations（entity + edge）
        all_obs = []
        for entity in evidence_graph.entities.values():
            for obs in entity.observations:
                all_obs.append(obs)
        for edge in evidence_graph.edges.values():
            for obs in edge.observations:
                all_obs.append(obs)

        # 2. 按 obs.id 去重
        seen_ids = set()
        unique_obs = []
        for obs in all_obs:
            if obs.id not in seen_ids:
                seen_ids.add(obs.id)
                unique_obs.append(obs)

        # 3. 按证据等级排序 (A→E, None 最后)
        unique_obs.sort(key=lambda o: self._grade_sort_key(o.evidence_grade))

        # 4. 生成 markdown 表格
        lines = [
            "\n\n---\n",
            "## 12. 完整证据引用列表\n",
            f"以下为本次分析中收集的全部证据（共 {len(unique_obs)} 条，按证据等级排序）：\n",
            "| 证据陈述 | # | 证据等级 | 来源Agent | 链接 |",
            "|----------|---|----------|-----------|------|",
        ]

        for i, obs in enumerate(unique_obs, 1):
            stmt = (obs.statement or "-").replace("|", "\\|")
            grade = obs.evidence_grade.value if obs.evidence_grade else "-"
            agent = obs.source_agent or "-"
            link = self._format_obs_link(obs.provenance, obs.source_url)
            lines.append(f"| {stmt} | {i} | {grade} | {agent} | {link} |")

        return "\n".join(lines)

    @staticmethod
    def _format_obs_link(provenance: str, source_url: str) -> str:
        """
        将 provenance + source_url 格式化为 markdown 链接。

        Returns:
            如 [PMID:12345678](https://pubmed.ncbi.nlm.nih.gov/12345678/)
        """
        prov = (provenance or "").strip()
        url = (source_url or "").strip()

        if not prov and not url:
            return "-"

        # 如果有 URL 且有 provenance，生成 markdown 链接
        if url and prov:
            return f"[{prov}]({url})"

        # 只有 provenance，尝试自动构建 URL
        if prov and not url:
            url = construct_provenance_url(prov)
            if url:
                return f"[{prov}]({url})"
            return prov

        # 只有 URL
        return f"[链接]({url})"

    # ==================== Section-based evidence organization ====================

    # 报告模块与证据类型的映射
    _EVIDENCE_SECTIONS = [
        {
            "title": "分子特征证据",
            "desc": "基因、变异、生物标志物、信号通路及其分子机制关系",
            "entity_types": {EntityType.GENE, EntityType.VARIANT, EntityType.BIOMARKER, EntityType.PATHWAY},
            "predicates": {
                Predicate.SENSITIZES, Predicate.CAUSES_RESISTANCE,
                Predicate.ACTIVATES, Predicate.INHIBITS, Predicate.BINDS,
                Predicate.PHOSPHORYLATES, Predicate.REGULATES,
                Predicate.AMPLIFIES, Predicate.MUTATES_TO, Predicate.MEMBER_OF,
            },
        },
        {
            "title": "治疗方案证据",
            "desc": "药物、方案及其治疗关系（含禁忌与相互作用）",
            "entity_types": {EntityType.DRUG, EntityType.REGIMEN},
            "predicates": {
                Predicate.TREATS, Predicate.RECOMMENDS,
                Predicate.INTERACTS_WITH, Predicate.CONTRAINDICATED_FOR,
            },
        },
        {
            "title": "临床试验证据",
            "desc": "相关临床试验及其评估内容",
            "entity_types": {EntityType.TRIAL},
            "predicates": {Predicate.EVALUATES, Predicate.INCLUDES_ARM},
        },
        {
            "title": "疾病背景证据",
            "desc": "疾病类型、关联及生物标志物",
            "entity_types": {EntityType.DISEASE},
            "predicates": {
                Predicate.ASSOCIATED_WITH, Predicate.BIOMARKER_FOR,
                Predicate.EXPRESSED_IN,
            },
        },
        {
            "title": "指南与文献证据",
            "desc": "参考指南、文献及其支持/矛盾关系",
            "entity_types": {EntityType.PAPER, EntityType.GUIDELINE},
            "predicates": {
                Predicate.SUPPORTS, Predicate.CONTRADICTS,
                Predicate.CITES, Predicate.DERIVED_FROM,
            },
        },
    ]

    def _format_evidence_for_chair(self, evidence_graph: Optional[EvidenceGraph]) -> str:
        """
        将证据图按报告模块组织为 Chair 可用的完整文本

        按报告模块（分子特征、治疗方案、临床试验、疾病背景、指南文献）
        组织证据，使 LLM 在生成每个模块时能看到最相关的上下文证据。
        总证据量不减少（遵循 no-truncation 策略），仅改变组织方式。
        实体和边可跨模块出现（如 DRUG 同时出现在治疗和试验中），不丢信息。

        Args:
            evidence_graph: 证据图对象

        Returns:
            格式化的证据图文本
        """
        if not evidence_graph or not evidence_graph.entities:
            return ""

        parts = []

        # ===== 1. 统计摘要（紧凑） =====
        summary = evidence_graph.summary()
        agent_summary = evidence_graph.summary_by_agent()

        entity_type_str = ', '.join(f'{k}({v})' for k, v in summary.get('entities_by_type', {}).items())
        agent_str = ', '.join(f'{k}({v["observation_count"]})' for k, v in agent_summary.items())
        grade_str = ', '.join(f'{k}({v})' for k, v in sorted(summary.get('best_grades', {}).items()))

        parts.append(f"""
## 证据图统计
- **总实体数**: {summary.get('total_entities', 0)}
- **总边数**: {summary.get('total_edges', 0)}
- **总观察数**: {summary.get('total_observations', 0)}
- **按实体类型**: {entity_type_str}
- **按Agent观察数**: {agent_str}
- **按等级**: {grade_str}
""")

        # ===== 2. 按报告模块组织证据 =====
        all_covered_entity_types = set()
        all_covered_predicates = set()

        for section in self._EVIDENCE_SECTIONS:
            section_entities = [
                e for e in evidence_graph.entities.values()
                if e.entity_type in section["entity_types"]
            ]
            section_edges = [
                e for e in evidence_graph.edges.values()
                if e.predicate in section["predicates"] and e.observations
            ]

            if not section_entities and not section_edges:
                continue

            all_covered_entity_types |= section["entity_types"]
            all_covered_predicates |= section["predicates"]

            parts.append(f"\n## {section['title']}")
            parts.append(f"*{section['desc']}*\n")

            # 实体与观察
            if section_entities:
                for entity in section_entities:
                    obs_list = sorted(
                        entity.observations,
                        key=lambda o: self._grade_sort_key(o.evidence_grade)
                    )
                    if not obs_list:
                        parts.append(f"**{entity.name}** ({entity.canonical_id}) — 无观察\n")
                        continue

                    parts.append(f"**{entity.name}** ({entity.canonical_id}) — {len(obs_list)} 条观察:")
                    for obs in obs_list:
                        parts.append(self._format_observation(obs))
                    parts.append("")

            # 关系边与观察
            if section_edges:
                parts.append(f"### {section['title']} — 关键关系\n")
                for edge in section_edges:
                    source = evidence_graph.get_entity(edge.source_id)
                    target = evidence_graph.get_entity(edge.target_id)
                    source_name = source.name if source else edge.source_id
                    target_name = target.name if target else edge.target_id
                    pred_str = edge.predicate.value if edge.predicate else "?"
                    conf_str = f" (confidence: {edge.confidence:.2f})" if edge.confidence else ""

                    parts.append(f"**{source_name}** → {pred_str} → **{target_name}**{conf_str}")
                    obs_sorted = sorted(
                        edge.observations,
                        key=lambda o: self._grade_sort_key(o.evidence_grade)
                    )
                    for obs in obs_sorted:
                        parts.append(self._format_observation(obs))
                    parts.append("")

        # ===== 3. 补充证据（未归入上述模块的实体和边） =====
        remaining_entities = [
            e for e in evidence_graph.entities.values()
            if e.entity_type not in all_covered_entity_types
        ]
        remaining_edges = [
            e for e in evidence_graph.edges.values()
            if e.predicate not in all_covered_predicates and e.observations
        ]

        if remaining_entities or remaining_edges:
            parts.append("\n## 补充证据\n")

            for entity in remaining_entities:
                obs_list = sorted(
                    entity.observations,
                    key=lambda o: self._grade_sort_key(o.evidence_grade)
                )
                if not obs_list:
                    parts.append(f"**{entity.name}** ({entity.canonical_id}) — 无观察\n")
                    continue
                parts.append(f"**{entity.name}** ({entity.canonical_id}) — {len(obs_list)} 条观察:")
                for obs in obs_list:
                    parts.append(self._format_observation(obs))
                parts.append("")

            for edge in remaining_edges:
                source = evidence_graph.get_entity(edge.source_id)
                target = evidence_graph.get_entity(edge.target_id)
                source_name = source.name if source else edge.source_id
                target_name = target.name if target else edge.target_id
                pred_str = edge.predicate.value if edge.predicate else "?"
                conf_str = f" (confidence: {edge.confidence:.2f})" if edge.confidence else ""
                parts.append(f"**{source_name}** → {pred_str} → **{target_name}**{conf_str}")
                for obs in edge.observations:
                    parts.append(self._format_observation(obs))
                parts.append("")

        # ===== 4. 矛盾/冲突证据（跨模块，需仲裁） =====
        conflict_edges = [
            e for e in evidence_graph.edges.values()
            if e.conflict_group or e.predicate == Predicate.CONTRADICTS
        ]
        if conflict_edges:
            parts.append("\n## 矛盾/冲突证据（需要仲裁）\n")
            for edge in conflict_edges:
                source = evidence_graph.get_entity(edge.source_id)
                target = evidence_graph.get_entity(edge.target_id)
                source_name = source.name if source else edge.source_id
                target_name = target.name if target else edge.target_id
                pred_str = edge.predicate.value if edge.predicate else "?"
                conflict_info = f" [conflict_group: {edge.conflict_group}]" if edge.conflict_group else ""

                parts.append(f"- {source_name} → {pred_str} → {target_name}{conflict_info}")
                for obs in edge.observations:
                    parts.append(self._format_observation(obs))
                parts.append("")

        # ===== 5. 完整引用列表（含所有字段） =====
        all_observations = []
        for entity in evidence_graph.entities.values():
            for obs in entity.observations:
                if obs.provenance:
                    all_observations.append(obs)
        for edge in evidence_graph.edges.values():
            for obs in edge.observations:
                if obs.provenance:
                    all_observations.append(obs)

        # 按 provenance 去重（保留最高等级的）
        seen_prov = {}
        for obs in all_observations:
            key = obs.provenance
            if key not in seen_prov or self._grade_sort_key(obs.evidence_grade) < self._grade_sort_key(seen_prov[key].evidence_grade):
                seen_prov[key] = obs

        if seen_prov:
            parts.append("\n## 完整引用列表（务必在报告中引用这些来源）\n")
            parts.append("| Provenance | URL | Statement | Agent | Tool | Grade | CivicType |")
            parts.append("|------------|-----|-----------|-------|------|-------|-----------|")

            for prov, obs in sorted(seen_prov.items()):
                url = obs.source_url or "-"
                stmt = obs.statement or "-"
                agent = obs.source_agent or "-"
                tool = obs.source_tool or "-"
                grade = obs.evidence_grade.value if obs.evidence_grade else "-"
                civic = obs.civic_type.value if obs.civic_type else "-"
                parts.append(f"| {prov} | {url} | {stmt} | {agent} | {tool} | {grade} | {civic} |")

        return "\n".join(parts)

    def synthesize(
        self,
        raw_pdf_text: str,
        pathologist_report: str = "",
        geneticist_report: str = "",
        recruiter_report: str = "",
        oncologist_plan: str = "",
        missing_sections: List[str] = None,
        evidence_graph: Optional[EvidenceGraph] = None,
        # New Phase 1 reports
        pharmacist_report: str = "",
        oncologist_analysis_report: str = "",
        # New Phase 2a reports
        oncologist_mapping_report: str = "",
        local_therapist_report: str = "",
        nutritionist_report: str = "",
        integrative_med_report: str = "",
        # New Phase 2b report
        pharmacist_review_report: str = "",
        # New Phase 3 report
        oncologist_integration_report: str = "",
    ) -> Dict[str, Any]:
        """
        基于全部 agent 报告生成最终 MTB 报告 (6章节+附录)

        Args:
            raw_pdf_text: PDF 解析后的完整病历原文
            pathologist_report: Phase 1 病理学报告
            geneticist_report: Phase 1 遗传学报告
            pharmacist_report: Phase 1 药师报告(合并症/用药)
            oncologist_analysis_report: Phase 1 过往治疗分析(3.1)
            oncologist_mapping_report: Phase 2a Oncologist Mapping报告
            local_therapist_report: Phase 2a 局部治疗报告
            recruiter_report: Phase 2a 临床试验报告
            nutritionist_report: Phase 2a 营养报告
            integrative_med_report: Phase 2a 整合医学报告
            pharmacist_review_report: Phase 2b 药学审查报告
            oncologist_integration_report: Phase 3 方案整合报告
            oncologist_plan: 向后兼容(同 oncologist_integration_report)
            missing_sections: 上一次验证失败时缺失的模块
            evidence_graph: 证据图

        Returns:
            包含综合报告和引用的字典
        """
        # 向后兼容：如果有 integration 报告但没有 oncologist_plan
        if oncologist_integration_report and not oncologist_plan:
            oncologist_plan = oncologist_integration_report

        regenerate_note = ""
        if missing_sections:
            regenerate_note = f"""
**重要**: 上一次报告缺少以下章节，请确保本次包含:
{chr(10).join([f'- {s}' for s in missing_sections])}
"""

        evidence_info = self._format_evidence_for_chair(evidence_graph)

        task_prompt = f"""
请作为 MTB 主席，汇总整合以下全部专家报告生成最终 MTB 报告。

**核心原则: 汇总整合，不是摘要压缩！**
- 保留所有专家报告中的关键发现，禁止压缩、合并、简化
- 保留所有临床试验推荐
- 保留完整的治疗史记录和 L1-L5 证据分层标注
- **使用证据图中的引用**（见下方证据图统计和引用列表）

{regenerate_note}{evidence_info}

---

**病历原文**:
{raw_pdf_text}

---

## Phase 1 报告

**1. 病理学报告** (1.1基础信息 + 1.2诊断 + 治疗史提取):
{pathologist_report if pathologist_report else "暂无"}

---

**2. 遗传学报告** (1.3分子特征 + 5.2分子复查初稿):
{geneticist_report if geneticist_report else "暂无"}

---

**3. 药师报告** (1.4合并症 + 1.5过敏史 + 器官功能基线):
{pharmacist_report if pharmacist_report else "暂无"}

---

**4. 过往治疗分析** (3.1 每线治疗评价):
{oncologist_analysis_report if oncologist_analysis_report else "暂无"}

---

## Phase 2a 报告

**5. Oncologist Mapping** (3.2 全身治疗4审批×5手段矩阵):
{oncologist_mapping_report if oncologist_mapping_report else "暂无"}

---

**6. 局部治疗** (手术/放疗/介入):
{local_therapist_report if local_therapist_report else "暂无"}

---

**7. 临床试验** (活跃+已结束):
{recruiter_report if recruiter_report else "暂无"}

---

**8. 营养方案**:
{nutritionist_report if nutritionist_report else "暂无"}

---

**9. 整合医学/替代疗法**:
{integrative_med_report if integrative_med_report else "暂无"}

---

## Phase 2b 报告

**10. 药学审查** (药物交互/剂量调整/禁忌标注):
{pharmacist_review_report if pharmacist_review_report else "暂无"}

---

## Phase 3 报告

**11. 方案整合** (3.3治疗方案+L1-L5 + 3.4路径排序 + 5.1+5.2复查):
{oncologist_integration_report if oncologist_integration_report else oncologist_plan if oncologist_plan else "暂无"}

---

**必须包含的章节**:
{chr(10).join([f'{i+1}. {s}' for i, s in enumerate(REQUIRED_SECTIONS)])}

**报告结构要求**:
1. 第1章"病情概要": 整合 pathologist(1.1/1.2) + geneticist(1.3) + pharmacist(1.4/1.5) 报告
2. 第2章"治疗史回顾": 使用 :::timeline 格式展示所有治疗记录，整合 pathologist 提取 + oncologist_analysis(3.1) 评价
3. 第3章"治疗方案探索": 3.1 来自 Phase1 oncologist_analysis; 3.2 来自 Phase2a mapping+local_therapist+recruiter+pharmacist_review; 3.3+3.4 来自 Phase3 integration (保留L1-L5标注)
4. 第4章"整体与辅助支持": 4.1 来自 nutritionist; 4.2 来自 integrative_med
5. 第5章"复查和追踪方案": 5.1+5.2 来自 Phase3 integration + geneticist 初稿
6. 第6章"核心建议汇总": Chair 综合
7. 附录A"完整证据引用列表": 由系统自动生成，你不需要生成
8. 附录B"证据等级说明": 包含 CIViC A-E + L1-L5 说明

**关键要求**:
- 保留 Phase 3 的 L1-L5 证据分层标注，不修改
- 引用 LocalTherapist 建议时不修改局部治疗技术参数
- 每条建议必须标注证据等级 [Evidence A/B/C/D/E]
- 仲裁原则：当安全性与疗效冲突时，以安全性为准
- 所有引用使用 `[PMID: xxx](url)` 或 `[[ref:ID;;Title;;URL;;Note]]` 格式
- 充分利用输出长度，确保报告完整详尽

请生成完整的 Markdown 格式 MTB 报告。
"""

        result = self.invoke(task_prompt)

        # 程序化生成附录A（完整证据引用列表）
        evidence_list = self._generate_evidence_reference_list(evidence_graph)
        output_with_evidence = result["output"] + evidence_list

        full_report = self.generate_full_report(
            main_content=output_with_evidence,
            title="MTB Chair Final Synthesis Report"
        )

        return {
            "synthesis": output_with_evidence,
            "full_report_md": full_report
        }


if __name__ == "__main__":
    print("ChairAgent 模块加载成功")
    print(f"必选模块数量: {len(REQUIRED_SECTIONS)}")
