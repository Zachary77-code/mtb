"""
Entity Extractors - 实体提取器 (DeepEvidence Style)

使用 LLM 将工具返回的 findings 分解为：
1. Entities - 原子生物医学概念 (基因、变异、药物、疾病等)
2. Edges - 实体间的语义关系
3. Observations - 附加到实体和边上的事实陈述

核心逻辑：
- 每个工具有专门的提取器
- 提取器使用 LLM 识别实体和关系
- 返回 ExtractionResult 包含所有提取内容
"""
import json
import os
import re
import requests
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple

from src.models.evidence_graph import (
    EvidenceGraph,
    Entity,
    Edge,
    Observation,
    EntityType,
    Predicate,
    EvidenceGrade,
    CivicEvidenceType,
)
from src.utils.logger import mtb_logger as logger


# ============================================================
# 提取结果数据类
# ============================================================

@dataclass
class ExtractedEntity:
    """提取的实体"""
    canonical_id: str                    # 规范 ID (GENE:EGFR, DRUG:OSIMERTINIB, etc.)
    entity_type: EntityType              # 实体类型
    name: str                            # 实体名称
    aliases: List[str] = field(default_factory=list)  # 别名
    observation: Optional[Observation] = None  # 该实体的观察


@dataclass
class ExtractedEdge:
    """提取的边"""
    source_id: str                       # 源实体 canonical_id
    target_id: str                       # 目标实体 canonical_id
    predicate: Predicate                 # 谓词
    observation: Optional[Observation] = None  # 该关系的观察
    confidence: float = 0.9              # 置信度


@dataclass
class ExtractedConflict:
    """检测到的冲突"""
    edge_ids: List[str]                  # 冲突的边 ID (会在后处理中填充)
    group_id: str                        # 冲突组 ID
    description: str                     # 冲突描述


@dataclass
class ExtractionResult:
    """提取结果"""
    entities: List[ExtractedEntity]      # 提取的实体
    edges: List[ExtractedEdge]           # 提取的边
    conflicts: List[ExtractedConflict] = field(default_factory=list)  # 检测到的冲突
    source_tool: Optional[str] = None    # 来源工具
    raw_finding: Optional[Dict[str, Any]] = None  # 原始 finding


# ============================================================
# LLM 实体提取器
# ============================================================

class EntityExtractor:
    """
    LLM 实体提取器基类

    使用 LLM 将 finding 分解为 entities + edges + observations
    """

    SYSTEM_PROMPT = """你是一个生物医学知识图谱构建专家。
你的任务是将给定的医学发现分解为结构化的实体(Entity)、关系(Edge)和观察(Observation)。

## 实体类型 (EntityType)
- gene: 基因 (如 EGFR, KRAS, TP53)
- variant: 基因变异 (如 L858R, T790M, G12C)
- drug: 药物/化合物 (如 Osimertinib, Pembrolizumab)
- disease: 疾病/癌种 (如 NSCLC, CRC, melanoma)
- pathway: 信号通路 (如 EGFR_signaling, PI3K_AKT)
- biomarker: 生物标志物 (如 PD-L1, TMB, MSI)
- paper: 文献 (PMID:xxx)
- trial: 临床试验 (NCT:xxx)
- guideline: 指南 (NCCN:xxx)
- regimen: 治疗方案 (如 platinum_doublet)
- finding: 临床发现

## 关系谓词 (Predicate)
分子机制: activates, inhibits, binds, phosphorylates, regulates, amplifies, mutates_to
药物关系: treats, sensitizes, causes_resistance, interacts_with, contraindicated_for
证据关系: supports, contradicts, cites, derived_from
成员关系: member_of, expressed_in, associated_with, biomarker_for
指南关系: recommends, evaluates, includes_arm

## 实体 ID 命名规范 (全部大写)
- 基因: GENE:EGFR
- 变异: EGFR_L858R (格式: 基因_变异)
- 药物: DRUG:OSIMERTINIB
- 疾病: DISEASE:NSCLC
- 通路: PATHWAY:EGFR_SIGNALING
- 标志物: BIOMARKER:PD-L1
- 文献: PMID:12345678
- 试验: NCT:NCT04487080
- 指南: NCCN:NSCLC
- 方案: REGIMEN:PLATINUM_DOUBLET

## 输出格式 (JSON)
{
  "entities": [
    {
      "canonical_id": "GENE:EGFR",
      "entity_type": "gene",
      "name": "EGFR",
      "aliases": ["ERBB1", "HER1"]
    },
    {
      "canonical_id": "EGFR_L858R",
      "entity_type": "variant",
      "name": "L858R",
      "aliases": []
    },
    {
      "canonical_id": "DRUG:OSIMERTINIB",
      "entity_type": "drug",
      "name": "OSIMERTINIB",
      "aliases": ["AZD9291", "TAGRISSO"]
    }
  ],
  "edges": [
    {
      "source_id": "EGFR_L858R",
      "target_id": "DRUG:OSIMERTINIB",
      "predicate": "sensitizes",
      "confidence": 0.95
    },
    {
      "source_id": "DRUG:OSIMERTINIB",
      "target_id": "DISEASE:NSCLC",
      "predicate": "treats",
      "confidence": 0.99
    }
  ],
  "observation": "EGFR L858R mutation shows 72% ORR to osimertinib in NSCLC patients (human, Phase III, n=347) [PMID:28854312]",
  "conflicts": []
}

## 重要规则
1. 实体名称全部大写 (EGFR, OSIMERTINIB, NSCLC)
2. 变异 ID 格式: 基因_变异 (EGFR_L858R, KRAS_G12C)
3. observation 不超过 50 词，包含上下文信息 (物种, 试验类型, 样本量) 和来源 [PMID:xxx]
4. confidence 范围 0.6-1.0: 规则/FDA批准=0.95+, 临床证据=0.85-0.95, 推断=0.7-0.85
5. 如果发现冲突证据，在 conflicts 中标注
6. 只提取明确的实体和关系，不要猜测
"""

    def __init__(self, llm_caller=None):
        """
        初始化提取器

        Args:
            llm_caller: 可选的 LLM 调用函数
        """
        self._llm_caller = llm_caller

    def extract(
        self,
        finding: Dict[str, Any],
        source_agent: str,
        source_tool: str,
        iteration: int,
        existing_entities: str = ""
    ) -> ExtractionResult:
        """
        从 finding 提取实体、边和观察

        Args:
            finding: 工具返回的发现数据
            source_agent: 来源 Agent
            source_tool: 来源工具
            iteration: 迭代轮次
            existing_entities: 已有实体索引（供 LLM 参考避免重复创建）

        Returns:
            ExtractionResult
        """
        # 构建用户提示
        user_prompt = self._build_prompt(finding, source_tool, existing_entities)

        # 调用 LLM
        try:
            response = self._call_llm(user_prompt)
            result = self._parse_response(
                response=response,
                finding=finding,
                source_agent=source_agent,
                source_tool=source_tool,
                iteration=iteration
            )
            return result
        except Exception as e:
            logger.warning(f"[EntityExtractor] Extraction failed: {e}")
            # 返回空结果
            return ExtractionResult(
                entities=[],
                edges=[],
                conflicts=[],
                source_tool=source_tool,
                raw_finding=finding
            )

    def _build_prompt(self, finding: Dict[str, Any], source_tool: str, existing_entities: str = "") -> str:
        """构建用户提示"""
        finding_str = json.dumps(finding, indent=2, ensure_ascii=False, default=str)

        existing_section = ""
        if existing_entities:
            existing_section = f"""
## 已有实体（必须复用，不要创建重复实体）
以下是当前知识图谱中已有的实体。如果你要提取的实体与其中某个相同或等价（包括单复数、缩写、别名），
**必须使用已有的 canonical_id**，不要新建。

{existing_entities}
"""

        return f"""## 来源工具
{source_tool}
{existing_section}
## 发现数据
```json
{finding_str}
```

请将上述发现分解为实体(entities)、关系(edges)和观察(observation)。
输出 JSON 格式，确保所有实体名称大写。
"""

    def _call_llm(self, user_prompt: str) -> str:
        """调用 LLM"""
        if self._llm_caller:
            return self._llm_caller(self.SYSTEM_PROMPT, user_prompt)

        return self._default_llm_call(user_prompt)

    def _default_llm_call(self, user_prompt: str) -> str:
        """默认的 OpenRouter LLM 调用"""
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            logger.warning("[EntityExtractor] No OPENROUTER_API_KEY found")
            return "{}"

        # 使用 SUBGRAPH_MODEL
        try:
            from config.settings import SUBGRAPH_MODEL
            model_id = SUBGRAPH_MODEL or "google/gemini-2.0-flash-001"
        except ImportError:
            model_id = "google/gemini-2.0-flash-001"

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model_id,
                    "messages": [
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.2
                },
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "{}")

        except Exception as e:
            logger.error(f"[EntityExtractor] LLM call failed: {e}")
            return "{}"

    def _parse_response(
        self,
        response: str,
        finding: Dict[str, Any],
        source_agent: str,
        source_tool: str,
        iteration: int
    ) -> ExtractionResult:
        """解析 LLM 响应"""
        entities = []
        edges = []
        conflicts = []

        # 提取 JSON
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            logger.debug(f"[EntityExtractor] No JSON found in response")
            return ExtractionResult(
                entities=[], edges=[], conflicts=[],
                source_tool=source_tool, raw_finding=finding
            )

        try:
            data = json.loads(json_match.group(0))
        except json.JSONDecodeError as e:
            logger.debug(f"[EntityExtractor] JSON parse error: {e}")
            return ExtractionResult(
                entities=[], edges=[], conflicts=[],
                source_tool=source_tool, raw_finding=finding
            )

        # 提取来源信息
        provenance = self._extract_provenance(finding)
        source_url = self._extract_source_url(finding)

        # 获取全局观察文本
        observation_text = data.get("observation", "")

        # 一个 finding 只生成一个共享的 observation（修复重复创建 bug）
        shared_obs = None
        if observation_text:
            shared_obs = Observation(
                id=Observation.generate_id(source_tool),
                statement=observation_text,
                source_agent=source_agent,
                source_tool=source_tool,
                provenance=provenance,
                source_url=source_url,
                evidence_grade=self._extract_grade(finding),
                civic_type=self._extract_civic_type(finding),
                iteration=iteration,
            )

        # 解析实体 - 所有实体共享同一个 observation
        for entity_data in data.get("entities", []):
            try:
                canonical_id = entity_data.get("canonical_id", "").upper()
                entity_type_str = entity_data.get("entity_type", "finding")
                name = entity_data.get("name", "").upper()
                aliases = [a.upper() for a in entity_data.get("aliases", [])]

                if not canonical_id or not name:
                    continue

                # 映射实体类型
                try:
                    entity_type = EntityType(entity_type_str.lower())
                except ValueError:
                    entity_type = EntityType.FINDING

                entities.append(ExtractedEntity(
                    canonical_id=canonical_id,
                    entity_type=entity_type,
                    name=name,
                    aliases=aliases,
                    observation=shared_obs,  # 共享引用
                ))

            except Exception as e:
                logger.debug(f"[EntityExtractor] Entity parse error: {e}")
                continue

        # 解析边 - 所有边也共享同一个 observation
        for edge_data in data.get("edges", []):
            try:
                source_id = edge_data.get("source_id", "").upper()
                target_id = edge_data.get("target_id", "").upper()
                predicate_str = edge_data.get("predicate", "associated_with")
                confidence = float(edge_data.get("confidence", 0.8))

                if not source_id or not target_id:
                    continue

                # 映射谓词
                try:
                    predicate = Predicate(predicate_str.lower())
                except ValueError:
                    predicate = Predicate.ASSOCIATED_WITH

                edges.append(ExtractedEdge(
                    source_id=source_id,
                    target_id=target_id,
                    predicate=predicate,
                    observation=shared_obs,  # 共享引用
                    confidence=confidence,
                ))

            except Exception as e:
                logger.debug(f"[EntityExtractor] Edge parse error: {e}")
                continue

        # 解析冲突
        for conflict_data in data.get("conflicts", []):
            try:
                conflicts.append(ExtractedConflict(
                    edge_ids=[],  # 会在后处理中填充
                    group_id=conflict_data.get("group_id", f"conflict_{len(conflicts)}"),
                    description=conflict_data.get("description", "")
                ))
            except Exception:
                continue

        if entities:
            logger.debug(f"[EntityExtractor] Extracted {len(entities)} entities, {len(edges)} edges from {source_tool}")

        return ExtractionResult(
            entities=entities,
            edges=edges,
            conflicts=conflicts,
            source_tool=source_tool,
            raw_finding=finding
        )

    def _extract_provenance(self, finding: Dict[str, Any]) -> Optional[str]:
        """提取来源追踪标识"""
        if finding.get("pmid"):
            return f"PMID:{finding['pmid']}"
        elif finding.get("nct_id"):
            return f"NCT:{finding['nct_id']}"
        elif finding.get("civic_id"):
            return f"CIViC:{finding['civic_id']}"
        elif finding.get("clinvar_id"):
            return f"ClinVar:{finding['clinvar_id']}"
        elif finding.get("provenance"):
            return finding["provenance"]
        # Fallback: 从 content 文本中提取 PMID/NCT
        content = finding.get("content", "")
        pmid_match = re.search(r'PMID[:\s]*(\d{7,9})', content)
        if pmid_match:
            return f"PMID:{pmid_match.group(1)}"
        nct_match = re.search(r'(NCT\d{8,11})', content)
        if nct_match:
            return f"NCT:{nct_match.group(1)}"
        return None

    def _extract_source_url(self, finding: Dict[str, Any]) -> Optional[str]:
        """提取来源 URL"""
        url = (
            finding.get("civic_url") or
            finding.get("url") or
            finding.get("cbioportal_url") or
            finding.get("source_url")
        )
        if not url and finding.get("pmid"):
            url = f"https://pubmed.ncbi.nlm.nih.gov/{finding['pmid']}/"
        # NCT ID URL 自动构建
        if not url and finding.get("nct_id"):
            nct = finding["nct_id"]
            if not nct.startswith("NCT"):
                nct = f"NCT{nct}"
            url = f"https://clinicaltrials.gov/study/{nct}"
        # Fallback: 从 content 文本中提取 PMID/NCT 构建 URL
        if not url:
            content = finding.get("content", "")
            pmid_match = re.search(r'PMID[:\s]*(\d{7,9})', content)
            if pmid_match:
                url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid_match.group(1)}/"
            else:
                nct_match = re.search(r'(NCT\d{8,11})', content)
                if nct_match:
                    url = f"https://clinicaltrials.gov/study/{nct_match.group(1)}"
        return url

    def _extract_grade(self, finding: Dict[str, Any]) -> Optional[EvidenceGrade]:
        """提取证据等级"""
        grade_str = finding.get("grade") or finding.get("evidence_level")
        if grade_str:
            try:
                return EvidenceGrade(grade_str.upper())
            except ValueError:
                pass
        return None

    def _extract_civic_type(self, finding: Dict[str, Any]) -> Optional[CivicEvidenceType]:
        """提取 CIViC 证据类型"""
        civic_str = finding.get("civic_type") or finding.get("evidence_type")
        if civic_str:
            try:
                return CivicEvidenceType(civic_str.lower())
            except ValueError:
                pass
        return None


# ============================================================
# 工具特定提取器
# ============================================================

class CIViCEntityExtractor(EntityExtractor):
    """CIViC 数据专用提取器"""

    SYSTEM_PROMPT = EntityExtractor.SYSTEM_PROMPT + """

## CIViC 数据特殊说明
CIViC 数据包含 therapeutic, diagnostic, prognostic 等证据类型。
特别注意提取:
- 基因和变异信息
- 药物敏感性/耐药性关系 (sensitizes, causes_resistance)
- 证据等级 (A/B/C/D/E)
- clinical_significance 字段决定关系类型
"""


class ClinicalTrialsEntityExtractor(EntityExtractor):
    """ClinicalTrials.gov 数据专用提取器"""

    SYSTEM_PROMPT = EntityExtractor.SYSTEM_PROMPT + """

## ClinicalTrials.gov 数据特殊说明
临床试验数据包含:
- NCT ID (作为 TRIAL 实体)
- interventions (药物/方案)
- conditions (疾病)
- arms (试验臂)

提取关系:
- TRIAL evaluates DRUG
- DRUG treats DISEASE
- TRIAL includes_arm REGIMEN
"""


class PubMedEntityExtractor(EntityExtractor):
    """PubMed 数据专用提取器"""

    SYSTEM_PROMPT = EntityExtractor.SYSTEM_PROMPT + """

## PubMed 数据特殊说明
文献数据包含:
- PMID (作为 PAPER 实体)
- 标题和摘要中的实体
- 引用关系

提取关系:
- PAPER supports/contradicts FINDING
- PAPER cites PAPER
"""


class FDALabelEntityExtractor(EntityExtractor):
    """FDA Label 数据专用提取器"""

    SYSTEM_PROMPT = EntityExtractor.SYSTEM_PROMPT + """

## FDA Label 数据特殊说明
FDA 药物标签数据包含:
- 药物名称和适应症
- 禁忌症
- 黑框警告

提取关系:
- DRUG treats DISEASE (适应症, confidence=0.99)
- DRUG contraindicated_for CONDITION (禁忌症)
"""


class NCCNEntityExtractor(EntityExtractor):
    """NCCN 指南数据专用提取器"""

    SYSTEM_PROMPT = EntityExtractor.SYSTEM_PROMPT + """

## NCCN 指南数据特殊说明
NCCN 指南数据包含:
- 推荐等级 (preferred, useful, etc.)
- 治疗方案
- 生物标志物要求

提取关系:
- GUIDELINE recommends REGIMEN
- GUIDELINE recommends DRUG
- BIOMARKER biomarker_for DRUG
"""


# ============================================================
# 提取器注册表
# ============================================================

ENTITY_EXTRACTOR_MAP: Dict[str, EntityExtractor] = {
    # CIViC
    "search_civic": CIViCEntityExtractor(),

    # 临床试验
    "search_clinical_trials": ClinicalTrialsEntityExtractor(),

    # 文献
    "search_pubmed": PubMedEntityExtractor(),

    # FDA
    "search_fda_label": FDALabelEntityExtractor(),

    # NCCN
    "search_nccn": NCCNEntityExtractor(),
    "query_nccn": NCCNEntityExtractor(),

    # 其他工具使用默认提取器
    "search_clinvar": EntityExtractor(),
    "search_cbioportal": EntityExtractor(),
    "get_mutation_frequency": EntityExtractor(),
    "check_interaction": EntityExtractor(),
}


def get_extractor(source_tool: str) -> EntityExtractor:
    """
    获取工具对应的提取器

    Args:
        source_tool: 工具名称

    Returns:
        EntityExtractor 实例
    """
    return ENTITY_EXTRACTOR_MAP.get(source_tool, EntityExtractor())


def extract_entities_from_finding(
    finding: Dict[str, Any],
    source_agent: str,
    source_tool: str,
    iteration: int,
    llm_caller=None,
    existing_entities: str = ""
) -> ExtractionResult:
    """
    从 finding 提取实体和关系的便捷函数

    Args:
        finding: 工具返回的发现数据
        source_agent: 来源 Agent
        source_tool: 来源工具
        iteration: 迭代轮次
        llm_caller: 可选的 LLM 调用函数
        existing_entities: 已有实体索引（供 LLM 参考避免重复创建）

    Returns:
        ExtractionResult
    """
    extractor = get_extractor(source_tool)
    if llm_caller:
        extractor._llm_caller = llm_caller

    return extractor.extract(
        finding=finding,
        source_agent=source_agent,
        source_tool=source_tool,
        iteration=iteration,
        existing_entities=existing_entities
    )


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    print("=== Entity Extractors 模块测试 ===\n")

    # 测试 finding
    test_finding = {
        "gene": "EGFR",
        "variant": "L858R",
        "therapeutic": [
            {
                "drugs": ["Osimertinib", "Gefitinib"],
                "clinical_significance": "SENSITIVITY",
                "evidence_level": "A",
                "pubmed_id": "28854312"
            }
        ],
        "pmid": "28854312",
        "source_tool": "search_civic"
    }

    print("测试 Finding:")
    print(json.dumps(test_finding, indent=2))

    # 创建提取器
    extractor = CIViCEntityExtractor()

    # 注意: 实际运行需要 OPENROUTER_API_KEY
    print("\n注意: 实际提取需要设置 OPENROUTER_API_KEY 环境变量")
    print("以下是手动构建的示例结果:\n")

    # 手动构建示例结果
    example_result = ExtractionResult(
        entities=[
            ExtractedEntity(
                canonical_id="GENE:EGFR",
                entity_type=EntityType.GENE,
                name="EGFR",
                aliases=["ERBB1"]
            ),
            ExtractedEntity(
                canonical_id="EGFR_L858R",
                entity_type=EntityType.VARIANT,
                name="L858R",
                aliases=[]
            ),
            ExtractedEntity(
                canonical_id="DRUG:OSIMERTINIB",
                entity_type=EntityType.DRUG,
                name="OSIMERTINIB",
                aliases=["AZD9291", "TAGRISSO"]
            ),
        ],
        edges=[
            ExtractedEdge(
                source_id="EGFR_L858R",
                target_id="DRUG:OSIMERTINIB",
                predicate=Predicate.SENSITIZES,
                confidence=0.95
            ),
        ],
        source_tool="search_civic",
        raw_finding=test_finding
    )

    print(f"提取的实体: {len(example_result.entities)}")
    for e in example_result.entities:
        print(f"  - {e.canonical_id} ({e.entity_type.value}): {e.name}")

    print(f"\n提取的边: {len(example_result.edges)}")
    for edge in example_result.edges:
        print(f"  - {edge.source_id} --[{edge.predicate.value}]--> {edge.target_id}")

    print("\n=== 测试完成 ===")
