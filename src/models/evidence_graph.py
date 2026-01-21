"""
Evidence Graph 数据结构

全局证据图，用于存储和管理所有 Agent 收集的证据。
支持 BFRS/DFRS 研究模式的证据追踪和空白识别。
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from enum import Enum
from datetime import datetime
import uuid


class EvidenceType(str, Enum):
    """证据类型枚举"""
    MOLECULAR = "molecular"       # 分子/基因证据
    CLINICAL = "clinical"         # 临床数据
    LITERATURE = "literature"     # 文献证据
    TRIAL = "trial"               # 临床试验
    GUIDELINE = "guideline"       # 指南建议
    DRUG = "drug"                 # 药物信息
    PATHOLOGY = "pathology"       # 病理发现
    IMAGING = "imaging"           # 影像发现


class EvidenceGrade(str, Enum):
    """证据等级（参考 CLAUDE.md 中的定义）"""
    A = "A"  # Phase III RCT
    B = "B"  # Phase I-II
    C = "C"  # Retrospective
    D = "D"  # Preclinical / Expert opinion


class RelationType(str, Enum):
    """证据关系类型"""
    SUPPORTS = "supports"           # 支持
    CONTRADICTS = "contradicts"     # 反驳
    TREATS = "treats"               # 治疗关系
    CAUSES_RESISTANCE = "causes_resistance"  # 导致耐药
    SENSITIZES = "sensitizes"       # 增敏
    RELATED_TO = "related_to"       # 一般关联
    DERIVED_FROM = "derived_from"   # 来源于
    MECHANISM_OF = "mechanism_of"   # 机制解释


@dataclass
class EvidenceNode:
    """
    证据节点

    每个节点代表一条独立的证据，可以是分子发现、临床数据、文献等。
    不限制内容长度，保留完整信息。
    """
    id: str
    evidence_type: EvidenceType
    content: Dict[str, Any]        # 完整内容，不限制长度
    source_agent: str              # 来源 Agent
    source_tool: Optional[str]     # 来源工具
    grade: Optional[EvidenceGrade] # 证据等级
    related_questions: List[str]   # 关联的研究问题 ID
    created_at: datetime
    iteration: int                 # 收集时的迭代轮次
    research_mode: str             # 收集时的模式 (breadth_first / depth_first)

    # DFRS 相关
    needs_deep_research: bool = False  # 是否需要深入研究
    depth_research_reason: Optional[str] = None  # 需要深入的原因

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "id": self.id,
            "evidence_type": self.evidence_type.value,
            "content": self.content,
            "source_agent": self.source_agent,
            "source_tool": self.source_tool,
            "grade": self.grade.value if self.grade else None,
            "related_questions": self.related_questions,
            "created_at": self.created_at.isoformat(),
            "iteration": self.iteration,
            "research_mode": self.research_mode,
            "needs_deep_research": self.needs_deep_research,
            "depth_research_reason": self.depth_research_reason,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceNode":
        """从字典反序列化"""
        return cls(
            id=data["id"],
            evidence_type=EvidenceType(data["evidence_type"]),
            content=data["content"],
            source_agent=data["source_agent"],
            source_tool=data.get("source_tool"),
            grade=EvidenceGrade(data["grade"]) if data.get("grade") else None,
            related_questions=data.get("related_questions", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            iteration=data.get("iteration", 0),
            research_mode=data.get("research_mode", "breadth_first"),
            needs_deep_research=data.get("needs_deep_research", False),
            depth_research_reason=data.get("depth_research_reason"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class EvidenceEdge:
    """
    证据关系边

    表示两个证据节点之间的关系。
    """
    id: str
    source_id: str                 # 源节点 ID
    target_id: str                 # 目标节点 ID
    relation_type: RelationType    # 关系类型
    confidence: float              # 置信度 0-1
    description: Optional[str]     # 关系描述
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "confidence": self.confidence,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceEdge":
        """从字典反序列化"""
        return cls(
            id=data["id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            relation_type=RelationType(data["relation_type"]),
            confidence=data.get("confidence", 1.0),
            description=data.get("description"),
            created_at=datetime.fromisoformat(data["created_at"]),
        )


class EvidenceGraph:
    """
    全局证据图

    管理所有证据节点和关系，支持：
    - 添加/查询节点和边
    - 识别研究空白
    - 追踪 BFRS/DFRS 进度
    """

    def __init__(self):
        self.nodes: Dict[str, EvidenceNode] = {}
        self.edges: Dict[str, EvidenceEdge] = {}
        self._adjacency: Dict[str, Set[str]] = {}  # 邻接表
        self._question_index: Dict[str, Set[str]] = {}  # 问题->节点索引

    def add_node(
        self,
        evidence_type: EvidenceType,
        content: Dict[str, Any],
        source_agent: str,
        source_tool: Optional[str] = None,
        grade: Optional[EvidenceGrade] = None,
        related_questions: Optional[List[str]] = None,
        iteration: int = 0,
        research_mode: str = "breadth_first",
        needs_deep_research: bool = False,
        depth_research_reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        添加证据节点

        Returns:
            节点 ID
        """
        node_id = f"ev_{uuid.uuid4().hex[:8]}"
        node = EvidenceNode(
            id=node_id,
            evidence_type=evidence_type,
            content=content,
            source_agent=source_agent,
            source_tool=source_tool,
            grade=grade,
            related_questions=related_questions or [],
            created_at=datetime.now(),
            iteration=iteration,
            research_mode=research_mode,
            needs_deep_research=needs_deep_research,
            depth_research_reason=depth_research_reason,
            metadata=metadata or {},
        )

        self.nodes[node_id] = node
        self._adjacency[node_id] = set()

        # 更新问题索引
        for q_id in node.related_questions:
            if q_id not in self._question_index:
                self._question_index[q_id] = set()
            self._question_index[q_id].add(node_id)

        return node_id

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        confidence: float = 1.0,
        description: Optional[str] = None,
    ) -> Optional[str]:
        """
        添加证据关系边

        Returns:
            边 ID，如果节点不存在则返回 None
        """
        if source_id not in self.nodes or target_id not in self.nodes:
            return None

        edge_id = f"edge_{uuid.uuid4().hex[:8]}"
        edge = EvidenceEdge(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            confidence=confidence,
            description=description,
            created_at=datetime.now(),
        )

        self.edges[edge_id] = edge
        self._adjacency[source_id].add(target_id)
        self._adjacency[target_id].add(source_id)

        return edge_id

    def get_node(self, node_id: str) -> Optional[EvidenceNode]:
        """获取节点"""
        return self.nodes.get(node_id)

    def get_nodes_by_type(self, evidence_type: EvidenceType) -> List[EvidenceNode]:
        """按类型获取节点"""
        return [n for n in self.nodes.values() if n.evidence_type == evidence_type]

    def get_nodes_by_agent(self, agent_name: str) -> List[EvidenceNode]:
        """按来源 Agent 获取节点"""
        return [n for n in self.nodes.values() if n.source_agent == agent_name]

    def get_related_nodes(self, node_id: str) -> List[tuple]:
        """
        获取相关节点

        Returns:
            List of (node, relation_type)
        """
        if node_id not in self._adjacency:
            return []

        results = []
        for related_id in self._adjacency[node_id]:
            node = self.nodes.get(related_id)
            if node:
                # 找到关系类型
                relation = None
                for edge in self.edges.values():
                    if (edge.source_id == node_id and edge.target_id == related_id) or \
                       (edge.target_id == node_id and edge.source_id == related_id):
                        relation = edge.relation_type
                        break
                results.append((node, relation))

        return results

    def get_evidence_for_question(self, question_id: str) -> List[EvidenceNode]:
        """获取与问题相关的证据"""
        node_ids = self._question_index.get(question_id, set())
        return [self.nodes[nid] for nid in node_ids if nid in self.nodes]

    def identify_gaps(self) -> List[Dict[str, Any]]:
        """
        识别研究空白（需要 DFRS 深入研究的情况）

        Returns:
            空白列表，每个包含类型、相关节点、建议
        """
        gaps = []

        # 1. 检查证据冲突
        conflicts = self._find_conflicts()
        for conflict in conflicts:
            gaps.append({
                "type": "evidence_conflict",
                "description": "同一实体有相互矛盾的证据",
                "nodes": conflict["nodes"],
                "suggestion": "需要深入研究以解决冲突",
            })

        # 2. 检查低等级证据
        low_grade_nodes = [
            n for n in self.nodes.values()
            if n.grade in [EvidenceGrade.C, EvidenceGrade.D]
            and n.evidence_type in [EvidenceType.DRUG, EvidenceType.GUIDELINE]
        ]
        for node in low_grade_nodes:
            gaps.append({
                "type": "low_evidence_grade",
                "description": f"关键发现只有 {node.grade.value} 级证据",
                "nodes": [node.id],
                "suggestion": "需要寻找更高级别的证据支持",
            })

        # 3. 检查 Agent 标记的需深入研究项
        marked_nodes = [n for n in self.nodes.values() if n.needs_deep_research]
        for node in marked_nodes:
            gaps.append({
                "type": "agent_marked",
                "description": node.depth_research_reason or "Agent 标记需要深入研究",
                "nodes": [node.id],
                "suggestion": "执行 DFRS 深度研究",
            })

        return gaps

    def _find_conflicts(self) -> List[Dict[str, Any]]:
        """查找证据冲突"""
        conflicts = []

        # 检查 CONTRADICTS 关系
        for edge in self.edges.values():
            if edge.relation_type == RelationType.CONTRADICTS:
                conflicts.append({
                    "nodes": [edge.source_id, edge.target_id],
                    "edge_id": edge.id,
                })

        return conflicts

    def get_gaps_requiring_depth(self) -> List[Dict[str, Any]]:
        """获取需要深度研究的空白（用于 DFRS 触发）"""
        return self.identify_gaps()

    def count_new_findings(self, since_iteration: int) -> int:
        """统计指定迭代后的新发现数量"""
        return len([n for n in self.nodes.values() if n.iteration > since_iteration])

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典（用于存入 State）"""
        return {
            "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
            "edges": {eid: edge.to_dict() for eid, edge in self.edges.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceGraph":
        """从字典反序列化"""
        graph = cls()

        # 恢复节点
        for nid, node_data in data.get("nodes", {}).items():
            node = EvidenceNode.from_dict(node_data)
            graph.nodes[nid] = node
            graph._adjacency[nid] = set()

            # 重建问题索引
            for q_id in node.related_questions:
                if q_id not in graph._question_index:
                    graph._question_index[q_id] = set()
                graph._question_index[q_id].add(nid)

        # 恢复边
        for eid, edge_data in data.get("edges", {}).items():
            edge = EvidenceEdge.from_dict(edge_data)
            graph.edges[eid] = edge

            # 重建邻接表
            if edge.source_id in graph._adjacency:
                graph._adjacency[edge.source_id].add(edge.target_id)
            if edge.target_id in graph._adjacency:
                graph._adjacency[edge.target_id].add(edge.source_id)

        return graph

    def __len__(self) -> int:
        """返回节点数量"""
        return len(self.nodes)

    def summary(self) -> Dict[str, Any]:
        """返回图摘要信息"""
        type_counts = {}
        agent_counts = {}
        grade_counts = {}

        for node in self.nodes.values():
            # 按类型统计
            t = node.evidence_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

            # 按 Agent 统计
            a = node.source_agent
            agent_counts[a] = agent_counts.get(a, 0) + 1

            # 按等级统计
            if node.grade:
                g = node.grade.value
                grade_counts[g] = grade_counts.get(g, 0) + 1

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "by_type": type_counts,
            "by_agent": agent_counts,
            "by_grade": grade_counts,
            "gaps_count": len(self.identify_gaps()),
        }


# ==================== 便捷函数 ====================

def create_evidence_graph() -> EvidenceGraph:
    """创建新的证据图"""
    return EvidenceGraph()


def load_evidence_graph(data: Dict[str, Any]) -> EvidenceGraph:
    """从字典加载证据图"""
    if not data:
        return EvidenceGraph()
    return EvidenceGraph.from_dict(data)


if __name__ == "__main__":
    # 测试
    graph = create_evidence_graph()

    # 添加测试节点
    node1_id = graph.add_node(
        evidence_type=EvidenceType.MOLECULAR,
        content={"gene": "EGFR", "variant": "L858R", "frequency": "45%"},
        source_agent="Geneticist",
        source_tool="search_civic",
        grade=EvidenceGrade.A,
        related_questions=["Q1", "Q2"],
        iteration=1,
    )

    node2_id = graph.add_node(
        evidence_type=EvidenceType.DRUG,
        content={"drug": "Osimertinib", "indication": "EGFR+ NSCLC"},
        source_agent="Oncologist",
        source_tool="search_fda_label",
        grade=EvidenceGrade.A,
        related_questions=["Q1"],
        iteration=1,
    )

    # 添加关系
    graph.add_edge(
        source_id=node1_id,
        target_id=node2_id,
        relation_type=RelationType.SENSITIZES,
        description="EGFR L858R 对 Osimertinib 敏感",
    )

    print("Evidence Graph 测试:")
    print(f"  节点数: {len(graph)}")
    print(f"  摘要: {graph.summary()}")

    # 测试序列化
    data = graph.to_dict()
    loaded = load_evidence_graph(data)
    print(f"  序列化后节点数: {len(loaded)}")
