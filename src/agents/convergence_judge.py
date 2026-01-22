"""
Convergence Judge Agent - 收敛判断 Agent

评估研究循环是否达到收敛条件：
- 检查证据图质量
- 评估关键模块的证据覆盖
- 识别需要继续研究的空白
"""
import json
import re
from typing import Dict, Any, Literal, Optional

from src.agents.base_agent import BaseAgent, SUBGRAPH_MODEL
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
            model=SUBGRAPH_MODEL  # 使用 flash 模型
        )

    def evaluate(self, state: Dict[str, Any]) -> Literal["converged", "continue"]:
        """
        评估研究是否收敛

        Args:
            state: MtbState 状态字典

        Returns:
            "converged" 或 "continue"
        """
        logger.info(f"[{self.role}] 开始收敛评估...")

        # 构建评估提示
        prompt = self._build_evaluation_prompt(state)

        # 调用 LLM
        try:
            result = self.invoke(prompt)
            output = result.get("output", "")

            # 解析决策
            decision = self._parse_decision(output)
            logger.info(f"[{self.role}] 评估完成: {decision}")

            return decision

        except Exception as e:
            logger.error(f"[{self.role}] 评估失败: {e}")
            # 出错时保守处理，继续研究
            return "continue"

    def _build_evaluation_prompt(self, state: Dict[str, Any]) -> str:
        """构建评估提示"""
        # 加载证据图
        graph = load_evidence_graph(state.get("evidence_graph", {}))
        plan = load_research_plan(state.get("research_plan", {}))

        # 收集证据统计
        evidence_summary = self._summarize_evidence(graph)

        # 收集模块覆盖信息
        module_coverage = self._get_module_coverage_info(plan)

        # 收集研究问题状态
        question_status = self._get_question_status(plan)

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

### 研究问题状态
{question_status}

### 评估标准

请根据以下标准判断是否收敛：

1. **关键变异/靶点**：主要可行动变异是否有 A/B 级证据支持？
2. **治疗方案**：是否有明确的治疗推荐（至少 1 个方案有 A/B 级证据）？
3. **证据冲突**：是否存在未解决的重要证据冲突？
4. **模块覆盖**：9 个需要覆盖的模块是否都有相关研究方向？
5. **研究空白**：是否有关键问题完全没有证据支持？

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

    def _get_question_status(self, plan) -> str:
        """获取研究问题状态"""
        if not plan:
            return "无研究计划"

        lines = [
            f"- 总问题数: {len(plan.questions)}",
            f"- 已覆盖: {len([q for q in plan.questions if q.is_covered])}",
            f"- 覆盖率: {plan.calculate_coverage():.1%}",
            "",
            "**问题详情:**"
        ]

        for q in plan.questions[:10]:  # 最多显示 10 个
            status = "✓" if q.is_covered else "○"
            evidence_count = len(q.evidence_ids)
            lines.append(f"  {status} [{q.priority.name}] {q.text[:50]}... (证据: {evidence_count})")

        if len(plan.questions) > 10:
            lines.append(f"  ... 还有 {len(plan.questions) - 10} 个问题")

        return "\n".join(lines)

    def _parse_decision(self, output: str) -> Literal["converged", "continue"]:
        """解析 LLM 输出的决策"""
        # 尝试解析 JSON
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', output)
        if json_match:
            try:
                data = json.loads(json_match.group(1).strip())
                decision = data.get("decision", "").lower()
                reasoning = data.get("reasoning", "")

                if decision == "converged":
                    logger.info(f"[{self.role}] 判断收敛: {reasoning[:100]}")
                    return "converged"
                else:
                    gaps = data.get("gaps", [])
                    logger.info(f"[{self.role}] 判断需继续: {gaps[:3]}")
                    return "continue"

            except json.JSONDecodeError:
                pass

        # 备用：检查关键词
        output_lower = output.lower()
        if "converged" in output_lower and "continue" not in output_lower:
            return "converged"

        # 默认保守处理
        logger.warning(f"[{self.role}] 无法解析决策，默认继续研究")
        return "continue"


if __name__ == "__main__":
    print("ConvergenceJudgeAgent 模块加载成功")
    print(f"使用模型: {SUBGRAPH_MODEL}")
