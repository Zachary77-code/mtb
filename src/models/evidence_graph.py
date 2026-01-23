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
    """证据等级（CIViC Evidence Level）"""
    A = "A"  # Validated - 已验证，多项独立研究或 meta 分析支持
    B = "B"  # Clinical - 临床证据，来自临床试验或大规模临床研究
    C = "C"  # Case Study - 病例研究，来自个案报道或小规模病例系列
    D = "D"  # Preclinical - 临床前证据，来自细胞系、动物模型等实验
    E = "E"  # Inferential - 推断性证据，间接证据或基于生物学原理的推断


class CivicEvidenceType(str, Enum):
    """CIViC 证据类型（临床意义分类）"""
    PREDICTIVE = "predictive"      # 预测性 - 预测对某种治疗的反应
    DIAGNOSTIC = "diagnostic"      # 诊断性 - 用于疾病诊断
    PROGNOSTIC = "prognostic"      # 预后性 - 与疾病预后相关
    PREDISPOSING = "predisposing"  # 易感性 - 与癌症风险相关
    ONCOGENIC = "oncogenic"        # 致癌性 - 变异的致癌功能


class ContextType(str, Enum):
    """上下文类型（参考 DeepEvidence 论文设计）"""
    SPECIES = "species"           # 物种 (human, mouse, etc.)
    CELL_TYPE = "cell_type"       # 细胞/癌种 (NSCLC, HCC, etc.)
    TISSUE = "tissue"             # 组织类型
    ASSAY = "assay"               # 实验方法 (WB, IHC, NGS, etc.)
    SAMPLE_SIZE = "sample_size"   # 样本量
    TREATMENT = "treatment"       # 治疗背景
    STAGE = "stage"               # 疾病分期
    BIOMARKER = "biomarker"       # 生物标志物状态


@dataclass
class EvidenceContext:
    """
    证据上下文（参考 DeepEvidence 论文设计）

    存储实验/临床背景信息，使证据可比较和可复用。
    Context 信息通常作为 observation 的一部分，只有当被多个 findings 复用时才创建独立节点。
    """
    species: Optional[str] = None          # 物种: human, mouse, rat
    cell_type: Optional[str] = None        # 细胞/癌种: NSCLC, HCC, melanoma
    tissue: Optional[str] = None           # 组织: lung, liver, brain
    assay: Optional[str] = None            # 方法: NGS, IHC, WB, FISH
    sample_size: Optional[int] = None      # 样本量
    treatment_line: Optional[str] = None   # 治疗线: 1L, 2L, 3L+
    disease_stage: Optional[str] = None    # 分期: I, II, III, IV
    biomarker_status: Optional[str] = None # 标志物状态: EGFR+, PD-L1 high

    # 扩展字段
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "species": self.species,
            "cell_type": self.cell_type,
            "tissue": self.tissue,
            "assay": self.assay,
            "sample_size": self.sample_size,
            "treatment_line": self.treatment_line,
            "disease_stage": self.disease_stage,
            "biomarker_status": self.biomarker_status,
            "extras": self.extras,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceContext":
        """从字典反序列化"""
        return cls(
            species=data.get("species"),
            cell_type=data.get("cell_type"),
            tissue=data.get("tissue"),
            assay=data.get("assay"),
            sample_size=data.get("sample_size"),
            treatment_line=data.get("treatment_line"),
            disease_stage=data.get("disease_stage"),
            biomarker_status=data.get("biomarker_status"),
            extras=data.get("extras", {}),
        )

    def is_empty(self) -> bool:
        """检查是否为空上下文"""
        return not any([
            self.species, self.cell_type, self.tissue, self.assay,
            self.sample_size, self.treatment_line, self.disease_stage,
            self.biomarker_status, self.extras
        ])

    def to_summary(self) -> str:
        """生成上下文摘要字符串"""
        parts = []
        if self.cell_type:
            parts.append(self.cell_type)
        if self.species and self.species != "human":
            parts.append(self.species)
        if self.tissue:
            parts.append(self.tissue)
        if self.disease_stage:
            parts.append(f"stage {self.disease_stage}")
        if self.treatment_line:
            parts.append(self.treatment_line)
        if self.assay:
            parts.append(f"by {self.assay}")
        if self.sample_size:
            parts.append(f"n={self.sample_size}")
        return ", ".join(parts) if parts else ""


class RelationType(str, Enum):
    """证据关系类型"""
    # 现有类型
    SUPPORTS = "supports"           # 支持
    CONTRADICTS = "contradicts"     # 反驳
    TREATS = "treats"               # 治疗关系
    CAUSES_RESISTANCE = "causes_resistance"  # 导致耐药
    SENSITIZES = "sensitizes"       # 增敏
    RELATED_TO = "related_to"       # 一般关联
    DERIVED_FROM = "derived_from"   # 来源于
    MECHANISM_OF = "mechanism_of"   # 机制解释

    # 新增：机制关系 (参考 DeepEvidence 论文)
    ACTIVATES = "activates"                    # 激活
    INHIBITS = "inhibits"                      # 抑制
    BINDS = "binds"                            # 结合
    PHOSPHORYLATES = "phosphorylates"          # 磷酸化
    REGULATES_EXPRESSION = "regulates_expression"  # 调控表达

    # 新增：成员/注释关系
    MEMBER_OF_PATHWAY = "member_of_pathway"    # 通路成员
    EXPRESSED_IN = "expressed_in"              # 表达于
    ASSOCIATED_WITH = "associated_with"        # 关联

    # 新增：证据关系
    CITES = "cites"                            # 引用
    REFUTES = "refutes"                        # 驳斥
    INCONCLUSIVE_FOR = "inconclusive_for"      # 不确定


@dataclass
class EvidenceNode:
    """
    证据节点（参考 DeepEvidence 论文设计）

    每个节点代表一条独立的证据，可以是分子发现、临床数据、文献等。
    包含结构化的 context 和 observation 以支持证据追溯和比较。
    """
    id: str
    evidence_type: EvidenceType
    content: Dict[str, Any]        # 完整内容，不限制长度
    source_agent: str              # 来源 Agent
    source_tool: Optional[str]     # 来源工具
    grade: Optional[EvidenceGrade] # 证据等级 (CIViC Evidence Level: A/B/C/D/E)
    civic_evidence_type: Optional[CivicEvidenceType] = None  # CIViC 证据类型
    created_at: datetime = field(default_factory=datetime.now)
    iteration: int = 0             # 收集时的迭代轮次
    research_mode: str = "breadth_first"  # 收集时的模式 (breadth_first / depth_first)

    # DFRS 相关
    needs_deep_research: bool = False  # 是否需要深入研究
    depth_research_reason: Optional[str] = None  # 需要深入的原因

    # ========== 新增字段 (参考 DeepEvidence 论文) ==========

    # Observation: 简短事实陈述 (≤50词，包含 context 摘要)
    # 格式: "{finding} in {context} [provenance]"
    observation: Optional[str] = None

    # Context: 结构化上下文 (species, cell_type, assay 等)
    context: Optional[EvidenceContext] = None

    # Provenance: 来源追踪 (PMID:12345678 或 CIViC@2024-01)
    provenance: Optional[str] = None

    # Numeric Result: 量化结果
    # 格式: {value, unit, CI_95, p_value, response_rate, ...}
    numeric_result: Optional[Dict[str, Any]] = None

    # ========== 保留字段 ==========
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
            "civic_evidence_type": self.civic_evidence_type.value if self.civic_evidence_type else None,
            "created_at": self.created_at.isoformat(),
            "iteration": self.iteration,
            "research_mode": self.research_mode,
            "needs_deep_research": self.needs_deep_research,
            "depth_research_reason": self.depth_research_reason,
            # 新增字段
            "observation": self.observation,
            "context": self.context.to_dict() if self.context else None,
            "provenance": self.provenance,
            "numeric_result": self.numeric_result,
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
            civic_evidence_type=CivicEvidenceType(data["civic_evidence_type"]) if data.get("civic_evidence_type") else None,
            created_at=datetime.fromisoformat(data["created_at"]),
            iteration=data.get("iteration", 0),
            research_mode=data.get("research_mode", "breadth_first"),
            needs_deep_research=data.get("needs_deep_research", False),
            depth_research_reason=data.get("depth_research_reason"),
            # 新增字段
            observation=data.get("observation"),
            context=EvidenceContext.from_dict(data["context"]) if data.get("context") else None,
            provenance=data.get("provenance"),
            numeric_result=data.get("numeric_result"),
            metadata=data.get("metadata", {}),
        )

    def generate_observation(self, max_words: int = 50) -> str:
        """
        从 content + context 自动生成 observation

        格式: "{finding} in {context} ({numeric}) [provenance]"
        示例: "EGFR L858R shows 45% response rate in NSCLC by NGS [PMID:12345678]"
        """
        parts = []

        # 主要发现
        if "finding" in self.content:
            parts.append(str(self.content["finding"]))
        elif "summary" in self.content:
            parts.append(str(self.content["summary"]))
        elif "title" in self.content:
            parts.append(str(self.content["title"]))

        # 上下文
        if self.context and not self.context.is_empty():
            ctx_summary = self.context.to_summary()
            if ctx_summary:
                parts.append(f"in {ctx_summary}")

        # 量化结果
        if self.numeric_result:
            if "value" in self.numeric_result:
                unit = self.numeric_result.get("unit", "")
                parts.append(f"({self.numeric_result['value']}{unit})")
            elif "response_rate" in self.numeric_result:
                parts.append(f"(RR: {self.numeric_result['response_rate']})")

        # 来源
        if self.provenance:
            parts.append(f"[{self.provenance}]")

        observation = " ".join(parts)

        # 截断到 max_words
        words = observation.split()
        if len(words) > max_words:
            observation = " ".join(words[:max_words]) + "..."

        return observation

    def has_context(self) -> bool:
        """检查是否有上下文"""
        return self.context is not None and not self.context.is_empty()

    def has_provenance(self) -> bool:
        """检查是否有来源追踪"""
        return bool(self.provenance)


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

    def add_node(
        self,
        evidence_type: EvidenceType,
        content: Dict[str, Any],
        source_agent: str,
        source_tool: Optional[str] = None,
        grade: Optional[EvidenceGrade] = None,
        civic_evidence_type: Optional[CivicEvidenceType] = None,
        iteration: int = 0,
        research_mode: str = "breadth_first",
        needs_deep_research: bool = False,
        depth_research_reason: Optional[str] = None,
        # 新增参数
        observation: Optional[str] = None,
        context: Optional[EvidenceContext] = None,
        provenance: Optional[str] = None,
        numeric_result: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        添加证据节点

        Args:
            evidence_type: 证据类型
            content: 完整内容
            source_agent: 来源 Agent
            source_tool: 来源工具
            grade: 证据等级 (CIViC Level)
            civic_evidence_type: CIViC 证据类型
            iteration: 迭代轮次
            research_mode: 研究模式
            needs_deep_research: 是否需要深入研究
            depth_research_reason: 深入研究原因
            observation: 简短事实陈述 (≤50词)
            context: 结构化上下文
            provenance: 来源追踪 (PMID 或 KG@version)
            numeric_result: 量化结果
            metadata: 额外元数据

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
            civic_evidence_type=civic_evidence_type,
            created_at=datetime.now(),
            iteration=iteration,
            research_mode=research_mode,
            needs_deep_research=needs_deep_research,
            depth_research_reason=depth_research_reason,
            # 新增字段
            observation=observation,
            context=context,
            provenance=provenance,
            numeric_result=numeric_result,
            metadata=metadata or {},
        )

        self.nodes[node_id] = node
        self._adjacency[node_id] = set()

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

        # 2. 检查低等级证据 (CIViC Level C/D/E 需要深入研究)
        low_grade_nodes = [
            n for n in self.nodes.values()
            if n.grade in [EvidenceGrade.C, EvidenceGrade.D, EvidenceGrade.E]
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

    # 添加测试节点 (带 context 和 observation)
    node1_id = graph.add_node(
        evidence_type=EvidenceType.MOLECULAR,
        content={
            "gene": "EGFR",
            "variant": "L858R",
            "finding": "EGFR L858R mutation confers sensitivity to EGFR-TKIs"
        },
        source_agent="Geneticist",
        source_tool="search_civic",
        grade=EvidenceGrade.A,
        civic_evidence_type=CivicEvidenceType.PREDICTIVE,
        iteration=1,
        # 新增参数
        context=EvidenceContext(
            species="human",
            cell_type="NSCLC",
            assay="NGS",
            sample_size=1200,
            treatment_line="1L"
        ),
        provenance="PMID:28854312",
        numeric_result={
            "response_rate": 0.72,
            "CI_95": [0.65, 0.79]
        }
    )

    node2_id = graph.add_node(
        evidence_type=EvidenceType.DRUG,
        content={
            "drug": "Osimertinib",
            "indication": "EGFR+ NSCLC",
            "finding": "Osimertinib is FDA-approved for EGFR+ NSCLC"
        },
        source_agent="Oncologist",
        source_tool="search_fda_label",
        grade=EvidenceGrade.A,
        iteration=1,
        provenance="FDA Label 2024",
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

    # 测试 observation 生成
    node1 = graph.get_node(node1_id)
    print(f"\n节点 1 (带 context):")
    print(f"  has_context: {node1.has_context()}")
    print(f"  context: {node1.context.to_summary() if node1.context else 'None'}")
    print(f"  observation: {node1.generate_observation()}")

    # 测试序列化
    print("\n序列化测试:")
    data = graph.to_dict()
    loaded = load_evidence_graph(data)
    print(f"  序列化后节点数: {len(loaded)}")

    # 验证 context 保留
    loaded_node1 = loaded.get_node(node1_id)
    print(f"  反序列化后 has_context: {loaded_node1.has_context()}")
    print(f"  反序列化后 provenance: {loaded_node1.provenance}")
