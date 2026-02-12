"""
Research Mixin - BFRS/DFRS 研究能力 (DeepEvidence Style)

为现有 Agent 提供 BFRS（广度优先研究）和 DFRS（深度优先研究）能力。
使用实体中心的证据图架构，将发现分解为 Entity + Edge + Observation。
"""
import json
import re
from typing import Dict, List, Any, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass

from src.models.evidence_graph import (
    EvidenceGraph,
    Observation,
    EntityType,
    EvidenceGrade,
    EvidenceType,
    Predicate,
    load_evidence_graph
)
from src.models.entity_extractors import extract_entities_from_finding
from src.tools.graph_query_tool import GraphQueryTool
from src.models.research_plan import (
    ResearchPlan,
    ResearchDirection,
    ResearchMode,
    DirectionStatus,
    load_research_plan
)
from src.utils.logger import mtb_logger as logger, log_separator

if TYPE_CHECKING:
    from src.agents.base_agent import BaseAgent


@dataclass
class ResearchResult:
    """单次研究迭代的结果"""
    findings: List[Dict[str, Any]]      # 发现列表
    entity_ids: List[str]             # 添加到图中的实体 canonical_id 列表
    directions_updated: List[str]       # 更新状态的方向 ID
    research_complete: bool             # 是否完成研究
    needs_deep_research: List[str]      # 需要深入研究的发现
    summary: str                        # 摘要


class ResearchMixin:
    """
    研究能力混入类 (DeepEvidence Style)

    为 Agent 添加 BFRS/DFRS 研究能力。
    使用实体中心架构：发现 -> LLM提取 -> Entity + Edge + Observation
    要求宿主类继承自 BaseAgent。
    """

    def research_iterate(
        self,
        mode: ResearchMode,
        directions: List[Dict[str, Any]],
        evidence_graph: Dict[str, Any],
        iteration: int,
        max_iterations: int,
        case_context: str,
        research_plan: Optional[Dict[str, Any]] = None,
        phase_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行一轮研究迭代

        Args:
            mode: 研究模式 (breadth_first / depth_first) - 仅作为默认值，
                  实际使用每个方向的 preferred_mode
            directions: 分配给此 Agent 的研究方向
            evidence_graph: 当前证据图（序列化格式）
            iteration: 当前迭代轮次
            max_iterations: 最大迭代次数
            case_context: 病例上下文
            research_plan: 研究计划（序列化格式）
            phase_context: 阶段上下文（可选），包含 current_phase, phase_description,
                          current_iteration, max_iterations, agent_mode, 
                          agent_role_in_phase, iteration_feedback

        Returns:
            研究结果字典
        """
        # 确保 self 是 BaseAgent 实例
        if not hasattr(self, 'invoke') or not hasattr(self, 'role'):
            raise TypeError("ResearchMixin requires host class to inherit from BaseAgent")

        agent_role = getattr(self, 'role', 'Unknown')

        # 增强日志输出
        log_separator(agent_role)
        logger.info(f"[{agent_role}] 研究迭代 {iteration + 1}/{max_iterations}")

        # 加载证据图和研究计划
        graph = load_evidence_graph(evidence_graph)
        plan = load_research_plan(research_plan) if research_plan else None

        # 绑定 GraphQueryTool 到当前证据图
        graph_tool = self._ensure_graph_query_tool()
        graph_tool.set_graph(graph)

        # 按 preferred_mode 分组方向 (新逻辑)
        bfrs_directions = []
        dfrs_directions = []
        skip_directions = []

        for d in directions:
            preferred_mode = d.get("preferred_mode", mode.value if mode else "breadth_first")
            if preferred_mode == "skip":
                skip_directions.append(d)
            elif preferred_mode == "depth_first":
                dfrs_directions.append(d)
            else:  # 默认 breadth_first
                bfrs_directions.append(d)

        logger.info(f"[{agent_role}] 方向分组: BFRS={len(bfrs_directions)}, DFRS={len(dfrs_directions)}, Skip={len(skip_directions)}")

        # 如果所有方向都 skip，直接返回
        if not bfrs_directions and not dfrs_directions:
            logger.info(f"[{agent_role}] 所有方向已完成，跳过本轮迭代")
            return {
                "evidence_graph": graph.to_dict(),
                "research_plan": plan.to_dict() if plan else None,
                "new_entity_ids": [],
                "direction_updates": {},
                "research_complete": True,
                "needs_deep_research": [],
                "summary": "所有分配方向已完成，无需继续研究",
                "raw_output": "",
                "tool_call_report": ""
            }

        # 收集所有结果
        all_findings = []
        all_direction_updates = {}
        all_needs_deep = []
        all_summaries = []
        all_outputs = []
        all_tool_call_reports = []  # 收集每阶段的工具调用报告
        all_tool_call_records = []  # 原始工具调用记录（dict 列表）
        all_agent_analysis = []     # JSON 外的分析文本
        all_per_direction_analysis = {}  # 各方向研究分析
        all_new_entity_ids = []         # 两阶段合并的新实体 ID
        all_extraction_details = []     # 两阶段合并的提取详情

        # 逐方向处理：每个方向独享工具调用预算，完成后立即提取实体入图
        def _process_direction(direction: Dict[str, Any], dir_mode: str, phase_label: str, research_mode: ResearchMode, max_tool_rounds: int):
            """处理单个方向的研究迭代"""
            d_id = direction.get('id', '?')
            d_topic = direction.get('topic', '?')
            logger.info(f"[{agent_role}] {phase_label} 方向 {d_id}: {d_topic} (max {max_tool_rounds} 轮)")

            prompt = self._build_direction_prompt(
                direction=direction,
                mode=dir_mode,
                all_directions=directions,
                graph=graph,
                iteration=iteration,
                max_iterations=max_iterations,
                case_context=case_context,
                phase_context=phase_context
            )
            result = self.invoke(prompt, max_tool_iterations=max_tool_rounds)  # type: ignore

            # 捕获工具调用报告
            tool_report = self.get_tool_call_report()  # type: ignore
            if tool_report:
                all_tool_call_reports.append(f"### {phase_label} {d_id} 工具调用\n{tool_report}")

            # 捕获原始 tool call records（标记 phase + direction_id）
            for record in getattr(self, 'tool_call_history', []):
                all_tool_call_records.append({
                    "tool_name": record.tool_name,
                    "parameters": record.parameters,
                    "reasoning": record.reasoning,
                    "result": record.result,
                    "timestamp": record.timestamp,
                    "phase": phase_label,
                    "direction_id": d_id,
                    "round_number": record.round_number,
                    "round_content": record.round_content,
                })

            # 解析输出
            output = result.get("output", "")
            all_outputs.append(output)
            parsed = self._parse_research_output(output, research_mode)
            parsed_findings = parsed.get("findings", [])
            all_findings.extend(parsed_findings)
            all_direction_updates.update(parsed.get("direction_updates", {}))
            all_needs_deep.extend(parsed.get("needs_deep_research", []))
            if parsed.get("summary"):
                all_summaries.append(f"[{phase_label} {d_id}] {parsed['summary']}")
            analysis = parsed.get("agent_analysis", "")
            if analysis:
                all_agent_analysis.append(f"[{phase_label} {d_id}] {analysis}")
            all_per_direction_analysis.update(parsed.get("per_direction_analysis", {}))

            # 立即实体提取 → 后续方向可查到本方向新发现
            if parsed_findings:
                nonlocal plan
                entity_ids, plan, extraction = self._update_evidence_graph(
                    graph=graph, findings=parsed_findings,
                    agent_role=agent_role, iteration=iteration, mode=mode, plan=plan
                )
                all_new_entity_ids.extend(entity_ids)
                all_extraction_details.extend(extraction)
                logger.info(f"[{agent_role}] {phase_label} {d_id}: {len(entity_ids)} 新实体入图")

        # BFRS 方向：逐方向执行，每方向 3 轮
        for direction in bfrs_directions:
            _process_direction(direction, "bfrs", "BFRS", ResearchMode.BREADTH_FIRST, max_tool_rounds=3)

        # DFRS 方向：逐方向执行，每方向 5 轮
        for direction in dfrs_directions:
            _process_direction(direction, "dfrs", "DFRS", ResearchMode.DEPTH_FIRST, max_tool_rounds=5)

        # 增强结果日志
        logger.info(f"[{agent_role}] 迭代完成:")
        logger.info(f"[{agent_role}]   发现数: {len(all_findings)}")
        logger.info(f"[{agent_role}]   新实体: {len(all_new_entity_ids)}")
        if all_direction_updates:
            logger.info(f"[{agent_role}]   方向更新: {all_direction_updates}")
        if all_needs_deep:
            logger.info(f"[{agent_role}]   需深入研究: {len(all_needs_deep)} 项")
        combined_summary = " | ".join(all_summaries) if all_summaries else ""
        if combined_summary:
            summary_short = combined_summary[:100] + "..." if len(combined_summary) > 100 else combined_summary
            logger.info(f"[{agent_role}]   摘要: {summary_short}")

        return {
            "evidence_graph": graph.to_dict(),
            "research_plan": plan.to_dict() if plan else None,
            "new_entity_ids": all_new_entity_ids,
            "direction_updates": all_direction_updates,
            "research_complete": len(bfrs_directions) == 0 and len(dfrs_directions) == 0,
            "needs_deep_research": all_needs_deep,
            "summary": combined_summary,
            "raw_output": "\n---\n".join(all_outputs),
            "tool_call_report": "\n\n".join(all_tool_call_reports),
            "tool_call_records": all_tool_call_records,
            "extraction_details": all_extraction_details,
            "agent_analysis": "\n\n".join(all_agent_analysis),
            "per_direction_analysis": all_per_direction_analysis,
        }

    def _ensure_graph_query_tool(self) -> GraphQueryTool:
        """确保 GraphQueryTool 已注册到 agent 的 tools 列表，返回实例。幂等操作。"""
        existing = getattr(self, 'tool_registry', {}).get('query_evidence_graph')
        if existing and isinstance(existing, GraphQueryTool):
            return existing

        graph_tool = GraphQueryTool()
        if not hasattr(self, 'tools') or self.tools is None:
            self.tools = []
        self.tools.append(graph_tool)
        if hasattr(self, 'tool_registry'):
            self.tool_registry[graph_tool.name] = graph_tool
        else:
            self.tool_registry = {graph_tool.name: graph_tool}

        return graph_tool

    def _build_direction_anchor_context(
        self,
        directions: List[Dict[str, Any]],
        graph: EvidenceGraph,
        mode: str = "bfrs"
    ) -> str:
        """为每个方向构建锚节点上下文（含实体+关系边，无截断）

        Args:
            directions: 方向列表
            graph: 证据图
            mode: 研究模式，"bfrs" 或 "dfrs"。DFRS 使用 3 hop 扩展，BFRS 使用 2 hop
        """
        max_hops = 3 if mode == "dfrs" else 2

        sections = []
        for d in directions:
            entity_ids = d.get('entity_ids', [])
            dir_id = d.get('id', '?')
            topic = d.get('topic', '未命名')

            if not entity_ids:
                sections.append(f"### {dir_id} ({topic})\n尚无已知实体")
                continue

            logger.info(f"[SUBGRAPH] 方向 {dir_id}: 锚点数={len(entity_ids)}, max_hops={max_hops}, mode={mode}")

            subgraph = graph.retrieve_subgraph(
                anchor_ids=entity_ids,
                max_hops=max_hops,
                include_observations=False
            )

            entities = subgraph.get('entities', [])
            edges = subgraph.get('edges', [])

            logger.info(f"[SUBGRAPH] 方向 {dir_id}: 扩展结果 entities={len(entities)}, edges={len(edges)}")

            # 日志：hop 分布
            hop_map = subgraph.get('hop_map', {})
            hop_dist = {}
            for _, hop in hop_map.items():
                hop_dist[hop] = hop_dist.get(hop, 0) + 1
            logger.debug(f"[SUBGRAPH] 方向 {dir_id}: hop分布={hop_dist}")

            if not entities:
                sections.append(f"### {dir_id} ({topic})\n尚无已知实体")
                continue

            # 实体行: 全量，含等级
            entity_strs = [
                f"{e['canonical_id']}({e['observation_count']}obs"
                + (f",{e['best_grade']}" if e.get('best_grade') else "")
                + ")"
                for e in entities
            ]
            entity_line = f"实体 ({len(entities)}): {', '.join(entity_strs)}"

            # 关系边行: 全量，含 confidence
            dir_lines = [f"### {dir_id} ({topic})", entity_line]
            if edges:
                edge_strs = []
                for e in edges:
                    conf = f" ({e['confidence']:.2f})" if e.get('confidence') else ""
                    edge_strs.append(
                        f"  {e['source_id']} → {e['predicate']} → {e['target_id']}{conf}"
                    )
                dir_lines.append(f"关系 ({len(edges)}):")
                dir_lines.extend(edge_strs)

            sections.append("\n".join(dir_lines))

        return "\n\n".join(sections) if sections else "尚无已知实体信息"

    def _build_other_directions_summary(
        self,
        current_direction_id: str,
        all_directions: List[Dict[str, Any]],
    ) -> str:
        """为非当前方向生成一行摘要（防重复研究）"""
        lines = []
        for d in all_directions:
            if d.get('id') == current_direction_id:
                continue
            topic = d.get('topic', '?')
            status = d.get('status', 'pending')
            preferred_mode = d.get('preferred_mode', 'breadth_first')
            entity_count = len(d.get('entity_ids', []))
            lines.append(f"- {d.get('id')} ({topic}): {entity_count} 实体, mode={preferred_mode}, status={status}")
        return "\n".join(lines) if lines else "（无其他方向）"

    def _build_direction_prompt(
        self,
        direction: Dict[str, Any],
        mode: str,  # "bfrs" or "dfrs"
        all_directions: List[Dict[str, Any]],
        graph: EvidenceGraph,
        iteration: int,
        max_iterations: int,
        case_context: str,
        phase_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        构建单方向研究提示（统一 BFRS/DFRS）

        Args:
            direction: 当前聚焦的研究方向
            mode: "bfrs" 或 "dfrs"
            all_directions: 所有方向（用于生成其他方向概况）
            graph: 当前证据图
            iteration: 当前迭代轮次
            max_iterations: 最大迭代次数
            case_context: 病例上下文
        """
        agent_role = getattr(self, 'role', 'Agent')
        dir_id = direction.get('id', '?')
        is_dfrs = (mode == "dfrs")
        is_phase3 = (phase_context.get('current_phase') == 'phase_3') if phase_context else False
        mode_label = "DFRS (深度优先研究)" if is_dfrs else "BFRS (广度优先研究)"
        tool_rounds = 5 if is_dfrs else 3
        tool_rounds_hint = "3-5" if is_dfrs else "2-3"

        # 本方向详情
        direction_detail = f"""### 方向 {dir_id}: {direction.get('topic', '未命名')}
- 目标模块: {', '.join(direction.get('target_modules', []))}
- 优先级: {direction.get('priority', 3)}
- 建议查询: {', '.join(direction.get('queries', []))}
- 完成标准: {direction.get('completion_criteria', '')}
- 当前状态: {direction.get('status', 'pending')}"""

        # DFRS 额外信息：深入研究原因和具体问题
        dfrs_section = ""
        if is_dfrs:
            findings_list = direction.get('deep_research_findings', [])
            findings_text = ""
            if findings_list:
                findings_text = "\n" + "\n".join(f"  - {f}" for f in findings_list)

            mode_reason = direction.get('mode_reason', '')
            mode_reason_text = f"\n- PlanAgent 评估指示: {mode_reason}" if mode_reason else ""

            dfrs_section = f"""
- 需要深入的原因: {direction.get('depth_research_reason', '需要更多证据')}{mode_reason_text}
- 具体待研究问题:{findings_text if findings_text else ' 请基于方向主题深入'}
- 已有证据 ID: {direction.get('entity_ids', [])}"""

        # 本方向锚节点上下文（DFRS 用 3 hop，BFRS 用 2 hop）
        anchor_context = self._build_direction_anchor_context([direction], graph, mode=mode)

        # 其他方向概况
        other_summary = self._build_other_directions_summary(dir_id, all_directions)

        total_entities = len(graph.entities) if graph.entities else 0
        total_edges = len(graph.edges) if graph.edges else 0

        # 执行指南（BFRS vs DFRS）
        if is_dfrs:
            guide = f"""### DFRS 执行指南
1. 你有 **{tool_rounds} 轮工具调用预算**（建议 {tool_rounds_hint} 轮），深入追踪证据链

**假设-验证研究策略**:
- **Step 1 (分析)**: 基于病例背景和已有证据图，针对本方向提出 2-3 个可验证的研究假设
  - 关注潜在的药物联系、安全风险、治疗机会
  - 假设应具体、可通过工具验证
- **Step 2 (验证)**: 使用工具逐一验证假设
  - 每个假设至少调用 1 个工具
  - 记录阳性结果（支持假设）和阴性结果（否定假设）
- **Step 3 (深化)**: 对验证通过的重要发现，追踪引用链和关联研究
  - 追踪引用链、相关研究、机制解释
  - 寻找更高级别的证据支持（A > B > C > D > E）

**深度推理重点**:
- 识别实体间的潜在联系（变异-药物、药物-药物、通路-疗效）
- 推理可能的副作用和药物相互作用
- 探索非显而易见的治疗机会（跨适应症、联合方案）"""
        else:
            guide = f"""### BFRS 执行指南
1. 你有 **{tool_rounds} 轮工具调用预算**（建议 {tool_rounds_hint} 轮），请高效利用

**广度研究策略**:
- 收集广泛的初步证据，不深入追踪单个发现
- 但在搜索前，先思考该方向可能存在哪些潜在联系
- 为方向标记状态: pending（需继续）/ completed（已充分）
- 标记需要深入研究的重要发现和未验证的假设"""

        # Build phase context section
        phase_context_section = ""
        if phase_context:
            phase_context_section = f"""
### 阶段上下文 [Phase Context]
- 当前阶段: {phase_context.get('current_phase', 'unknown')} ({phase_context.get('phase_description', '')})
- 当前迭代: {phase_context.get('current_iteration', '?')}/{phase_context.get('max_iterations', '?')}
- Agent 模式: {phase_context.get('agent_mode', 'research')}
- 阶段角色: {phase_context.get('agent_role_in_phase', '')}
- 输出格式: {phase_context.get('output_format', 'json')}
"""
            feedback = phase_context.get('iteration_feedback', '')
            if feedback:
                phase_context_section += f"\n### 迭代反馈 [Iteration Feedback]\n{feedback}\n"

        return f"""## 研究模式: {mode_label}

### 当前迭代信息
- 迭代轮次: {iteration + 1} / {max_iterations}
- 你的角色: {agent_role}
- 证据图概况: {total_entities} 个实体, {total_edges} 条关系

{phase_context_section}
### 你的研究方向（本次聚焦）
{direction_detail}{dfrs_section}

### 本方向已知信息
{anchor_context}

### 其他方向概况（仅供参考，避免重复工作）
{other_summary}

### 证据图查询工具 (query_evidence_graph)
你可以使用 `query_evidence_graph` 工具查询证据图中已知的信息。
**重要**: 在调用外部工具（PubMed、CIViC 等）之前，必须先查图里已有信息！
{'**提示**: BFRS 阶段发现的新实体已入图，可直接查询！' if is_dfrs else ''}

用法:
- `search_entities`: 搜索图中实体（基因、药物、变异等）
- `get_entity_detail`: 查看某实体的完整观察和关系
- `get_neighborhood`: 从锚点实体出发 BFS 探索邻域
- `get_treatment_evidence`: 查看治疗相关证据

如果返回 "Not found"，说明图中尚无此信息 → 转用外部工具搜索。

### 病例背景
{case_context}

{guide}

### 输出格式
请以 JSON 格式输出研究结果（direction_id 固定为 "{dir_id}"）:

```json
{{{{
    "summary": "本轮研究摘要",
    "findings": [
        {{{{
            "direction_id": "{dir_id}",
            "content": "发现内容（完整详细，不限长度）",
            "evidence_type": "molecular|clinical|pathology|imaging|guideline|drug|drug_interaction|pharmacokinetics|comorbidity|organ_function|allergy|surgical|radiation|interventional|trial|nutrition|cam_evidence|safety|literature",
            "grade": "A|B|C|D|E",
            "civic_type": "predictive|diagnostic|prognostic|predisposing|oncogenic",
            "source_tool": "你实际调用的工具名称（必填，严禁留空）",
            "gene": "基因名（如有）",
            "variant": "变异名（如有）",
            "drug": "药物名（如有）",
            "pmid": "PubMed ID（如有，仅填数字，必须来自工具返回结果）",
            "nct_id": "NCT ID（如有，含NCT前缀，必须来自工具返回结果）",
            "url": "来源 URL（如有，PubMed/ClinicalTrials/GDC/CIViC 页面链接）",
            {"\"l_tier\": \"L1|L2|L3|L4|L5（Phase 3 必填，描述证据分层）\"," if is_phase3 else ""}
            {"\"l_tier_reasoning\": \"L1→L5 降级搜索过程描述（Phase 3 必填）\"," if is_phase3 else ""}
            {"\"depth_chain\": [\"引用1\", \"引用2\", \"推理步骤\"]," if is_dfrs else ""}
            "entities": [{{{{ "canonical_id": "GENE:EGFR", "entity_type": "gene|variant|drug|disease|pathway|biomarker|regimen|finding", "name": "EGFR", "aliases": ["ErbB1"] }}}}],
            "relationships": [{{{{ "source_id": "GENE:EGFR", "target_id": "DRUG:OSIMERTINIB", "predicate": "RESPONDS_TO|TREATS|INTERACTS_WITH|ASSOCIATED_WITH", "confidence": 0.9 }}}}]
        }}}}
    ],
    "direction_updates": {{{{
        "{dir_id}": "pending|completed"
    }}}},
    "needs_deep_research": [
        {{{{
            "direction_id": "{dir_id}",
            "finding": "需要深入的发现描述",
            "reason": "为什么需要深入研究"
        }}}}
    ],
    "per_direction_analysis": {{{{
        "{dir_id}": {{{{
            "research_question": "本轮需要解决的核心研究问题",
            "hypotheses_explored": [
                {{{{
                    "hypothesis": "提出的假设",
                    "validation_tool": "用于验证的工具",
                    "result": "validated|refuted|inconclusive",
                    "detail": "验证结果详情"
                }}}}
            ],
            "tools_used": "使用了哪些工具和查询关键词",
            "what_found": "找到了哪些关键证据",
            "what_not_found": "没找到什么 / 未能解决的问题（包括被否定的假设）",
            "new_questions": "是否产生了新的研究问题",
            "conclusion": "该方向的当前结论"
        }}}}
    }},
    "research_complete": false
}}}}
```

**⚠️ 工具来源强制规则**:
- 每条 finding 必须来自你在本轮中实际调用的外部工具（search_pubmed, search_nccn, search_civic, search_gdc, search_clinical_trials, search_fda_labels, search_rxnorm 等）
- source_tool 必须填写你实际调用的工具名，严禁留空或填写 "unknown"
- 严禁基于你的内部知识编撰 findings，即使你认为内容正确
- pmid/nct_id 必须是工具返回的真实编号，严禁凭记忆编造
- 如果工具未返回足够结果，请在 per_direction_analysis.what_not_found 中记录缺口，而非自行补充

**证据等级说明 (CIViC Evidence Level)**:
- A: Validated - 已验证，多项独立研究或 meta 分析支持
- B: Clinical - 临床证据，来自临床试验或大规模临床研究
- C: Case Study - 病例研究，来自个案报道或小规模病例系列
- D: Preclinical - 临床前证据，来自细胞系、动物模型等实验
- E: Inferential - 推断性证据，间接证据或基于生物学原理的推断

**CIViC 证据类型说明**:
- predictive: 预测性 - 预测对某种治疗的反应
- diagnostic: 诊断性 - 用于疾病诊断
- prognostic: 预后性 - 与疾病预后相关
- predisposing: 易感性 - 与癌症风险相关
- oncogenic: 致癌性 - 变异的致癌功能

请开始执行{'深度优先' if is_dfrs else '广度优先'}研究。
"""

    def _parse_research_output(self, output: str, mode: ResearchMode) -> Dict[str, Any]:
        """解析研究输出，同时提取 JSON 和 agent 分析文本"""
        import re
        agent_analysis = ""

        # 尝试提取 ```json ... ``` 格式
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', output)
        if json_match:
            before = output[:json_match.start()].strip()
            after = output[json_match.end():].strip()
            agent_analysis = f"{before}\n\n{after}".strip()
            try:
                parsed = json.loads(json_match.group(1).strip())
                parsed["agent_analysis"] = agent_analysis
                return parsed
            except json.JSONDecodeError:
                pass

        # 尝试直接解析 { ... } 格式
        brace_match = re.search(r'\{[\s\S]*\}', output)
        if brace_match:
            before = output[:brace_match.start()].strip()
            after = output[brace_match.end():].strip()
            agent_analysis = f"{before}\n\n{after}".strip()
            try:
                parsed = json.loads(brace_match.group(0))
                parsed["agent_analysis"] = agent_analysis
                return parsed
            except json.JSONDecodeError:
                pass

        # 解析失败，返回默认结构
        logger.warning(f"[ResearchMixin] JSON 解析失败，使用默认结构")
        return {
            "summary": output if output else "无摘要",
            "findings": [],
            "direction_updates": {},
            "needs_deep_research": [],
            "per_direction_analysis": {},
            "research_complete": False,
            "agent_analysis": output or ""
        }

    # 统一 evidence_type 枚举值
    VALID_EVIDENCE_TYPES = {
        "molecular", "clinical", "pathology", "imaging", "guideline", "drug",
        "drug_interaction", "pharmacokinetics", "comorbidity", "organ_function",
        "allergy", "surgical", "radiation", "interventional", "trial",
        "nutrition", "cam_evidence", "safety", "literature",
    }
    # 常见非标准值 → 标准值映射
    EVIDENCE_TYPE_ALIASES = {
        "interaction": "drug_interaction",
        "gene": "molecular",
        "variant": "molecular",
        "genomic": "molecular",
        "genetic": "molecular",
        "pharma": "pharmacokinetics",
        "pk": "pharmacokinetics",
        "surgery": "surgical",
        "radiotherapy": "radiation",
        "ablation": "interventional",
        "cam": "cam_evidence",
        "alternative": "cam_evidence",
        "integrative": "cam_evidence",
        "nccn": "guideline",
        "fda": "drug",
    }

    @staticmethod
    def _normalize_evidence_type(raw: str) -> str:
        """归一化 evidence_type 到标准枚举值"""
        if not raw:
            return "literature"
        lower = raw.lower().strip()
        if lower in ResearchMixin.VALID_EVIDENCE_TYPES:
            return lower
        if lower in ResearchMixin.EVIDENCE_TYPE_ALIASES:
            return ResearchMixin.EVIDENCE_TYPE_ALIASES[lower]
        return "literature"  # fallback

    def _update_evidence_graph(
        self,
        graph: EvidenceGraph,
        findings: List[Dict[str, Any]],
        agent_role: str,
        iteration: int,
        mode: ResearchMode,
        plan: Optional[ResearchPlan] = None
    ) -> Tuple[List[str], Optional[ResearchPlan], List[Dict[str, Any]]]:
        """
        更新证据图并同步更新研究计划中的方向证据关联

        DeepEvidence Style 实体提取策略:
        - 使用 LLM 将 finding 分解为 Entity + Edge + Observation
        - 实体通过 canonical_id 合并（不创建重复）
        - Observation 附加到 Entity 和 Edge

        Returns:
            (新增/更新的实体 canonical_id 列表, 更新后的研究计划, per-finding 提取详情)
        """
        new_entity_ids = []
        extraction_details = []
        existing_entities = graph.get_entity_index()

        for finding in findings:
            # 归一化 evidence_type
            if "evidence_type" in finding:
                finding["evidence_type"] = self._normalize_evidence_type(finding["evidence_type"])
            source_tool = finding.get("source_tool", "unknown")
            finding_new_entities = []
            finding_entity_ids = set()  # 追踪本 finding 引用的所有实体（用于方向关联）
            finding_new_obs = 0
            finding_new_edges = 0

            # ========== Agent 提供的结构化实体（优先使用）==========
            agent_entities = finding.get("entities", [])
            agent_relationships = finding.get("relationships", [])
            if agent_entities:
                # 直接从 agent 提供的结构化实体构建图
                # Comprehensive provenance extraction for all tools
                source_tool = finding.get("source_tool", "")
                provenance = ""
                source_url = ""

                # Priority 1: Handle tool-specific provenance (check source_tool FIRST)
                if source_tool == "search_nccn":
                    # NCCN PageIndex RAG - no URL, may have page_range
                    provenance = "NCCN"
                    page_range = finding.get("page_range", "")
                    if page_range:
                        provenance = f"NCCN:p.{page_range}"
                    source_url = ""  # No direct URL for RAG results

                elif source_tool == "search_civic":
                    # CIViC - prioritize civic_url over embedded pmid
                    civic_url = finding.get("civic_url", "")
                    if civic_url:
                        # Extract molecular profile ID from URL
                        match = re.search(r'/molecular-profiles/(\d+)', civic_url)
                        if match:
                            provenance = f"CIViC:MP{match.group(1)}"
                        else:
                            provenance = "CIViC"
                        source_url = civic_url
                    else:
                        # Fallback to pmid if no civic_url
                        provenance = finding.get("pmid", "")
                        if provenance:
                            source_url = f"https://pubmed.ncbi.nlm.nih.gov/{provenance}/"

                elif source_tool == "search_gdc":
                    # GDC - extract gene ID from URL
                    gdc_url = finding.get("gdc_url", "")
                    if gdc_url:
                        match = re.search(r'/genes/([A-Z0-9_]+)', gdc_url)
                        if match:
                            provenance = f"GDC:{match.group(1)}"
                        else:
                            gene_name = finding.get("gene_name", "") or finding.get("gene", "")
                            provenance = f"GDC:{gene_name}" if gene_name else "GDC"
                        source_url = gdc_url

                elif source_tool == "search_fda_labels":
                    # FDA - extract drug name or set_id
                    drug_name = finding.get("drug_name", "") or finding.get("generic_name", "")
                    if drug_name:
                        provenance = f"FDA:{drug_name.upper()}"
                    else:
                        # Try extracting from URL
                        fda_url = finding.get("url", "")
                        if "setid=" in fda_url:
                            match = re.search(r'setid=([a-f0-9-]+)', fda_url)
                            if match:
                                provenance = f"FDA:SETID_{match.group(1)[:8]}"
                        else:
                            provenance = "FDA"
                    source_url = finding.get("url", "")

                elif source_tool == "search_rxnorm":
                    # RxNorm - extract rxcui
                    rxcui = finding.get("rxcui", "")
                    if rxcui:
                        provenance = f"RxNorm:{rxcui}"
                        source_url = f"https://mor.nlm.nih.gov/RxNav/search?searchBy=RXCUI&searchTerm={rxcui}"
                    else:
                        provenance = "RxNorm"
                        source_url = finding.get("url", "") or finding.get("rxnorm_url", "")

                elif source_tool == "search_clinvar":
                    # ClinVar - use provided URL
                    provenance = "ClinVar"
                    source_url = finding.get("url", "")

                elif source_tool == "search_cbioportal":
                    # cBioPortal - use provided URL
                    provenance = "cBioPortal"
                    source_url = finding.get("cbioportal_url", "") or finding.get("url", "")

                # Priority 2: Fallback to PMID/NCT if tool not matched or no tool-specific ID
                if not provenance:
                    provenance = finding.get("pmid", "") or finding.get("nct_id", "")

                # Priority 3: Construct URL if missing
                if not source_url:
                    if provenance and provenance.startswith("PMID:"):
                        pmid = provenance.replace("PMID:", "").replace("pmid:", "")
                        source_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    elif provenance and provenance.startswith("NCT"):
                        source_url = f"https://clinicaltrials.gov/study/{provenance}"
                    elif finding.get("pmid"):
                        pmid = str(finding["pmid"]).strip()
                        if pmid:
                            source_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    elif finding.get("nct_id"):
                        nct = str(finding["nct_id"]).strip()
                        if not nct.startswith("NCT"):
                            nct = f"NCT{nct}"
                        source_url = f"https://clinicaltrials.gov/study/{nct}"
                    else:
                        # Check for generic url fields
                        source_url = (
                            finding.get("civic_url") or
                            finding.get("url") or
                            finding.get("gdc_url") or
                            finding.get("cbioportal_url") or
                            finding.get("source_url") or
                            ""
                        )
                obs = Observation(
                    id=Observation.generate_id(source_tool),
                    statement=finding.get("content", "")[:200],
                    source_agent=agent_role,
                    source_tool=source_tool,
                    provenance=provenance,
                    source_url=source_url,
                    evidence_grade=EvidenceGrade(finding["grade"].upper()) if finding.get("grade") else None,
                    evidence_type=EvidenceType(finding["evidence_type"]) if finding.get("evidence_type") else None,
                    l_tier=finding.get("l_tier"),
                    l_tier_reasoning=finding.get("l_tier_reasoning"),
                    iteration=iteration,
                )
                for ent_data in agent_entities:
                    cid = ent_data.get("canonical_id", "").upper()
                    ename = ent_data.get("name", "").upper()
                    if not cid or not ename:
                        continue
                    etype_str = ent_data.get("entity_type", "finding")
                    try:
                        etype = EntityType(etype_str.lower())
                    except (ValueError, KeyError):
                        etype = EntityType.FINDING
                    entity = graph.get_or_create_entity(
                        canonical_id=cid, entity_type=etype, name=ename,
                        source=source_tool, aliases=ent_data.get("aliases", [])
                    )
                    graph.add_observation_to_entity(canonical_id=entity.canonical_id, observation=obs)
                    finding_entity_ids.add(entity.canonical_id)
                    if entity.canonical_id not in new_entity_ids:
                        new_entity_ids.append(entity.canonical_id)
                        finding_new_entities.append(entity.canonical_id)
                    finding_new_obs += 1
                for rel_data in agent_relationships:
                    src_id = rel_data.get("source_id", "").upper()
                    tgt_id = rel_data.get("target_id", "").upper()
                    # Convert string predicate to Predicate enum (type-safe)
                    pred_str = rel_data.get("predicate", "ASSOCIATED_WITH")
                    try:
                        pred = Predicate(pred_str.lower())
                    except (ValueError, AttributeError):
                        pred = Predicate.ASSOCIATED_WITH  # Safe fallback
                    conf = rel_data.get("confidence", 0.5)
                    src_ent = graph.get_entity(src_id) or graph.find_entity_by_name(src_id)
                    tgt_ent = graph.get_entity(tgt_id) or graph.find_entity_by_name(tgt_id)
                    if src_ent and tgt_ent:
                        graph.add_edge(
                            source_id=src_ent.canonical_id, target_id=tgt_ent.canonical_id,
                            predicate=pred, observation=obs, confidence=conf
                        )
                        finding_new_edges += 1
                        finding_entity_ids.add(src_ent.canonical_id)
                        finding_entity_ids.add(tgt_ent.canonical_id)
                # 更新方向的证据关联（agent 提供的实体）
                direction_id = finding.get("direction_id")
                if direction_id and plan:
                    direction = plan.get_direction_by_id(direction_id)
                    if direction:
                        for entity_id in finding_entity_ids:
                            direction.add_entity_id(entity_id)

                # 跳过 LLM 提取，直接用 agent 提供的数据
                extraction_details.append({
                    "source_tool": source_tool,
                    "entities_extracted": len(agent_entities),
                    "edges_extracted": len(agent_relationships),
                    "extraction_method": "agent_provided",
                })
                continue

            # ========== LLM 实体提取 (fallback) ==========
            try:
                extraction_result = extract_entities_from_finding(
                    finding=finding,
                    source_agent=agent_role,
                    source_tool=source_tool,
                    iteration=iteration,
                    existing_entities=existing_entities
                )
            except Exception as e:
                logger.warning(f"[{agent_role}] Entity extraction failed: {e}")
                continue

            # ========== 处理提取的实体 ==========
            finding_entities_detail = []
            for extracted_entity in extraction_result.entities:
                # 获取或创建实体（自动合并）
                entity = graph.get_or_create_entity(
                    canonical_id=extracted_entity.canonical_id,
                    entity_type=extracted_entity.entity_type,
                    name=extracted_entity.name,
                    source=source_tool,
                    aliases=extracted_entity.aliases
                )
                finding_entity_ids.add(entity.canonical_id)

                # 添加观察到实体
                if extracted_entity.observation:
                    graph.add_observation_to_entity(
                        canonical_id=entity.canonical_id,
                        observation=extracted_entity.observation
                    )
                    finding_new_obs += 1

                # 记录新实体
                if entity.canonical_id not in new_entity_ids:
                    new_entity_ids.append(entity.canonical_id)
                    finding_new_entities.append(entity.canonical_id)

                # 收集实体详情
                obs = extracted_entity.observation
                finding_entities_detail.append({
                    "canonical_id": extracted_entity.canonical_id,
                    "type": extracted_entity.entity_type.value if hasattr(extracted_entity.entity_type, 'value') else str(extracted_entity.entity_type),
                    "name": extracted_entity.name,
                    "observation_statement": obs.statement if obs else "",
                    "evidence_grade": obs.evidence_grade.value if obs and hasattr(obs.evidence_grade, 'value') else (str(obs.evidence_grade) if obs else ""),
                })

            # ========== 处理提取的边 ==========
            finding_edges_detail = []
            for extracted_edge in extraction_result.edges:
                # 确保源和目标实体存在
                source_entity = graph.get_entity(extracted_edge.source_id)
                target_entity = graph.get_entity(extracted_edge.target_id)

                if not source_entity:
                    # 尝试通过名称查找
                    source_entity = graph.find_entity_by_name(extracted_edge.source_id)
                if not target_entity:
                    target_entity = graph.find_entity_by_name(extracted_edge.target_id)

                if source_entity and target_entity:
                    graph.add_edge(
                        source_id=source_entity.canonical_id,
                        target_id=target_entity.canonical_id,
                        predicate=extracted_edge.predicate,
                        observation=extracted_edge.observation,
                        confidence=extracted_edge.confidence
                    )
                    finding_new_edges += 1
                    finding_entity_ids.add(source_entity.canonical_id)
                    finding_entity_ids.add(target_entity.canonical_id)

                    # 收集边详情
                    edge_obs = extracted_edge.observation
                    predicate_str = extracted_edge.predicate.value if hasattr(extracted_edge.predicate, 'value') else str(extracted_edge.predicate)
                    finding_edges_detail.append({
                        "source": source_entity.canonical_id,
                        "target": target_entity.canonical_id,
                        "predicate": predicate_str,
                        "observation_statement": edge_obs.statement if edge_obs else "",
                        "confidence": extracted_edge.confidence,
                    })

            # ========== 处理冲突 ==========
            for conflict in extraction_result.conflicts:
                # 冲突标记会在 add_edge 时处理
                pass

            # ========== 更新方向的证据关联 ==========
            direction_id = finding.get("direction_id")
            if direction_id and plan:
                direction = plan.get_direction_by_id(direction_id)
                if direction:
                    # 关联本 finding 引用的实体到方向
                    for entity_id in finding_entity_ids:
                        direction.add_entity_id(entity_id)

            # 更新实体索引，让后续 finding 的 LLM 提取看到新增实体
            existing_entities = graph.get_entity_index()

            # ========== 记录 per-finding 提取详情 ==========
            finding_summary = finding.get("statement", finding.get("title", ""))
            extraction_details.append({
                "source_tool": source_tool,
                "direction_id": direction_id or "",
                "finding_summary": finding_summary,
                "new_entities": finding_new_entities,
                "new_observations": finding_new_obs,
                "new_edges": finding_new_edges,
                "entities_detail": finding_entities_detail,
                "edges_detail": finding_edges_detail,
            })

        # 记录统计
        summary = graph.summary()
        logger.info(f"[{agent_role}] Evidence graph: {summary.get('total_entities', 0)} entities, {summary.get('total_edges', 0)} edges")

        return new_entity_ids, plan, extraction_details


# ==================== 增强版 Agent 创建工厂 ====================

def create_research_agent(agent_class, **kwargs):
    """
    创建具有研究能力的 Agent

    Args:
        agent_class: 原始 Agent 类
        **kwargs: 传递给 Agent 构造函数的参数

    Returns:
        具有 ResearchMixin 能力的 Agent 实例
    """
    # 动态创建混入类
    class ResearchAgent(agent_class, ResearchMixin):
        pass

    return ResearchAgent(**kwargs)


if __name__ == "__main__":
    print("ResearchMixin 模块加载成功 (DeepEvidence Style)")

    # 测试解析
    mixin = ResearchMixin()
    test_output = '''```json
{
    "summary": "测试摘要",
    "findings": [{"content": "测试发现", "evidence_type": "molecular", "gene": "EGFR"}],
    "direction_updates": {"D1": "completed"},
    "needs_deep_research": [],
    "research_complete": false
}
```'''
    parsed = mixin._parse_research_output(test_output, ResearchMode.BREADTH_FIRST)
    print(f"解析结果: {parsed}")
