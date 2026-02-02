"""
Chair Agent（MTB 主席）
"""
import re
from typing import Dict, Any, List, Optional

from src.agents.base_agent import BaseAgent
from src.tools.guideline_tools import NCCNTool, FDALabelTool
from src.tools.literature_tools import PubMedTool
from src.models.evidence_graph import EvidenceGraph, EntityType, Predicate, EvidenceGrade
from src.models.evidence_graph import construct_provenance_url, format_provenance_citation
from config.settings import CHAIR_PROMPT_FILE, REQUIRED_SECTIONS


class ChairAgent(BaseAgent):
    """
    MTB 主席 Agent

    汇总所有专家意见，生成最终的 12 模块报告。
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

    def _inject_missing_citations(self, markdown: str, evidence_graph: Optional[EvidenceGraph]) -> str:
        """
        扫描 Chair LLM 输出的 markdown，找出未引用的 evidence graph provenance，
        在末尾追加完整证据引用列表。

        Args:
            markdown: Chair LLM 生成的 markdown 报告
            evidence_graph: 完整证据图

        Returns:
            追加了缺失引用的 markdown
        """
        if not evidence_graph or not evidence_graph.entities:
            return markdown

        # 1. 提取 markdown 中已引用的 provenance key（归一化：去空格、统一大写）
        cited_keys = set()

        # PMID 模式
        for m in re.finditer(r'PMID[:\s]*(\d+)', markdown):
            cited_keys.add(f"PMID:{m.group(1)}")

        # NCT 模式
        for m in re.finditer(r'(NCT\d+)', markdown):
            cited_keys.add(m.group(1).upper())

        # cBioPortal 模式
        for m in re.finditer(r'cBioPortal[:\s]*([^\]\s,|]+)', markdown, re.IGNORECASE):
            cited_keys.add(f"CBIOPORTAL:{m.group(1).strip().upper()}")

        # NCCN 模式
        for m in re.finditer(r'NCCN[:\s]*([^\]\s|]+)', markdown, re.IGNORECASE):
            cited_keys.add(f"NCCN:{m.group(1).strip().upper()}")

        # CIViC 模式
        for m in re.finditer(r'CIViC[:\s]*([^\]\s|]+)', markdown, re.IGNORECASE):
            cited_keys.add(f"CIVIC:{m.group(1).strip().upper()}")

        # 2. 收集 evidence graph 全部 provenance + observation（去重，保留最高 grade）
        all_observations = []
        for entity in evidence_graph.entities.values():
            for obs in entity.observations:
                if obs.provenance:
                    all_observations.append(obs)
        for edge in evidence_graph.edges.values():
            for obs in edge.observations:
                if obs.provenance:
                    all_observations.append(obs)

        seen_prov = {}
        for obs in all_observations:
            key = obs.provenance
            if key not in seen_prov or self._grade_sort_key(obs.evidence_grade) < self._grade_sort_key(seen_prov[key].evidence_grade):
                seen_prov[key] = obs

        # 3. 归一化 evidence graph provenance key 并匹配
        def normalize_prov(prov: str) -> set:
            """将一个 provenance 归一化为可能的 key 集合"""
            keys = set()
            prov_clean = prov.strip()

            if prov_clean.upper().startswith("PMID"):
                pmid = prov_clean.split(":")[-1].strip()
                # 处理多 PMID 的情况，如 "PMID:12345678, PMID:23456789"
                for part in pmid.split(","):
                    part = part.strip()
                    if part.upper().startswith("PMID"):
                        part = part.split(":")[-1].strip()
                    if part.isdigit():
                        keys.add(f"PMID:{part}")
            elif prov_clean.upper().startswith("NCT"):
                for part in prov_clean.split(","):
                    part = part.strip()
                    if part.upper().startswith("NCT"):
                        keys.add(part.upper())
            elif prov_clean.lower().startswith("cbioportal"):
                study = prov_clean.split(":")[-1].strip()
                keys.add(f"CBIOPORTAL:{study.upper()}")
            elif prov_clean.upper().startswith("NCCN"):
                label = prov_clean.split(":")[-1].strip()
                keys.add(f"NCCN:{label.upper()}")
            elif prov_clean.lower().startswith("civic"):
                label = prov_clean.split(":")[-1].strip()
                keys.add(f"CIVIC:{label.upper()}")
            else:
                keys.add(prov_clean.upper())

            return keys

        missing = []
        for prov, obs in sorted(seen_prov.items()):
            norm_keys = normalize_prov(prov)
            if not norm_keys.intersection(cited_keys):
                missing.append((prov, obs))

        if not missing:
            return markdown

        # 4. 追加缺失引用表格
        lines = [
            "\n\n---\n",
            "## 完整证据引用列表\n",
            "以下证据来源已被纳入本次分析参考，此处汇总列出以确保引用完整性：\n",
            "| # | 引用 | 证据等级 | 来源Agent | 工具 | 证据陈述 |",
            "|---|------|----------|-----------|------|----------|",
        ]

        for i, (prov, obs) in enumerate(missing, 1):
            citation = format_provenance_citation(prov, obs.source_url or "")
            grade = obs.evidence_grade.value if obs.evidence_grade else "?"
            agent = obs.source_agent or "-"
            tool = obs.source_tool or "-"
            stmt = (obs.statement or "-").replace("|", "\\|")
            lines.append(f"| {i} | {citation} | {grade} | {agent} | {tool} | {stmt} |")

        return markdown + "\n".join(lines)

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
        pathologist_report: str,
        geneticist_report: str,
        recruiter_report: str,
        oncologist_plan: str,
        missing_sections: List[str] = None,
        evidence_graph: Optional[EvidenceGraph] = None
    ) -> Dict[str, Any]:
        """
        基于完整报告生成最终 MTB 报告

        注意：这是汇总整合，不是摘要压缩！保留所有专家报告中的关键发现。

        Args:
            raw_pdf_text: PDF 解析后的完整病历原文
            pathologist_report: 病理学分析报告（完整）
            geneticist_report: 遗传学家报告（完整）
            recruiter_report: 临床试验专员报告（完整）
            oncologist_plan: 肿瘤学家方案（完整）
            missing_sections: 上一次验证失败时缺失的模块
            evidence_graph: 证据图（包含所有 Agent 收集的结构化证据）

        Returns:
            包含综合报告和引用的字典
        """
        # 构建综合请求
        regenerate_note = ""
        if missing_sections:
            regenerate_note = f"""
**重要**: 上一次报告缺少以下模块，请确保本次包含:
{chr(10).join([f'- {s}' for s in missing_sections])}
"""

        # 格式化证据图信息
        evidence_info = self._format_evidence_for_chair(evidence_graph)

        task_prompt = f"""
请作为 MTB 主席，汇总整合以下专家报告生成最终 MTB 报告。

**核心原则: 汇总整合，不是摘要压缩！**
- 保留所有专家报告中的关键发现
- 保留所有临床试验推荐
- 保留完整的治疗史记录
- 保留所有分子特征和证据等级
- 输出应包含完整的信息
- **使用证据图中的引用**（见下方证据图统计和引用列表）

{regenerate_note}{evidence_info}

---

**病历原文**:
{raw_pdf_text}

---

**病理学分析报告** (完整):
{pathologist_report}

---

**分子分析报告** (完整):
{geneticist_report}

---

**临床试验推荐** (完整):
{recruiter_report}

---

**治疗方案** (完整):
{oncologist_plan}

---

**必须包含的 12 个模块**:
{chr(10).join([f'{i+1}. {s}' for i, s in enumerate(REQUIRED_SECTIONS)])}

**关键要求**:
1. 报告必须包含**全部 12 个模块**，按顺序排列
2. 第4模块"治疗史回顾"必须使用:::timeline格式展示**所有治疗记录**（不要合并或省略）
3. 第9模块"临床试验推荐"必须保留临床试验专员报告中的**所有试验**（至少Top 5）
4. **禁止压缩、合并、简化**任何治疗记录或试验信息
5. 每条建议都需要证据等级标注 [Evidence A/B/C/D/E]
6. 必须包含"不建议"章节
7. 仲裁原则：当安全性与疗效冲突时，以安全性为准
8. 所有引用使用 [PMID: xxx] 或 [NCT xxx] 格式
9. 整合病理学分析报告中的关键发现（病理类型、IHC解读等）

**信息完整性要求**:
- Gemini 支持 66K Tokens输出
- 请充分利用输出长度，确保报告完整详尽
- 宁可信息冗余，不可遗漏关键内容

请生成完整的 Markdown 格式 MTB 报告。
"""

        result = self.invoke(task_prompt)

        # 程序化补充 LLM 未引用的 evidence graph 证据
        enriched_output = self._inject_missing_citations(result["output"], evidence_graph)

        # 合并所有引用（Chair 生成的 + 证据图中的）
        all_references = result["references"] or []

        # 从证据图中提取引用，合并去重
        if evidence_graph and evidence_graph.entities:
            seen_ids = {ref.get("id") for ref in all_references if ref.get("id")}
            provenances = evidence_graph.get_all_provenances()
            for prov_info in provenances:
                prov = prov_info.get("provenance")
                if prov and prov not in seen_ids:
                    ref_entry = {
                        "id": prov,
                        "url": prov_info.get("source_url") or "",
                    }
                    all_references.append(ref_entry)
                    seen_ids.add(prov)

        # 生成完整报告（含工具调用详情和引用）
        full_report = self.generate_full_report(
            main_content=enriched_output,
            title="MTB Chair Final Synthesis Report"
        )

        return {
            "synthesis": enriched_output,
            "references": all_references,
            "full_report_md": full_report
        }


if __name__ == "__main__":
    print("ChairAgent 模块加载成功")
    print(f"必选模块数量: {len(REQUIRED_SECTIONS)}")
