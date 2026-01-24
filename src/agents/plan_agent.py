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
from config.settings import PLAN_AGENT_PROMPT_FILE

# 证据等级权重（用于计算方向完成度）
GRADE_WEIGHTS = {
    "A": 5.0,   # Validated - 一条 A 级 ≈ 5 条 E 级
    "B": 3.0,   # Clinical
    "C": 2.0,   # Case Study
    "D": 1.5,   # Preclinical
    "E": 1.0,   # Inferential
}

# 方向完成度目标得分（相当于 2 条 A 级 或 10 条 E 级）
TARGET_COMPLETENESS_SCORE = 10.0

# 收敛阈值
CONVERGENCE_COMPLETENESS_THRESHOLD = 80  # 完成度 >= 80% 视为完成
CONTINUE_COMPLETENESS_THRESHOLD = 60     # 完成度 < 60% 需要继续收集


# 必须覆盖的 Chair 模块列表
REQUIRED_MODULE_COVERAGE = [
    "患者概况",
    "分子特征",
    "方案对比",
    "器官功能与剂量",
    "治疗路线图",
    "分子复查建议",
    "临床试验推荐",
    "局部治疗建议",
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

    def _build_analysis_prompt(self, case_text: str) -> str:
        """构建分析任务提示"""
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
    "directions": [
        {{
            "id": "D1",
            "topic": "研究方向主题",
            "target_agent": "Geneticist",  // Pathologist/Geneticist/Recruiter/Oncologist
            "target_modules": ["分子特征"],  // 目标 Chair 模块
            "priority": 1,  // 1-5，1最高
            "queries": ["建议的查询关键词"],
            "completion_criteria": "完成标准描述"
        }}
    ]
}}
```

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

### Recruiter（临床试验招募员）
- 适用临床试验匹配
- 入排标准评估
- 试验阶段和状态

### Oncologist（肿瘤学家）
- 治疗方案制定
- 药物相互作用
- 剂量调整建议
- 安全性评估

## 必需模块覆盖
确保研究方向覆盖以下所有模块：
- 患者概况 (Pathologist)
- 分子特征 (Geneticist + Pathologist)
- 方案对比 (Oncologist)
- 器官功能与剂量 (Oncologist)
- 治疗路线图 (Oncologist + Geneticist + Recruiter)
- 分子复查建议 (Geneticist + Oncologist)
- 临床试验推荐 (Recruiter)
- 局部治疗建议 (Oncologist + Pathologist)

## 注意事项
1. 每个 Agent 分配 2-5 个研究方向
2. 优先级 1 为最关键方向
3. 确保 JSON 格式正确，可以被解析
4. 每个方向必须指定 target_modules
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
            plan = create_research_plan(
                case_summary=data.get("case_summary", ""),
                key_entities=data.get("key_entities", {}),
                directions=data.get("directions", [])
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

        # 构建评估提示
        eval_prompt = self._build_evaluation_prompt(
            state, phase, iteration, plan, graph, direction_stats
        )

        # 调用 LLM 进行评估
        result = self.invoke(eval_prompt)
        output = result.get("output", "")

        # 解析评估结果
        eval_result = self._parse_evaluation_output(output, plan, direction_stats)

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
                    "evidence_count": 5,
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
            evidence_ids = direction.evidence_ids

            # 统计证据等级分布
            grade_dist = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0}
            weighted_score = 0.0

            for eid in evidence_ids:
                node = graph.get_node(eid) if graph else None
                if node and node.grade:
                    grade = node.grade.value
                    grade_dist[grade] = grade_dist.get(grade, 0) + 1
                    weighted_score += GRADE_WEIGHTS.get(grade, 1.0)
                else:
                    # 无等级的证据按 E 级计算
                    grade_dist["E"] = grade_dist.get("E", 0) + 1
                    weighted_score += 1.0

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
                "evidence_count": len(evidence_ids),
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
        direction_stats: Dict[str, Dict[str, Any]]
    ) -> str:
        """构建迭代评估提示"""

        # 汇总证据质量
        total_evidence = sum(s["evidence_count"] for s in direction_stats.values())
        high_quality_directions = [d for d, s in direction_stats.items() if s["has_high_quality"]]
        low_quality_directions = [d for d, s in direction_stats.items() if s["low_quality_only"]]
        incomplete_directions = [
            d for d, s in direction_stats.items()
            if s["completeness"] < CONTINUE_COMPLETENESS_THRESHOLD
        ]

        # 检测证据冲突
        conflicts = graph.identify_gaps() if graph else []
        conflict_descriptions = [c.get("description", "") for c in conflicts if c.get("type") == "evidence_conflict"]

        # Phase 1 检查的 Agent
        if phase == "phase1":
            agents_to_check = ["Pathologist", "Geneticist", "Recruiter"]
        else:
            agents_to_check = ["Oncologist"]

        # 过滤当前 phase 相关的方向
        relevant_stats = {
            d: s for d, s in direction_stats.items()
            if s["target_agent"] in agents_to_check
        }

        return f"""## 迭代评估任务

你正在评估 {phase.upper()} 的第 {iteration + 1} 轮迭代结果。

### 当前研究进度

**总证据数**: {total_evidence}
**本阶段相关方向数**: {len(relevant_stats)}

### 各研究方向状态

{self._format_direction_stats(relevant_stats)}

### 证据质量概况

- **有高质量证据 (A/B级) 的方向**: {high_quality_directions if high_quality_directions else "无"}
- **只有低质量证据 (D/E级) 的方向**: {low_quality_directions if low_quality_directions else "无"}
- **完成度不足 (<60%) 的方向**: {incomplete_directions if incomplete_directions else "无"}

### 证据冲突

{conflict_descriptions if conflict_descriptions else "无检测到的证据冲突"}

### 评估要求

请根据以上信息，完成以下评估：

1. **更新各方向状态**：
   - 完成度 >= 80%: 标记为 "completed"
   - 完成度 < 60%: 保持 "pending" 或 "in_progress"
   - 调整优先级（低质量方向提升优先级）

2. **决定研究模式**：
   - "breadth_first": 还有未覆盖方向，需要广度收集
   - "depth_first": 有高优先级发现需要深入，或证据冲突需要解决

3. **收敛判断**：
   - "converged": 所有方向完成度 >= 80%，且有足够高质量证据，无重大冲突
   - "continue": 存在未完成方向，或只有低质量证据，或有未解决冲突

### 输出格式

请以 JSON 格式输出：

```json
{{
    "updated_directions": [
        {{
            "id": "D1",
            "status": "completed",
            "priority": 1,
            "completeness": 85
        }}
    ],
    "new_directions": [],
    "research_mode": "breadth_first",
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
"""

    def _format_direction_stats(self, stats: Dict[str, Dict[str, Any]]) -> str:
        """格式化方向统计为 Markdown 表格"""
        lines = ["| ID | 主题 | Agent | 证据数 | A | B | C | D | E | 加权分 | 完成度 | 状态 |",
                 "|:---|:-----|:------|:-------|:--|:--|:--|:--|:--|:-------|:-------|:-----|"]

        for d_id, s in stats.items():
            gd = s["grade_distribution"]
            lines.append(
                f"| {d_id} | {s['topic'][:20]}... | {s['target_agent']} | "
                f"{s['evidence_count']} | {gd['A']} | {gd['B']} | {gd['C']} | {gd['D']} | {gd['E']} | "
                f"{s['weighted_score']:.1f} | {s['completeness']:.0f}% | {s['status']} |"
            )

        return "\n".join(lines)

    def _parse_evaluation_output(
        self,
        output: str,
        plan: ResearchPlan,
        direction_stats: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """解析 LLM 评估输出"""

        # 提取 JSON
        json_str = self._extract_json(output)

        if not json_str:
            logger.warning(f"[{self.role}] 无法从评估输出中提取 JSON，使用默认值")
            return self._create_default_evaluation(plan, direction_stats)

        try:
            data = json.loads(json_str)

            # 更新研究计划
            updated_plan = self._apply_direction_updates(plan, data.get("updated_directions", []))

            # 添加新方向（如果有）
            new_directions = data.get("new_directions", [])
            if new_directions:
                for nd in new_directions:
                    updated_plan.directions.append(ResearchDirection.from_dict(nd))

            return {
                "research_plan": updated_plan.to_dict(),
                "research_mode": data.get("research_mode", "breadth_first"),
                "decision": data.get("decision", "continue"),
                "reasoning": data.get("reasoning", ""),
                "quality_assessment": data.get("quality_assessment", {}),
                "gaps": data.get("gaps", []),
                "next_priorities": data.get("next_priorities", []),
            }

        except json.JSONDecodeError as e:
            logger.warning(f"[{self.role}] JSON 解析失败: {e}，使用默认值")
            return self._create_default_evaluation(plan, direction_stats)

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

        return plan

    def _create_default_evaluation(
        self,
        plan: ResearchPlan,
        direction_stats: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """创建默认评估结果（当 LLM 解析失败时）"""

        # 根据统计数据自动判断
        all_complete = all(
            s["completeness"] >= CONVERGENCE_COMPLETENESS_THRESHOLD
            for s in direction_stats.values()
        )

        has_low_quality_only = any(
            s["low_quality_only"]
            for s in direction_stats.values()
        )

        # 更新方向状态
        updated_directions = []
        for d_id, s in direction_stats.items():
            status = "completed" if s["completeness"] >= CONVERGENCE_COMPLETENESS_THRESHOLD else "in_progress"
            updated_directions.append({
                "id": d_id,
                "status": status,
                "priority": s["priority"],
                "completeness": s["completeness"]
            })

        # 应用更新
        updated_plan = self._apply_direction_updates(plan, updated_directions)

        # 决策
        if all_complete and not has_low_quality_only:
            decision = "converged"
            reasoning = "所有方向完成度达标，且有足够高质量证据"
        else:
            decision = "continue"
            reasoning = "存在未完成方向或只有低质量证据的方向"

        return {
            "research_plan": updated_plan.to_dict(),
            "research_mode": "depth_first" if has_low_quality_only else "breadth_first",
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
            ][:3],
        }


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
