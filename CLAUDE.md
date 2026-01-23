# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MTB (分子肿瘤委员会) is a multi-agent workflow system for generating clinical tumor board reports. It processes patient case files (PDF) through specialized AI agents and produces structured HTML reports.

**Key constraint**: This system uses **LangGraph 1.0.6 only** - it does NOT use LangChain. All LLM calls go through OpenRouter API directly.

## Commands

```bash
# Run the workflow
python main.py <case_file.pdf>
python main.py tests/fixtures/test_report.pdf

# Test all external API tools
python tests/test_all_tools.py

# Verify configuration
python config/settings.py

# Run pytest
pytest tests/
```

## Architecture

### Workflow Pipeline (LangGraph StateGraph)

```
PDF Input → PDF Parser → PlanAgent (生成研究计划+初始化EvidenceGraph)
                             ↓
              ┌──────────────────────────────────────┐
              │ Research Subgraph (两阶段研究循环)    │
              │                                      │
              │ ┌────────── Phase 1 Loop ──────────┐ │
              │ │    (最多 MAX_PHASE1_ITERATIONS=7) │ │
              │ │ [Pathologist][Geneticist][Recruiter]│
              │ │        ↓ (并行 BFRS/DFRS)          │ │
              │ │      Phase1 Aggregator            │ │
              │ │        ↓                          │ │
              │ │  Convergence Check (3步)          │ │
              │ │    continue ↺    ↓ converged      │ │
              │ └───────────────────┘               │
              │                     ↓               │
              │ ┌────────── Phase 2 Loop ──────────┐ │
              │ │    (最多 MAX_PHASE2_ITERATIONS=7) │ │
              │ │         Oncologist               │ │
              │ │        ↓ (独立 BFRS/DFRS)         │ │
              │ │  Convergence Check (3步)          │ │
              │ │    continue ↺    ↓ converged      │ │
              │ └───────────────────┘               │
              │                     ↓               │
              │        Generate Agent Reports       │
              └──────────────────────────────────────┘
                             ↓
                           Chair  ← Receives upstream_references
                             ↓
                    Format Verification
                      ↓           ↓
                   [Pass]      [Fail → Chair Retry, max 2x]
                      ↓
                  HTML Report
```

- **State**: `MtbState` TypedDict in [src/models/state.py](src/models/state.py) - all data flows through this state object
- **Graph**: [src/graph/state_graph.py](src/graph/state_graph.py) - workflow definition with `StateGraph`
- **Research Subgraph**: [src/graph/research_subgraph.py](src/graph/research_subgraph.py) - 两阶段BFRS/DFRS研究循环
- **Nodes**: [src/graph/nodes.py](src/graph/nodes.py) - each node calls an agent and updates state
- **Edges**: [src/graph/edges.py](src/graph/edges.py) - conditional logic for retry decisions

### Agent Architecture

Agents inherit from `BaseAgent` in [src/agents/base_agent.py](src/agents/base_agent.py):
- Direct OpenRouter API calls via `requests` (not OpenAI SDK)
- System prompt = global_principles.txt + role-specific prompt
- Support for multi-turn tool calling (up to 5 iterations)
- Reference management with `ReferenceManager` class
- **ResearchMixin** ([src/agents/research_mixin.py](src/agents/research_mixin.py)) adds BFRS/DFRS research capabilities

Seven agents in `src/agents/`:

| Agent | Role | Tools | Temp |
|-------|------|-------|------|
| **Pathologist** | Pathology/imaging analysis | PubMed, cBioPortal | 0.3 |
| **Geneticist** | Molecular profile analysis | CIViC, ClinVar, cBioPortal, PubMed | 0.2 |
| **Recruiter** | Clinical trial matching | ClinicalTrials.gov, NCCN, PubMed | 0.2 |
| **Oncologist** | Treatment planning, safety | NCCN, FDA Label, RxNorm, PubMed | 0.2 |
| **Chair** | Final synthesis (12 modules) | NCCN, FDA Label, PubMed | 0.3 |
| **PlanAgent** | Research plan generation | - | 0.2 |
| **ConvergenceJudge** | Convergence evaluation | - | 0.2 |

**Research-Enhanced Agents**: In the Research Subgraph, agents are enhanced with `ResearchMixin`:
- `ResearchPathologist`, `ResearchGeneticist`, `ResearchRecruiter`, `ResearchOncologist`
- Use `SUBGRAPH_MODEL` (flash model) for cost efficiency
- Support `research_iterate()` for BFRS/DFRS execution

**Reference Preservation**: Chair receives `upstream_references` from Pathologist, Geneticist, and Recruiter, then merges and deduplicates all citations in the final report.

### External API Tools

Tools in `src/tools/` follow the `BaseTool` pattern (OpenAI function calling format):

| Tool | API | Purpose |
|------|-----|---------|
| CIViCTool | CIViC | Variant evidence levels |
| ClinVarTool | NCBI ClinVar | Pathogenicity classification |
| cBioPortalTool | cBioPortal | Mutation frequencies |
| PubMedTool | NCBI PubMed | Literature search |
| ClinicalTrialsTool | ClinicalTrials.gov | Trial matching |
| FDALabelTool | openFDA | Drug labels |
| RxNormTool | NLM RxNorm | Drug interactions |
| NCCNRagTool | Local ChromaDB | NCCN guideline RAG |

### Research Subgraph

两阶段研究循环实现 BFRS/DFRS 研究模式 ([src/graph/research_subgraph.py](src/graph/research_subgraph.py)):

**研究模式**:
- **BFRS (Breadth-First Research)**: 广度优先，每方向1-2次工具调用，收集广泛初步证据
- **DFRS (Depth-First Research)**: 深度优先，针对高优先级发现进行3-5次连续工具调用

**三步收敛检查**:
1. **Metric-based Fast Check**: 方向完成 + 证据充分 (≥ `MIN_EVIDENCE_PER_DIRECTION`)
2. **Agent Module Coverage Check**: 各Agent覆盖了分配给自己的`target_modules`
   - Phase 1: 检查 Pathologist/Geneticist/Recruiter 各自分配的模块
   - Phase 2: 检查 Oncologist 分配的模块
3. **ConvergenceJudge Agent**: LLM评估研究质量

**研究迭代输出** (每次 `research_iterate()` 返回):
```python
{
    "evidence_graph": Dict,        # 更新后的证据图
    "research_plan": Dict,         # 更新后的研究计划
    "new_evidence_ids": List[str], # 新添加的证据ID
    "direction_updates": Dict,     # 方向状态更新 {id: "pending"|"completed"}
    "needs_deep_research": List,   # 需要深入研究的发现
    "summary": str
}
```

### Evidence Graph

全局证据图用于存储和管理所有Agent收集的证据 ([src/models/evidence_graph.py](src/models/evidence_graph.py)):

**生命周期**:
| 时机 | 操作 | 位置 |
|------|------|------|
| 创建 | `plan_agent_node()` 初始化空图 | nodes.py |
| 更新 | `research_iterate()` 添加节点 | research_mixin.py |
| 收敛检查 | `check_direction_evidence_sufficiency()` | research_subgraph.py |
| 报告生成 | `generate_agent_reports()` 按Agent提取证据 | research_subgraph.py |

**数据结构**:
- `EvidenceNode`: 证据节点（类型、等级、来源Agent、迭代轮次、上下文）
- `EvidenceEdge`: 关系边（supports, contradicts, sensitizes 等）
- `EvidenceContext`: 结构化上下文（species, cell_type, assay, sample_size 等）

**证据类型** (`EvidenceType`): molecular, clinical, literature, trial, guideline, drug, pathology, imaging

**证据等级** (`EvidenceGrade`): A, B, C, D, E (CIViC标准)

### Monitoring & Logging

日志配置使用 Loguru ([src/utils/logger.py](src/utils/logger.py)):
- **输出位置**: `logs/mtb.log`
- **轮转**: 10MB 触发，保留7天，zip压缩

**日志标签**:
| 标签 | 说明 |
|------|------|
| `[PHASE1]` / `[PHASE2]` | 研究循环迭代 |
| `[PHASE1_CONVERGENCE]` | 收敛检查详情 |
| `[EVIDENCE]` | 证据图统计 |
| `[Agent名称]` | Agent执行状态 |
| `[Tool:工具名]` | 工具调用详情 |

**辅助函数**:
- `log_phase_progress()` - 进度条 `[████░░] 4/7`
- `log_evidence_stats()` - 证据图统计（类型分布、Agent分布）
- `log_convergence_status()` - 收敛状态快照

**监控中间过程**:
1. 查看 `logs/mtb.log` 实时日志
2. 检查 `[EVIDENCE]` 标签了解证据收集进度
3. 检查 `[PHASE1_CONVERGENCE]` / `[PHASE2_CONVERGENCE]` 标签了解收敛决策

### Report Validation

Reports must contain **12 mandatory modules** (defined in `config/settings.py:REQUIRED_SECTIONS`):
1. 执行摘要 (Executive Summary)
2. 患者概况 (Patient Profile)
3. 分子特征 (Molecular Profile)
4. 治疗史回顾 (Treatment History)
5. 药物/方案对比 (Regimen Comparison)
6. 器官功能与剂量 (Organ Function & Dosing)
7. 治疗路线图 (Treatment Roadmap)
8. 分子复查建议 (Re-biopsy/Liquid Biopsy)
9. 临床试验推荐 (Clinical Trials)
10. 局部治疗建议 (Local Therapy)
11. 核心建议汇总 (Core Recommendations)
12. 参考文献 (References)

`FormatChecker` in [src/validators/format_checker.py](src/validators/format_checker.py) validates these modules with fuzzy matching.

### HTML Generation

[src/renderers/html_generator.py](src/renderers/html_generator.py) supports custom block markers:
- `:::exec-summary ... :::` - executive summary block
- `:::timeline ... :::` - treatment timeline (YAML format)
- `:::roadmap ... :::` - treatment roadmap cards
- `[[ref:ID|Title|URL|Note]]` - inline reference with tooltip

## Configuration

Environment variables (`.env`):
```
OPENROUTER_API_KEY=<required>
OPENROUTER_MODEL=google/gemini-2.5-pro-preview  # default
DASHSCOPE_API_KEY=<for embeddings>
NCBI_API_KEY=<optional, increases rate limits>
```

Key settings in `config/settings.py`:
- `AGENT_TEMPERATURE=0.2`
- `AGENT_TIMEOUT=120` seconds
- `MAX_RETRY_ITERATIONS=2`
- `MAX_PHASE1_ITERATIONS=7` - Phase 1 最大迭代次数
- `MAX_PHASE2_ITERATIONS=7` - Phase 2 最大迭代次数
- `MIN_EVIDENCE_PER_DIRECTION=20` - 每研究方向最少证据数
- `SUBGRAPH_MODEL` - 研究子图使用的模型（flash模型降低成本）

## Prompts

All agent prompts are in `config/prompts/`:
- `global_principles.txt` - shared rules (evidence grading, citation format, safety-first)
- `{agent}_prompt.txt` - role-specific instructions

Evidence grading (CIViC Evidence Level):
- A: Validated - 已验证，多项独立研究或 meta 分析支持
- B: Clinical - 临床证据，来自临床试验或大规模临床研究
- C: Case Study - 病例研究，来自个案报道或小规模病例系列
- D: Preclinical - 临床前证据，来自细胞系、动物模型等实验
- E: Inferential - 推断性证据，间接证据或基于生物学原理的推断

CIViC Evidence Types (临床意义分类):
- Predictive (预测性): 预测对某种治疗的反应
- Diagnostic (诊断性): 用于疾病诊断
- Prognostic (预后性): 与疾病预后相关
- Predisposing (易感性): 与癌症风险相关
- Oncogenic (致癌性): 变异的致癌功能

Citation format: `[PMID: 12345678](url)` or `[NCT04123456](url)`

## Key Patterns

1. **State updates**: Nodes return `Dict[str, Any]` that gets merged into `MtbState`
2. **Tool invocation**: Agents can call tools during generation; results feed back into conversation
3. **Retry logic**: If format validation fails, workflow loops back to Chair node (max 2 times)
4. **Reference flow**: Upstream agents generate `*_references` arrays; Chair merges all into `chair_final_references`
5. **Logging**: All logs go to `logs/mtb.log` via Loguru
6. **Report saving**: Each agent saves `{n}_{agent}_report.md` to the run folder
