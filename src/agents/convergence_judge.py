"""
Convergence Judge Agent - 收敛判断 Agent

!!! DEPRECATED !!!
此模块已废弃。收敛判断功能已移至 PlanAgent.evaluate_and_update()。
保留此文件仅用于回滚目的。

原功能：
- 检查证据图质量
- 评估关键模块的证据覆盖
- 识别需要继续研究的空白

新架构：
- PlanAgent 在每轮迭代后统一评估研究进度
- 基于证据质量（等级权重）而非仅数量判断收敛
- 动态更新研究计划和方向优先级

参见: src/agents/plan_agent.py - evaluate_and_update()
"""
import warnings

warnings.warn(
    "ConvergenceJudgeAgent 已废弃，收敛判断已移至 PlanAgent.evaluate_and_update()",
    DeprecationWarning,
    stacklevel=2
)
import json
import re
from typing import Dict, Any, Optional, List

from src.agents.base_agent import BaseAgent, CONVERGENCE_JUDGE_MODEL
from src.models.evidence_graph import load_evidence_graph, EvidenceGrade
from src.models.research_plan import load_research_plan
from config.settings import (
    COVERAGE_REQUIRED_MODULES,
    load_prompt
)
from src.utils.logger import mtb_logger as logger


CONVERGENCE_JUDGE_PROMPT_FILE = "convergence_judge_prompt.txt"


class ConvergenceJudgeAgent(BaseAgent):
    """
    收敛判断 Agent

    在 metric-based 检查和 module coverage 检查通过后，
    作为第三步质量关口，评估研究是否真正充分。
    """

    def __init__(self):
        super().__init__(
            role="ConvergenceJudge",
            prompt_file=CONVERGENCE_JUDGE_PROMPT_FILE,
            tools=[],  # 无工具调用，纯评估
            temperature=0.1,  # 低温度，保证一致性
            model=CONVERGENCE_JUDGE_MODEL  # 使用 flash 模型
        )

    def evaluate(
        self,
        state: Dict[str, Any],
        phase: str = "phase1",
        agent_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        评估研究是否收敛

        Args:
            state: MtbState 状态字典
            phase: 当前阶段 "phase1" 或 "phase2"
            agent_name: 要评估的单个Agent名称，None表示评估整个Phase

        Returns:
            完整评估结果字典:
            {
                "decision": "converged" | "continue",
                "confidence": 0.0-1.0,
                "reasoning": str,
                "gaps": List[str],
                "strengths": List[str]
            }
        """
        if agent_name:
            logger.info(f"[{self.role}] 开始单 Agent 收敛评估: {agent_name}...")
        else:
            logger.info(f"[{self.role}] 开始 {phase} 收敛评估...")

        # 构建评估提示
        prompt = self._build_evaluation_prompt(state, phase, agent_name)

        # 调用 LLM
        try:
            result = self.invoke(prompt)
            output = result.get("output", "")

            # 解析完整决策结果
            eval_result = self._parse_decision(output)
            logger.info(f"[{self.role}] 评估完成: {eval_result['decision']} (置信度: {eval_result['confidence']})")

            return eval_result

        except Exception as e:
            logger.error(f"[{self.role}] 评估失败: {e}")
            # 出错时保守处理，继续研究
            return {
                "decision": "continue",
                "confidence": 0.0,
                "reasoning": f"评估过程出错: {str(e)}",
                "gaps": ["评估失败，需要重试"],
                "strengths": []
            }

    def _build_evaluation_prompt(
        self,
        state: Dict[str, Any],
        phase: str = "phase1",
        agent_name: Optional[str] = None
    ) -> str:
        """构建评估提示"""
        # 加载证据图
        graph = load_evidence_graph(state.get("evidence_graph", {}))
        plan = load_research_plan(state.get("research_plan", {}))

        # 获取病例背景（完整，不截断）
        case_summary = state.get("raw_pdf_text", "")

        # 根据评估模式确定要检查的 Agent 列表和重点
        if agent_name:
            # 单个 Agent 评估
            agents_to_check = [agent_name]
            focus = self._get_agent_focus(agent_name)
            eval_mode = f"单个 Agent 评估: {agent_name}"
        elif phase == "phase1":
            agents_to_check = ["Pathologist", "Geneticist", "Recruiter"]
            focus = "分子特征分析、病理/影像解读、临床试验匹配"
            eval_mode = "Phase 1 整体评估"
        else:
            agents_to_check = ["Oncologist"]
            focus = "治疗方案制定、药物选择、安全性评估"
            eval_mode = "Phase 2 整体评估"

        # 收集证据统计（按指定 Agent 过滤）
        evidence_summary = self._summarize_evidence(graph, agents_to_check)

        # 收集模块覆盖信息（按指定 Agent 过滤）
        module_coverage = self._get_agent_module_coverage_info(plan, agents_to_check)

        # 收集研究方向状态（按指定 Agent 过滤）
        direction_status = self._get_direction_status(plan, agents_to_check)

        # 获取 Agent 特定的评估标准
        eval_criteria = self._get_agent_eval_criteria(agent_name) if agent_name else self._get_phase_eval_criteria(phase)

        prompt = f"""## 收敛评估任务

**评估模式**: {eval_mode}
**评估重点**: {focus}

请评估当前研究是否已充分。

### 病例背景摘要
{case_summary}

### 当前证据图统计（{', '.join(agents_to_check)}）
{evidence_summary}

### 模块覆盖情况
{module_coverage}

### 研究方向状态
{direction_status}

### 评估标准

{eval_criteria}

### 输出格式

请以 JSON 格式输出评估结果：

```json
{{
    "decision": "converged|continue",
    "confidence": 0.0-1.0,
    "reasoning": "简要说明判断理由",
    "gaps": ["如果 continue，列出需要补充的空白"],
    "strengths": ["当前研究的优势/已充分覆盖的方面"]
}}
```
"""
        return prompt

    def _get_agent_focus(self, agent_name: str) -> str:
        """获取 Agent 的评估重点"""
        focus_map = {
            "Pathologist": "病理分析、影像解读、组织学特征、TNM分期",
            "Geneticist": "分子特征、基因变异、靶点分析、耐药突变",
            "Recruiter": "临床试验匹配、入组标准评估、试验可行性",
            "Oncologist": "治疗方案、药物选择、安全性评估、剂量调整"
        }
        return focus_map.get(agent_name, "综合评估")

    def _get_agent_eval_criteria(self, agent_name: str) -> str:
        """获取单个 Agent 的评估标准"""
        criteria_map = {
            "Pathologist": """请根据以下标准判断 Pathologist 的研究是否充分：

1. **病理切片分析**：组织学类型是否明确？分化程度是否描述？
2. **影像学特征**：肿瘤大小、位置、转移情况是否有充分描述？
3. **TNM 分期**：临床分期是否有依据？
4. **证据充分性**：关键发现是否有 A/B 级证据支持？""",

            "Geneticist": """请根据以下标准判断 Geneticist 的研究是否充分：

1. **驱动突变**：主要可行动变异是否有 A/B 级证据支持？
2. **共突变分析**：是否分析了影响治疗的共突变？
3. **耐药突变**：是否评估了潜在耐药机制？
4. **分子亚型**：是否明确了分子分型？""",

            "Recruiter": """请根据以下标准判断 Recruiter 的研究是否充分：

1. **试验匹配**：是否找到足够的匹配临床试验（≥3个）？
2. **入组评估**：入组/排除标准是否评估？
3. **试验可行性**：地点、阶段、招募状态是否考虑？
4. **替代方案**：是否有多个备选试验？""",

            "Oncologist": """请根据以下标准判断 Oncologist 的研究是否充分：

1. **治疗方案**：是否有明确的治疗推荐（至少 1 个方案有 A/B 级证据）？
2. **药物选择**：药物适应症是否与患者情况匹配？
3. **安全性评估**：是否考虑了器官功能和药物相互作用？
4. **序贯策略**：是否有后续治疗规划？"""
        }
        return criteria_map.get(agent_name, "请综合评估研究充分性。")

    def _get_phase_eval_criteria(self, phase: str) -> str:
        """获取 Phase 级别的评估标准"""
        if phase == "phase1":
            return """请根据以下标准判断 Phase 1 研究是否充分：

1. **分子特征**：主要可行动变异是否有 A/B 级证据支持？
2. **病理分析**：组织学和影像学特征是否描述充分？
3. **临床试验**：是否找到足够的匹配临床试验？
4. **证据冲突**：是否存在未解决的重要证据冲突？
5. **方向证据充分性**：每个研究方向是否有足够的证据支持？"""
        else:
            return """请根据以下标准判断 Phase 2 研究是否充分：

1. **治疗方案**：是否有明确的治疗推荐（至少 1 个方案有 A/B 级证据）？
2. **药物选择**：是否考虑了适应症、禁忌症和药物相互作用？
3. **安全性评估**：是否有剂量调整建议？
4. **序贯策略**：是否有后续治疗路线图？"""

    def _summarize_evidence(self, graph, agents_to_check: Optional[List[str]] = None) -> str:
        """汇总证据图信息（可按 Agent 过滤）"""
        if not graph or len(graph) == 0:
            return "证据图为空"

        summary = graph.summary()

        # 如果指定了 Agent，只统计这些 Agent 的证据
        if agents_to_check:
            # 获取指定 Agent 的证据节点
            filtered_nodes = []
            for agent in agents_to_check:
                filtered_nodes.extend(graph.get_nodes_by_agent(agent))

            total_nodes = len(filtered_nodes)

            # 按类型统计
            by_type = {}
            by_grade = {}
            for node in filtered_nodes:
                t = node.evidence_type.value if node.evidence_type else "unknown"
                by_type[t] = by_type.get(t, 0) + 1
                g = node.grade.value if node.grade else "unknown"
                by_grade[g] = by_grade.get(g, 0) + 1

            lines = [
                f"- 证据节点数（{', '.join(agents_to_check)}）: {total_nodes}",
                "",
                "**按类型分布:**"
            ]

            for t, count in by_type.items():
                lines.append(f"  - {t}: {count}")

            lines.append("")
            lines.append("**按证据等级分布:**")

            for g, count in by_grade.items():
                lines.append(f"  - Level {g}: {count}")
        else:
            # 全局统计
            lines = [
                f"- 总证据节点数: {summary.get('total_nodes', 0)}",
                f"- 总关系边数: {summary.get('total_edges', 0)}",
                f"- 研究空白数: {summary.get('gaps_count', 0)}",
                "",
                "**按类型分布:**"
            ]

            by_type = summary.get("by_type", {})
            for t, count in by_type.items():
                lines.append(f"  - {t}: {count}")

            lines.append("")
            lines.append("**按证据等级分布:**")

            by_grade = summary.get("by_grade", {})
            for g, count in by_grade.items():
                lines.append(f"  - Level {g}: {count}")

            lines.append("")
            lines.append("**按 Agent 分布:**")

            by_agent = summary.get("by_agent", {})
            for a, count in by_agent.items():
                lines.append(f"  - {a}: {count}")

        return "\n".join(lines)

    def _get_module_coverage_info(self, plan) -> str:
        """获取全局模块覆盖信息"""
        if not plan:
            return "无研究计划"

        coverage = plan.get_module_coverage()
        lines = ["**需要覆盖的 9 个模块:**", ""]

        for module in COVERAGE_REQUIRED_MODULES:
            if module in coverage:
                direction_ids = coverage[module]
                lines.append(f"- [x] {module}: {len(direction_ids)} 个研究方向")
            else:
                lines.append(f"- [ ] {module}: **未覆盖**")

        return "\n".join(lines)

    def _get_agent_module_coverage_info(self, plan, agents_to_check: List[str]) -> str:
        """获取指定 Agent 的模块覆盖信息"""
        if not plan:
            return "无研究计划"

        lines = [f"**{', '.join(agents_to_check)} 负责的模块覆盖情况:**", ""]

        # 收集该 Agent 分配的所有方向和模块
        agent_directions = [d for d in plan.directions if d.target_agent in agents_to_check]

        if not agent_directions:
            lines.append("该 Agent 没有分配的研究方向。")
            return "\n".join(lines)

        # 按模块汇总
        module_evidence = {}
        for d in agent_directions:
            evidence_count = len(d.evidence_ids)
            for module in d.target_modules:
                if module not in module_evidence:
                    module_evidence[module] = {"directions": [], "total_evidence": 0}
                module_evidence[module]["directions"].append(d.id)
                module_evidence[module]["total_evidence"] += evidence_count

        for module, data in module_evidence.items():
            status = "✓" if data["total_evidence"] > 0 else "✗"
            lines.append(f"- [{status}] {module}: {data['total_evidence']} 条证据 ({len(data['directions'])} 个方向)")

        return "\n".join(lines)

    def _get_direction_status(self, plan, agents_to_check: Optional[List[str]] = None) -> str:
        """获取研究方向状态（可按 Agent 过滤）"""
        if not plan:
            return "无研究计划"

        # 过滤方向
        if agents_to_check:
            directions = [d for d in plan.directions if d.target_agent in agents_to_check]
        else:
            directions = plan.directions

        # 统计方向状态
        total = len(directions)
        completed = len([d for d in directions if d.status.value == "completed"])
        pending = len([d for d in directions if d.status.value == "pending"])
        in_progress = total - completed - pending

        # 计算完成率
        completion_rate = completed / total if total > 0 else 1.0

        lines = [
            f"- 总方向数: {total}",
            f"- 已完成: {completed}",
            f"- 进行中: {in_progress}",
            f"- 待处理: {pending}",
            f"- 完成率: {completion_rate:.1%}",
            "",
            "**方向详情:**"
        ]

        for d in directions[:10]:  # 最多显示 10 个
            status_icon = "✓" if d.status.value == "completed" else "○"
            evidence_count = len(d.evidence_ids)
            modules = ", ".join(d.target_modules[:2])
            lines.append(f"  {status_icon} [P{d.priority}] {d.topic[:40]}... (证据: {evidence_count}, 模块: {modules})")

        if len(directions) > 10:
            lines.append(f"  ... 还有 {len(directions) - 10} 个方向")

        return "\n".join(lines)

    def _parse_decision(self, output: str) -> Dict[str, Any]:
        """
        解析 LLM 输出的完整决策结果

        Returns:
            {
                "decision": "converged" | "continue",
                "confidence": float,
                "reasoning": str,
                "gaps": List[str],
                "strengths": List[str]
            }
        """
        default_result = {
            "decision": "continue",
            "confidence": 0.0,
            "reasoning": "无法解析决策",
            "gaps": [],
            "strengths": []
        }

        # 尝试解析 JSON
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', output)
        if json_match:
            try:
                data = json.loads(json_match.group(1).strip())
                decision = data.get("decision", "continue").lower()
                confidence = float(data.get("confidence", 0.5))
                reasoning = data.get("reasoning", "")
                gaps = data.get("gaps", [])
                strengths = data.get("strengths", [])

                # 确保 decision 是有效值
                if decision not in ("converged", "continue"):
                    decision = "continue"

                result = {
                    "decision": decision,
                    "confidence": confidence,
                    "reasoning": reasoning,
                    "gaps": gaps if isinstance(gaps, list) else [],
                    "strengths": strengths if isinstance(strengths, list) else []
                }

                if decision == "converged":
                    logger.info(f"[{self.role}] 判断收敛: {reasoning[:100]}")
                else:
                    logger.info(f"[{self.role}] 判断需继续: {gaps[:3] if gaps else '无具体空白'}")

                return result

            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"[{self.role}] JSON 解析失败: {e}")

        # 备用：检查关键词
        output_lower = output.lower()
        if "converged" in output_lower and "continue" not in output_lower:
            return {
                "decision": "converged",
                "confidence": 0.5,
                "reasoning": "基于关键词匹配判断收敛",
                "gaps": [],
                "strengths": []
            }

        # 默认保守处理
        logger.warning(f"[{self.role}] 无法解析决策，默认继续研究")
        return default_result


if __name__ == "__main__":
    print("ConvergenceJudgeAgent 模块加载成功")
    print(f"使用模型: {CONVERGENCE_JUDGE_MODEL}")
