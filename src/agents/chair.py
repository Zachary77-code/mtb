"""
Chair Agent（MTB 主席）
"""
from typing import Dict, Any, List, Optional

from src.agents.base_agent import BaseAgent
from src.tools.guideline_tools import NCCNTool, FDALabelTool
from src.tools.literature_tools import PubMedTool
from src.models.evidence_graph import EvidenceGraph, EntityType, Predicate, EvidenceGrade
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

    def _format_evidence_for_chair(self, evidence_graph: Optional[EvidenceGraph]) -> str:
        """
        将证据图格式化为 Chair 可用的完整文本

        输出：
        1. 证据统计摘要（按实体类型/Agent/等级分布）
        2. 所有实体及其全部 Observation（按类型分组，含所有字段）
        3. 所有边关系及其 Observation（按谓词重要性排序）
        4. 矛盾/冲突证据
        5. 完整引用列表（含 statement、source_tool、evidence_grade 等）

        Args:
            evidence_graph: 证据图对象

        Returns:
            格式化的证据图文本
        """
        if not evidence_graph or not evidence_graph.entities:
            return ""

        # ===== 1. 统计摘要 =====
        summary = evidence_graph.summary()
        agent_summary = evidence_graph.summary_by_agent()

        entity_type_str = ', '.join(f'{k}({v})' for k, v in summary.get('entities_by_type', {}).items())
        agent_str = ', '.join(f'{k}({v["observation_count"]})' for k, v in agent_summary.items())
        grade_str = ', '.join(f'{k}({v})' for k, v in sorted(summary.get('best_grades', {}).items()))

        parts = [f"""
## 证据图统计
- **总实体数**: {summary.get('total_entities', 0)}
- **总边数**: {summary.get('total_edges', 0)}
- **总观察数**: {summary.get('total_observations', 0)}
- **按实体类型**: {entity_type_str}
- **按Agent观察数**: {agent_str}
- **按等级**: {grade_str}
"""]

        # ===== 2. 所有实体与观察（按类型分组）=====
        type_order = [
            EntityType.VARIANT, EntityType.GENE, EntityType.DRUG,
            EntityType.DISEASE, EntityType.BIOMARKER, EntityType.TRIAL,
            EntityType.GUIDELINE, EntityType.PATHWAY, EntityType.REGIMEN,
            EntityType.FINDING
        ]

        parts.append("\n## 关键实体与观察\n")

        for etype in type_order:
            entities = evidence_graph.get_entities_by_type(etype)
            if not entities:
                continue

            parts.append(f"\n### [{etype.value}]\n")

            for entity in entities:
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
                parts.append("")  # 空行分隔

        # ===== 3. 所有边关系与观察 =====
        predicate_order = [
            Predicate.SENSITIZES, Predicate.CAUSES_RESISTANCE,
            Predicate.TREATS, Predicate.RECOMMENDS,
            Predicate.EVALUATES, Predicate.BIOMARKER_FOR,
            Predicate.CONTRAINDICATED_FOR, Predicate.INTERACTS_WITH,
            Predicate.SUPPORTS, Predicate.CONTRADICTS,
            Predicate.ACTIVATES, Predicate.INHIBITS,
            Predicate.BINDS, Predicate.REGULATES,
            Predicate.ASSOCIATED_WITH, Predicate.MEMBER_OF,
            Predicate.EXPRESSED_IN, Predicate.INCLUDES_ARM,
            Predicate.CITES, Predicate.DERIVED_FROM,
            Predicate.PHOSPHORYLATES, Predicate.AMPLIFIES,
            Predicate.MUTATES_TO,
        ]
        predicate_rank = {p: i for i, p in enumerate(predicate_order)}

        edges_with_obs = [
            e for e in evidence_graph.edges.values() if e.observations
        ]
        edges_with_obs.sort(key=lambda e: predicate_rank.get(e.predicate, 999))

        if edges_with_obs:
            parts.append("\n## 关键关系（含观察）\n")

            for edge in edges_with_obs:
                source = evidence_graph.get_entity(edge.source_id)
                target = evidence_graph.get_entity(edge.target_id)
                source_name = source.name if source else edge.source_id
                target_name = target.name if target else edge.target_id
                pred_str = edge.predicate.value if edge.predicate else "?"
                conf_str = f" (confidence: {edge.confidence:.2f})" if edge.confidence else ""

                parts.append(f"### {source_name} → {pred_str} → {target_name}{conf_str}")

                obs_sorted = sorted(
                    edge.observations,
                    key=lambda o: self._grade_sort_key(o.evidence_grade)
                )
                for obs in obs_sorted:
                    parts.append(self._format_observation(obs))
                parts.append("")

        # ===== 4. 矛盾/冲突证据 =====
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

        # ===== 5. 完整引用列表（含所有字段）=====
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
            main_content=result["output"],
            title="MTB Chair Final Synthesis Report"
        )

        return {
            "synthesis": result["output"],
            "references": all_references,
            "full_report_md": full_report
        }


if __name__ == "__main__":
    print("ChairAgent 模块加载成功")
    print(f"必选模块数量: {len(REQUIRED_SECTIONS)}")
