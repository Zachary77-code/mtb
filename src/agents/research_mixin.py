"""
Research Mixin - BFRS/DFRS 研究能力 (DeepEvidence Style)

为现有 Agent 提供 BFRS（广度优先研究）和 DFRS（深度优先研究）能力。
使用实体中心的证据图架构，将发现分解为 Entity + Edge + Observation。
"""
import json
from typing import Dict, List, Any, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass

from src.models.evidence_graph import (
    EvidenceGraph,
    load_evidence_graph
)
from src.models.entity_extractors import extract_entities_from_finding
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
    evidence_ids: List[str]             # 添加到图中的实体 canonical_id 列表
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
        research_plan: Optional[Dict[str, Any]] = None
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
                "new_evidence_ids": [],
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

        # 处理 BFRS 方向
        if bfrs_directions:
            logger.info(f"[{agent_role}] 执行 BFRS 广度研究: {len(bfrs_directions)} 个方向")
            prompt = self._build_bfrs_prompt(bfrs_directions, graph, iteration, max_iterations, case_context)
            result = self.invoke(prompt)  # type: ignore
            bfrs_tool_report = self.get_tool_call_report()  # type: ignore  # 在下次 invoke() 重置前捕获
            if bfrs_tool_report:
                all_tool_call_reports.append(f"### BFRS 工具调用\n{bfrs_tool_report}")
            # 捕获原始 tool call records（标记 phase）
            for record in getattr(self, 'tool_call_history', []):
                all_tool_call_records.append({
                    "tool_name": record.tool_name,
                    "parameters": record.parameters,
                    "reasoning": record.reasoning,
                    "result": record.result,
                    "timestamp": record.timestamp,
                    "phase": "BFRS",
                })
            output = result.get("output", "")
            all_outputs.append(output)
            parsed = self._parse_research_output(output, ResearchMode.BREADTH_FIRST)
            all_findings.extend(parsed.get("findings", []))
            all_direction_updates.update(parsed.get("direction_updates", {}))
            all_needs_deep.extend(parsed.get("needs_deep_research", []))
            if parsed.get("summary"):
                all_summaries.append(f"[BFRS] {parsed['summary']}")
            bfrs_analysis = parsed.get("agent_analysis", "")
            if bfrs_analysis:
                all_agent_analysis.append(f"[BFRS] {bfrs_analysis}")
            all_per_direction_analysis.update(parsed.get("per_direction_analysis", {}))

        # 处理 DFRS 方向
        if dfrs_directions:
            logger.info(f"[{agent_role}] 执行 DFRS 深度研究: {len(dfrs_directions)} 个方向")
            prompt = self._build_dfrs_prompt(dfrs_directions, graph, iteration, max_iterations, case_context)
            result = self.invoke(prompt)  # type: ignore
            dfrs_tool_report = self.get_tool_call_report()  # type: ignore  # 捕获 DFRS 工具调用报告
            if dfrs_tool_report:
                all_tool_call_reports.append(f"### DFRS 工具调用\n{dfrs_tool_report}")
            # 捕获原始 tool call records（标记 phase）
            for record in getattr(self, 'tool_call_history', []):
                all_tool_call_records.append({
                    "tool_name": record.tool_name,
                    "parameters": record.parameters,
                    "reasoning": record.reasoning,
                    "result": record.result,
                    "timestamp": record.timestamp,
                    "phase": "DFRS",
                })
            output = result.get("output", "")
            all_outputs.append(output)
            parsed = self._parse_research_output(output, ResearchMode.DEPTH_FIRST)
            all_findings.extend(parsed.get("findings", []))
            all_direction_updates.update(parsed.get("direction_updates", {}))
            all_needs_deep.extend(parsed.get("needs_deep_research", []))
            if parsed.get("summary"):
                all_summaries.append(f"[DFRS] {parsed['summary']}")
            dfrs_analysis = parsed.get("agent_analysis", "")
            if dfrs_analysis:
                all_agent_analysis.append(f"[DFRS] {dfrs_analysis}")
            all_per_direction_analysis.update(parsed.get("per_direction_analysis", {}))

        # 更新证据图和研究计划（实体中心架构）
        new_entity_ids, updated_plan, extraction_details = self._update_evidence_graph(
            graph=graph,
            findings=all_findings,
            agent_role=agent_role,
            iteration=iteration,
            mode=mode,
            plan=plan
        )

        # 增强结果日志
        logger.info(f"[{agent_role}] 迭代完成:")
        logger.info(f"[{agent_role}]   发现数: {len(all_findings)}")
        logger.info(f"[{agent_role}]   新实体: {len(new_entity_ids)}")
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
            "research_plan": updated_plan.to_dict() if updated_plan else None,
            "new_evidence_ids": new_entity_ids,
            "direction_updates": all_direction_updates,
            "research_complete": len(bfrs_directions) == 0 and len(dfrs_directions) == 0,
            "needs_deep_research": all_needs_deep,
            "summary": combined_summary,
            "raw_output": "\n---\n".join(all_outputs),
            "tool_call_report": "\n\n".join(all_tool_call_reports),
            "tool_call_records": all_tool_call_records,
            "extraction_details": extraction_details,
            "agent_analysis": "\n\n".join(all_agent_analysis),
            "per_direction_analysis": all_per_direction_analysis,
        }

    def _build_bfrs_prompt(
        self,
        directions: List[Dict[str, Any]],
        graph: EvidenceGraph,
        iteration: int,
        max_iterations: int,
        case_context: str
    ) -> str:
        """构建 BFRS 模式提示"""
        agent_role = getattr(self, 'role', 'Agent')

        # 格式化方向列表
        directions_text = ""
        for i, d in enumerate(directions, 1):
            directions_text += f"""
### 方向 {i}: {d.get('topic', '未命名')}
- ID: {d.get('id', '')}
- 目标模块: {', '.join(d.get('target_modules', []))}
- 优先级: {d.get('priority', 3)}
- 建议查询: {', '.join(d.get('queries', []))}
- 完成标准: {d.get('completion_criteria', '')}
- 当前状态: {d.get('status', 'pending')}
"""

        # 现有证据摘要
        existing_evidence = graph.summary()

        return f"""## 研究模式: BFRS (广度优先研究)

### 当前迭代信息
- 迭代轮次: {iteration + 1} / {max_iterations}
- 你的角色: {agent_role}
- 现有实体: {existing_evidence.get('total_entities', 0)} 个
- 现有边: {existing_evidence.get('total_edges', 0)} 条

### 病例背景
{case_context}

### 分配给你的研究方向
{directions_text}

### BFRS 执行指南
1. 对每个研究方向执行 1-2 次工具调用
2. 收集广泛的初步证据，不深入追踪单个发现
3. 为每个方向标记状态: pending（需继续）/ completed（已充分）
4. 标记需要深入研究的重要发现

### 输出格式
请以 JSON 格式输出研究结果:

```json
{{
    "summary": "本轮研究摘要",
    "findings": [
        {{
            "direction_id": "D1",
            "content": "发现内容（完整详细，不限长度）",
            "evidence_type": "molecular|clinical|literature|trial|guideline|drug|pathology|imaging",
            "grade": "A|B|C|D|E",
            "civic_type": "predictive|diagnostic|prognostic|predisposing|oncogenic",
            "source_tool": "工具名称",
            "gene": "基因名（如有）",
            "variant": "变异名（如有）",
            "drug": "药物名（如有）",
            "pmid": "PubMed ID（如有）",
            "nct_id": "NCT ID（如有）"
        }}
    ],
    "direction_updates": {{
        "D1": "pending|completed",
        "D2": "pending|completed"
    }},
    "needs_deep_research": [
        {{
            "direction_id": "D1",
            "finding": "需要深入的发现描述",
            "reason": "为什么需要深入研究"
        }}
    ],
    "per_direction_analysis": {{
        "D1": {{
            "research_question": "本轮需要解决的核心研究问题",
            "tools_used": "使用了哪些工具和查询关键词",
            "what_found": "找到了哪些关键证据",
            "what_not_found": "没找到什么 / 未能解决的问题",
            "new_questions": "是否产生了新的研究问题",
            "conclusion": "该方向的当前结论"
        }}
    }},
    "research_complete": false
}}
```

**per_direction_analysis 要求**:
- 必须对每个分配的方向输出分析，即使该方向本轮无新发现
- research_question: 根据方向的完成标准和已有证据，本轮需解决什么问题
- tools_used: 具体列出使用的工具名称和查询参数
- what_found: 找到了什么关键信息（简洁概括）
- what_not_found: 哪些问题未被解答，或工具返回无结果
- new_questions: 研究过程中是否产生了需要后续跟进的新问题
- conclusion: 该方向的当前状态判断（是否需要继续、需要什么类型的后续研究）

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

请开始执行广度优先研究。
"""

    def _build_dfrs_prompt(
        self,
        directions: List[Dict[str, Any]],
        graph: EvidenceGraph,
        iteration: int,
        max_iterations: int,
        case_context: str
    ) -> str:
        """构建 DFRS 模式提示"""
        agent_role = getattr(self, 'role', 'Agent')

        # 找到需要深入研究的方向（检查 needs_deep_research 标记或 deep_research_findings 列表）
        depth_items = []
        for d in directions:
            if d.get('needs_deep_research') or d.get('deep_research_findings'):
                depth_items.append(d)

        # 格式化深入研究项（含具体待研究问题）
        depth_text = ""
        for i, item in enumerate(depth_items, 1):
            findings_list = item.get('deep_research_findings', [])
            findings_text = ""
            if findings_list:
                findings_text = "\n" + "\n".join(f"  - {f}" for f in findings_list)

            mode_reason = item.get('mode_reason', '')
            mode_reason_text = f"\n- PlanAgent 评估指示: {mode_reason}" if mode_reason else ""

            depth_text += f"""
### 深入研究项 {i}
- 方向 ID: {item.get('id', '')}
- 主题: {item.get('topic', '')}
- 目标模块: {', '.join(item.get('target_modules', []))}
- 完成标准: {item.get('completion_criteria', '')}
- 需要深入的原因: {item.get('depth_research_reason', '需要更多证据')}{mode_reason_text}
- 具体待研究问题:{findings_text if findings_text else ' 请基于方向主题深入'}
- 已有证据 ID: {item.get('evidence_ids', [])}
"""

        # 无深入项时的回退（从所有方向的 mode_reason 中提取指示）
        if not depth_text:
            reasons = [d.get('mode_reason', '') for d in directions if d.get('mode_reason')]
            if reasons:
                depth_text = "### 研究指示\n" + "\n".join(f"- {r}" for r in reasons)
            else:
                depth_text = "无特定深入项，请基于现有证据进行深化研究"

        # 现有证据摘要
        existing_evidence = graph.summary()

        return f"""## 研究模式: DFRS (深度优先研究)

### 当前迭代信息
- 迭代轮次: {iteration + 1} / {max_iterations}
- 你的角色: {agent_role}
- 现有实体: {existing_evidence.get('total_entities', 0)} 个
- 现有边: {existing_evidence.get('total_edges', 0)} 条

### 病例背景
{case_context}

### 需要深入研究的项目
{depth_text}

### DFRS 执行指南
1. 针对高优先级发现进行多跳推理
2. 追踪引用链、相关研究、机制解释
3. 最多执行 3-5 次连续工具调用
4. 寻找更高级别的证据支持

### 输出格式
请以 JSON 格式输出研究结果:

```json
{{
    "summary": "深入研究摘要",
    "findings": [
        {{
            "direction_id": "D1",
            "content": "深入发现内容（完整详细，不限长度）",
            "evidence_type": "molecular|clinical|literature|trial|guideline|drug|pathology|imaging",
            "grade": "A|B|C|D|E",
            "civic_type": "predictive|diagnostic|prognostic|predisposing|oncogenic",
            "source_tool": "工具名称",
            "gene": "基因名（如有）",
            "variant": "变异名（如有）",
            "drug": "药物名（如有）",
            "pmid": "PubMed ID（如有）",
            "nct_id": "NCT ID（如有）",
            "depth_chain": ["引用1", "引用2", "推理步骤"]
        }}
    ],
    "direction_updates": {{
        "D1": "pending|completed"
    }},
    "needs_deep_research": [
        {{
            "direction_id": "D1",
            "finding": "仍需深入的发现描述",
            "reason": "为什么需要继续深入"
        }}
    ],
    "per_direction_analysis": {{
        "D1": {{
            "research_question": "本轮深入研究需要解决的核心问题",
            "tools_used": "使用了哪些工具和查询关键词",
            "what_found": "找到了哪些关键证据",
            "what_not_found": "没找到什么 / 未能解决的问题",
            "new_questions": "是否产生了新的研究问题",
            "conclusion": "该方向的当前结论"
        }}
    }},
    "research_complete": true|false
}}
```

**per_direction_analysis 要求**:
- 必须对每个分配的方向输出分析，即使该方向本轮无新发现
- research_question: 根据待研究问题列表，本轮需解决什么
- tools_used: 具体列出使用的工具名称和查询参数
- what_found: 找到了什么关键信息（简洁概括）
- what_not_found: 哪些问题未被解答，或工具返回无结果
- new_questions: 研究过程中是否产生了需要后续跟进的新问题
- conclusion: 该方向的当前状态判断

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

请开始执行深度优先研究。
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
            source_tool = finding.get("source_tool", "unknown")
            finding_new_entities = []
            finding_new_obs = 0
            finding_new_edges = 0

            # ========== LLM 实体提取 ==========
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
                    # 关联所有新实体到方向
                    for entity_id in new_entity_ids:
                        direction.add_evidence(entity_id)

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
