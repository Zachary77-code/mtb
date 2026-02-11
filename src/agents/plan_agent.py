"""
PlanAgent - 研究计划生成 Agent

分析病例，生成结构化的研究计划，指导 BFRS/DFRS 研究循环。
使用 gemini-3-pro-preview 模型。
"""
import json
from typing import Dict, List, Any, Optional

from src.agents.base_agent import BaseAgent, ORCHESTRATOR_MODEL, SUBGRAPH_MODEL
from src.models.research_plan import (
    ResearchPlan,
    ResearchDirection,
    ResearchMode,
    DirectionStatus,
    create_research_plan,
    load_research_plan
)
from src.models.evidence_graph import load_evidence_graph, EvidenceGrade
from src.utils.logger import mtb_logger as logger
from config.settings import (
    PLAN_AGENT_PROMPT_FILE,
    MAX_PHASE2A_ITERATIONS,
    MAX_PHASE2B_ITERATIONS,
    MAX_PHASE3_ITERATIONS,
)

# 证据等级权重（用于计算方向完成度）
GRADE_WEIGHTS = {
    "A": 5.0,   # Validated - 一条 A 级 ≈ 5 条 E 级
    "B": 3.0,   # Clinical
    "C": 2.0,   # Case Study
    "D": 1.5,   # Preclinical
    "E": 1.0,   # Inferential
}

# 方向完成度目标得分（相当于 10 条 A 级 或 50 条 E 级）
TARGET_COMPLETENESS_SCORE = 50.0

# 收敛阈值
CONVERGENCE_COMPLETENESS_THRESHOLD = 80  # 完成度 >= 80% 视为完成
CONTINUE_COMPLETENESS_THRESHOLD = 60     # 完成度 < 60% 需要继续收集

# Phase → 允许的 Agent 映射（用于 new_directions 校验）
PHASE_AGENT_MAP = {
    "phase1": {"Pathologist", "Geneticist", "Pharmacist", "Oncologist"},
    "phase2a": {"Oncologist", "LocalTherapist", "Recruiter", "Nutritionist", "IntegrativeMed"},
    "phase2b": {"Pharmacist"},
    "phase3": {"Oncologist"},
}


# 必须覆盖的 Chair 模块列表
# Phase 1 必需覆盖的模块（Oncologist 相关模块在 Phase 2 覆盖）
REQUIRED_MODULE_COVERAGE = [
    "患者概况",
    "分子特征",
    "合并症",
    "过往治疗分析",
    "复查和追踪方案",  # Geneticist 分子复查初稿
]


class PlanAgent(BaseAgent):
    """
    研究计划 Agent

    职责：
    1. 分析病例，提取关键实体（基因、变异、癌种、治疗史）
    2. 为每个 Agent 分配研究方向
    3. 设置目标模块映射和完成标准
    """

    def __init__(self):
        """初始化 PlanAgent，使用 ORCHESTRATOR_MODEL"""
        super().__init__(
            role="PlanAgent",
            prompt_file=PLAN_AGENT_PROMPT_FILE,
            tools=[],  # PlanAgent 不需要外部工具
            temperature=0.3,
            model=ORCHESTRATOR_MODEL  # 使用 pro 模型
        )

    def analyze_case(self, case_text: str) -> Dict[str, Any]:
        """
        分析病例并生成研究计划

        Args:
            case_text: 病例文本

        Returns:
            研究计划字典（可序列化到 State）

        Raises:
            ValueError: 当解析失败或模块覆盖不完整时
        """
        logger.info(f"[{self.role}] 开始分析病例...")

        # 构建任务提示
        task_prompt = self._build_analysis_prompt(case_text)

        # 调用 LLM
        result = self.invoke(task_prompt)
        output = result.get("output", "")

        # 解析 LLM 输出（失败时抛出异常）
        plan = self._parse_plan_output(output)

        logger.info(f"[{self.role}] 研究计划生成完成: {plan.summary()}")

        return plan.to_dict()

    def _get_available_nccn_indexes(self) -> list:
        """扫描 NCCN_IMAGE_VECTOR_DIR 获取可用索引名称列表"""
        try:
            from config.settings import NCCN_IMAGE_VECTOR_DIR
            if not NCCN_IMAGE_VECTOR_DIR.exists():
                return []
            return sorted([
                d.name for d in NCCN_IMAGE_VECTOR_DIR.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ])
        except Exception:
            return []

    def _build_analysis_prompt(self, case_text: str) -> str:
        """构建分析任务提示"""

        # 动态获取可用 NCCN 索引
        available_indexes = self._get_available_nccn_indexes()
        nccn_index_section = ""
        if available_indexes:
            index_list = "\n".join(f"- `{name}`" for name in available_indexes)
            nccn_index_section = f"""
## NCCN 指南索引选择

系统中可用的 NCCN 指南索引如下：
{index_list}

请在输出 JSON 中额外添加 `nccn_guideline_index` 字段，选择与本病例癌种最匹配的索引名称。
如果没有匹配的索引，填写 `null`。
"""

        return f"""请分析以下病例，生成结构化的研究计划。

## 病例内容
{case_text}

## 输出要求
请以 JSON 格式输出研究计划，包含以下字段：

```json
{{
    "case_summary": "病例摘要（50-100字）",
    "key_entities": {{
        "genes": ["基因列表"],
        "variants": ["变异列表"],
        "cancer_type": ["癌症类型"],
        "drugs_mentioned": ["提及的药物"],
        "treatment_history": ["治疗史要点"]
    }},
    "nccn_guideline_index": "索引名称或null",
    "directions": [
        {{
            "id": "D1",
            "topic": "研究方向主题",
            "target_agent": "Geneticist",  // Pathologist/Geneticist/Pharmacist/Oncologist
            "target_modules": ["分子特征"],  // 目标 Chair 模块
            "priority": 1,  // 1-5，1最高
            "queries": ["建议的查询关键词"],
            "completion_criteria": "完成标准描述"
        }}
    ]
}}
```
{nccn_index_section}

## 研究方向分配指南

### Pathologist（病理学家）
- 病理学形态特征分析
- 影像学发现解读
- 免疫组化结果意义
- 病理分期评估

### Geneticist（遗传学家）
- 基因变异致病性评估
- 变异-药物敏感性关系
- 耐药机制分析
- 分子分型确认

### Pharmacist（药师 - Phase 1 信息提取）
- 合并症（病症+用药清单）
- 过敏史
- 器官功能基线（eGFR、肝功能、血象）
- 药物互作初步分析

### Oncologist（肿瘤学家 - Phase 1 Analysis 模式）
- 过往治疗和当前治疗方案的分析评价
- 每线治疗疗效评估
- 方案合理性分析
- 耐药机制推断
- 关键决策点回顾

## 必需模块覆盖
确保研究方向覆盖以下 Phase 1 模块：
- 患者概况 (Pathologist)
- 分子特征 (Geneticist)
- 合并症 (Pharmacist)
- 过往治疗分析 (Pathologist + Oncologist)
- 复查和追踪方案 (Geneticist 分子复查初稿)

注意：Recruiter（临床试验招募员）已移至 Phase 2a，此处无需分配。
方案 Mapping、局部治疗、临床试验匹配等将在 Phase 2a 中进行。

## Phase 1 研究方向模板与模块映射

**CRITICAL**: 每个研究方向必须使用下表指定的确切 target_modules 名称，不可自行创造：

| 方向类别 | target_agent | target_modules (确切名称) |
|---------|--------------|--------------------------|
| 患者基线信息+诊断信息+分期影像 | Pathologist | ["患者概况"] |
| 完整治疗史提取 | Pathologist | ["过往治疗分析"] |
| 分子图谱解读 | Geneticist | ["分子特征"] |
| 分子复查初稿（耐药突变谱/复查策略） | Geneticist | ["复查和追踪方案"] |
| 合并症+用药清单+过敏史 | Pharmacist | ["合并症"] |
| 器官功能基线 | Pharmacist | ["合并症"] |
| 过往治疗分析与评价 | Oncologist | ["过往治疗分析"] |

**必需覆盖**: 以下 5 个模块必须至少被一个研究方向覆盖：
- 患者概况
- 分子特征
- 合并症
- 过往治疗分析
- 复查和追踪方案

**示例**:
```json
{{
    "id": "D_PATIENT_BASELINE",
    "topic": "患者基线信息与诊断信息提取",
    "target_agent": "Pathologist",
    "target_modules": ["患者概况"],  // 必须使用确切名称
    "priority": 1,
    "queries": ["..."],
    "completion_criteria": "..."
}}
```

## 定制化示例

以下是一个结直肠癌 KRAS G12C 患者的方向示例（仅供参考格式和定制化程度，不要照搬内容）：

```json
{{
    "id": "D_KRAS_RESISTANCE",
    "topic": "KRAS G12C 抑制剂耐药机制与获得性突变监测策略",
    "target_agent": "Geneticist",
    "target_modules": ["分子特征"],  // 从上表选择确切名称
    "priority": 1,
    "queries": ["KRAS G12C sotorasib resistance mechanism", "KRAS G12C acquired mutation Y96D R68S", "ctDNA KRAS monitoring CRC"],
    "completion_criteria": "明确 KRAS G12C 抑制剂的原发耐药（EGFR 反馈激活、RAS-MAPK 旁路）和获得性耐药（Y96D/R68S/MET 扩增）机制，给出 ctDNA 监测策略建议"
}}
```

注意：
- ID 反映具体研究内容（D_KRAS_RESISTANCE），不是泛化分类（D_MOLECULAR_PROFILE）
- topic 包含具体基因、药物名
- queries 全部可直接用于 PubMed/CIViC 检索
- completion_criteria 明确需要回答的具体临床问题
- **target_modules 必须从上表选择确切名称**

## 注意事项
1. 每个 Agent 分配 2-4 个研究方向（仅限 Pathologist/Geneticist/Pharmacist/Oncologist）
2. 优先级 1 为最关键方向
3. 确保 JSON 格式正确，可以被解析
4. **每个方向的 target_modules 必须从上表选择确切名称，不可自创**
5. **必须确保 5 个必需模块都被至少一个研究方向覆盖**
6. 方向的 topic/queries/completion_criteria 必须反映本病例的具体实体和临床问题，不要使用泛化描述
"""

    def _parse_plan_output(self, output: str) -> ResearchPlan:
        """
        解析 LLM 输出为 ResearchPlan

        Args:
            output: LLM 原始输出

        Returns:
            ResearchPlan 实例

        Raises:
            ValueError: 当解析失败或模块覆盖不完整时
        """
        # 尝试提取 JSON
        json_str = self._extract_json(output)

        if not json_str:
            raise ValueError(f"[{self.role}] 无法从 LLM 输出中提取 JSON")

        try:
            data = json.loads(json_str)
            # Phase 1 仅包含 Pathologist/Geneticist/Pharmacist/Oncologist 方向
            # Recruiter 已移至 Phase 2a
            directions = [d for d in data.get("directions", []) if d.get("target_agent") in ("Pathologist", "Geneticist", "Pharmacist", "Oncologist")]
            plan = create_research_plan(
                case_summary=data.get("case_summary", ""),
                key_entities=data.get("key_entities", {}),
                directions=directions,
                nccn_guideline_index=data.get("nccn_guideline_index"),
            )

            # 验证模块覆盖
            missing = plan.validate_module_coverage(REQUIRED_MODULE_COVERAGE)
            if missing:
                raise ValueError(f"[{self.role}] 模块覆盖不完整，缺失: {missing}")

            return plan

        except json.JSONDecodeError as e:
            raise ValueError(f"[{self.role}] JSON 解析失败: {e}")

    def _extract_json(self, text: str) -> Optional[str]:
        """从文本中提取 JSON 块"""
        import re

        # 尝试匹配 ```json ... ``` 格式
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if json_match:
            return json_match.group(1).strip()

        # 尝试匹配 { ... } 格式
        brace_match = re.search(r'\{[\s\S]*\}', text)
        if brace_match:
            return brace_match.group(0)

        return None

    # ==================== 迭代评估方法 ====================

    def evaluate_and_update(
        self,
        state: Dict[str, Any],
        phase: str,
        iteration: int,
    ) -> Dict[str, Any]:
        """
        评估当前研究进度，更新研究计划，并判断是否收敛

        Args:
            state: 当前工作流状态
            phase: 当前阶段 ("phase1" | "phase2")
            iteration: 当前迭代轮次

        Returns:
            {
                "research_plan": Dict,      # 更新后的研究计划
                "research_mode": str,       # 下一轮模式
                "decision": str,            # "continue" | "converged"
                "reasoning": str,           # 决策理由
                "quality_assessment": Dict, # 证据质量评估
                "gaps": List[str],          # 待填补空白
                "next_priorities": List[str] # 下一轮优先事项
            }
        """
        logger.info(f"[{self.role}] 开始评估 {phase} 迭代 {iteration}...")

        # 加载当前状态
        plan = load_research_plan(state.get("research_plan", {}))
        graph = load_evidence_graph(state.get("evidence_graph", {}))

        if not plan:
            raise ValueError(f"[{self.role}] 无法加载研究计划")

        # 计算各方向的证据质量统计
        direction_stats = self._calculate_direction_stats(plan, graph)

        # 提取 Research Agent 的自述字段
        if phase == "phase1":
            agent_keys = ["pathologist_research_result", "geneticist_research_result", "pharmacist_research_result", "oncologist_analysis_research_result"]
        elif phase == "phase2a":
            agent_keys = ["oncologist_mapping_research_result", "local_therapist_research_result", "recruiter_research_result", "nutritionist_research_result", "integrative_med_research_result"]
        elif phase == "phase2b":
            agent_keys = ["pharmacist_review_research_result"]
        elif phase == "phase3":
            agent_keys = ["oncologist_integration_research_result"]
        else:
            # backward compat: "phase2" maps to old Phase 2 (now phase2a)
            agent_keys = ["oncologist_research_result"]

        all_needs_deep = []  # List[Dict]: {agent, direction_id, finding, reason}
        all_agent_summaries = {}  # {agent_name: {summary, per_direction_analysis, agent_analysis, needs_deep_research}}

        for key in agent_keys:
            result = state.get(key, {})
            agent_name = key.replace("_research_result", "").capitalize()

            # 收集所有自述字段
            all_agent_summaries[agent_name] = {
                "summary": result.get("summary", ""),
                "per_direction_analysis": result.get("per_direction_analysis", {}),
                "agent_analysis": result.get("agent_analysis", ""),
                "needs_deep_research": result.get("needs_deep_research", []),
            }

            # 提取 needs_deep_research 到扁平列表（向后兼容）
            items = result.get("needs_deep_research", [])
            if items:
                for item in items:
                    if isinstance(item, dict):
                        all_needs_deep.append({
                            "agent": agent_name,
                            "direction_id": item.get("direction_id", ""),
                            "finding": item.get("finding", item.get("reason", str(item))),
                            "reason": item.get("reason", ""),
                        })
                    else:
                        all_needs_deep.append({
                            "agent": agent_name,
                            "direction_id": "",
                            "finding": str(item),
                            "reason": "",
                        })

        # 构建评估提示（包含 agent 自述）
        eval_prompt = self._build_evaluation_prompt(
            state, phase, iteration, plan, graph, direction_stats,
            needs_deep_research=all_needs_deep,
            agent_summaries=all_agent_summaries
        )

        # 调用 LLM 进行评估
        result = self.invoke(eval_prompt)
        output = result.get("output", "")

        # 解析评估结果
        eval_result = self._parse_evaluation_output(output, plan, direction_stats, needs_deep_research=all_needs_deep, phase=phase)

        # 附加统计数据和待深入研究项，供迭代报告使用
        eval_result["direction_stats"] = direction_stats
        eval_result["needs_deep_research"] = all_needs_deep

        logger.info(f"[{self.role}] 评估完成: decision={eval_result['decision']}, "
                   f"reasoning={eval_result['reasoning'][:100]}...")

        return eval_result

    def _calculate_direction_stats(
        self,
        plan: ResearchPlan,
        graph
    ) -> Dict[str, Dict[str, Any]]:
        """
        计算各研究方向的证据质量统计

        Returns:
            {
                "D1": {
                    "evidence_count": 5,  # 证据数 = 去重后的 observation 数量
                    "entity_count": 3,    # 实体数 = entity_ids 数量
                    "grade_distribution": {"A": 1, "B": 2, "C": 1, "D": 0, "E": 1},
                    "weighted_score": 12.0,
                    "completeness": 100.0,
                    "has_high_quality": True,  # 有 A/B 级
                    "low_quality_only": False  # 只有 D/E 级
                },
                ...
            }
        """
        stats = {}

        for direction in plan.directions:
            d_id = direction.id
            entity_ids = direction.entity_ids
            entity_id_set = set(entity_ids)

            # 统计证据等级分布（按 observation 的 evidence_grade 计数，去重）
            grade_dist = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0}
            weighted_score = 0.0

            # 收集去重后的 observation 及其等级
            obs_grades = {}  # {obs_id: grade_value} 用于去重后统计

            for eid in entity_ids:
                # entity_ids 存储的是实体 canonical_id
                entity = graph.get_entity(eid) if graph else None
                if entity:
                    # 收集实体上的 observation 及其等级
                    for obs in entity.observations:
                        if hasattr(obs, 'id') and obs.id and obs.id not in obs_grades:
                            grade = obs.evidence_grade.value if obs.evidence_grade else "E"
                            obs_grades[obs.id] = grade

            # 收集关联边上的 observation 及其等级
            if graph:
                for edge in graph.edges.values():
                    if edge.source_id in entity_id_set or edge.target_id in entity_id_set:
                        for obs in edge.observations:
                            if hasattr(obs, 'id') and obs.id and obs.id not in obs_grades:
                                grade = obs.evidence_grade.value if obs.evidence_grade else "E"
                                obs_grades[obs.id] = grade

            # 统计等级分布和加权得分
            for grade in obs_grades.values():
                grade_dist[grade] = grade_dist.get(grade, 0) + 1
                weighted_score += GRADE_WEIGHTS.get(grade, 1.0)

            # 计算完成度
            completeness = min(100.0, (weighted_score / TARGET_COMPLETENESS_SCORE) * 100)

            # 判断证据质量
            has_high_quality = (grade_dist["A"] > 0 or grade_dist["B"] > 0)
            low_quality_only = (
                grade_dist["A"] == 0 and
                grade_dist["B"] == 0 and
                grade_dist["C"] == 0 and
                (grade_dist["D"] > 0 or grade_dist["E"] > 0)
            )

            stats[d_id] = {
                "evidence_count": len(obs_grades),  # 证据数 = 去重后的 observation 数量
                "entity_count": len(entity_ids),  # 实体数 = entity_ids 数量
                "grade_distribution": grade_dist,
                "weighted_score": weighted_score,
                "completeness": completeness,
                "has_high_quality": has_high_quality,
                "low_quality_only": low_quality_only,
                "topic": direction.topic,
                "target_agent": direction.target_agent,
                "target_modules": direction.target_modules,
                "status": direction.status.value,
                "priority": direction.priority,
            }

        return stats

    def _build_evaluation_prompt(
        self,
        state: Dict[str, Any],
        phase: str,
        iteration: int,
        plan: ResearchPlan,
        graph,
        direction_stats: Dict[str, Dict[str, Any]],
        needs_deep_research: List[Dict[str, str]] = None,
        agent_summaries: Dict[str, Dict[str, Any]] = None
    ) -> str:
        """构建迭代评估提示

        Args:
            agent_summaries: Agent 自述字段，格式为:
                {agent_name: {summary, per_direction_analysis, agent_analysis, needs_deep_research}}
        """

        # 汇总证据质量
        total_evidence = sum(s["evidence_count"] for s in direction_stats.values())
        high_quality_directions = [d for d, s in direction_stats.items() if s["has_high_quality"]]
        low_quality_directions = [d for d, s in direction_stats.items() if s["low_quality_only"]]
        incomplete_directions = [
            d for d, s in direction_stats.items()
            if s["completeness"] < CONTINUE_COMPLETENESS_THRESHOLD
        ]

        # 检测证据冲突
        conflicts = graph.get_conflicts() if graph else []
        conflict_descriptions = [c.get("description", "") for c in conflicts if c.get("type") == "evidence_conflict"]

        # Phase-specific Agent check
        if phase == "phase1":
            agents_to_check = ["Pathologist", "Geneticist", "Pharmacist", "Oncologist"]
        elif phase == "phase2a":
            agents_to_check = ["Oncologist", "LocalTherapist", "Recruiter", "Nutritionist", "IntegrativeMed"]
        elif phase == "phase2b":
            agents_to_check = ["Pharmacist"]
        elif phase == "phase3":
            agents_to_check = ["Oncologist"]
        else:
            agents_to_check = ["Oncologist"]

        # 过滤当前 phase 相关的方向
        relevant_stats = {
            d: s for d, s in direction_stats.items()
            if s["target_agent"] in agents_to_check
        }

        # 按方向分组 needs_deep_research
        deep_by_direction = {}
        if needs_deep_research:
            for item in needs_deep_research:
                d_id = item.get("direction_id", "")
                if d_id not in deep_by_direction:
                    deep_by_direction[d_id] = []
                deep_by_direction[d_id].append(item)

        # 构建各方向证据内容详情（含 per-direction needs_deep_research）
        evidence_details = self._build_direction_evidence_details(
            plan, graph, set(relevant_stats.keys()), deep_by_direction
        )

        # 构建 DFRS 执行检查信息
        dfrs_warning_lines = []
        for d in plan.directions:
            if d.id not in relevant_stats:
                continue
            if d.preferred_mode == "depth_first":
                deep_items = d.deep_research_findings
                if deep_items:
                    dfrs_warning_lines.append(
                        f"- **{d.id}** ({d.topic}): 待研究 = {'; '.join(deep_items)}"
                    )
                elif d.mode_reason:
                    dfrs_warning_lines.append(
                        f"- **{d.id}** ({d.topic}): 原因 = {d.mode_reason}"
                    )

        dfrs_warning_section = ""
        if dfrs_warning_lines:
            dfrs_warning_section = f"""
### DFRS 方向特别注意

以下方向在本轮被指定为 DFRS（深度优先）模式，有待深入研究的具体问题。
如果当前证据仍未覆盖这些问题，该方向**不应收敛**：

{chr(10).join(dfrs_warning_lines)}
"""

        return f"""## 迭代评估任务

你正在评估 {phase.upper()} 的第 {iteration + 1} 轮迭代结果。

### 当前研究进度

**总证据数**: {total_evidence}
**本阶段相关方向数**: {len(relevant_stats)}

### 各研究方向状态

{self._format_direction_stats(relevant_stats)}

### Agent 研究自述

{self._format_agent_summaries(agent_summaries)}

### 各方向证据子图（Ground Truth）

{evidence_details}

### 证据质量概况

- **有高质量证据 (A/B级) 的方向**: {high_quality_directions if high_quality_directions else "无"}
- **只有低质量证据 (D/E级) 的方向**: {low_quality_directions if low_quality_directions else "无"}
- **完成度不足 (<60%) 的方向**: {incomplete_directions if incomplete_directions else "无"}

### 证据冲突

{conflict_descriptions if conflict_descriptions else "无检测到的证据冲突"}
{dfrs_warning_section}
### 评估要求

请根据以上信息，对每个研究方向逐一进行综合评估，判断该方向是否可以收敛：

**关键原则**：Agent 自述仅为参考，证据子图为 Ground Truth。必须交叉验证。

0. **Agent 自述验证**（首先进行）：
   - 阅读各 Agent 的研究自述（what_found, what_not_found, conclusion）
   - 对比证据子图中的实际数据，验证自述的准确性
   - 特别注意 what_not_found — 这些信息在证据图中确实不存在
   - 具体 observation 内容已包含在下方各方向子图的「核心观察」部分（仅锚点实体）。

1. **证据充分性评估**（每个方向）：
   - 对比「完成标准」与证据子图中的实体和关系，判断研究问题是否已被充分回答
   - 即使完成度数值较高，如果子图未覆盖完成标准的关键问题，仍应标记为未完成
   - 即使完成度数值较低，如果子图已充分回答研究问题，可标记为完成

1.5 **证据链结构分析**（每个方向）：
   - 从子图实体 canonical_id 前缀检查实体类型覆盖（如治疗方向应有 DRUG + DISEASE 实体）
   - 从子图边 predicate 检查关键关系是否已建立（sensitizes、causes_resistance、treats、interacts_with 等）
   - 关注应有但缺失的关系（如两个 DRUG 实体都存在但无 interacts_with 边）
   - 结构缺陷属于 critical（如治疗方向无 DRUG 实体）→ 该方向需 depth_first 或 breadth_first

2. **待深入研究项评估**（每个方向，如有「待深入研究项」则必须逐条评估）：
   - 逐条评估该方向的每个「待深入研究项」
   - 判断该项是否已被当前证据覆盖: covered（完全覆盖）/ partial（部分覆盖）/ uncovered（未覆盖）
   - 判断未覆盖/部分覆盖的项对最终报告质量的影响程度:
     - **critical（关键）**: 直接影响患者治疗决策或安全性
     - **important（重要）**: 影响报告完整性或证据强度
     - **minor（次要）**: 与患者病情、治疗基本不相关的补充信息
   - 只有 minor 级别的未覆盖项可以忽略；存在 critical 或 important 级别的未覆盖/部分覆盖项，该方向不应收敛
   - 如该方向无「待深入研究项」，则 deep_research_assessment 为空数组 []

3. **方向收敛判定**（综合以上两点）：
   - 证据已充分回答完成标准 且 无 critical/important 级别未覆盖的待深入研究项 → status="completed", preferred_mode="skip"
   - 证据不足 或 有 critical/important 待深入研究项未覆盖 → status="pending"/"in_progress", preferred_mode="breadth_first"/"depth_first"
   - 调整优先级（证据缺口大、有 critical/important 待深入项的方向提升优先级）

4. **全局收敛判断**（基于所有方向的综合判定）：
   - "converged": 所有方向均已收敛（status=completed, preferred_mode=skip）
   - "continue": 任何方向未收敛

### 输出格式

请以 JSON 格式输出：

```json
{{
    "updated_directions": [
        {{
            "id": "D1",
            "status": "completed",
            "priority": 1,
            "completeness": 85,
            "preferred_mode": "skip",
            "mode_reason": "证据已充分回答完成标准，待深入项已被覆盖",
            "evidence_assessment": "已找到 EGFR L858R 的靶向药物证据(A级)及耐药机制(B级)，完成标准中的分子分型、药物敏感性、耐药机制均有覆盖",
            "chain_analysis": "实体: GENE(2)/VARIANT(1)/DRUG(3)/DISEASE(1) 完整; 谓词: sensitizes(3)/causes_resistance(1)/treats(2) 关键关系已覆盖",
            "deep_research_assessment": [
                {{
                    "item": "耐药后二线方案",
                    "coverage": "covered",
                    "impact": "minor",
                    "justification": "已有奥希替尼耐药后方案数据(B级)"
                }}
            ]
        }},
        {{
            "id": "D2",
            "status": "in_progress",
            "priority": 1,
            "completeness": 60,
            "preferred_mode": "depth_first",
            "mode_reason": "有关键待深入项未覆盖，需深入研究",
            "evidence_assessment": "已找到肾功能剂量调整的初步数据(C/D级)，但缺少 FDA 标签中的具体剂量建议",
            "chain_analysis": "实体: DRUG(2)/DISEASE(1) 但无 VARIANT; 谓词: treats(1) 但缺少 interacts_with → 药物互作未评估",
            "deep_research_assessment": [
                {{
                    "item": "氟泽雷赛联合西妥昔单抗 ORR/PFS 数据",
                    "coverage": "uncovered",
                    "impact": "critical",
                    "justification": "患者正在使用该方案，缺少疗效数据直接影响治疗评估"
                }}
            ]
        }},
        {{
            "id": "D3",
            "status": "pending",
            "priority": 2,
            "completeness": 30,
            "preferred_mode": "breadth_first",
            "mode_reason": "完成度30%，需要广度收集更多初步证据",
            "evidence_assessment": "仅有 PubMed 文献中的间接证据(D级)，缺少指南级治疗方案对比数据",
            "chain_analysis": "实体: GENE(1) 仅单类型; 谓词: 仅 associated_with(2) → 实体类型和关系谓词均大面积缺失",
            "deep_research_assessment": []
        }}
    ],
    "new_directions": [],
    "decision": "continue",
    "reasoning": "决策理由...",
    "quality_assessment": {{
        "high_quality_coverage": ["模块1"],
        "low_quality_only": ["模块2"],
        "conflicts": []
    }},
    "gaps": ["空白1"],
    "next_priorities": ["优先事项1"]
}}
```

**preferred_mode 选择指南**:
- "skip": 证据已充分回答完成标准，且证据链结构完整（实体类型+关键谓词覆盖），待深入研究项已覆盖或仅剩 minor 级别的未覆盖项
- "breadth_first": 证据覆盖面不足，多个关键问题未涉及，或关键实体类型大面积缺失，需要广度收集
- "depth_first": 有初步发现但证据等级不够（只有 D/E 级），或有初步实体但关键关系未建立（如有 GENE+DRUG 但无 sensitizes 边），或存在证据冲突（contradicts 边）需要解决，或有 critical/important 级别的待深入研究项未覆盖

**chain_analysis 必须包含**:
1. 子图实体类型统计（从 canonical_id 前缀提取）
2. 子图关系谓词统计（从 edge predicate 提取）
3. 结构完整性判断（是否有关键缺失及其对 DFRS 判定的影响）

**evidence_assessment 必须包含**:
1. 已有证据要点（关键发现 + 等级）
2. 完成标准覆盖情况（已覆盖/未覆盖的关键点）
3. 综合充分性判断

**deep_research_assessment 格式要求**:
- 如该方向有「待深入研究项」，必须对每一项输出结构化评估
- coverage 取值: "covered" / "partial" / "uncovered"
- impact 取值: "critical" / "important" / "minor"
- justification: 说明判断依据
- 如无待深入研究项，输出空数组 []
"""

    def _format_agent_summaries(self, agent_summaries: Dict[str, Dict[str, Any]]) -> str:
        """格式化 agent 自述为 prompt 文本

        Args:
            agent_summaries: {agent_name: {summary, per_direction_analysis, agent_analysis, needs_deep_research}}

        Returns:
            格式化的自述文本
        """
        if not agent_summaries:
            return "（无 Agent 自述）"

        sections = []
        for agent_name, data in agent_summaries.items():
            lines = [f"#### {agent_name}"]

            # Agent 整体分析
            if data.get("agent_analysis"):
                lines.append(f"**整体分析**: {data['agent_analysis']}")

            # 摘要
            if data.get("summary"):
                summary = data['summary']
                lines.append(f"**摘要**: {summary}")

            # 每个方向的分析
            pda = data.get("per_direction_analysis", {})
            if pda:
                lines.append("**各方向分析**:")
                for d_id, analysis in pda.items():
                    what_found = analysis.get('what_found', 'N/A')
                    what_not_found = analysis.get('what_not_found', 'N/A')
                    conclusion = analysis.get('conclusion', 'N/A')
                    lines.append(f"  - **{d_id}**:")
                    lines.append(f"    - 已找到: {what_found}")
                    lines.append(f"    - 未找到: {what_not_found}")
                    lines.append(f"    - 结论: {conclusion}")
                    # 展示假设验证过程
                    hypotheses = analysis.get('hypotheses_explored', [])
                    if hypotheses:
                        lines.append(f"    - 假设验证:")
                        for h in hypotheses:
                            if isinstance(h, dict):
                                hyp = h.get('hypothesis', '')
                                result = h.get('result', '')
                                lines.append(f"      - [{result}] {hyp}")

            sections.append("\n".join(lines))

        return "\n\n".join(sections)

    def _build_direction_subgraph_context(
        self,
        direction: ResearchDirection,
        graph
    ) -> str:
        """为单个方向生成锚点+子图上下文（含锚点实体的 observation 文本）

        与 ResearchMixin 的 _build_direction_anchor_context() 类似，
        但额外包含 hop_distance=0 锚点实体的 observation 原文，供收敛评估验证。
        """
        entity_ids = direction.entity_ids
        if not entity_ids:
            return f"### {direction.id} ({direction.topic})\n暂无证据"

        logger.info(f"[PLAN_SUBGRAPH] 方向 {direction.id}: 锚点数={len(entity_ids)}")

        subgraph = graph.retrieve_subgraph(
            anchor_ids=entity_ids,
            max_hops=2,
            include_observations=True
        )

        entities = subgraph.get('entities', [])
        edges = subgraph.get('edges', [])

        logger.info(f"[PLAN_SUBGRAPH] 方向 {direction.id}: entities={len(entities)}, edges={len(edges)}")

        # 日志：hop 分布
        hop_map = subgraph.get('hop_map', {})
        hop_dist = {}
        for _, hop in hop_map.items():
            hop_dist[hop] = hop_dist.get(hop, 0) + 1
        logger.debug(f"[PLAN_SUBGRAPH] 方向 {direction.id}: hop分布={hop_dist}")

        if not entities:
            return f"### {direction.id} ({direction.topic})\n暂无证据"

        # 实体行（含统计：observation_count + best_grade）
        entity_strs = [
            f"{e['canonical_id']}({e['observation_count']}obs"
            + (f",{e['best_grade']}" if e.get('best_grade') else "")
            + ")"
            for e in entities
        ]

        lines = [
            f"### {direction.id}: {direction.topic}",
            f"**完成标准**: {direction.completion_criteria}",
            f"**实体** ({len(entities)}): {', '.join(entity_strs)}",
        ]

        # 关系边（图结构）
        if edges:
            lines.append(f"**关系** ({len(edges)}):")
            for e in edges:
                conf = f" ({e['confidence']:.2f})" if e.get('confidence') else ""
                lines.append(f"  {e['source_id']} → {e['predicate']} → {e['target_id']}{conf}")

        # 锚点实体的核心观察（仅 hop_distance=0 的直接锚点，避免 prompt 膨胀）
        obs_lines = []
        for e in entities:
            if e.get('hop_distance', 99) > 0:
                continue
            obs_list = e.get('observations', [])
            if not obs_list:
                continue
            obs_lines.append(f"  **{e['canonical_id']}**:")
            grade_order = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}
            sorted_obs = sorted(obs_list, key=lambda o: grade_order.get(o.get('evidence_grade') or 'E', 5))
            for obs in sorted_obs:
                grade = f"[{obs.get('evidence_grade', '?')}]"
                source = f" ({obs.get('source_tool', '')})" if obs.get('source_tool') else ""
                prov = f" — {obs.get('provenance', '')}" if obs.get('provenance') else ""
                obs_lines.append(f"    - {grade}{source} {obs.get('statement', '')}{prov}")

        if obs_lines:
            lines.append(f"**核心观察** (锚点实体):")
            lines.extend(obs_lines)

        return "\n".join(lines)

    def _build_direction_evidence_details(
        self, plan: ResearchPlan, graph, relevant_direction_ids: set,
        deep_by_direction: Dict[str, List[Dict[str, str]]] = None
    ) -> str:
        """为每个方向生成证据子图详情（锚点+子图结构+锚点实体 observation）"""
        if not graph:
            return "无证据图谱数据"

        if deep_by_direction is None:
            deep_by_direction = {}

        sections = []
        for direction in plan.directions:
            if direction.id not in relevant_direction_ids:
                continue

            # 使用锚点+子图方案（替换原来的 get_direction_evidence_summary）
            subgraph_context = self._build_direction_subgraph_context(direction, graph)
            sections.append(subgraph_context)
            sections.append("")

            # 该方向的待深入研究项
            dir_deep = deep_by_direction.get(direction.id, [])
            # 也包含未关联到具体方向的项（direction_id 为空）
            if not dir_deep:
                dir_deep = []
            if dir_deep:
                sections.append("**待深入研究项**:")
                for item in dir_deep:
                    agent = item.get("agent", "")
                    finding = item.get("finding", "")
                    reason = item.get("reason", "")
                    reason_str = f" — {reason}" if reason else ""
                    sections.append(f"- [{agent}] {finding}{reason_str}")
                sections.append("")

        # 显示未关联到方向的待深入研究项
        unassigned = deep_by_direction.get("", [])
        if unassigned:
            sections.append("#### 未关联方向的待深入研究项")
            for item in unassigned:
                agent = item.get("agent", "")
                finding = item.get("finding", "")
                reason = item.get("reason", "")
                reason_str = f" — {reason}" if reason else ""
                sections.append(f"- [{agent}] {finding}{reason_str}")
            sections.append("")

        return "\n".join(sections) if sections else "暂无证据数据"

    def _format_direction_stats(self, stats: Dict[str, Dict[str, Any]]) -> str:
        """格式化方向统计为 Markdown 表格"""
        lines = ["| ID | 主题 | Agent | 证据数 | A | B | C | D | E | 加权分 | 完成度 | 状态 |",
                 "|:---|:-----|:------|:-------|:--|:--|:--|:--|:--|:-------|:-------|:-----|"]

        for d_id, s in stats.items():
            gd = s["grade_distribution"]
            lines.append(
                f"| {d_id} | {s['topic']} | {s['target_agent']} | "
                f"{s['evidence_count']} | {gd['A']} | {gd['B']} | {gd['C']} | {gd['D']} | {gd['E']} | "
                f"{s['weighted_score']:.1f} | {s['completeness']:.0f}% | {s['status']} |"
            )

        return "\n".join(lines)

    def _parse_evaluation_output(
        self,
        output: str,
        plan: ResearchPlan,
        direction_stats: Dict[str, Dict[str, Any]],
        needs_deep_research: List[Dict[str, str]] = None,
        phase: str = ""
    ) -> Dict[str, Any]:
        """解析 LLM 评估输出"""

        # 提取 JSON
        json_str = self._extract_json(output)

        if not json_str:
            logger.warning(f"[{self.role}] 无法从评估输出中提取 JSON，使用默认值")
            return self._create_default_evaluation(plan, direction_stats, needs_deep_research=needs_deep_research)

        try:
            data = json.loads(json_str)

            # 更新研究计划（包括每个方向的 preferred_mode）
            updated_directions = data.get("updated_directions", [])

            # 应用待深入研究项惩罚（与 fallback 路径一致）
            deep_by_direction = {}
            if needs_deep_research:
                for item in needs_deep_research:
                    d_id = item.get("direction_id", "")
                    if d_id not in deep_by_direction:
                        deep_by_direction[d_id] = []
                    deep_by_direction[d_id].append(item)

            for u in updated_directions:
                d_id = u.get("id", "")
                if not d_id:
                    continue
                dir_deep = deep_by_direction.get(d_id, [])
                if dir_deep:
                    original_completeness = u.get("completeness", 0)
                    deep_penalty = len(dir_deep) * 10
                    u["completeness"] = max(original_completeness - deep_penalty, 0)

            updated_plan = self._apply_direction_updates(plan, updated_directions)

            # 提取各方向证据评估 + 待深入研究项评估（用于报告展示）
            direction_assessments = {}
            for u in updated_directions:
                d_id = u.get("id", "")
                if not d_id:
                    continue
                direction_assessments[d_id] = {
                    "evidence_assessment": u.get("evidence_assessment", ""),
                    "deep_research_assessment": u.get("deep_research_assessment", []),
                }

            # 添加新方向（如果有，需校验 target_agent 属于当前 phase）
            new_directions = data.get("new_directions", [])
            if new_directions:
                allowed_agents = PHASE_AGENT_MAP.get(phase, set())
                for nd in new_directions:
                    target_agent = nd.get("target_agent", "")
                    if allowed_agents and target_agent not in allowed_agents:
                        logger.warning(
                            f"[{self.role}] 新方向 '{nd.get('id', '?')}' 的 target_agent='{target_agent}' "
                            f"不属于当前 phase '{phase}' 的 agent 列表 {allowed_agents}，已跳过"
                        )
                        continue
                    updated_plan.directions.append(ResearchDirection.from_dict(nd))

            return {
                "research_plan": updated_plan.to_dict(),
                "decision": data.get("decision", "continue"),
                "reasoning": data.get("reasoning", ""),
                "quality_assessment": data.get("quality_assessment", {}),
                "gaps": data.get("gaps", []),
                "next_priorities": data.get("next_priorities", []),
                "direction_assessments": direction_assessments,
            }

        except json.JSONDecodeError as e:
            logger.warning(f"[{self.role}] JSON 解析失败: {e}，使用默认值")
            return self._create_default_evaluation(plan, direction_stats, needs_deep_research=needs_deep_research)

    def _apply_direction_updates(
        self,
        plan: ResearchPlan,
        updates: List[Dict[str, Any]]
    ) -> ResearchPlan:
        """应用方向更新到研究计划"""

        update_map = {u["id"]: u for u in updates}

        for direction in plan.directions:
            if direction.id in update_map:
                update = update_map[direction.id]

                # 更新状态
                if "status" in update:
                    direction.status = DirectionStatus(update["status"])

                # 更新优先级
                if "priority" in update:
                    direction.priority = update["priority"]

                # 更新研究模式 (新增)
                if "preferred_mode" in update:
                    direction.preferred_mode = update["preferred_mode"]

                # 更新模式选择理由 (新增)
                if "mode_reason" in update:
                    direction.mode_reason = update["mode_reason"]

                # 传播深入研究信息
                if "needs_deep_research" in update:
                    direction.needs_deep_research = update["needs_deep_research"]
                if "deep_research_findings" in update:
                    direction.deep_research_findings = update["deep_research_findings"]

                # 如果 preferred_mode == depth_first 但未显式设置 deep 字段，
                # 则从 deep_research_assessment 自动提取
                if update.get("preferred_mode") == "depth_first" and not direction.needs_deep_research:
                    deep_assessment = update.get("deep_research_assessment", [])
                    actionable = [
                        item.get("item", "")
                        for item in deep_assessment
                        if isinstance(item, dict)
                        and item.get("coverage") in ("uncovered", "partial")
                        and item.get("impact") in ("critical", "important")
                    ]
                    if actionable:
                        direction.needs_deep_research = True
                        direction.deep_research_findings = actionable
                    elif update.get("mode_reason"):
                        direction.needs_deep_research = True
                        direction.deep_research_findings = [update["mode_reason"]]
                elif update.get("preferred_mode") == "skip":
                    direction.needs_deep_research = False
                    direction.deep_research_findings = []

        return plan

    def _create_default_evaluation(
        self,
        plan: ResearchPlan,
        direction_stats: Dict[str, Dict[str, Any]],
        needs_deep_research: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """创建默认评估结果（当 LLM 解析失败时）"""

        # 按方向分组 needs_deep_research
        deep_by_direction = {}
        if needs_deep_research:
            for item in needs_deep_research:
                d_id = item.get("direction_id", "")
                if d_id not in deep_by_direction:
                    deep_by_direction[d_id] = []
                deep_by_direction[d_id].append(item)

        has_low_quality_only = any(
            s["low_quality_only"]
            for s in direction_stats.values()
        )

        # 更新方向状态，并为每个方向设置独立的研究模式
        updated_directions = []
        direction_assessments = {}
        for d_id, s in direction_stats.items():
            completeness = s["completeness"]
            has_high_quality = s["has_high_quality"]
            low_quality_only = s["low_quality_only"]
            dir_deep = deep_by_direction.get(d_id, [])

            # 有待深入研究项的方向，完成度打折（每项扣 10%，无上限）
            if dir_deep:
                deep_penalty = len(dir_deep) * 10
                completeness = max(completeness - deep_penalty, 0)

            # 确定状态（使用打折后的完成度）
            status = "completed" if completeness >= CONVERGENCE_COMPLETENESS_THRESHOLD else "in_progress"

            # 确定每个方向的研究模式
            if dir_deep:
                # 该方向有待深入研究项 → 强制 depth_first
                preferred_mode = "depth_first"
                deep_items_str = "; ".join(item.get("finding", "") for item in dir_deep)
                mode_reason = f"有{len(dir_deep)}项待深入研究: {deep_items_str}"
            elif completeness >= CONVERGENCE_COMPLETENESS_THRESHOLD and has_high_quality:
                preferred_mode = "skip"
                mode_reason = f"完成度{completeness:.0f}%，有高质量证据，无需继续研究"
            elif completeness < CONTINUE_COMPLETENESS_THRESHOLD:
                preferred_mode = "breadth_first"
                mode_reason = f"完成度{completeness:.0f}%，需要广度收集更多初步证据"
            elif low_quality_only:
                preferred_mode = "depth_first"
                mode_reason = f"完成度{completeness:.0f}%但只有D/E级证据，需深入找高质量证据"
            else:
                preferred_mode = "depth_first"
                mode_reason = f"完成度{completeness:.0f}%，需深入完善证据"

            # 生成默认 direction_assessments（与 LLM 路径格式一致）
            gd = s["grade_distribution"]
            grade_parts = []
            for g in ["A", "B", "C", "D", "E"]:
                if gd[g] > 0:
                    grade_parts.append(f"{g}级{gd[g]}条")
            grade_str = "、".join(grade_parts) if grade_parts else "无证据"

            evidence_text = (
                f"完成度{completeness:.0f}%，证据{s['evidence_count']}条（{grade_str}），"
                f"模式: {preferred_mode}"
            )

            # 生成默认 deep_research_assessment
            default_deep_assessment = []
            if dir_deep:
                for item in dir_deep:
                    default_deep_assessment.append({
                        "item": item.get("finding", item.get("reason", "")),
                        "coverage": "uncovered",
                        "impact": "important",  # default 路径无法判断，保守标记为 important
                        "justification": f"[{item.get('agent', '')}] {item.get('reason', '待深入研究')}",
                    })

            updated_directions.append({
                "id": d_id,
                "status": status,
                "priority": s["priority"],
                "completeness": completeness,
                "preferred_mode": preferred_mode,
                "mode_reason": mode_reason,
                "needs_deep_research": bool(dir_deep) or preferred_mode == "depth_first",
                "deep_research_findings": [item.get("finding", "") for item in dir_deep] if dir_deep else [],
                "deep_research_assessment": default_deep_assessment,
            })

            direction_assessments[d_id] = {
                "evidence_assessment": evidence_text,
                "deep_research_assessment": default_deep_assessment,
            }

        # 应用更新
        updated_plan = self._apply_direction_updates(plan, updated_directions)

        # 基于惩罚后的完成度判断是否全部完成
        all_complete = all(
            ud["completeness"] >= CONVERGENCE_COMPLETENESS_THRESHOLD
            for ud in updated_directions
        )

        # 决策（完成度已含 needs_deep_research 惩罚）
        if all_complete and not has_low_quality_only:
            decision = "converged"
            reasoning = "所有方向完成度达标，且有足够高质量证据"
        else:
            decision = "continue"
            reasons = []
            if not all_complete:
                reasons.append("存在未完成方向")
            if has_low_quality_only:
                reasons.append("存在只有低质量证据的方向")
            reasoning = "；".join(reasons) if reasons else "存在未完成方向或只有低质量证据的方向"

        return {
            "research_plan": updated_plan.to_dict(),
            "decision": decision,
            "reasoning": reasoning,
            "quality_assessment": {
                "high_quality_coverage": [
                    s["topic"] for s in direction_stats.values() if s["has_high_quality"]
                ],
                "low_quality_only": [
                    s["topic"] for s in direction_stats.values() if s["low_quality_only"]
                ],
                "conflicts": []
            },
            "gaps": [
                s["topic"] for s in direction_stats.values()
                if s["completeness"] < CONTINUE_COMPLETENESS_THRESHOLD
            ],
            "next_priorities": [
                s["topic"] for s in direction_stats.values()
                if s["low_quality_only"] or s["completeness"] < CONTINUE_COMPLETENESS_THRESHOLD
            ],
            "direction_assessments": direction_assessments,
        }

    # ==================== Phase 2 方向生成 ====================

    def generate_phase2_directions(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于 Phase 1 结果生成 Phase 2 (Oncologist) 研究方向

        Args:
            state: 当前工作流状态，包含：
                - evidence_graph: Phase 1 收集的证据图
                - pathologist_report: 完整病理报告
                - geneticist_report: 完整遗传学报告
                - recruiter_report: 完整临床试验报告
                - raw_pdf_text: 原始病历
                - research_plan: 当前研究计划

        Returns:
            更新后的 research_plan（替换 Oncologist 方向）
        """
        logger.info(f"[{self.role}] 开始生成 Phase 2 研究方向...")

        # 获取 Phase 1 完整报告（不截断）
        pathologist_report = state.get("pathologist_report", "")
        geneticist_report = state.get("geneticist_report", "")
        recruiter_report = state.get("recruiter_report", "")
        raw_pdf_text = state.get("raw_pdf_text", "")

        # 获取证据图摘要
        graph = load_evidence_graph(state.get("evidence_graph", {}))
        graph_summary = graph.summary() if graph else {}

        # 获取当前研究计划
        current_plan = load_research_plan(state.get("research_plan", {}))

        # 构建提示
        prompt = self._build_phase2_prompt(
            raw_pdf_text=raw_pdf_text,
            pathologist_report=pathologist_report,
            geneticist_report=geneticist_report,
            recruiter_report=recruiter_report,
            graph_summary=graph_summary
        )

        # 调用 LLM
        result = self.invoke(prompt)
        output = result.get("output", "")

        # 解析输出
        new_directions = self._parse_phase2_output(output)

        # 更新研究计划：移除旧的 Oncologist 方向，添加新方向
        updated_plan = self._update_plan_with_phase2_directions(current_plan, new_directions)

        logger.info(f"[{self.role}] Phase 2 方向生成完成: {len(new_directions)} 个方向")

        return updated_plan.to_dict()

    def _build_phase2_prompt(
        self,
        raw_pdf_text: str,
        pathologist_report: str,
        geneticist_report: str,
        recruiter_report: str,
        graph_summary: Dict[str, Any]
    ) -> str:
        """构建 Phase 2 方向生成提示"""

        # 读取 Phase 2 prompt 模板
        from pathlib import Path
        prompt_file = Path("config/prompts/phase2_plan_prompt.txt")
        if prompt_file.exists():
            base_prompt = prompt_file.read_text(encoding="utf-8")
        else:
            base_prompt = "基于 Phase 1 结果生成 Oncologist 研究方向。"

        # 构建完整提示
        return f"""{base_prompt}

---

## Phase 1 完整报告

### Pathologist 报告
{pathologist_report}

### Geneticist 报告
{geneticist_report}

### Recruiter 报告（临床试验匹配）
{recruiter_report}

---

## 证据图统计摘要
- 总实体数: {graph_summary.get('total_entities', 0)}
- 总边数: {graph_summary.get('total_edges', 0)}
- 总观察数: {graph_summary.get('total_observations', 0)}
- 实体类型分布: {graph_summary.get('entities_by_type', {})}
- 证据等级分布: {graph_summary.get('best_grades', {})}

---

## 原始病历（参考）
{raw_pdf_text}...

---

请基于以上 Phase 1 完整报告和原始病历，生成针对性的 Oncologist 研究方向。注意：研究方向不限于 Phase 1 发现，也应覆盖原始病历中的患者临床特征和标准临床实践需求。
"""

    def _parse_phase2_output(self, output: str) -> List[Dict[str, Any]]:
        """解析 Phase 2 方向生成输出"""
        json_str = self._extract_json(output)

        if not json_str:
            logger.warning(f"[{self.role}] 无法从 Phase 2 输出中提取 JSON，使用默认方向")
            return self._get_default_phase2_directions()

        try:
            data = json.loads(json_str)
            directions = data.get("phase2_directions", [])

            if not directions:
                logger.warning(f"[{self.role}] Phase 2 输出无方向，使用默认方向")
                return self._get_default_phase2_directions()

            return directions

        except json.JSONDecodeError as e:
            logger.warning(f"[{self.role}] Phase 2 JSON 解析失败: {e}，使用默认方向")
            return self._get_default_phase2_directions()

    def _get_default_phase2_directions(self) -> List[Dict[str, Any]]:
        """获取默认的 Phase 2 方向（备用）"""
        return [
            {
                "id": "P2_D1",
                "topic": "一线治疗方案评估",
                "target_agent": "Oncologist",
                "target_modules": ["方案对比"],
                "priority": 1,
                "queries": ["first-line treatment", "NCCN guidelines"],
                "completion_criteria": "完成一线方案证据对比"
            },
            {
                "id": "P2_D2",
                "topic": "器官功能与剂量调整",
                "target_agent": "Oncologist",
                "target_modules": ["器官功能与剂量"],
                "priority": 2,
                "queries": ["renal dose adjustment", "hepatic impairment"],
                "completion_criteria": "完成剂量调整建议"
            },
            {
                "id": "P2_D3",
                "topic": "治疗路线图制定",
                "target_agent": "Oncologist",
                "target_modules": ["治疗路线图"],
                "priority": 2,
                "queries": ["treatment sequence", "second-line options"],
                "completion_criteria": "完成完整治疗路线图"
            },
            {
                "id": "P2_D4",
                "topic": "局部治疗评估",
                "target_agent": "Oncologist",
                "target_modules": ["局部治疗建议"],
                "priority": 3,
                "queries": ["SBRT", "palliative radiotherapy"],
                "completion_criteria": "评估局部治疗适应症"
            }
        ]

    def _update_plan_with_phase2_directions(
        self,
        plan: ResearchPlan,
        new_directions: List[Dict[str, Any]]
    ) -> ResearchPlan:
        """更新研究计划，添加 Phase 2 Oncologist 方向（Phase 1 不含 Oncologist 方向）"""

        for d_data in new_directions:
            direction = ResearchDirection(
                id=d_data.get("id", f"P2_D{len(plan.directions) + 1}"),
                topic=d_data.get("topic", ""),
                target_agent="Oncologist",
                target_modules=d_data.get("target_modules", []),
                priority=d_data.get("priority", 1),
                queries=d_data.get("queries", []),
                status=DirectionStatus.PENDING,
                completion_criteria=d_data.get("completion_criteria", ""),
                entity_ids=[],
                preferred_mode="breadth_first",
                mode_reason="Phase 2 新方向，需要广度收集证据"
            )
            plan.directions.append(direction)

        return plan


    def generate_phase2a_directions(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 2a 研究方向生成: 治疗 Mapping

        读取 Phase1 的 4 份报告 + evidence_graph，为 5 个 agent 生成 Phase2a 方向
        """
        from src.models.evidence_graph import EvidenceGraph

        pathologist_report = state.get("pathologist_report", "")
        geneticist_report = state.get("geneticist_report", "")
        pharmacist_report = state.get("pharmacist_report", "")
        oncologist_analysis = state.get("oncologist_analysis_report", "")

        eg_data = state.get("evidence_graph", {})
        if isinstance(eg_data, dict):
            eg = EvidenceGraph.from_dict(eg_data)
            graph_summary = eg.summary()
        else:
            graph_summary = str(eg_data.summary()) if hasattr(eg_data, "summary") else "{}"

        phase1_context = (
            f"病理学报告:\n{pathologist_report}\n\n"
            f"遗传学报告:\n{geneticist_report}\n\n"
            f"药师报告(合并症/用药):\n{pharmacist_report}\n\n"
            f"过往治疗分析(3.1):\n{oncologist_analysis}\n\n"
            f"证据图摘要:\n{graph_summary}"
        )

        prompt = (
            "请基于 Phase 1 的研究结果，为 Phase 2a (治疗 Mapping) 生成研究方向。\n\n"
            f"**Phase 1 报告**:\n{phase1_context}\n\n"
            "**Phase 2a 涉及的 Agent 和角色**:\n"
            "1. Oncologist (Mapping模式): 全身治疗手段Mapping，按4审批×5手段=20格矩阵，只罗列分析不做推荐\n"
            "2. LocalTherapist: 手术评估(根治/姑息) + 放疗方案(普通/SBRT/质子/BNCT) + 介入治疗(消融/粒子/HIFU)\n"
            "3. Recruiter: 临床试验(c有试验可入组 + d无试验但临床阶段)，含已结束试验及结果\n"
            "4. Nutritionist: 营养状态评估 + 癌种饮食建议 + 治疗期营养管理\n"
            "5. IntegrativeMed: 替代疗法逐一评估(吸氢/大剂量VC/中医/免疫调节等)\n\n"
            "**CRITICAL - target_modules 必须使用以下确切名称**:\n"
            "| Agent | target_modules |\n"
            "|-------|----------------|\n"
            '| Oncologist | ["治疗方案探索"] |\n'
            '| LocalTherapist | ["治疗方案探索"] |\n'
            '| Recruiter | ["治疗方案探索"] |\n'
            '| Nutritionist | ["整体与辅助支持"] |\n'
            '| IntegrativeMed | ["整体与辅助支持"] |\n\n'
            "**输出格式**: 严格按照 JSON 格式输出研究方向列表:\n"
            "```json\n"
            '{"directions": [{"id": "D_xxx", "topic": "主题", "target_agent": "Oncologist", '
            '"target_modules": ["治疗方案探索"], "priority": 1, "queries": ["查询词"], '
            '"completion_criteria": "完成标准"}]}\n'
            "```\n\n"
            "基于 Phase 1 发现的癌种、突变谱、治疗史，为每个 Agent 分配 1-3 个具体研究方向。\n\n"
            "**定制化要求**:\n"
            "- topic 必须引用 Phase 1 发现的具体基因、药物、合并症（如 '肺转移灶 SBRT 可行性 - CrCl 39 限制下的方案选择'）\n"
            "- queries 必须包含可直接用于工具查询的具体术语（如 'KRAS G12C CRC SBRT oligometastatic'），不要使用泛化词汇\n"
            "- completion_criteria 必须引用具体临床决策点（如 '明确 CrCl<40 患者是否可安全使用 TAS-102'）\n"
            "- 方向 ID 应反映具体研究内容（如 D_LUNG_METS_SBRT），不要使用泛化 ID（如 D_LOCAL_THERAPY）\n"
            "- 根据病情复杂度调整方向数量：每个 Agent 1-2 个方向（简单）或 2-3 个（复杂）\n"
            "- **target_modules 必须严格按照上表使用，不可自创**"
        )

        try:
            result = self.invoke(prompt)
            output = result.get("output", "")

            import re
            json_match = re.search(r'\{[\s\S]*\}', output)
            if json_match:
                import json
                parsed = json.loads(json_match.group())
                directions = parsed.get("directions", [])
            else:
                directions = self._get_default_phase2a_directions(state)
        except Exception as e:
            logger.warning(f"[PLAN_AGENT] Phase 2a 方向生成失败，使用默认方向: {e}")
            directions = self._get_default_phase2a_directions(state)

        current_plan = state.get("research_plan", {})
        if isinstance(current_plan, dict):
            plan_data = current_plan.copy()
        else:
            plan_data = current_plan.to_dict() if hasattr(current_plan, "to_dict") else {}

        plan_data["directions"] = directions
        plan_data["phase"] = "phase_2a"

        return {
            "research_plan": plan_data,
            "current_phase": "phase_2a",
            "current_phase_description": "治疗Mapping",
            "current_phase_iteration": 0,
            "current_phase_max_iterations": MAX_PHASE2A_ITERATIONS,
            "phase2a_iteration": 0,
        }

    def _get_default_phase2a_directions(self, state: Dict[str, Any]) -> list:
        """Phase 2a 默认方向（LLM 生成失败时的回退，尽量从 state 提取患者信息）"""
        rp = state.get("research_plan", {})
        if isinstance(rp, dict):
            key_entities = rp.get("key_entities", {})
            cancer_types = key_entities.get("cancer_type", [])
            cancer_type = ", ".join(cancer_types) if cancer_types else rp.get("case_summary", "肿瘤")[:50]
            genes = key_entities.get("genes", [])
            key_genes = ", ".join(genes[:3]) if genes else ""
            drugs = key_entities.get("drugs_mentioned", [])
        else:
            cancer_type, key_genes = "肿瘤", ""
            genes, drugs = [], []

        # 构建患者特异的 queries 后缀
        gene_queries = [f"{g} targeted therapy" for g in genes[:2]] if genes else []
        drug_queries = [f"{d} {cancer_type}" for d in drugs[:2]] if drugs else []

        return [
            {
                "id": "D_SYSTEMIC_THERAPY",
                "topic": f"全身治疗手段Mapping - {cancer_type}" + (f" ({key_genes})" if key_genes else ""),
                "target_agent": "Oncologist",
                "target_modules": ["治疗方案探索"],
                "priority": 1,
                "queries": [f"{cancer_type} standard treatment", f"{cancer_type} targeted therapy",
                            f"{cancer_type} immunotherapy", f"{cancer_type} chemotherapy"] + gene_queries[:2],
                "completion_criteria": f"完成 {cancer_type} 的4审批×5手段=20格全身治疗矩阵"
            },
            {
                "id": "D_SURGERY",
                "topic": f"{cancer_type} 手术评估",
                "target_agent": "LocalTherapist",
                "target_modules": ["治疗方案探索"],
                "priority": 2,
                "queries": [f"{cancer_type} surgery indication", f"{cancer_type} resection", "palliative surgery"],
                "completion_criteria": f"完成 {cancer_type} 手术可行性评估（根治 vs 姑息）"
            },
            {
                "id": "D_RADIATION",
                "topic": f"{cancer_type} 放疗方案评估",
                "target_agent": "LocalTherapist",
                "target_modules": ["治疗方案探索"],
                "priority": 2,
                "queries": [f"{cancer_type} radiation therapy", f"{cancer_type} SBRT", "proton therapy"],
                "completion_criteria": f"完成 {cancer_type} 放疗方案对比评估（普通/SBRT/质子/BNCT）"
            },
            {
                "id": "D_INTERVENTION",
                "topic": f"{cancer_type} 介入治疗评估",
                "target_agent": "LocalTherapist",
                "target_modules": ["治疗方案探索"],
                "priority": 3,
                "queries": [f"{cancer_type} ablation", "radiofrequency ablation", "microwave ablation"],
                "completion_criteria": f"完成 {cancer_type} 介入治疗可行性评估（消融/粒子/HIFU）"
            },
            {
                "id": "D_TRIALS_ACTIVE",
                "topic": f"{cancer_type} 活跃临床试验匹配" + (f" ({key_genes})" if key_genes else ""),
                "target_agent": "Recruiter",
                "target_modules": ["治疗方案探索"],
                "priority": 1,
                "queries": [f"{cancer_type} clinical trial"] + gene_queries[:1] + drug_queries[:1],
                "completion_criteria": f"匹配至少5个针对 {cancer_type} 的可行临床试验"
            },
            {
                "id": "D_TRIALS_COMPLETED",
                "topic": f"{cancer_type} 已结束试验及结果" + (f" ({key_genes})" if key_genes else ""),
                "target_agent": "Recruiter",
                "target_modules": ["治疗方案探索"],
                "priority": 2,
                "queries": [f"{cancer_type} completed trial results"] + drug_queries[:1],
                "completion_criteria": f"列出 {cancer_type} 相关已结束试验及结果摘要"
            },
            {
                "id": "D_NUTRITION",
                "topic": f"{cancer_type} 营养评估与方案",
                "target_agent": "Nutritionist",
                "target_modules": ["整体与辅助支持"],
                "priority": 2,
                "queries": [f"{cancer_type} nutrition", "cancer cachexia", "nutritional support oncology"],
                "completion_criteria": f"完成 {cancer_type} 营养状态评估和癌种特异饮食方案"
            },
            {
                "id": "D_ALTERNATIVE",
                "topic": f"{cancer_type} 替代疗法评估",
                "target_agent": "IntegrativeMed",
                "target_modules": ["整体与辅助支持"],
                "priority": 3,
                "queries": [f"{cancer_type} complementary therapy", "integrative oncology", "traditional Chinese medicine cancer"],
                "completion_criteria": f"完成 {cancer_type} 每种替代疗法（吸氢/大剂量VC/中医/免疫调节）的逐一评估"
            },
        ]

    def generate_phase2b_directions(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 2b 研究方向生成: 药学审查

        读取 Phase2a 的 5 份报告，为 Pharmacist(Review模式) 生成审查方向。
        方向 ID 固定为 3 个审查类别，但 topic/queries/completion_criteria 由 LLM 定制。
        """
        import re as _re

        # 提取患者上下文
        rp = state.get("research_plan", {})
        key_entities = rp.get("key_entities", {}) if isinstance(rp, dict) else {}
        case_summary = rp.get("case_summary", "") if isinstance(rp, dict) else ""
        oncologist_mapping = state.get("oncologist_mapping_report", "")
        pharmacist_baseline = state.get("pharmacist_report", "")

        # 构造 LLM 定制化 prompt
        prompt = (
            "你是药学审查方向定制专家。基于以下患者信息，为 3 个固定药学审查方向定制患者特异的 topic、queries、completion_criteria。\n\n"
            f"**患者概要**: {case_summary}\n"
            f"**关键药物**: {json.dumps(key_entities.get('drugs_mentioned', []), ensure_ascii=False)}\n"
            f"**关键基因**: {json.dumps(key_entities.get('genes', []), ensure_ascii=False)}\n"
            f"**Oncologist Mapping 摘要（前2000字）**: {oncologist_mapping[:2000]}\n"
            f"**药师基线报告摘要（前1000字）**: {pharmacist_baseline[:1000]}\n\n"
            "请严格按以下 JSON 格式输出，定制 3 个方向的内容：\n"
            "```json\n"
            '{"directions": [\n'
            '  {"id": "D_DRUG_INTERACTION_REVIEW", "topic": "包含具体药物名的互作审查主题", '
            '"queries": ["具体药物名 drug interaction", ...], "completion_criteria": "具体的完成标准"},\n'
            '  {"id": "D_DOSE_ADJUSTMENT_REVIEW", "topic": "包含具体器官功能状态的剂量调整主题", '
            '"queries": ["具体药物 dose renal impairment", ...], "completion_criteria": "..."},\n'
            '  {"id": "D_CONTRAINDICATION_REVIEW", "topic": "包含具体禁忌/超适应症的审查主题", '
            '"queries": ["具体药物 contraindication", ...], "completion_criteria": "..."}\n'
            "]}\n"
            "```\n\n"
            "要求:\n"
            "- topic 必须包含具体候选药物名和患者特征（如器官功能状态、合并症）\n"
            "- queries 必须可直接用于 FDALabel/RxNorm 查询（英文药物名）\n"
            "- completion_criteria 必须引用具体药物和患者临床问题"
        )

        try:
            result = self.invoke(prompt)
            output = result.get("output", "")
            json_match = _re.search(r'\{[\s\S]*\}', output)
            if json_match:
                parsed = json.loads(json_match.group())
                customized = parsed.get("directions", [])
                if len(customized) == 3:
                    # 强制保持结构字段不变，只取 LLM 定制的内容字段
                    expected_ids = ["D_DRUG_INTERACTION_REVIEW", "D_DOSE_ADJUSTMENT_REVIEW", "D_CONTRAINDICATION_REVIEW"]
                    for i, d in enumerate(customized):
                        d["id"] = expected_ids[i] if i < len(expected_ids) else d.get("id", expected_ids[0])
                        d["target_agent"] = "Pharmacist"
                        d["target_modules"] = ["治疗方案探索"]
                        d["priority"] = 1
                    directions = customized
                    logger.info(f"[PLAN_AGENT] Phase 2b 方向已定制化: {[d['topic'][:30] for d in directions]}")
                else:
                    logger.warning(f"[PLAN_AGENT] Phase 2b LLM 返回 {len(customized)} 个方向（期望3个），使用默认")
                    directions = self._get_default_phase2b_directions()
            else:
                logger.warning("[PLAN_AGENT] Phase 2b LLM 输出无法解析 JSON，使用默认")
                directions = self._get_default_phase2b_directions()
        except Exception as e:
            logger.warning(f"[PLAN_AGENT] Phase 2b 方向定制失败，使用默认: {e}")
            directions = self._get_default_phase2b_directions()

        current_plan = state.get("research_plan", {})
        if isinstance(current_plan, dict):
            plan_data = current_plan.copy()
        else:
            plan_data = current_plan.to_dict() if hasattr(current_plan, "to_dict") else {}

        plan_data["directions"] = directions
        plan_data["phase"] = "phase_2b"

        return {
            "research_plan": plan_data,
            "current_phase": "phase_2b",
            "current_phase_description": "药学审查",
            "current_phase_iteration": 0,
            "current_phase_max_iterations": MAX_PHASE2B_ITERATIONS,
            "phase2b_iteration": 0,
        }

    def _get_default_phase2b_directions(self) -> list:
        """Phase 2b 默认方向（LLM 定制失败时的回退）"""
        return [
            {
                "id": "D_DRUG_INTERACTION_REVIEW",
                "topic": "药物交互风险审查",
                "target_agent": "Pharmacist",
                "target_modules": ["治疗方案探索"],
                "priority": 1,
                "queries": ["drug interaction", "药物相互作用"],
                "completion_criteria": "完成所有候选药物的交互风险评估"
            },
            {
                "id": "D_DOSE_ADJUSTMENT_REVIEW",
                "topic": "肝肾功能剂量调整审查",
                "target_agent": "Pharmacist",
                "target_modules": ["治疗方案探索"],
                "priority": 1,
                "queries": ["dose adjustment", "renal impairment", "hepatic impairment"],
                "completion_criteria": "完成所有候选药物的剂量调整建议"
            },
            {
                "id": "D_CONTRAINDICATION_REVIEW",
                "topic": "禁忌症和超适应症标注",
                "target_agent": "Pharmacist",
                "target_modules": ["治疗方案探索"],
                "priority": 1,
                "queries": ["contraindication", "off-label use"],
                "completion_criteria": "完成所有候选药物的禁忌症标注和超适应症伦理/审批要求"
            },
        ]

    def generate_phase3_directions(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 3 研究方向生成: 方案整合

        读取 Phase1+2a+2b 全部产出，为 Oncologist(Integration模式) 生成方向。
        方向 ID 固定为 3 个整合类别，但 topic/queries/completion_criteria 由 LLM 定制。
        """
        import re as _re

        # 提取患者上下文
        rp = state.get("research_plan", {})
        key_entities = rp.get("key_entities", {}) if isinstance(rp, dict) else {}
        case_summary = rp.get("case_summary", "") if isinstance(rp, dict) else ""
        oncologist_mapping = state.get("oncologist_mapping_report", "")
        pharmacist_review = state.get("pharmacist_review_report", "")

        # 构造 LLM 定制化 prompt
        prompt = (
            "你是治疗方案整合方向定制专家。基于以下患者信息，为 3 个固定整合方向定制患者特异的 topic、queries、completion_criteria。\n\n"
            f"**患者概要**: {case_summary}\n"
            f"**关键药物**: {json.dumps(key_entities.get('drugs_mentioned', []), ensure_ascii=False)}\n"
            f"**关键基因**: {json.dumps(key_entities.get('genes', []), ensure_ascii=False)}\n"
            f"**关键变异**: {json.dumps(key_entities.get('variants', []), ensure_ascii=False)}\n"
            f"**Mapping 摘要（前2000字）**: {oncologist_mapping[:2000]}\n"
            f"**药学审查摘要（前1500字）**: {pharmacist_review[:1500]}\n\n"
            "请严格按以下 JSON 格式输出，定制 3 个方向的内容：\n"
            "```json\n"
            '{"directions": [\n'
            '  {"id": "D_TREATMENT_PLAN_L1L5", "topic": "包含具体治疗方案名的L1-L5分层主题", '
            '"queries": ["具体方案名 evidence level", ...], "completion_criteria": "具体的完成标准"},\n'
            '  {"id": "D_PATHWAY_RANKING", "topic": "包含具体路径选项的排序主题", '
            '"queries": ["具体方案 vs 方案 comparison", ...], "completion_criteria": "..."},\n'
            '  {"id": "D_FOLLOWUP_TIMELINE", "topic": "包含具体监测指标的复查主题", '
            '"queries": ["具体癌种 surveillance guideline", ...], "completion_criteria": "..."}\n'
            "]}\n"
            "```\n\n"
            "要求:\n"
            "- topic 必须包含具体治疗方案名（如 '氟泽雷赛联合西妥昔单抗 vs TAS-102 L1-L5证据分层'）\n"
            "- queries 必须可直接用于 NCCN/PubMed 查询\n"
            "- completion_criteria 必须引用具体的方案对比和决策点"
        )

        try:
            result = self.invoke(prompt)
            output = result.get("output", "")
            json_match = _re.search(r'\{[\s\S]*\}', output)
            if json_match:
                parsed = json.loads(json_match.group())
                customized = parsed.get("directions", [])
                if len(customized) == 3:
                    expected_ids = ["D_TREATMENT_PLAN_L1L5", "D_PATHWAY_RANKING", "D_FOLLOWUP_TIMELINE"]
                    expected_modules = [["治疗方案探索"], ["治疗方案探索"], ["复查和追踪方案"]]
                    expected_priorities = [1, 1, 2]
                    for i, d in enumerate(customized):
                        d["id"] = expected_ids[i] if i < len(expected_ids) else d.get("id", expected_ids[0])
                        d["target_agent"] = "Oncologist"
                        d["target_modules"] = expected_modules[i] if i < len(expected_modules) else ["治疗方案探索"]
                        d["priority"] = expected_priorities[i] if i < len(expected_priorities) else 1
                    directions = customized
                    logger.info(f"[PLAN_AGENT] Phase 3 方向已定制化: {[d['topic'][:30] for d in directions]}")
                else:
                    logger.warning(f"[PLAN_AGENT] Phase 3 LLM 返回 {len(customized)} 个方向（期望3个），使用默认")
                    directions = self._get_default_phase3_directions()
            else:
                logger.warning("[PLAN_AGENT] Phase 3 LLM 输出无法解析 JSON，使用默认")
                directions = self._get_default_phase3_directions()
        except Exception as e:
            logger.warning(f"[PLAN_AGENT] Phase 3 方向定制失败，使用默认: {e}")
            directions = self._get_default_phase3_directions()

        current_plan = state.get("research_plan", {})
        if isinstance(current_plan, dict):
            plan_data = current_plan.copy()
        else:
            plan_data = current_plan.to_dict() if hasattr(current_plan, "to_dict") else {}

        plan_data["directions"] = directions
        plan_data["phase"] = "phase_3"

        return {
            "research_plan": plan_data,
            "current_phase": "phase_3",
            "current_phase_description": "方案整合",
            "current_phase_iteration": 0,
            "current_phase_max_iterations": MAX_PHASE3_ITERATIONS,
            "phase3_iteration": 0,
        }

    def _get_default_phase3_directions(self) -> list:
        """Phase 3 默认方向（LLM 定制失败时的回退）"""
        return [
            {
                "id": "D_TREATMENT_PLAN_L1L5",
                "topic": "治疗方案制定 + L1-L5证据分层",
                "target_agent": "Oncologist",
                "target_modules": ["治疗方案探索"],
                "priority": 1,
                "queries": ["treatment plan", "evidence level", "clinical trial"],
                "completion_criteria": "每个方案组合完成L1-L5证据分层寻证和标注"
            },
            {
                "id": "D_PATHWAY_RANKING",
                "topic": "治疗路径排序",
                "target_agent": "Oncologist",
                "target_modules": ["治疗方案探索"],
                "priority": 1,
                "queries": ["treatment sequence", "pathway ranking"],
                "completion_criteria": "完成路径排序(证据+获益+安全+可及+患者因素5维打分)"
            },
            {
                "id": "D_FOLLOWUP_TIMELINE",
                "topic": "复查时间线 + 分子复查补充",
                "target_agent": "Oncologist",
                "target_modules": ["复查和追踪方案"],
                "priority": 2,
                "queries": ["follow-up", "surveillance", "molecular monitoring"],
                "completion_criteria": "完成5.1常规复查时间线和5.2分子复查补充"
            },
        ]


if __name__ == "__main__":
    # 测试
    print("PlanAgent 模块加载成功")
    print(f"使用模型: {ORCHESTRATOR_MODEL}")

    # 测试实例化
    try:
        agent = PlanAgent()
        print(f"PlanAgent 初始化成功，角色: {agent.role}")
        print(f"模型: {agent.model}")
    except Exception as e:
        print(f"初始化失败: {e}")
