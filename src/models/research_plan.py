"""
Research Plan 数据结构

研究计划定义，由 PlanAgent 生成，指导 BFRS/DFRS 研究循环。
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
import uuid


class ResearchMode(str, Enum):
    """研究模式"""
    BREADTH_FIRST = "breadth_first"  # 广度优先
    DEPTH_FIRST = "depth_first"      # 深度优先


class DirectionStatus(str, Enum):
    """研究方向状态"""
    PENDING = "pending"           # 待处理
    IN_PROGRESS = "in_progress"   # 进行中
    COMPLETED = "completed"       # 已完成


@dataclass
class ResearchDirection:
    """
    研究方向

    分配给特定 Agent 的研究任务。
    """
    id: str
    topic: str                         # 研究主题
    target_agent: str                  # 目标 Agent
    priority: int                      # 优先级 1-5
    queries: List[str]                 # 建议查询
    status: DirectionStatus            # 状态
    completion_criteria: str           # 完成标准描述
    evidence_ids: List[str]            # 已收集的证据 ID

    # 目标模块映射（对应 Chair 的 12 模块）
    target_modules: List[str] = field(default_factory=list)  # 目标模块列表

    # 迭代追踪
    iterations_spent: int = 0          # 已花费的迭代次数
    last_iteration: int = 0            # 最后处理的迭代轮次

    # DFRS 标记
    needs_deep_research: bool = False  # 是否需要深入研究
    deep_research_findings: List[str] = field(default_factory=list)  # 深入研究的发现

    # 每个方向独立的研究模式 (新增)
    preferred_mode: str = "breadth_first"  # "breadth_first" | "depth_first" | "skip"
    mode_reason: str = ""              # 模式选择理由

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "id": self.id,
            "topic": self.topic,
            "target_agent": self.target_agent,
            "target_modules": self.target_modules,
            "priority": self.priority,
            "queries": self.queries,
            "status": self.status.value,
            "completion_criteria": self.completion_criteria,
            "evidence_ids": self.evidence_ids,
            "iterations_spent": self.iterations_spent,
            "last_iteration": self.last_iteration,
            "needs_deep_research": self.needs_deep_research,
            "deep_research_findings": self.deep_research_findings,
            "preferred_mode": self.preferred_mode,
            "mode_reason": self.mode_reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchDirection":
        """从字典反序列化"""
        return cls(
            id=data["id"],
            topic=data["topic"],
            target_agent=data["target_agent"],
            priority=data.get("priority", 3),
            queries=data.get("queries", []),
            status=DirectionStatus(data.get("status", "pending")),
            completion_criteria=data.get("completion_criteria", ""),
            evidence_ids=data.get("evidence_ids", []),
            target_modules=data.get("target_modules", []),
            iterations_spent=data.get("iterations_spent", 0),
            last_iteration=data.get("last_iteration", 0),
            needs_deep_research=data.get("needs_deep_research", False),
            deep_research_findings=data.get("deep_research_findings", []),
            preferred_mode=data.get("preferred_mode", "breadth_first"),
            mode_reason=data.get("mode_reason", ""),
        )

    def mark_completed(self):
        """标记为完成"""
        self.status = DirectionStatus.COMPLETED

    def mark_in_progress(self, iteration: int):
        """标记为进行中"""
        self.status = DirectionStatus.IN_PROGRESS
        self.last_iteration = iteration
        self.iterations_spent += 1

    def add_evidence(self, evidence_id: str):
        """添加证据"""
        if evidence_id not in self.evidence_ids:
            self.evidence_ids.append(evidence_id)


@dataclass
class ResearchPlan:
    """
    研究计划

    由 PlanAgent 生成的完整研究计划。
    """
    id: str
    case_summary: str                  # 病例摘要
    key_entities: Dict[str, List[str]] # 关键实体 {基因: [], 变异: [], 药物: []}
    directions: List[ResearchDirection] # 研究方向列表
    initial_mode: ResearchMode         # 初始研究模式
    created_at: str                    # 创建时间

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "id": self.id,
            "case_summary": self.case_summary,
            "key_entities": self.key_entities,
            "directions": [d.to_dict() for d in self.directions],
            "initial_mode": self.initial_mode.value,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchPlan":
        """从字典反序列化"""
        return cls(
            id=data["id"],
            case_summary=data.get("case_summary", ""),
            key_entities=data.get("key_entities", {}),
            directions=[ResearchDirection.from_dict(d) for d in data.get("directions", [])],
            initial_mode=ResearchMode(data.get("initial_mode", "breadth_first")),
            created_at=data.get("created_at", ""),
        )

    def get_directions_for_agent(self, agent_name: str) -> List[ResearchDirection]:
        """获取特定 Agent 的研究方向"""
        return [d for d in self.directions if d.target_agent == agent_name]

    def get_directions_for_module(self, module_name: str) -> List[ResearchDirection]:
        """获取特定模块的研究方向"""
        return [d for d in self.directions if module_name in d.target_modules]

    def get_direction_by_id(self, direction_id: str) -> Optional[ResearchDirection]:
        """根据 ID 获取研究方向"""
        for d in self.directions:
            if d.id == direction_id:
                return d
        return None

    def get_module_coverage(self) -> Dict[str, List[str]]:
        """获取模块覆盖情况"""
        coverage = {}
        for d in self.directions:
            for module in d.target_modules:
                if module not in coverage:
                    coverage[module] = []
                coverage[module].append(d.id)
        return coverage

    def validate_module_coverage(self, required_modules: List[str]) -> List[str]:
        """验证模块覆盖，返回缺失的模块列表"""
        coverage = self.get_module_coverage()
        missing = [m for m in required_modules if m not in coverage]
        return missing

    def get_pending_directions(self, agent_name: Optional[str] = None) -> List[ResearchDirection]:
        """获取待处理的研究方向"""
        pending = [d for d in self.directions if d.status == DirectionStatus.PENDING]
        if agent_name:
            pending = [d for d in pending if d.target_agent == agent_name]
        return pending

    def get_directions_requiring_depth(self) -> List[ResearchDirection]:
        """获取需要深入研究的方向"""
        return [d for d in self.directions if d.needs_deep_research]

    def calculate_direction_completion_rate(self) -> float:
        """计算研究方向完成率"""
        if not self.directions:
            return 1.0
        completed = len([d for d in self.directions if d.status == DirectionStatus.COMPLETED])
        return completed / len(self.directions)

    def summary(self) -> Dict[str, Any]:
        """返回计划摘要"""
        status_counts = {}
        agent_counts = {}

        for d in self.directions:
            # 按状态统计
            s = d.status.value
            status_counts[s] = status_counts.get(s, 0) + 1

            # 按 Agent 统计
            a = d.target_agent
            agent_counts[a] = agent_counts.get(a, 0) + 1

        # 统计每个方向的证据数
        evidence_counts = {d.id: len(d.evidence_ids) for d in self.directions}

        return {
            "total_directions": len(self.directions),
            "completion_rate": self.calculate_direction_completion_rate(),
            "directions_by_status": status_counts,
            "directions_by_agent": agent_counts,
            "pending_count": len(self.get_pending_directions()),
            "depth_required_count": len(self.get_directions_requiring_depth()),
            "evidence_per_direction": evidence_counts,
        }


# ==================== 工厂函数 ====================

def create_research_plan(
    case_summary: str,
    key_entities: Dict[str, List[str]],
    directions: List[Dict[str, Any]],
) -> ResearchPlan:
    """
    创建研究计划

    Args:
        case_summary: 病例摘要
        key_entities: 关键实体
        directions: 研究方向列表（字典格式）

    Returns:
        ResearchPlan 实例
    """
    from datetime import datetime

    plan_id = f"plan_{uuid.uuid4().hex[:8]}"

    # 转换方向
    parsed_directions = []
    for i, d in enumerate(directions):
        d_id = d.get("id", f"D{i+1}")
        parsed_directions.append(ResearchDirection(
            id=d_id,
            topic=d["topic"],
            target_agent=d["target_agent"],
            priority=d.get("priority", 3),
            queries=d.get("queries", []),
            status=DirectionStatus.PENDING,
            completion_criteria=d.get("completion_criteria", "收集到相关证据"),
            evidence_ids=[],
            target_modules=d.get("target_modules", []),
        ))

    return ResearchPlan(
        id=plan_id,
        case_summary=case_summary,
        key_entities=key_entities,
        directions=parsed_directions,
        initial_mode=ResearchMode.BREADTH_FIRST,
        created_at=datetime.now().isoformat(),
    )


def load_research_plan(data: Dict[str, Any]) -> Optional[ResearchPlan]:
    """从字典加载研究计划"""
    if not data:
        return None
    return ResearchPlan.from_dict(data)


# ==================== 动态模式决策 ====================

def determine_research_mode(
    iteration: int,
    plan: ResearchPlan,
    gaps_requiring_depth: List[Dict[str, Any]],
) -> ResearchMode:
    """
    动态决定当前迭代的研究模式

    Args:
        iteration: 当前迭代轮次
        plan: 研究计划
        gaps_requiring_depth: 需要深入研究的空白列表

    Returns:
        研究模式
    """
    # 规则 1：前 2 轮强制 BFRS（广度收集）
    if iteration < 2:
        return ResearchMode.BREADTH_FIRST

    # 规则 2：检查是否有需要深入的高优先级发现
    if gaps_requiring_depth:
        return ResearchMode.DEPTH_FIRST

    # 规则 3：如果还有未覆盖的研究方向，继续 BFRS
    uncovered_directions = plan.get_pending_directions()
    if uncovered_directions:
        return ResearchMode.BREADTH_FIRST

    # 规则 4：默认 DFRS 深入已有发现
    return ResearchMode.DEPTH_FIRST


if __name__ == "__main__":
    # 测试
    plan = create_research_plan(
        case_summary="58岁女性，晚期非小细胞肺癌，EGFR L858R 突变阳性",
        key_entities={
            "genes": ["EGFR"],
            "variants": ["L858R"],
            "cancer_type": ["NSCLC"],
        },
        directions=[
            {
                "id": "D1",
                "topic": "EGFR L858R 变异证据收集",
                "target_agent": "Geneticist",
                "target_modules": ["分子特征", "治疗路线图"],
                "priority": 1,
                "queries": ["EGFR L858R sensitivity", "EGFR L858R TKI response"],
                "completion_criteria": "收集到至少 2 条药敏证据",
            },
            {
                "id": "D2",
                "topic": "临床试验匹配",
                "target_agent": "Recruiter",
                "target_modules": ["临床试验推荐", "治疗路线图"],
                "priority": 2,
                "queries": ["EGFR NSCLC clinical trial"],
                "completion_criteria": "找到至少 3 个相关临床试验",
            },
        ],
    )

    print("Research Plan 测试:")
    print(f"  计划 ID: {plan.id}")
    print(f"  摘要: {plan.summary()}")

    # 测试序列化
    data = plan.to_dict()
    loaded = load_research_plan(data)
    print(f"  序列化后方向数: {len(loaded.directions)}")

    # 测试模式决策
    mode = determine_research_mode(0, plan, [])
    print(f"  迭代 0 模式: {mode.value}")
    mode = determine_research_mode(3, plan, [{"type": "conflict"}])
    print(f"  迭代 3 (有空白) 模式: {mode.value}")
