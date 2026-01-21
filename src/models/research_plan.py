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


class QuestionPriority(int, Enum):
    """问题优先级"""
    CRITICAL = 1    # 关键问题
    HIGH = 2        # 高优先级
    MEDIUM = 3      # 中优先级
    LOW = 4         # 低优先级


@dataclass
class ResearchQuestion:
    """
    研究问题

    PlanAgent 生成的需要回答的问题。
    """
    id: str
    text: str                          # 问题内容
    priority: QuestionPriority         # 优先级
    target_agents: List[str]           # 目标 Agent 列表
    related_entities: List[str]        # 相关实体（基因、药物等）
    is_covered: bool = False           # 是否已有证据覆盖
    evidence_ids: List[str] = field(default_factory=list)  # 关联的证据 ID

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "id": self.id,
            "text": self.text,
            "priority": self.priority.value,
            "target_agents": self.target_agents,
            "related_entities": self.related_entities,
            "is_covered": self.is_covered,
            "evidence_ids": self.evidence_ids,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchQuestion":
        """从字典反序列化"""
        return cls(
            id=data["id"],
            text=data["text"],
            priority=QuestionPriority(data["priority"]),
            target_agents=data.get("target_agents", []),
            related_entities=data.get("related_entities", []),
            is_covered=data.get("is_covered", False),
            evidence_ids=data.get("evidence_ids", []),
        )


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
    related_question_ids: List[str]    # 关联的研究问题 ID

    # 迭代追踪
    iterations_spent: int = 0          # 已花费的迭代次数
    last_iteration: int = 0            # 最后处理的迭代轮次

    # DFRS 标记
    needs_deep_research: bool = False  # 是否需要深入研究
    deep_research_findings: List[str] = field(default_factory=list)  # 深入研究的发现

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "id": self.id,
            "topic": self.topic,
            "target_agent": self.target_agent,
            "priority": self.priority,
            "queries": self.queries,
            "status": self.status.value,
            "completion_criteria": self.completion_criteria,
            "evidence_ids": self.evidence_ids,
            "related_question_ids": self.related_question_ids,
            "iterations_spent": self.iterations_spent,
            "last_iteration": self.last_iteration,
            "needs_deep_research": self.needs_deep_research,
            "deep_research_findings": self.deep_research_findings,
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
            related_question_ids=data.get("related_question_ids", []),
            iterations_spent=data.get("iterations_spent", 0),
            last_iteration=data.get("last_iteration", 0),
            needs_deep_research=data.get("needs_deep_research", False),
            deep_research_findings=data.get("deep_research_findings", []),
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
    questions: List[ResearchQuestion]  # 研究问题列表
    directions: List[ResearchDirection] # 研究方向列表
    initial_mode: ResearchMode         # 初始研究模式
    created_at: str                    # 创建时间

    # 收敛条件
    min_evidence_per_question: int = 1  # 每个问题的最小证据数
    target_coverage: float = 0.8        # 目标问题覆盖率

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "id": self.id,
            "case_summary": self.case_summary,
            "key_entities": self.key_entities,
            "questions": [q.to_dict() for q in self.questions],
            "directions": [d.to_dict() for d in self.directions],
            "initial_mode": self.initial_mode.value,
            "created_at": self.created_at,
            "min_evidence_per_question": self.min_evidence_per_question,
            "target_coverage": self.target_coverage,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchPlan":
        """从字典反序列化"""
        return cls(
            id=data["id"],
            case_summary=data.get("case_summary", ""),
            key_entities=data.get("key_entities", {}),
            questions=[ResearchQuestion.from_dict(q) for q in data.get("questions", [])],
            directions=[ResearchDirection.from_dict(d) for d in data.get("directions", [])],
            initial_mode=ResearchMode(data.get("initial_mode", "breadth_first")),
            created_at=data.get("created_at", ""),
            min_evidence_per_question=data.get("min_evidence_per_question", 1),
            target_coverage=data.get("target_coverage", 0.8),
        )

    def get_directions_for_agent(self, agent_name: str) -> List[ResearchDirection]:
        """获取特定 Agent 的研究方向"""
        return [d for d in self.directions if d.target_agent == agent_name]

    def get_pending_directions(self, agent_name: Optional[str] = None) -> List[ResearchDirection]:
        """获取待处理的研究方向"""
        pending = [d for d in self.directions if d.status == DirectionStatus.PENDING]
        if agent_name:
            pending = [d for d in pending if d.target_agent == agent_name]
        return pending

    def get_directions_requiring_depth(self) -> List[ResearchDirection]:
        """获取需要深入研究的方向"""
        return [d for d in self.directions if d.needs_deep_research]

    def calculate_coverage(self) -> float:
        """计算问题覆盖率"""
        if not self.questions:
            return 1.0
        covered = len([q for q in self.questions if q.is_covered])
        return covered / len(self.questions)

    def update_question_coverage(self, question_id: str, evidence_id: str):
        """更新问题覆盖状态"""
        for q in self.questions:
            if q.id == question_id:
                if evidence_id not in q.evidence_ids:
                    q.evidence_ids.append(evidence_id)
                if len(q.evidence_ids) >= self.min_evidence_per_question:
                    q.is_covered = True
                break

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

        return {
            "total_questions": len(self.questions),
            "total_directions": len(self.directions),
            "coverage": self.calculate_coverage(),
            "directions_by_status": status_counts,
            "directions_by_agent": agent_counts,
            "pending_count": len(self.get_pending_directions()),
            "depth_required_count": len(self.get_directions_requiring_depth()),
        }


# ==================== 工厂函数 ====================

def create_research_plan(
    case_summary: str,
    key_entities: Dict[str, List[str]],
    questions: List[Dict[str, Any]],
    directions: List[Dict[str, Any]],
) -> ResearchPlan:
    """
    创建研究计划

    Args:
        case_summary: 病例摘要
        key_entities: 关键实体
        questions: 研究问题列表（字典格式）
        directions: 研究方向列表（字典格式）

    Returns:
        ResearchPlan 实例
    """
    from datetime import datetime

    plan_id = f"plan_{uuid.uuid4().hex[:8]}"

    # 转换问题
    parsed_questions = []
    for i, q in enumerate(questions):
        q_id = q.get("id", f"Q{i+1}")
        parsed_questions.append(ResearchQuestion(
            id=q_id,
            text=q["text"],
            priority=QuestionPriority(q.get("priority", 3)),
            target_agents=q.get("target_agents", []),
            related_entities=q.get("related_entities", []),
        ))

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
            related_question_ids=d.get("related_question_ids", []),
        ))

    return ResearchPlan(
        id=plan_id,
        case_summary=case_summary,
        key_entities=key_entities,
        questions=parsed_questions,
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
        questions=[
            {
                "id": "Q1",
                "text": "EGFR L858R 对哪些 TKI 敏感？",
                "priority": 1,
                "target_agents": ["Geneticist", "Oncologist"],
                "related_entities": ["EGFR", "L858R"],
            },
            {
                "id": "Q2",
                "text": "患者是否存在耐药突变？",
                "priority": 1,
                "target_agents": ["Geneticist"],
                "related_entities": ["EGFR", "T790M"],
            },
            {
                "id": "Q3",
                "text": "有哪些适用的临床试验？",
                "priority": 2,
                "target_agents": ["Recruiter"],
                "related_entities": ["EGFR", "NSCLC"],
            },
        ],
        directions=[
            {
                "id": "D1",
                "topic": "EGFR L858R 变异证据收集",
                "target_agent": "Geneticist",
                "priority": 1,
                "queries": ["EGFR L858R sensitivity", "EGFR L858R TKI response"],
                "completion_criteria": "收集到至少 2 条药敏证据",
                "related_question_ids": ["Q1"],
            },
            {
                "id": "D2",
                "topic": "临床试验匹配",
                "target_agent": "Recruiter",
                "priority": 2,
                "queries": ["EGFR NSCLC clinical trial"],
                "completion_criteria": "找到至少 3 个相关临床试验",
                "related_question_ids": ["Q3"],
            },
        ],
    )

    print("Research Plan 测试:")
    print(f"  计划 ID: {plan.id}")
    print(f"  摘要: {plan.summary()}")

    # 测试序列化
    data = plan.to_dict()
    loaded = load_research_plan(data)
    print(f"  序列化后问题数: {len(loaded.questions)}")
    print(f"  序列化后方向数: {len(loaded.directions)}")

    # 测试模式决策
    mode = determine_research_mode(0, plan, [])
    print(f"  迭代 0 模式: {mode.value}")
    mode = determine_research_mode(3, plan, [{"type": "conflict"}])
    print(f"  迭代 3 (有空白) 模式: {mode.value}")
