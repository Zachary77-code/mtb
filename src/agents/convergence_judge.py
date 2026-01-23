"""
Convergence Judge Agent - 收敛判断 Agent

评估研究循环是否达到收敛条件：
- 检查证据图质量
- 评估关键模块的证据覆盖
- 识别需要继续研究的空白
"""
import json
import re
from typing import Dict, Any

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

    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估研究是否收敛

        Args:
            state: MtbState 状态字典

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
        logger.info(f"[{self.role}] 开始收敛评估...")

        # 构建评估提示
        prompt = self._build_evaluation_prompt(state)

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

    def _build_evaluation_prompt(self, state: Dict[str, Any]) -> str:
        """构建评估提示"""
        # 加载证据图
        graph = load_evidence_graph(state.get("evidence_graph", {}))
        plan = load_research_plan(state.get("research_plan", {}))

        # 收集证据统计
        evidence_summary = self._summarize_evidence(graph)

        # 收集模块覆盖信息
        module_coverage = self._get_module_coverage_info(plan)

        # 收集研究方向状态
        direction_status = self._get_direction_status(plan)

        # 获取病例背景摘要
        case_summary = state.get("raw_pdf_text", "")[:1500]

        prompt = f"""## 收敛评估任务

请评估当前研究是否已充分，可以进入下一阶段（Chair 报告生成）。

### 病例背景摘要
{case_summary}

### 当前证据图统计
{evidence_summary}

### 模块覆盖情况
{module_coverage}

### 研究方向状态
{direction_status}

### 评估标准

请根据以下标准判断是否收敛：

1. **关键变异/靶点**：主要可行动变异是否有 A/B 级证据支持？
2. **治疗方案**：是否有明确的治疗推荐（至少 1 个方案有 A/B 级证据）？
3. **证据冲突**：是否存在未解决的重要证据冲突？
4. **模块覆盖**：8 个需要覆盖的模块是否都有相关研究方向？
5. **方向证据充分性**：每个研究方向是否有足够的证据支持（至少 20 条）？

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

    def _summarize_evidence(self, graph) -> str:
        """汇总证据图信息"""
        if not graph or len(graph) == 0:
            return "证据图为空"

        summary = graph.summary()
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
        """获取模块覆盖信息"""
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

    def _get_direction_status(self, plan) -> str:
        """获取研究方向状态"""
        if not plan:
            return "无研究计划"

        # 统计方向状态
        total = len(plan.directions)
        completed = len([d for d in plan.directions if d.status.value == "completed"])
        pending = len([d for d in plan.directions if d.status.value == "pending"])
        in_progress = total - completed - pending

        lines = [
            f"- 总方向数: {total}",
            f"- 已完成: {completed}",
            f"- 进行中: {in_progress}",
            f"- 待处理: {pending}",
            f"- 完成率: {plan.calculate_direction_completion_rate():.1%}",
            "",
            "**方向详情:**"
        ]

        for d in plan.directions[:10]:  # 最多显示 10 个
            status_icon = "✓" if d.status.value == "completed" else "○"
            evidence_count = len(d.evidence_ids)
            modules = ", ".join(d.target_modules[:2])
            lines.append(f"  {status_icon} [P{d.priority}] {d.topic[:40]}... (证据: {evidence_count}, 模块: {modules})")

        if len(plan.directions) > 10:
            lines.append(f"  ... 还有 {len(plan.directions) - 10} 个方向")

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
