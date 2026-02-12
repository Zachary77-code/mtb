"""
Evidence Graph 数据结构 (DeepEvidence Style)

基于 DeepEvidence 论文的实体-边-观察架构重构。
每个发现被分解为多个实体(Entity)和边(Edge)，观察(Observation)作为属性附加。

核心概念:
- Entity: 原子生物医学概念，通过 canonical_id 合并去重
- Edge: 实体间的语义关系，使用受控谓词
- Observation: 简短事实陈述，附加到实体和边上

实体命名规则:
- 所有名称统一转为大写
- 同一概念不允许创建新实体，必须合并
- ID格式: {source}_{uuid8}
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Tuple
from enum import Enum
from datetime import datetime
import uuid


# ==================== 枚举类型 ====================

class EntityType(str, Enum):
    """实体类型枚举"""
    GENE = "gene"               # 基因 (GENE:EGFR)
    VARIANT = "variant"         # 变异 (EGFR_L858R)
    DRUG = "drug"               # 药物 (DRUG:OSIMERTINIB)
    DISEASE = "disease"         # 疾病/癌种 (DISEASE:NSCLC)
    PATHWAY = "pathway"         # 信号通路 (PATHWAY:EGFR_SIGNALING)
    BIOMARKER = "biomarker"     # 生物标志物 (BIOMARKER:PD-L1)
    PAPER = "paper"             # 文献 (PMID:12345678)
    TRIAL = "trial"             # 临床试验 (NCT:NCT04487080)
    GUIDELINE = "guideline"     # 指南 (NCCN:NSCLC_2024)
    REGIMEN = "regimen"         # 治疗方案 (REGIMEN:PLATINUM_DOUBLET)
    FINDING = "finding"         # 临床发现 ({source}_{uuid})


class Predicate(str, Enum):
    """边谓词枚举 (受控词汇表)"""
    # 分子机制
    ACTIVATES = "activates"                     # 激活
    INHIBITS = "inhibits"                       # 抑制
    BINDS = "binds"                             # 结合
    PHOSPHORYLATES = "phosphorylates"           # 磷酸化
    REGULATES = "regulates"                     # 调控
    AMPLIFIES = "amplifies"                     # 扩增
    MUTATES_TO = "mutates_to"                   # 突变为 (耐药突变)

    # 药物-疾病关系
    TREATS = "treats"                           # 治疗
    SENSITIZES = "sensitizes"                   # 增敏
    CAUSES_RESISTANCE = "causes_resistance"     # 导致耐药
    INTERACTS_WITH = "interacts_with"           # 药物相互作用
    CONTRAINDICATED_FOR = "contraindicated_for" # 禁忌

    # 证据关系
    SUPPORTS = "supports"                       # 支持
    CONTRADICTS = "contradicts"                 # 矛盾
    CITES = "cites"                             # 引用
    DERIVED_FROM = "derived_from"               # 来源于

    # 成员/注释关系
    MEMBER_OF = "member_of"                     # 属于 (通路成员)
    EXPRESSED_IN = "expressed_in"               # 表达于
    ASSOCIATED_WITH = "associated_with"         # 关联
    BIOMARKER_FOR = "biomarker_for"             # 生物标志物

    # 指南/试验关系
    RECOMMENDS = "recommends"                   # 推荐
    EVALUATES = "evaluates"                     # 评估 (试验评估药物)
    INCLUDES_ARM = "includes_arm"               # 包含臂


class EvidenceGrade(str, Enum):
    """证据等级 (CIViC Evidence Level)"""
    A = "A"  # Validated - 已验证，多项独立研究或 meta 分析支持
    B = "B"  # Clinical - 临床证据，来自临床试验或大规模临床研究
    C = "C"  # Case Study - 病例研究，来自个案报道或小规模病例系列
    D = "D"  # Preclinical - 临床前证据，来自细胞系、动物模型等实验
    E = "E"  # Inferential - 推断性证据，间接证据或基于生物学原理的推断


class CivicEvidenceType(str, Enum):
    """CIViC 证据类型 (临床意义分类)"""
    PREDICTIVE = "predictive"      # 预测性 - 预测对某种治疗的反应
    DIAGNOSTIC = "diagnostic"      # 诊断性 - 用于疾病诊断
    PROGNOSTIC = "prognostic"      # 预后性 - 与疾病预后相关
    PREDISPOSING = "predisposing"  # 易感性 - 与癌症风险相关
    ONCOGENIC = "oncogenic"        # 致癌性 - 变异的致癌功能


class EvidenceType(str, Enum):
    """证据类型分类（按信息性质，区别于 CIViC 临床意义分类）"""
    MOLECULAR = "molecular"                # 分子/基因组证据
    CLINICAL = "clinical"                  # 临床疗效数据 (ORR/PFS/OS)
    PATHOLOGY = "pathology"                # 病理/组织学证据
    IMAGING = "imaging"                    # 影像学证据
    GUIDELINE = "guideline"                # 指南推荐 (NCCN/CSCO/ESMO)
    DRUG = "drug"                          # 药物信息 (FDA标签/剂量/适应证)
    DRUG_INTERACTION = "drug_interaction"   # 药物相互作用
    PHARMACOKINETICS = "pharmacokinetics"   # 药代动力学
    COMORBIDITY = "comorbidity"            # 合并症评估
    ORGAN_FUNCTION = "organ_function"       # 器官功能评估
    ALLERGY = "allergy"                    # 过敏/不良反应
    SURGICAL = "surgical"                  # 手术相关证据
    RADIATION = "radiation"                # 放疗相关证据
    INTERVENTIONAL = "interventional"       # 介入治疗证据
    TRIAL = "trial"                        # 临床试验信息
    NUTRITION = "nutrition"                # 营养学证据
    CAM_EVIDENCE = "cam_evidence"          # 替代疗法证据
    SAFETY = "safety"                      # 安全性数据
    LITERATURE = "literature"              # 综合文献证据 (综述/meta分析)


# ==================== 核心数据类 ====================

@dataclass
class Observation:
    """
    观察 - 简短事实陈述 (<=50词)

    附加到 Entity 和 Edge 上，提供证据来源和上下文。
    上下文信息嵌入在 statement 中，而不是单独存储。

    格式: "{finding} ({context}) [provenance]"
    示例: "EGFR L858R shows 72% ORR to osimertinib (human, Phase III, n=347) [PMID:28854312]"
    """
    id: str                                      # obs_{uuid8}
    statement: str                               # 事实陈述 (包含嵌入的上下文)
    source_agent: str                            # 来源 Agent
    source_tool: Optional[str] = None            # 来源工具
    provenance: Optional[str] = None             # PMID:xxx, NCT:xxx, NCCN:xxx 等
    source_url: Optional[str] = None             # 完整 URL
    evidence_grade: Optional[EvidenceGrade] = None  # 证据等级 A/B/C/D/E
    civic_type: Optional[CivicEvidenceType] = None  # CIViC 证据类型
    evidence_type: Optional[EvidenceType] = None  # 证据类型分类 (molecular/clinical/drug/...)
    l_tier: Optional[str] = None                 # L1-L5 证据分层 (Phase 3 Oncologist)
    l_tier_reasoning: Optional[str] = None       # L1-L5 分层寻证过程
    direction_id: Optional[str] = None            # 所属研究方向 ID
    iteration: int = 0                           # 收集迭代轮次
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "id": self.id,
            "statement": self.statement,
            "source_agent": self.source_agent,
            "source_tool": self.source_tool,
            "provenance": self.provenance,
            "source_url": self.source_url,
            "evidence_grade": self.evidence_grade.value if self.evidence_grade else None,
            "civic_type": self.civic_type.value if self.civic_type else None,
            "evidence_type": self.evidence_type.value if self.evidence_type else None,
            "l_tier": self.l_tier,
            "l_tier_reasoning": self.l_tier_reasoning,
            "direction_id": self.direction_id,
            "iteration": self.iteration,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Observation":
        """从字典反序列化"""
        return cls(
            id=data["id"],
            statement=data["statement"],
            source_agent=data["source_agent"],
            source_tool=data.get("source_tool"),
            provenance=data.get("provenance"),
            source_url=data.get("source_url"),
            evidence_grade=EvidenceGrade(data["evidence_grade"]) if data.get("evidence_grade") else None,
            civic_type=CivicEvidenceType(data["civic_type"]) if data.get("civic_type") else None,
            evidence_type=EvidenceType(data["evidence_type"]) if data.get("evidence_type") else None,
            l_tier=data.get("l_tier"),
            l_tier_reasoning=data.get("l_tier_reasoning"),
            direction_id=data.get("direction_id"),
            iteration=data.get("iteration", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
        )

    @staticmethod
    def generate_id(source: str = "obs") -> str:
        """生成观察 ID"""
        return f"{source}_{uuid.uuid4().hex[:8]}"


@dataclass
class Entity:
    """
    实体 - 原子生物医学概念

    通过 canonical_id 进行去重合并。
    同一概念遇到多次时，observations 会累加而不是创建新实体。

    命名规则:
    - name 统一转为大写
    - canonical_id 格式: TYPE:NAME 或 特殊格式 (如变异 EGFR_L858R)
    """
    id: str                                      # {source}_{uuid8}
    canonical_id: str                            # GENE:EGFR, DRUG:OSIMERTINIB 等
    entity_type: EntityType                      # 实体类型
    name: str                                    # 规范化名称 (大写)
    aliases: List[str] = field(default_factory=list)  # 别名列表
    observations: List[Observation] = field(default_factory=list)  # 所有观察
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "id": self.id,
            "canonical_id": self.canonical_id,
            "entity_type": self.entity_type.value,
            "name": self.name,
            "aliases": self.aliases,
            "observations": [obs.to_dict() for obs in self.observations],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        """从字典反序列化"""
        return cls(
            id=data["id"],
            canonical_id=data["canonical_id"],
            entity_type=EntityType(data["entity_type"]),
            name=data["name"],
            aliases=data.get("aliases", []),
            observations=[Observation.from_dict(o) for o in data.get("observations", [])],
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
        )

    @staticmethod
    def generate_id(source: str) -> str:
        """生成实体 ID"""
        return f"{source}_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def normalize_name(name: str) -> str:
        """规范化实体名称 (转大写)"""
        return name.strip().upper()

    @staticmethod
    def generate_canonical_id(entity_type: EntityType, name: str, gene: str = None) -> str:
        """
        生成规范 ID

        Args:
            entity_type: 实体类型
            name: 实体名称
            gene: 基因名 (仅用于 VARIANT 类型)

        Returns:
            规范 ID
        """
        normalized_name = Entity.normalize_name(name)

        if entity_type == EntityType.VARIANT and gene:
            # 变异格式: GENE_VARIANT
            return f"{Entity.normalize_name(gene)}_{normalized_name}"
        elif entity_type == EntityType.PAPER:
            # 文献格式: PMID:xxx
            if normalized_name.startswith("PMID:"):
                return normalized_name
            return f"PMID:{normalized_name}"
        elif entity_type == EntityType.TRIAL:
            # 试验格式: NCT:xxx
            if normalized_name.startswith("NCT"):
                return f"NCT:{normalized_name}"
            return f"NCT:{normalized_name}"
        else:
            # 其他格式: TYPE:NAME
            return f"{entity_type.value.upper()}:{normalized_name}"

    def add_observation(self, observation: Observation) -> None:
        """添加观察 (去重)"""
        # 检查是否已存在相同 ID 的观察
        existing_ids = {obs.id for obs in self.observations}
        if observation.id not in existing_ids:
            self.observations.append(observation)
            self.updated_at = datetime.now()

    def add_alias(self, alias: str) -> None:
        """添加别名 (去重, 大写)"""
        normalized = Entity.normalize_name(alias)
        if normalized not in self.aliases and normalized != self.name:
            self.aliases.append(normalized)
            self.updated_at = datetime.now()

    def get_best_grade(self) -> Optional[EvidenceGrade]:
        """获取最高证据等级"""
        grades = [obs.evidence_grade for obs in self.observations if obs.evidence_grade]
        if not grades:
            return None
        # A > B > C > D > E
        grade_order = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}
        return min(grades, key=lambda g: grade_order.get(g.value, 5))

    def get_all_provenances(self) -> List[str]:
        """获取所有来源"""
        return list(set(obs.provenance for obs in self.observations if obs.provenance))


@dataclass
class Edge:
    """
    边 - 实体间的语义关系

    使用受控谓词词汇表。
    可附加多个观察作为关系的证据/上下文。
    """
    id: str                                      # edge_{uuid8}
    source_id: str                               # 源实体 canonical_id
    target_id: str                               # 目标实体 canonical_id
    predicate: Predicate                         # 谓词 (受控词汇)
    observations: List[Observation] = field(default_factory=list)  # 关系的观察/证据
    confidence: float = 1.0                      # 置信度 0-1
    conflict_group: Optional[str] = None         # 冲突组 ID (相同 ID 表示冲突)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "predicate": self.predicate.value,
            "observations": [obs.to_dict() for obs in self.observations],
            "confidence": self.confidence,
            "conflict_group": self.conflict_group,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Edge":
        """从字典反序列化"""
        return cls(
            id=data["id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            predicate=Predicate(data["predicate"]),
            observations=[Observation.from_dict(o) for o in data.get("observations", [])],
            confidence=data.get("confidence", 1.0),
            conflict_group=data.get("conflict_group"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
        )

    @staticmethod
    def generate_id() -> str:
        """生成边 ID"""
        return f"edge_{uuid.uuid4().hex[:8]}"

    def add_observation(self, observation: Observation) -> None:
        """添加观察 (去重)"""
        existing_ids = {obs.id for obs in self.observations}
        if observation.id not in existing_ids:
            self.observations.append(observation)

    def get_best_grade(self) -> Optional[EvidenceGrade]:
        """获取最高证据等级"""
        grades = [obs.evidence_grade for obs in self.observations if obs.evidence_grade]
        if not grades:
            return None
        grade_order = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}
        return min(grades, key=lambda g: grade_order.get(g.value, 5))


# ==================== 证据图 ====================

class EvidenceGraph:
    """
    证据图 - 实体中心的知识图谱

    核心特性:
    - 实体通过 canonical_id 去重合并
    - 边通过 (source_id, target_id, predicate) 去重
    - 观察附加到实体和边上
    - 支持冲突检测和标记
    """

    def __init__(self):
        self.entities: Dict[str, Entity] = {}    # canonical_id -> Entity
        self.edges: Dict[str, Edge] = {}         # edge_id -> Edge
        self._edge_index: Dict[str, Set[str]] = {}  # entity_canonical_id -> edge_ids
        self._name_index: Dict[str, str] = {}    # normalized_name -> canonical_id (用于模糊匹配)

    # ==================== 实体操作 ====================

    def get_or_create_entity(
        self,
        canonical_id: str,
        entity_type: EntityType,
        name: str,
        source: str,
        aliases: List[str] = None,
    ) -> Entity:
        """
        获取或创建实体 (核心合并逻辑)

        如果 canonical_id 已存在，返回现有实体。
        如果不存在，创建新实体并添加到图中。

        Args:
            canonical_id: 规范 ID
            entity_type: 实体类型
            name: 实体名称
            source: 来源 (用于生成 entity id)
            aliases: 别名列表

        Returns:
            实体对象
        """
        normalized_name = Entity.normalize_name(name)

        # 1. 通过 canonical_id 查找
        if canonical_id in self.entities:
            entity = self.entities[canonical_id]
            # 添加可能的新别名
            if aliases:
                for alias in aliases:
                    entity.add_alias(alias)
            return entity

        # 2. 通过规范化名称查找 (模糊匹配)
        if normalized_name in self._name_index:
            existing_canonical_id = self._name_index[normalized_name]
            if existing_canonical_id in self.entities:
                entity = self.entities[existing_canonical_id]
                if aliases:
                    for alias in aliases:
                        entity.add_alias(alias)
                return entity

        # 3. 创建新实体
        entity = Entity(
            id=Entity.generate_id(source),
            canonical_id=canonical_id,
            entity_type=entity_type,
            name=normalized_name,
            aliases=[Entity.normalize_name(a) for a in (aliases or []) if Entity.normalize_name(a) != normalized_name],
        )

        self.entities[canonical_id] = entity
        self._edge_index[canonical_id] = set()
        self._name_index[normalized_name] = canonical_id

        # 索引别名
        for alias in entity.aliases:
            if alias not in self._name_index:
                self._name_index[alias] = canonical_id

        return entity

    def add_observation_to_entity(
        self,
        canonical_id: str,
        observation: Observation,
    ) -> bool:
        """
        向实体添加观察

        Args:
            canonical_id: 实体规范 ID
            observation: 观察对象

        Returns:
            是否成功添加
        """
        if canonical_id not in self.entities:
            return False

        self.entities[canonical_id].add_observation(observation)
        return True

    def find_entity_by_name(
        self,
        name: str,
        entity_type: EntityType = None,
    ) -> Optional[Entity]:
        """
        通过名称查找实体 (模糊匹配)

        Args:
            name: 实体名称
            entity_type: 可选的类型过滤

        Returns:
            匹配的实体或 None
        """
        normalized = Entity.normalize_name(name)

        # 通过名称索引查找
        if normalized in self._name_index:
            canonical_id = self._name_index[normalized]
            entity = self.entities.get(canonical_id)
            if entity and (entity_type is None or entity.entity_type == entity_type):
                return entity

        # 遍历查找 (包括别名)
        for entity in self.entities.values():
            if entity_type and entity.entity_type != entity_type:
                continue
            if entity.name == normalized or normalized in entity.aliases:
                return entity

        return None

    def get_entity(self, canonical_id: str) -> Optional[Entity]:
        """获取实体"""
        return self.entities.get(canonical_id)

    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """按类型获取实体"""
        return [e for e in self.entities.values() if e.entity_type == entity_type]

    def get_entities_by_source(self, source: str) -> List[Entity]:
        """按来源获取实体 (通过 ID 前缀)"""
        return [e for e in self.entities.values() if e.id.startswith(f"{source}_")]

    def get_entity_index(self) -> str:
        """生成已有实体索引（供 LLM 实体提取时参考，避免重复创建）"""
        if not self.entities:
            return ""
        lines = []
        for entity in self.entities.values():
            aliases_str = f" (别名: {', '.join(entity.aliases)})" if entity.aliases else ""
            lines.append(f"- {entity.canonical_id}: {entity.name}{aliases_str}")
        return "\n".join(lines)

    def get_direction_evidence_summary(self, entity_ids: List[str]) -> str:
        """
        生成指定方向的证据摘要（供 PlanAgent 评估时参考）

        Args:
            entity_ids: 方向关联的实体 canonical_id 列表

        Returns:
            格式化的证据摘要字符串
        """
        if not entity_ids:
            return "暂无证据"

        entities_found = []
        all_observations = []

        for eid in entity_ids:
            entity = self.entities.get(eid)
            if entity:
                entities_found.append(f"{entity.canonical_id} ({entity.entity_type.value})")
                for obs in entity.observations:
                    all_observations.append(obs)

        if not entities_found:
            return "暂无证据"

        # 按证据等级排序（A > B > C > D > E > None）
        grade_order = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}
        all_observations.sort(
            key=lambda o: grade_order.get(o.evidence_grade.value if o.evidence_grade else "E", 5)
        )

        top_obs = all_observations

        lines = []
        lines.append(f"**关键实体** ({len(entities_found)}个): {', '.join(entities_found)}")
        lines.append("")
        lines.append(f"**核心观察** (共{len(top_obs)}条):")
        for obs in top_obs:
            grade_str = f"[{obs.evidence_grade.value}级]" if obs.evidence_grade else "[未分级]"
            source_str = f" ({obs.source_tool})" if obs.source_tool else ""
            lines.append(f"- {grade_str} {obs.statement}{source_str}")

        return "\n".join(lines)

    # ==================== 边操作 ====================

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        predicate: Predicate,
        observation: Optional[Observation] = None,
        confidence: float = 1.0,
        conflict_group: Optional[str] = None,
    ) -> Optional[str]:
        """
        添加或更新边

        如果相同 (source_id, target_id, predicate) 的边已存在，
        则添加观察到现有边而不是创建新边。

        Args:
            source_id: 源实体 canonical_id
            target_id: 目标实体 canonical_id
            predicate: 谓词
            observation: 观察 (可选)
            confidence: 置信度
            conflict_group: 冲突组 ID

        Returns:
            边 ID 或 None (如果实体不存在)
        """
        # 验证实体存在
        if source_id not in self.entities or target_id not in self.entities:
            return None

        # 查找现有边
        edge_key = self._make_edge_key(source_id, target_id, predicate)
        existing_edge = self._find_edge_by_key(edge_key)

        if existing_edge:
            # 更新现有边
            if observation:
                existing_edge.add_observation(observation)
            existing_edge.confidence = max(existing_edge.confidence, confidence)
            if conflict_group:
                existing_edge.conflict_group = conflict_group
            return existing_edge.id

        # 创建新边
        edge = Edge(
            id=Edge.generate_id(),
            source_id=source_id,
            target_id=target_id,
            predicate=predicate,
            observations=[observation] if observation else [],
            confidence=confidence,
            conflict_group=conflict_group,
        )

        self.edges[edge.id] = edge
        self._edge_index[source_id].add(edge.id)
        self._edge_index[target_id].add(edge.id)

        return edge.id

    def _make_edge_key(self, source_id: str, target_id: str, predicate: Predicate) -> str:
        """生成边的唯一键"""
        return f"{source_id}|{target_id}|{predicate.value}"

    def _find_edge_by_key(self, edge_key: str) -> Optional[Edge]:
        """通过键查找边"""
        for edge in self.edges.values():
            if self._make_edge_key(edge.source_id, edge.target_id, edge.predicate) == edge_key:
                return edge
        return None

    def get_edge(self, edge_id: str) -> Optional[Edge]:
        """获取边"""
        return self.edges.get(edge_id)

    def get_edges_by_predicate(self, predicate: Predicate) -> List[Edge]:
        """按谓词获取边"""
        return [e for e in self.edges.values() if e.predicate == predicate]

    def get_entity_edges(
        self,
        canonical_id: str,
        direction: str = "both",
    ) -> List[Edge]:
        """
        获取实体相关的边

        Args:
            canonical_id: 实体规范 ID
            direction: "in" (入边), "out" (出边), "both" (所有)

        Returns:
            边列表
        """
        if canonical_id not in self._edge_index:
            return []

        edges = []
        for edge_id in self._edge_index[canonical_id]:
            edge = self.edges.get(edge_id)
            if not edge:
                continue

            if direction == "out" and edge.source_id == canonical_id:
                edges.append(edge)
            elif direction == "in" and edge.target_id == canonical_id:
                edges.append(edge)
            elif direction == "both":
                edges.append(edge)

        return edges

    def get_connected_entities(
        self,
        canonical_id: str,
        predicate: Predicate = None,
        direction: str = "both",
    ) -> List[Tuple[Entity, Edge]]:
        """
        获取连接的实体

        Args:
            canonical_id: 实体规范 ID
            predicate: 可选的谓词过滤
            direction: "in", "out", "both"

        Returns:
            (实体, 边) 元组列表
        """
        results = []
        edges = self.get_entity_edges(canonical_id, direction)

        for edge in edges:
            if predicate and edge.predicate != predicate:
                continue

            # 确定连接的实体
            connected_id = edge.target_id if edge.source_id == canonical_id else edge.source_id
            connected_entity = self.entities.get(connected_id)

            if connected_entity:
                results.append((connected_entity, edge))

        return results

    # ==================== 子图检索 (retrieve_from_graph) ====================

    def get_neighborhood(
        self,
        entity_id: str,
        max_hops: int = 2,
        max_entities: int = 50,
        predicate_filter: Optional[List[Predicate]] = None,
        entity_type_filter: Optional[List[EntityType]] = None,
    ) -> Dict[str, Any]:
        """
        BFS traversal from an anchor entity, returning local neighborhood.

        Args:
            entity_id: Starting entity canonical_id
            max_hops: Maximum BFS depth (default 2)
            max_entities: Maximum entities to return (safety cap)
            predicate_filter: Only traverse edges with these predicates
            entity_type_filter: Only include entities of these types

        Returns:
            {
                "anchor": entity_id,
                "entities": [Entity, ...],
                "edges": [Edge, ...],
                "hop_map": {canonical_id: hop_distance, ...}
            }
        """
        if entity_id not in self.entities:
            return {"anchor": entity_id, "entities": [], "edges": [], "hop_map": {}}

        visited: Set[str] = {entity_id}
        hop_map: Dict[str, int] = {entity_id: 0}
        collected_edges: Dict[str, Edge] = {}  # edge_id -> Edge (dedup)
        queue: List[Tuple[str, int]] = [(entity_id, 0)]

        while queue:
            current_id, current_hop = queue.pop(0)

            if current_hop >= max_hops:
                continue
            if len(visited) >= max_entities:
                break

            # Get all edges for current entity
            edges = self.get_entity_edges(current_id, direction="both")

            for edge in edges:
                # Apply predicate filter
                if predicate_filter and edge.predicate not in predicate_filter:
                    continue

                # Determine neighbor
                neighbor_id = edge.target_id if edge.source_id == current_id else edge.source_id
                neighbor = self.entities.get(neighbor_id)

                if not neighbor:
                    continue

                # Apply entity type filter
                if entity_type_filter and neighbor.entity_type not in entity_type_filter:
                    continue

                # Collect edge
                collected_edges[edge.id] = edge

                # BFS expansion
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    hop_map[neighbor_id] = current_hop + 1
                    queue.append((neighbor_id, current_hop + 1))

                    if len(visited) >= max_entities:
                        break

        # Collect entities
        entities = [self.entities[eid] for eid in visited if eid in self.entities]

        return {
            "anchor": entity_id,
            "entities": entities,
            "edges": list(collected_edges.values()),
            "hop_map": hop_map,
        }

    def retrieve_subgraph(
        self,
        anchor_ids: List[str],
        max_hops: int = 2,
        max_entities: int = 100,
        predicate_filter: Optional[List[Predicate]] = None,
        entity_type_filter: Optional[List[EntityType]] = None,
        include_observations: bool = True,
    ) -> Dict[str, Any]:
        """
        Extract a subgraph around multiple anchor nodes (merges neighborhoods).

        Args:
            anchor_ids: List of anchor entity canonical_ids
            max_hops: Maximum BFS hops per anchor (default 2)
            max_entities: Maximum total entities (default 100)
            predicate_filter: Only traverse edges with these predicates
            entity_type_filter: Only include entities of these types
            include_observations: If False, omit observation details (just counts)

        Returns:
            {
                "entities": [{canonical_id, name, type, observation_count, best_grade, aliases, observations?}, ...],
                "edges": [{source_id, target_id, predicate, confidence, observation_count, observations?}, ...],
                "stats": {total_entities, total_edges, total_observations}
            }
        """
        all_entity_ids: Set[str] = set()
        all_edges: Dict[str, Edge] = {}  # edge_id -> Edge
        all_hop_map: Dict[str, int] = {}

        for anchor_id in anchor_ids:
            if anchor_id not in self.entities:
                continue

            per_anchor_limit = max(10, max_entities // max(1, len(anchor_ids)))
            neighborhood = self.get_neighborhood(
                entity_id=anchor_id,
                max_hops=max_hops,
                max_entities=per_anchor_limit,
                predicate_filter=predicate_filter,
                entity_type_filter=entity_type_filter,
            )

            for e in neighborhood["entities"]:
                all_entity_ids.add(e.canonical_id)

            for edge in neighborhood["edges"]:
                all_edges[edge.id] = edge

            # Merge hop maps (keep shortest distance)
            for eid, dist in neighborhood["hop_map"].items():
                if eid not in all_hop_map or dist < all_hop_map[eid]:
                    all_hop_map[eid] = dist

            if len(all_entity_ids) >= max_entities:
                break

        # Build serializable result
        entities_out = []
        total_observations = 0
        for eid in all_entity_ids:
            entity = self.entities.get(eid)
            if not entity:
                continue

            obs_count = len(entity.observations)
            total_observations += obs_count
            best_grade = entity.get_best_grade()

            entry = {
                "canonical_id": entity.canonical_id,
                "name": entity.name,
                "type": entity.entity_type.value,
                "observation_count": obs_count,
                "best_grade": best_grade.value if best_grade else None,
                "aliases": entity.aliases,
                "hop_distance": all_hop_map.get(eid, -1),
            }

            if include_observations and entity.observations:
                entry["observations"] = [
                    {
                        "statement": obs.statement,
                        "evidence_grade": obs.evidence_grade.value if obs.evidence_grade else None,
                        "source_agent": obs.source_agent,
                        "source_tool": obs.source_tool,
                        "provenance": obs.provenance,
                    }
                    for obs in entity.observations
                ]

            entities_out.append(entry)

        edges_out = []
        for edge in all_edges.values():
            obs_count = len(edge.observations)
            total_observations += obs_count

            entry = {
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "predicate": edge.predicate.value,
                "confidence": edge.confidence,
                "observation_count": obs_count,
            }

            if include_observations and edge.observations:
                entry["observations"] = [
                    {
                        "statement": obs.statement,
                        "evidence_grade": obs.evidence_grade.value if obs.evidence_grade else None,
                        "provenance": obs.provenance,
                    }
                    for obs in edge.observations
                ]

            edges_out.append(entry)

        return {
            "entities": entities_out,
            "edges": edges_out,
            "stats": {
                "total_entities": len(entities_out),
                "total_edges": len(edges_out),
                "total_observations": total_observations,
            },
        }

    def search_entities(
        self,
        query: str,
        entity_types: Optional[List[EntityType]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Search entities by name/alias with substring matching and relevance scoring.

        Scoring: exact match=100, prefix=80, substring=60, alias match=40

        Args:
            query: Search query string
            entity_types: Optional filter by entity types
            limit: Maximum results to return

        Returns:
            List of {canonical_id, name, type, aliases, observation_count, best_grade, score}
        """
        if not query:
            return []

        query_upper = query.upper().strip()
        results = []

        for entity in self.entities.values():
            if entity_types and entity.entity_type not in entity_types:
                continue

            score = 0

            # Check canonical_id exact match
            if entity.canonical_id.upper() == query_upper:
                score = 100
            # Check name exact match
            elif entity.name.upper() == query_upper:
                score = 100
            # Check name prefix
            elif entity.name.upper().startswith(query_upper):
                score = 80
            # Check canonical_id prefix
            elif entity.canonical_id.upper().startswith(query_upper):
                score = 75
            # Check name substring
            elif query_upper in entity.name.upper():
                score = 60
            # Check canonical_id substring
            elif query_upper in entity.canonical_id.upper():
                score = 55
            # Check aliases
            else:
                for alias in entity.aliases:
                    if alias.upper() == query_upper:
                        score = 50
                        break
                    elif query_upper in alias.upper():
                        score = 40
                        break

            if score > 0:
                best_grade = entity.get_best_grade()
                results.append({
                    "canonical_id": entity.canonical_id,
                    "name": entity.name,
                    "type": entity.entity_type.value,
                    "aliases": entity.aliases,
                    "observation_count": len(entity.observations),
                    "best_grade": best_grade.value if best_grade else None,
                    "score": score,
                })

        # Sort by score descending, then by observation_count descending
        results.sort(key=lambda r: (-r["score"], -r["observation_count"]))

        return results[:limit]

    def get_entity_detail(self, canonical_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full detail for a single entity including all observations and connected edges.

        Args:
            canonical_id: Entity canonical_id

        Returns:
            {
                "entity": {canonical_id, name, type, aliases, observations: [...]},
                "edges": [{source_id, target_id, predicate, confidence, observations: [...]}, ...],
                "connected_entities": [{canonical_id, name, type}, ...]
            }
            or None if entity not found
        """
        entity = self.entities.get(canonical_id)
        if not entity:
            return None

        # Format entity with all observations
        entity_out = {
            "canonical_id": entity.canonical_id,
            "name": entity.name,
            "type": entity.entity_type.value,
            "aliases": entity.aliases,
            "observations": [
                {
                    "id": obs.id,
                    "statement": obs.statement,
                    "evidence_grade": obs.evidence_grade.value if obs.evidence_grade else None,
                    "civic_type": obs.civic_type.value if obs.civic_type else None,
                    "source_agent": obs.source_agent,
                    "source_tool": obs.source_tool,
                    "provenance": obs.provenance,
                    "source_url": obs.source_url,
                    "iteration": obs.iteration,
                }
                for obs in entity.observations
            ],
        }

        # Collect connected edges
        edges = self.get_entity_edges(canonical_id, direction="both")
        edges_out = []
        connected_out = []
        seen_connected = set()

        for edge in edges:
            edge_entry = {
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "predicate": edge.predicate.value,
                "confidence": edge.confidence,
                "observations": [
                    {
                        "statement": obs.statement,
                        "evidence_grade": obs.evidence_grade.value if obs.evidence_grade else None,
                        "provenance": obs.provenance,
                    }
                    for obs in edge.observations
                ],
            }
            edges_out.append(edge_entry)

            # Connected entity
            neighbor_id = edge.target_id if edge.source_id == canonical_id else edge.source_id
            if neighbor_id not in seen_connected:
                seen_connected.add(neighbor_id)
                neighbor = self.entities.get(neighbor_id)
                if neighbor:
                    connected_out.append({
                        "canonical_id": neighbor.canonical_id,
                        "name": neighbor.name,
                        "type": neighbor.entity_type.value,
                    })

        return {
            "entity": entity_out,
            "edges": edges_out,
            "connected_entities": connected_out,
        }

    def filter_observations(
        self,
        entity_id: str,
        min_grade: Optional[EvidenceGrade] = None,
        source_agent: Optional[str] = None,
        source_tool: Optional[str] = None,
        civic_type: Optional['CivicEvidenceType'] = None,
    ) -> List[Dict[str, Any]]:
        """
        Filter observations on an entity with precise criteria.
        Addresses the 'can't do p-value filtering with LLM eyeballing' problem.

        Args:
            entity_id: Entity canonical_id
            min_grade: Minimum evidence grade (A is best, E is worst)
            source_agent: Filter by source agent name
            source_tool: Filter by source tool name
            civic_type: Filter by CIViC evidence type

        Returns:
            Filtered observation list as dicts
        """
        entity = self.entities.get(entity_id)
        if not entity:
            return []

        grade_order = {
            EvidenceGrade.A: 0, EvidenceGrade.B: 1, EvidenceGrade.C: 2,
            EvidenceGrade.D: 3, EvidenceGrade.E: 4
        }
        min_grade_rank = grade_order.get(min_grade, 999) if min_grade else 999

        results = []
        for obs in entity.observations:
            # Grade filter
            if min_grade:
                obs_rank = grade_order.get(obs.evidence_grade, 5) if obs.evidence_grade else 5
                if obs_rank > min_grade_rank:
                    continue

            # Agent filter
            if source_agent and obs.source_agent != source_agent:
                continue

            # Tool filter
            if source_tool and obs.source_tool != source_tool:
                continue

            # CIViC type filter
            if civic_type and obs.civic_type != civic_type:
                continue

            results.append({
                "id": obs.id,
                "statement": obs.statement,
                "evidence_grade": obs.evidence_grade.value if obs.evidence_grade else None,
                "civic_type": obs.civic_type.value if obs.civic_type else None,
                "source_agent": obs.source_agent,
                "source_tool": obs.source_tool,
                "provenance": obs.provenance,
                "source_url": obs.source_url,
            })

        return results

    # ==================== 冲突处理 ====================

    def mark_conflict_group(self, edge_ids: List[str], group_id: str) -> int:
        """
        标记冲突组

        Args:
            edge_ids: 边 ID 列表
            group_id: 冲突组 ID

        Returns:
            成功标记的边数量
        """
        count = 0
        for edge_id in edge_ids:
            if edge_id in self.edges:
                self.edges[edge_id].conflict_group = group_id
                count += 1
        return count

    def get_conflicts(self) -> List[Dict[str, Any]]:
        """
        获取所有冲突

        Returns:
            冲突列表，每个包含:
            - conflict_group: 冲突组 ID
            - edges: 冲突的边列表
            - entities: 涉及的实体
        """
        # 按冲突组分组
        groups: Dict[str, List[Edge]] = {}
        for edge in self.edges.values():
            if edge.conflict_group:
                if edge.conflict_group not in groups:
                    groups[edge.conflict_group] = []
                groups[edge.conflict_group].append(edge)

        # 构建结果
        conflicts = []
        for group_id, edges in groups.items():
            entity_ids = set()
            for edge in edges:
                entity_ids.add(edge.source_id)
                entity_ids.add(edge.target_id)

            conflicts.append({
                "conflict_group": group_id,
                "edges": edges,
                "entities": [self.entities.get(eid) for eid in entity_ids if eid in self.entities],
            })

        return conflicts

    def detect_contradictions(self) -> List[Tuple[Edge, Edge]]:
        """
        检测 CONTRADICTS 关系的边对

        Returns:
            矛盾的边对列表
        """
        contradicting_edges = self.get_edges_by_predicate(Predicate.CONTRADICTS)
        pairs = []

        for edge in contradicting_edges:
            source_entity = self.entities.get(edge.source_id)
            target_entity = self.entities.get(edge.target_id)
            if source_entity and target_entity:
                pairs.append((edge, edge))  # 边本身就代表矛盾关系

        return pairs

    # ==================== 查询辅助 ====================

    def get_drug_sensitivity_map(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取药物敏感性映射

        Returns:
            {variant_canonical_id: [{drug_entity, edge, grade}, ...]}
        """
        result: Dict[str, List[Dict[str, Any]]] = {}

        for edge in self.edges.values():
            if edge.predicate not in [Predicate.SENSITIZES, Predicate.CAUSES_RESISTANCE]:
                continue

            source_entity = self.entities.get(edge.source_id)
            target_entity = self.entities.get(edge.target_id)

            if not source_entity or not target_entity:
                continue

            # 通常: VARIANT -> SENSITIZES -> DRUG
            if source_entity.entity_type == EntityType.VARIANT:
                variant_id = source_entity.canonical_id
                drug_entity = target_entity
            elif target_entity.entity_type == EntityType.VARIANT:
                variant_id = target_entity.canonical_id
                drug_entity = source_entity
            else:
                continue

            if variant_id not in result:
                result[variant_id] = []

            result[variant_id].append({
                "drug": drug_entity,
                "edge": edge,
                "predicate": edge.predicate.value,
                "grade": edge.get_best_grade(),
            })

        return result

    def get_treatment_evidence(
        self,
        drug_canonical_id: str,
        disease_canonical_id: str = None,
    ) -> List[Observation]:
        """
        获取治疗相关的所有观察

        Args:
            drug_canonical_id: 药物规范 ID
            disease_canonical_id: 可选的疾病规范 ID

        Returns:
            相关观察列表
        """
        observations = []

        # 药物实体上的观察
        drug = self.entities.get(drug_canonical_id)
        if drug:
            observations.extend(drug.observations)

        # 相关边上的观察
        for edge in self.get_entity_edges(drug_canonical_id, direction="both"):
            if edge.predicate in [Predicate.TREATS, Predicate.SENSITIZES, Predicate.CAUSES_RESISTANCE]:
                if disease_canonical_id is None or edge.target_id == disease_canonical_id or edge.source_id == disease_canonical_id:
                    observations.extend(edge.observations)

        return observations

    # ==================== 统计与摘要 ====================

    def summary(self) -> Dict[str, Any]:
        """返回图摘要信息（按 obs.id 去重，同一 observation 可能出现在多个 entity/edge 上）"""
        entity_by_type: Dict[str, int] = {}
        entity_by_source: Dict[str, int] = {}
        seen_obs_ids: set = set()
        best_grades: Dict[str, int] = {}
        evidence_types: Dict[str, int] = {}

        for entity in self.entities.values():
            # 按类型统计
            t = entity.entity_type.value
            entity_by_type[t] = entity_by_type.get(t, 0) + 1

            # 按来源统计
            source = entity.id.split("_")[0] if "_" in entity.id else "unknown"
            entity_by_source[source] = entity_by_source.get(source, 0) + 1

            # 观察数量 + 证据类型统计（按 obs.id 去重）
            for obs in entity.observations:
                obs_id = getattr(obs, 'id', None)
                if obs_id and obs_id not in seen_obs_ids:
                    seen_obs_ids.add(obs_id)
                    if obs.evidence_type:
                        et = obs.evidence_type.value
                        evidence_types[et] = evidence_types.get(et, 0) + 1

            # 最佳等级
            best = entity.get_best_grade()
            if best:
                best_grades[best.value] = best_grades.get(best.value, 0) + 1

        edge_by_predicate: Dict[str, int] = {}
        conflicts_count = 0

        for edge in self.edges.values():
            p = edge.predicate.value
            edge_by_predicate[p] = edge_by_predicate.get(p, 0) + 1
            for obs in edge.observations:
                obs_id = getattr(obs, 'id', None)
                if obs_id and obs_id not in seen_obs_ids:
                    seen_obs_ids.add(obs_id)
                    if obs.evidence_type:
                        et = obs.evidence_type.value
                        evidence_types[et] = evidence_types.get(et, 0) + 1
            if edge.conflict_group:
                conflicts_count += 1

        return {
            "total_entities": len(self.entities),
            "total_edges": len(self.edges),
            "total_observations": len(seen_obs_ids),
            "entities_by_type": entity_by_type,
            "entities_by_source": entity_by_source,
            "edges_by_predicate": edge_by_predicate,
            "best_grades": best_grades,
            "evidence_types": evidence_types,
            "conflicts_count": conflicts_count,
        }

    def get_all_provenances(self) -> List[Dict[str, str]]:
        """
        获取所有唯一来源 (用于参考文献)

        Returns:
            [{provenance, source_url}, ...]
        """
        seen = set()
        provenances = []

        for entity in self.entities.values():
            for obs in entity.observations:
                if obs.provenance and obs.provenance not in seen:
                    seen.add(obs.provenance)
                    provenances.append({
                        "provenance": obs.provenance,
                        "source_url": obs.source_url,
                    })

        for edge in self.edges.values():
            for obs in edge.observations:
                if obs.provenance and obs.provenance not in seen:
                    seen.add(obs.provenance)
                    provenances.append({
                        "provenance": obs.provenance,
                        "source_url": obs.source_url,
                    })

        return provenances

    # ==================== Agent 查询 ====================

    def get_observations_by_agent(self, agent_name: str) -> List[Observation]:
        """
        获取指定 Agent 收集的所有观察

        Args:
            agent_name: Agent 名称 (e.g., "Pathologist", "Geneticist")

        Returns:
            该 Agent 收集的所有观察列表
        """
        observations = []
        for entity in self.entities.values():
            for obs in entity.observations:
                if obs.source_agent == agent_name:
                    observations.append(obs)
        for edge in self.edges.values():
            for obs in edge.observations:
                if obs.source_agent == agent_name:
                    observations.append(obs)
        return observations

    def get_entities_with_agent_observations(self, agent_name: str) -> List[Entity]:
        """
        获取包含指定 Agent 观察的所有实体

        Args:
            agent_name: Agent 名称

        Returns:
            包含该 Agent 观察的实体列表
        """
        entities = []
        for entity in self.entities.values():
            has_agent_obs = any(obs.source_agent == agent_name for obs in entity.observations)
            if has_agent_obs:
                entities.append(entity)
        return entities

    def get_agent_edges(self, agent_name: str) -> List[Edge]:
        """
        获取包含指定 Agent 观察的所有边

        Args:
            agent_name: Agent 名称

        Returns:
            包含该 Agent 观察的边列表
        """
        edges = []
        for edge in self.edges.values():
            has_agent_obs = any(obs.source_agent == agent_name for obs in edge.observations)
            if has_agent_obs:
                edges.append(edge)
        return edges

    def get_agent_observation_count(self, agent_name: str) -> int:
        """
        统计指定 Agent 收集的观察数量

        Args:
            agent_name: Agent 名称

        Returns:
            观察数量
        """
        count = 0
        for entity in self.entities.values():
            count += sum(1 for obs in entity.observations if obs.source_agent == agent_name)
        for edge in self.edges.values():
            count += sum(1 for obs in edge.observations if obs.source_agent == agent_name)
        return count

    def summary_by_agent(self) -> Dict[str, Dict[str, Any]]:
        """
        按 Agent 统计观察（按 obs.id 去重，同一 observation 可能出现在多个 entity/edge 上）

        Returns:
            {agent_name: {observation_count, entity_count, grades}}
        """
        agent_stats: Dict[str, Dict[str, Any]] = {}

        for entity in self.entities.values():
            for obs in entity.observations:
                agent = obs.source_agent
                if agent not in agent_stats:
                    agent_stats[agent] = {
                        "seen_obs_ids": set(),
                        "entity_ids": set(),
                        "grades": {}
                    }
                obs_id = getattr(obs, 'id', None)
                if obs_id and obs_id not in agent_stats[agent]["seen_obs_ids"]:
                    agent_stats[agent]["seen_obs_ids"].add(obs_id)
                    if obs.evidence_grade:
                        g = obs.evidence_grade.value
                        agent_stats[agent]["grades"][g] = agent_stats[agent]["grades"].get(g, 0) + 1
                agent_stats[agent]["entity_ids"].add(entity.canonical_id)

        for edge in self.edges.values():
            for obs in edge.observations:
                agent = obs.source_agent
                if agent not in agent_stats:
                    agent_stats[agent] = {
                        "seen_obs_ids": set(),
                        "entity_ids": set(),
                        "grades": {}
                    }
                obs_id = getattr(obs, 'id', None)
                if obs_id and obs_id not in agent_stats[agent]["seen_obs_ids"]:
                    agent_stats[agent]["seen_obs_ids"].add(obs_id)
                    if obs.evidence_grade:
                        g = obs.evidence_grade.value
                        agent_stats[agent]["grades"][g] = agent_stats[agent]["grades"].get(g, 0) + 1

        # Convert sets to counts
        result = {}
        for agent, stats in agent_stats.items():
            result[agent] = {
                "observation_count": len(stats["seen_obs_ids"]),
                "entity_count": len(stats["entity_ids"]),
                "grades": stats["grades"]
            }

        return result

    # ==================== 序列化 ====================

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典 (用于存入 State)"""
        return {
            "entities": {cid: entity.to_dict() for cid, entity in self.entities.items()},
            "edges": {eid: edge.to_dict() for eid, edge in self.edges.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceGraph":
        """从字典反序列化"""
        graph = cls()

        # 恢复实体
        for cid, entity_data in data.get("entities", {}).items():
            entity = Entity.from_dict(entity_data)
            graph.entities[cid] = entity
            graph._edge_index[cid] = set()
            graph._name_index[entity.name] = cid
            for alias in entity.aliases:
                if alias not in graph._name_index:
                    graph._name_index[alias] = cid

        # 恢复边
        for eid, edge_data in data.get("edges", {}).items():
            edge = Edge.from_dict(edge_data)
            graph.edges[eid] = edge

            # 重建边索引
            if edge.source_id in graph._edge_index:
                graph._edge_index[edge.source_id].add(eid)
            if edge.target_id in graph._edge_index:
                graph._edge_index[edge.target_id].add(eid)

        return graph

    def __len__(self) -> int:
        """返回实体数量"""
        return len(self.entities)

    # ==================== Mermaid 图生成 ====================

    def to_mermaid(self) -> str:
        """
        生成 Mermaid 格式的图表

        Returns:
            Mermaid 格式字符串
        """
        lines = ["```mermaid", "graph LR"]

        # 实体类型对应的样式
        type_styles = {
            "gene": ":::gene",
            "variant": ":::variant",
            "drug": ":::drug",
            "disease": ":::disease",
            "pathway": ":::pathway",
            "biomarker": ":::biomarker",
            "paper": ":::paper",
            "trial": ":::trial",
            "guideline": ":::guideline",
            "regimen": ":::regimen",
            "finding": ":::finding",
        }

        # 生成节点 ID 映射 (Mermaid 不支持特殊字符)
        node_map = {}
        for i, (cid, entity) in enumerate(self.entities.items()):
            node_id = f"N{i}"
            node_map[cid] = node_id

            # 节点标签: 类型缩写 + 名称
            etype = entity.entity_type.value if entity.entity_type else "?"
            etype_abbr = etype[:3].upper()
            name = entity.name[:20] if len(entity.name) > 20 else entity.name
            # 转义特殊字符
            name = name.replace('"', "'").replace(":", "_")

            # 获取最佳等级
            best_grade = entity.get_best_grade()
            grade_str = f" [{best_grade.value}]" if best_grade else ""

            style = type_styles.get(etype, "")
            lines.append(f'    {node_id}["{etype_abbr}: {name}{grade_str}"]{style}')

        lines.append("")

        # 生成边
        for edge in self.edges.values():
            source_node = node_map.get(edge.source_id)
            target_node = node_map.get(edge.target_id)

            if source_node and target_node:
                predicate = edge.predicate.value if edge.predicate else "?"
                # 缩短谓词显示
                pred_short = predicate[:12] if len(predicate) > 12 else predicate
                lines.append(f"    {source_node} -->|{pred_short}| {target_node}")

        lines.append("")

        # 添加样式定义
        lines.append("    %% 样式定义")
        lines.append("    classDef gene fill:#e1f5fe,stroke:#0288d1")
        lines.append("    classDef variant fill:#fff3e0,stroke:#f57c00")
        lines.append("    classDef drug fill:#e8f5e9,stroke:#388e3c")
        lines.append("    classDef disease fill:#fce4ec,stroke:#c2185b")
        lines.append("    classDef pathway fill:#f3e5f5,stroke:#7b1fa2")
        lines.append("    classDef biomarker fill:#e0f2f1,stroke:#00796b")
        lines.append("    classDef paper fill:#eceff1,stroke:#546e7a")
        lines.append("    classDef trial fill:#fff8e1,stroke:#ffa000")
        lines.append("    classDef guideline fill:#e8eaf6,stroke:#3f51b5")
        lines.append("    classDef regimen fill:#fbe9e7,stroke:#e64a19")
        lines.append("    classDef finding fill:#f5f5f5,stroke:#9e9e9e")

        lines.append("```")

        return "\n".join(lines)

    def to_persistence_dict(self, phase: str = "", iteration: int = 0, checkpoint_type: str = "checkpoint") -> Dict[str, Any]:
        """
        序列化图 + metadata 信封，用于 JSON 持久化

        Args:
            phase: 阶段标识 ("phase1", "phase2", "final")
            iteration: 迭代次数
            checkpoint_type: 检查点类型 ("checkpoint", "phase_complete", "final")

        Returns:
            包含元数据和图数据的字典
        """
        summary = self.summary()
        return {
            "metadata": {
                "version": "1.0",
                "timestamp": datetime.now().isoformat(),
                "phase": phase,
                "iteration": iteration,
                "checkpoint_type": checkpoint_type,
                "stats": {
                    "entity_count": summary.get("total_entities", 0),
                    "edge_count": summary.get("total_edges", 0),
                    "observation_count": summary.get("total_observations", 0),
                    "entities_by_type": summary.get("entities_by_type", {}),
                    "edges_by_predicate": summary.get("edges_by_predicate", {}),
                }
            },
            "graph": self.to_dict(),
        }

    def to_cytoscape_json(self) -> Dict[str, Any]:
        """
        转换为 Cytoscape.js JSON 格式

        Returns:
            {
                "elements": {
                    "nodes": [{"data": {id, label, entity_type, best_grade, obs_count, aliases, source_agents, grade_distribution, observations}}, ...],
                    "edges": [{"data": {id, source, target, predicate, confidence, best_grade, obs_count, observations}}, ...]
                },
                "stats": {entity_count, edge_count, observation_count, entities_by_type}
            }
        """
        nodes = []
        edges = []

        # 证据等级排序辅助
        grade_order = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}

        # 处理实体节点
        for entity in self.entities.values():
            # 获取最佳等级
            best_grade = entity.get_best_grade()
            best_grade_str = best_grade.value if best_grade else None

            # 统计观察数量
            obs_count = len(entity.observations)

            # 收集唯一的源 Agent
            source_agents = list(set(obs.source_agent for obs in entity.observations if obs.source_agent))

            # 构建等级分布
            grade_distribution = {}
            for obs in entity.observations:
                if obs.evidence_grade:
                    grade_str = obs.evidence_grade.value
                    grade_distribution[grade_str] = grade_distribution.get(grade_str, 0) + 1

            # 构建观察详情列表
            observations = []
            for obs in entity.observations:
                obs_detail = {
                    "id": obs.id,
                    "statement": obs.statement,
                    "grade": obs.evidence_grade.value if obs.evidence_grade else None,
                    "civic_type": obs.civic_type.value if obs.civic_type else None,
                    "evidence_type": obs.evidence_type.value if obs.evidence_type else None,
                    "source_agent": obs.source_agent,
                    "source_tool": obs.source_tool,
                    "provenance": obs.provenance,
                    "source_url": obs.source_url,
                }
                observations.append(obs_detail)

            # 按等级排序观察（A > B > C > D > E > None）
            observations.sort(key=lambda o: grade_order.get(o["grade"], 5) if o["grade"] else 5)

            # 构建节点数据
            node_data = {
                "id": entity.canonical_id,
                "label": entity.name,
                "entity_type": entity.entity_type.value,
                "best_grade": best_grade_str,
                "obs_count": obs_count,
                "aliases": entity.aliases,
                "source_agents": source_agents,
                "grade_distribution": grade_distribution,
                "observations": observations
            }

            nodes.append({"data": node_data})

        # 处理边
        for edge in self.edges.values():
            # 获取最佳等级
            best_grade = edge.get_best_grade()
            best_grade_str = best_grade.value if best_grade else None

            # 统计观察数量
            obs_count = len(edge.observations)

            # 构建观察详情列表
            observations = []
            for obs in edge.observations:
                obs_detail = {
                    "id": obs.id,
                    "statement": obs.statement,
                    "grade": obs.evidence_grade.value if obs.evidence_grade else None,
                    "civic_type": obs.civic_type.value if obs.civic_type else None,
                    "evidence_type": obs.evidence_type.value if obs.evidence_type else None,
                    "source_agent": obs.source_agent,
                    "source_tool": obs.source_tool,
                    "provenance": obs.provenance,
                    "source_url": obs.source_url,
                }
                observations.append(obs_detail)

            # 按等级排序
            observations.sort(key=lambda o: grade_order.get(o["grade"], 5) if o["grade"] else 5)

            # 构建边数据
            edge_data = {
                "id": edge.id,
                "source": edge.source_id,
                "target": edge.target_id,
                "predicate": edge.predicate.value,
                "confidence": edge.confidence,
                "best_grade": best_grade_str,
                "obs_count": obs_count,
                "conflict_group": edge.conflict_group,
                "observations": observations
            }

            edges.append({"data": edge_data})

        # 构建统计信息
        summary = self.summary()

        return {
            "elements": {
                "nodes": nodes,
                "edges": edges
            },
            "stats": {
                "entity_count": summary.get("total_entities", 0),
                "edge_count": summary.get("total_edges", 0),
                "observation_count": summary.get("total_observations", 0),
                "entities_by_type": summary.get("entities_by_type", {}),
            }
        }


# ==================== 便捷函数 ====================

def create_evidence_graph() -> EvidenceGraph:
    """创建新的证据图"""
    return EvidenceGraph()


def load_evidence_graph(data: Dict[str, Any]) -> EvidenceGraph:
    """从字典加载证据图（支持 {"graph": {...}} 嵌套格式）"""
    if not data:
        return EvidenceGraph()
    # 兼容 {"metadata":..., "graph": {"entities":..., "edges":...}} 格式
    if "graph" in data and "entities" not in data:
        data = data["graph"]
    return EvidenceGraph.from_dict(data)


# ==================== Provenance 格式化工具 ====================


def construct_provenance_url(provenance: str) -> str:
    """
    根据 provenance 字符串构造 URL

    Args:
        provenance: 出处标识，如 "PMID:12345678", "NCT04123456" 等

    Returns:
        对应的 URL，无法构造时返回空字符串
    """
    if not provenance:
        return ""
    prov = provenance.strip()

    # PMID:12345678 or PMID: 12345678
    if prov.upper().startswith("PMID"):
        pmid = prov.split(":")[-1].strip()
        if pmid.isdigit():
            return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

    # NCT04123456
    if prov.upper().startswith("NCT"):
        nct_id = prov.split(",")[0].strip()
        return f"https://clinicaltrials.gov/study/{nct_id}"

    # GDC: TCGA-LUAD
    if prov.lower().startswith("gdc"):
        project_id = prov.split(":")[-1].strip()
        return f"https://portal.gdc.cancer.gov/projects/{project_id}"

    # cBioPortal: COADREAD (向后兼容旧数据)
    if prov.lower().startswith("cbioportal"):
        study_id = prov.split(":")[-1].strip()
        return f"https://www.cbioportal.org/study/summary?id={study_id.lower()}"

    # CIViC
    if prov.lower().startswith("civic"):
        return "https://civicdb.org/"

    # FDA: drug_name → DailyMed 搜索
    if prov.upper().startswith("FDA"):
        drug = prov.split(":")[-1].strip()
        if drug:
            return f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?query={drug}"

    # RxNorm: drug_name → RxNav 搜索
    if prov.upper().startswith("RXNORM"):
        drug = prov.split(":")[-1].strip()
        if drug:
            return f"https://mor.nlm.nih.gov/RxNav/search?searchBy=STRING&searchTerm={drug}"

    # ClinVar: variation_id
    if prov.lower().startswith("clinvar"):
        var_id = prov.split(":")[-1].strip()
        if var_id.isdigit():
            return f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{var_id}/"

    # NCCN（本地 RAG，无真实可导航 URL）
    if prov.upper().startswith("NCCN"):
        return ""

    return ""


def format_provenance_citation(provenance: str, url: str = "") -> str:
    """
    将 provenance 格式化为 markdown 内联引用

    Args:
        provenance: 出处标识
        url: URL（可选，若为空则自动构造）

    Returns:
        markdown 格式引用，如 [PMID: 12345678](url)
    """
    if not provenance:
        return ""
    prov = provenance.strip()
    if not url:
        url = construct_provenance_url(prov)

    # PMID 格式化为 [PMID: xxx](url)
    if prov.upper().startswith("PMID"):
        pmid = prov.split(":")[-1].strip()
        if url:
            return f"[PMID: {pmid}]({url})"
        return f"PMID: {pmid}"

    # NCT 格式化为 [NCTxxx](url)
    if prov.upper().startswith("NCT"):
        nct_id = prov.split(",")[0].strip()
        if url:
            return f"[{nct_id}]({url})"
        return nct_id

    # 其他：[provenance](url) 或 provenance
    if url:
        return f"[{prov}]({url})"
    return prov


# ==================== 测试 ====================

if __name__ == "__main__":
    print("=== Evidence Graph (DeepEvidence Style) 测试 ===\n")

    graph = create_evidence_graph()

    # 创建实体
    egfr_gene = graph.get_or_create_entity(
        canonical_id="GENE:EGFR",
        entity_type=EntityType.GENE,
        name="EGFR",
        source="civic",
        aliases=["ERBB1", "HER1"],
    )
    print(f"创建基因实体: {egfr_gene.canonical_id} (ID: {egfr_gene.id})")

    # 创建变异实体
    l858r_variant = graph.get_or_create_entity(
        canonical_id="EGFR_L858R",
        entity_type=EntityType.VARIANT,
        name="L858R",
        source="civic",
    )
    print(f"创建变异实体: {l858r_variant.canonical_id} (ID: {l858r_variant.id})")

    # 创建药物实体
    osimertinib = graph.get_or_create_entity(
        canonical_id="DRUG:OSIMERTINIB",
        entity_type=EntityType.DRUG,
        name="Osimertinib",
        source="fda",
        aliases=["AZD9291", "TAGRISSO"],
    )
    print(f"创建药物实体: {osimertinib.canonical_id} (ID: {osimertinib.id})")

    # 创建疾病实体
    nsclc = graph.get_or_create_entity(
        canonical_id="DISEASE:NSCLC",
        entity_type=EntityType.DISEASE,
        name="NSCLC",
        source="civic",
        aliases=["NON-SMALL CELL LUNG CANCER"],
    )
    print(f"创建疾病实体: {nsclc.canonical_id} (ID: {nsclc.id})")

    # 添加观察
    obs1 = Observation(
        id=Observation.generate_id("civic"),
        statement="EGFR L858R shows 72% ORR to osimertinib (human, Phase III, n=347) [PMID:28854312]",
        source_agent="Geneticist",
        source_tool="search_civic",
        provenance="PMID:28854312",
        source_url="https://pubmed.ncbi.nlm.nih.gov/28854312/",
        evidence_grade=EvidenceGrade.A,
        civic_type=CivicEvidenceType.PREDICTIVE,
        iteration=1,
    )
    graph.add_observation_to_entity(l858r_variant.canonical_id, obs1)
    print(f"\n添加观察到变异实体: {obs1.statement[:50]}...")

    # 添加边
    edge_id = graph.add_edge(
        source_id=l858r_variant.canonical_id,
        target_id=osimertinib.canonical_id,
        predicate=Predicate.SENSITIZES,
        observation=obs1,
        confidence=0.95,
    )
    print(f"创建边: {l858r_variant.canonical_id} --SENSITIZES--> {osimertinib.canonical_id}")

    edge_id2 = graph.add_edge(
        source_id=osimertinib.canonical_id,
        target_id=nsclc.canonical_id,
        predicate=Predicate.TREATS,
        confidence=0.99,
    )
    print(f"创建边: {osimertinib.canonical_id} --TREATS--> {nsclc.canonical_id}")

    # 测试实体合并 (同一实体不创建新的)
    same_egfr = graph.get_or_create_entity(
        canonical_id="GENE:EGFR",
        entity_type=EntityType.GENE,
        name="egfr",  # 小写，应该被规范化
        source="pubmed",
    )
    print(f"\n尝试创建相同实体: 返回 {same_egfr.id} (应与原始相同: {egfr_gene.id})")
    assert same_egfr.id == egfr_gene.id, "实体合并失败!"

    # 通过名称查找
    found = graph.find_entity_by_name("AZD9291")  # 通过别名查找
    print(f"通过别名查找 'AZD9291': {found.canonical_id if found else 'Not found'}")

    # 获取连接的实体
    connected = graph.get_connected_entities(l858r_variant.canonical_id, predicate=Predicate.SENSITIZES)
    print(f"\n{l858r_variant.canonical_id} 通过 SENSITIZES 连接的实体:")
    for entity, edge in connected:
        print(f"  - {entity.canonical_id} (confidence: {edge.confidence})")

    # 获取药物敏感性映射
    sensitivity_map = graph.get_drug_sensitivity_map()
    print(f"\n药物敏感性映射:")
    for variant_id, drugs in sensitivity_map.items():
        print(f"  {variant_id}:")
        for item in drugs:
            print(f"    - {item['drug'].canonical_id} ({item['predicate']}, grade: {item['grade']})")

    # 摘要
    print(f"\n图摘要:")
    summary = graph.summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")

    # 序列化测试
    print("\n序列化测试:")
    data = graph.to_dict()
    loaded = load_evidence_graph(data)
    print(f"  原始实体数: {len(graph)}, 加载后: {len(loaded)}")
    print(f"  原始边数: {len(graph.edges)}, 加载后: {len(loaded.edges)}")

    # 验证加载后的实体
    loaded_egfr = loaded.get_entity("GENE:EGFR")
    print(f"  加载后 EGFR 别名: {loaded_egfr.aliases if loaded_egfr else 'Not found'}")

    print("\n=== 测试完成 ===")
