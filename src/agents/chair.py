"""
Chair Agent（MTB 主席）
"""
from typing import Dict, Any, List, Optional
from collections import Counter

from src.agents.base_agent import BaseAgent
from src.tools.guideline_tools import NCCNTool, FDALabelTool
from src.tools.literature_tools import PubMedTool
from src.models.evidence_graph import EvidenceGraph
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

    def _format_evidence_for_chair(self, evidence_graph: Optional[EvidenceGraph]) -> str:
        """
        将证据图格式化为 Chair 可用的文本

        生成：
        1. 证据统计摘要（按类型/Agent/等级分布）
        2. 完整引用列表（包含 URL、provenance、等级）

        Args:
            evidence_graph: 证据图对象

        Returns:
            格式化的证据图文本
        """
        if not evidence_graph or not evidence_graph.nodes:
            return ""

        nodes = list(evidence_graph.nodes.values())

        # 统计
        type_counts = Counter(n.evidence_type.value for n in nodes)
        agent_counts = Counter(n.source_agent for n in nodes)
        grade_counts = Counter(n.grade.value if n.grade else "Unknown" for n in nodes)

        # 构建统计摘要
        stats = f"""
## 证据图统计
- **总证据数**: {len(nodes)}
- **按类型**: {', '.join(f'{k}({v})' for k, v in type_counts.most_common())}
- **按Agent**: {', '.join(f'{k}({v})' for k, v in agent_counts.most_common())}
- **按等级**: {', '.join(f'{k}({v})' for k, v in sorted(grade_counts.items()))}
"""

        # 构建引用列表（只包含有 URL 或 provenance 的证据）
        refs_with_url = [n for n in nodes if n.source_url or n.provenance]

        if refs_with_url:
            ref_lines = ["\n## 完整引用列表（务必在报告中引用这些来源）\n"]
            ref_lines.append("| 类型 | 等级 | 来源Agent | 工具 | Provenance | URL |")
            ref_lines.append("|------|------|-----------|------|------------|-----|")

            for n in refs_with_url:
                ev_type = n.evidence_type.value
                grade = n.grade.value if n.grade else "-"
                agent = n.source_agent
                tool = n.source_tool or "-"
                prov = n.provenance or "-"
                url = n.source_url or "-"
                # 截断 URL 以便显示
                url_display = url[:50] + "..." if len(url) > 50 else url
                ref_lines.append(f"| {ev_type} | {grade} | {agent} | {tool} | {prov} | {url_display} |")

            stats += "\n".join(ref_lines)

        return stats

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
5. 每条建议都需要证据等级标注 [Evidence A/B/C/D]
6. 必须包含"不建议"章节
7. 仲裁原则：当安全性与疗效冲突时，以安全性为准
8. 所有引用使用 [PMID: xxx] 或 [NCT xxx] 格式
9. 整合病理学分析报告中的关键发现（病理类型、IHC解读等）

**信息完整性要求**:
- Gemini 支持 8000-12000 字符输出
- 请充分利用输出长度，确保报告完整详尽
- 宁可信息冗余，不可遗漏关键内容

请生成完整的 Markdown 格式 MTB 报告。
"""

        result = self.invoke(task_prompt)

        # 合并所有引用（Chair 生成的 + 证据图中的）
        all_references = result["references"] or []

        # 从证据图中提取引用，合并去重
        if evidence_graph and evidence_graph.nodes:
            seen_ids = {ref.get("id") for ref in all_references if ref.get("id")}
            for node in evidence_graph.nodes.values():
                if node.provenance and node.provenance not in seen_ids:
                    ref_entry = {
                        "type": node.evidence_type.value,
                        "id": node.provenance,
                        "url": node.source_url or "",
                        "grade": node.grade.value if node.grade else None,
                        "source_agent": node.source_agent
                    }
                    all_references.append(ref_entry)
                    seen_ids.add(node.provenance)

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
