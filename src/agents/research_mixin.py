"""
Research Mixin - BFRS/DFRS 研究能力

为现有 Agent 提供 BFRS（广度优先研究）和 DFRS（深度优先研究）能力。
"""
import json
from typing import Dict, List, Any, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass

from src.models.evidence_graph import (
    EvidenceGraph,
    EvidenceType,
    EvidenceGrade,
    CivicEvidenceType,
    load_evidence_graph
)
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
    evidence_ids: List[str]             # 添加到图中的证据 ID
    directions_updated: List[str]       # 更新状态的方向 ID
    research_complete: bool             # 是否完成研究
    needs_deep_research: List[str]      # 需要深入研究的发现
    summary: str                        # 摘要


class ResearchMixin:
    """
    研究能力混入类

    为 Agent 添加 BFRS/DFRS 研究能力。
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
            mode: 研究模式 (breadth_first / depth_first)
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
        logger.info(f"[{agent_role}] 模式: {mode.value}")
        logger.info(f"[{agent_role}] 分配方向: {len(directions)} 个")

        # 加载证据图和研究计划
        graph = load_evidence_graph(evidence_graph)
        plan = load_research_plan(research_plan) if research_plan else None

        # 构建研究提示
        if mode == ResearchMode.BREADTH_FIRST:
            prompt = self._build_bfrs_prompt(directions, graph, iteration, max_iterations, case_context)
        else:
            prompt = self._build_dfrs_prompt(directions, graph, iteration, max_iterations, case_context)

        # 调用 Agent
        result = self.invoke(prompt)  # type: ignore
        output = result.get("output", "")

        # 解析研究结果
        parsed = self._parse_research_output(output, mode)

        # 更新证据图和研究计划（双向关联）
        new_evidence_ids, updated_plan = self._update_evidence_graph(
            graph=graph,
            findings=parsed.get("findings", []),
            agent_role=agent_role,
            iteration=iteration,
            mode=mode,
            plan=plan
        )

        # 更新方向状态
        direction_updates = parsed.get("direction_updates", {})

        # 增强结果日志
        logger.info(f"[{agent_role}] 迭代完成:")
        logger.info(f"[{agent_role}]   发现数: {len(parsed.get('findings', []))}")
        logger.info(f"[{agent_role}]   新证据: {len(new_evidence_ids)}")
        if direction_updates:
            logger.info(f"[{agent_role}]   方向更新: {direction_updates}")
        needs_deep = parsed.get('needs_deep_research', [])
        if needs_deep:
            logger.info(f"[{agent_role}]   需深入研究: {len(needs_deep)} 项")
        summary = parsed.get('summary', '')
        if summary:
            summary_short = summary[:100] + "..." if len(summary) > 100 else summary
            logger.info(f"[{agent_role}]   摘要: {summary_short}")

        return {
            "evidence_graph": graph.to_dict(),
            "research_plan": updated_plan.to_dict() if updated_plan else None,
            "new_evidence_ids": new_evidence_ids,
            "direction_updates": direction_updates,
            "research_complete": parsed.get("research_complete", False),
            "needs_deep_research": parsed.get("needs_deep_research", []),
            "summary": parsed.get("summary", ""),
            "raw_output": output
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
- 现有证据: {existing_evidence.get('total_nodes', 0)} 条

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
            "source_tool": "工具名称"
        }}
    ],
    "direction_updates": {{
        "D1": "pending|completed",
        "D2": "pending|completed"
    }},
    "needs_deep_research": [
        {{
            "finding": "需要深入的发现描述",
            "reason": "为什么需要深入研究"
        }}
    ],
    "research_complete": false
}}
```

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

        # 找到需要深入研究的方向
        depth_items = []
        for d in directions:
            if d.get('needs_deep_research'):
                depth_items.append(d)

        # 格式化深入研究项
        depth_text = ""
        for i, item in enumerate(depth_items, 1):  # 处理所有需要深入的方向
            depth_text += f"""
### 深入研究项 {i}
- 方向 ID: {item.get('id', '')}
- 主题: {item.get('topic', '')}
- 目标模块: {', '.join(item.get('target_modules', []))}
- 需要深入的原因: {item.get('depth_research_reason', '需要更多证据')}
- 已有证据 ID: {item.get('evidence_ids', [])}
"""

        # 现有证据摘要
        existing_evidence = graph.summary()

        return f"""## 研究模式: DFRS (深度优先研究)

### 当前迭代信息
- 迭代轮次: {iteration + 1} / {max_iterations}
- 你的角色: {agent_role}
- 现有证据: {existing_evidence.get('total_nodes', 0)} 条

### 病例背景
{case_context}

### 需要深入研究的项目
{depth_text if depth_text else "无特定深入项，请基于现有证据进行深化研究"}

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
            "depth_chain": ["引用1", "引用2", "推理步骤"]
        }}
    ],
    "direction_updates": {{
        "D1": "pending|completed"
    }},
    "needs_deep_research": [],
    "research_complete": true|false
}}
```

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
        """解析研究输出"""
        import re

        # 尝试提取 JSON
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', output)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 尝试直接解析
        brace_match = re.search(r'\{[\s\S]*\}', output)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        # 解析失败，返回默认结构
        logger.warning(f"[ResearchMixin] JSON 解析失败，使用默认结构")
        return {
            "summary": output if output else "无摘要",
            "findings": [],
            "direction_updates": {},
            "needs_deep_research": [],
            "research_complete": False
        }

    def _update_evidence_graph(
        self,
        graph: EvidenceGraph,
        findings: List[Dict[str, Any]],
        agent_role: str,
        iteration: int,
        mode: ResearchMode,
        plan: Optional[ResearchPlan] = None
    ) -> Tuple[List[str], Optional[ResearchPlan]]:
        """
        更新证据图并同步更新研究计划中的方向证据关联

        Returns:
            (新增的证据 ID 列表, 更新后的研究计划)
        """
        new_ids = []

        for finding in findings:
            # 映射证据类型
            type_str = finding.get("evidence_type", "literature")
            try:
                evidence_type = EvidenceType(type_str)
            except ValueError:
                evidence_type = EvidenceType.LITERATURE

            # 映射证据等级
            grade_str = finding.get("grade")
            grade = None
            if grade_str:
                try:
                    grade = EvidenceGrade(grade_str)
                except ValueError:
                    pass

            # 映射 CIViC 证据类型
            civic_type_str = finding.get("civic_type")
            civic_type = None
            if civic_type_str:
                try:
                    civic_type = CivicEvidenceType(civic_type_str)
                except ValueError:
                    pass

            # 添加节点
            node_id = graph.add_node(
                evidence_type=evidence_type,
                content={"text": finding.get("content", ""), "raw": finding},
                source_agent=agent_role,
                source_tool=finding.get("source_tool"),
                grade=grade,
                civic_evidence_type=civic_type,
                iteration=iteration,
                research_mode=mode.value,
                needs_deep_research=bool(finding.get("needs_deep_research")),
                depth_research_reason=finding.get("depth_research_reason"),
                metadata={
                    "direction_id": finding.get("direction_id"),
                    "depth_chain": finding.get("depth_chain", [])
                }
            )
            new_ids.append(node_id)

            # 更新 direction 的 evidence_ids（双向关联）
            direction_id = finding.get("direction_id")
            if direction_id and plan:
                direction = plan.get_direction_by_id(direction_id)
                if direction:
                    direction.add_evidence(node_id)

        return new_ids, plan


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
    print("ResearchMixin 模块加载成功")

    # 测试解析
    mixin = ResearchMixin()
    test_output = '''```json
{
    "summary": "测试摘要",
    "findings": [{"content": "测试发现", "evidence_type": "molecular"}],
    "direction_updates": {"D1": "completed"},
    "needs_deep_research": [],
    "research_complete": false
}
```'''
    parsed = mixin._parse_research_output(test_output, ResearchMode.BREADTH_FIRST)
    print(f"解析结果: {parsed}")
