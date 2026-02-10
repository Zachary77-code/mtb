# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SMTB 2.0 (Smart Molecular Tumor Board) is a multi-agent workflow system for generating clinical tumor board reports. It processes patient case files (PDF) through specialized AI agents across 4 research phases and produces structured HTML reports with 6 chapters + appendices.

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
PDF Input → PDF Parser → PlanAgent (generates research plan + initializes EvidenceGraph)
                             ↓
              ┌──────────────────────────────────────────────┐
              │ Research Subgraph (4-Phase Loop)              │
              │                                              │
              │ ┌─── Phase 1: 信息提取 (max 3, 轻量) ─────┐ │
              │ │ [Pathologist][Geneticist][Pharmacist]      │ │
              │ │ [Oncologist(analysis)]                     │ │
              │ │ → Aggregator → PlanAgent.evaluate()       │ │
              │ │   continue ↺     ↓ converged              │ │
              │ └──────────────────┘                        │ │
              │              ↓ generate_phase1_reports()     │
              │              ↓ phase2a_plan_init()           │
              │ ┌─── Phase 2a: 治疗Mapping (max 7) ───────┐ │
              │ │ [Oncologist(mapping)][LocalTherapist]      │ │
              │ │ [Recruiter][Nutritionist][IntegrativeMed]  │ │
              │ │ → Aggregator → PlanAgent.evaluate()       │ │
              │ │   continue ↺     ↓ converged              │ │
              │ └──────────────────┘                        │ │
              │              ↓ generate_phase2a_reports()    │
              │              ↓ phase2b_plan_init()           │
              │ ┌─── Phase 2b: 药学审查 (max 3, 轻量) ────┐ │
              │ │ [Pharmacist(review)] solo BFRS/DFRS       │ │
              │ │ → PlanAgent.evaluate()                    │ │
              │ │   continue ↺     ↓ converged              │ │
              │ └──────────────────┘                        │ │
              │              ↓ generate_phase2b_report()     │
              │              ↓ phase3_plan_init()            │
              │ ┌─── Phase 3: 方案整合 (max 7) ───────────┐ │
              │ │ [Oncologist(integration)] solo BFRS/DFRS  │ │
              │ │ L1-L5 evidence tiering                    │ │
              │ │ → PlanAgent.evaluate()                    │ │
              │ │   continue ↺     ↓ converged              │ │
              │ └──────────────────┘                        │ │
              │              ↓ generate_phase3_report()      │
              │              ↓ generate_reports()            │
              └──────────────────────────────────────────────┘
                             ↓
                          Chair  ← synthesizes 11 agent reports + EvidenceGraph
                             ↓
                   Format Verification
                     ↓           ↓
                  [Pass]      [Fail → Chair Retry, max 2x]
                     ↓
                 HTML Report (with TOC + Agent Appendix)
```

- **State**: `MtbState` TypedDict in [src/models/state.py](src/models/state.py) - all data flows through this state object
- **Graph**: [src/graph/state_graph.py](src/graph/state_graph.py) - workflow definition with `StateGraph`
- **Research Subgraph**: [src/graph/research_subgraph.py](src/graph/research_subgraph.py) - 4-phase BFRS/DFRS research loop
- **Nodes**: [src/graph/nodes.py](src/graph/nodes.py) - each node calls an agent and updates state
- **Edges**: [src/graph/edges.py](src/graph/edges.py) - conditional logic for retry decisions

### Agent Architecture

Agents inherit from `BaseAgent` in [src/agents/base_agent.py](src/agents/base_agent.py):
- Direct OpenRouter API calls via `requests` (not OpenAI SDK)
- System prompt = global_principles.txt + role-specific prompt
- Support for multi-turn tool calling (up to 5 iterations)
- Reference management with `ReferenceManager` class
- **ResearchMixin** ([src/agents/research_mixin.py](src/agents/research_mixin.py)) adds BFRS/DFRS research capabilities with `phase_context` injection

Ten agents in `src/agents/`:

| Agent | Role | Phase(s) | Tools | Temp |
|-------|------|----------|-------|------|
| **Pathologist** | Pathology/imaging/treatment history extraction | P1 | PubMed, GDC | 0.3 |
| **Geneticist** | Molecular profile + resistance mutation analysis | P1 | CIViC, ClinVar, GDC, PubMed | 0.2 |
| **Pharmacist** | Comorbidity/drug baseline (P1) + Pharmacy review (P2b) | P1, P2b | FDALabel, RxNorm, PubMed | 0.2 |
| **Oncologist** | Analysis (P1) / Mapping (P2a) / Integration+L1-L5 (P3) | P1, P2a, P3 | NCCN, FDALabel, RxNorm, PubMed | 0.2 |
| **LocalTherapist** | Surgery/radiation/intervention evaluation | P2a | NCCN, PubMed | 0.3 |
| **Recruiter** | Clinical trial matching (active + completed) | P2a | ClinicalTrials, NCCN, PubMed | 0.2 |
| **Nutritionist** | Nutrition assessment and cancer diet planning | P2a | PubMed | 0.3 |
| **IntegrativeMed** | Alternative therapy evaluation (per-therapy risk analysis) | P2a | PubMed | 0.3 |
| **Chair** | Final synthesis (6 chapters + appendices) | P4 | NCCN, FDALabel, PubMed | 0.3 |
| **PlanAgent** | Research plan + phase init + convergence evaluation | All | - | 0.3 |

**Multi-Mode Agents**:
- **Oncologist**: `analysis` (P1) → `mapping` (P2a, 4×5 matrix) → `integration` (P3, L1-L5 tiering)
- **Pharmacist**: `research` (P1, comorbidity baseline) → `review` (P2b, pharmacy review labels)

**Research-Enhanced Agents**: In the Research Subgraph, agents are enhanced with `ResearchMixin`:
- Phase 1: `ResearchPathologist`, `ResearchGeneticist`, `ResearchPharmacist`, `ResearchOncologist`
- Phase 2a: `ResearchOncologist`, `ResearchLocalTherapist`, `ResearchRecruiter`, `ResearchNutritionist`, `ResearchIntegrativeMed`
- Phase 2b: `ResearchPharmacist` (review mode)
- Phase 3: `ResearchOncologist` (integration mode)
- Use `SUBGRAPH_MODEL` (flash model) for cost efficiency
- Support `research_iterate()` with `phase_context` dict for phase/mode awareness

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

### Research Subgraph (4-Phase)

Four-phase research loop implementing BFRS/DFRS research modes ([src/graph/research_subgraph.py](src/graph/research_subgraph.py)):

**Phase Structure**:

| Phase | Mode | Max Iter | Agents | Purpose |
|-------|------|----------|--------|---------|
| Phase 1 | 轻量 BFRS/DFRS | 3 | Pathologist, Geneticist, Pharmacist, Oncologist(analysis) | Information extraction |
| Phase 2a | 完整 BFRS/DFRS | 7 | Oncologist(mapping), LocalTherapist, Recruiter, Nutritionist, IntegrativeMed | Treatment mapping (list, don't recommend) |
| Phase 2b | 轻量 BFRS/DFRS | 3 | Pharmacist(review) solo | Pharmacy review labels |
| Phase 3 | 完整 BFRS/DFRS | 7 | Oncologist(integration) solo | Treatment plan + L1-L5 tiering |

**PlanAgent Phase Initialization**:
Each phase begins with PlanAgent generating research directions and injecting `phase_context`:
```python
phase_context = {
    "current_phase": "phase_2a",
    "phase_description": "治疗Mapping",
    "current_iteration": 3,
    "max_iterations": 7,
    "agent_mode": "mapping",
    "agent_role_in_phase": "全身治疗手段Mapping，只罗列不推荐",
    "iteration_feedback": "..."
}
```

**Research Modes**:
- **BFRS (Breadth-First Research)**: 1-2 tool calls per direction, collecting broad preliminary evidence
- **DFRS (Depth-First Research)**: 3-5 consecutive tool calls for high-priority findings

**Convergence Check**: `PlanAgent.evaluate_and_update()`
- Unified convergence judgment by PlanAgent
- Computes evidence quality stats per direction (count, grade distribution, weighted score)
- LLM evaluates research quality, decides whether to converge
- Dynamically updates research plan: adjusts priorities, sets direction's preferred_mode (breadth_first/depth_first/skip)

**Report Files** (numbered by phase):
```
1_pathologist_report.md        Phase 1
2_geneticist_report.md         Phase 1
3_pharmacist_report.md         Phase 1
4_oncologist_analysis.md       Phase 1
5_oncologist_mapping.md        Phase 2a
6_local_therapist.md           Phase 2a
7_recruiter.md                 Phase 2a
8_nutritionist.md              Phase 2a
9_integrative_med.md           Phase 2a
10_pharmacist_review.md        Phase 2b
11_oncologist_integration.md   Phase 3
12_chair_final_report.md       Phase 4
13_final_report.html           Phase 4
```

### Evidence Graph (Entity-Edge-Observation Architecture)

Global evidence graph uses DeepEvidence paper's entity-centric architecture ([src/models/evidence_graph.py](src/models/evidence_graph.py)):

**Data Structures**:
- `Entity`: Node (canonical_id, entity_type, name, aliases, observations)
- `Edge`: Relationship (source_id, target_id, predicate, observations, confidence, conflict_group)
- `Observation`: Factual statement (statement, evidence_grade, civic_type, provenance, source_url)

**Entity Types** (`EntityType`): gene, variant, drug, disease, pathway, biomarker, paper, trial, guideline, regimen, finding

**Evidence Grades** (`EvidenceGrade`): A, B, C, D, E (CIViC standard)

**L1-L5 Evidence Tiering** (Phase 3 treatment plan decisions):
| Level | Label | Meaning |
|-------|-------|---------|
| L1 | 直接循证 | Direct RCT/Meta-analysis |
| L2 | 指南推荐 | NCCN/CSCO/ESMO guideline |
| L3 | 间接外推 | Indirect evidence extrapolation |
| L4 | 机制推断 | Biological mechanism inference |
| L5 | 经验性 | Clinical experience only |

### Report Structure (6 Chapters + Appendices)

| Chapter | Sections | Data Source |
|---------|----------|-------------|
| **1. 病情概要** | 1.1基础信息, 1.2诊断, 1.3分子, 1.4合并症, 1.5过敏 | Pathologist P1, Geneticist P1, Pharmacist P1 |
| **2. 治疗史回顾** | Timeline + 分析评价 | Pathologist P1 + Oncologist P1(3.1) |
| **3. 治疗方案探索** | 3.1分析, 3.2 Mapping(4×5矩阵), 3.3方案制定(L1-L5), 3.4路径规划 | Oncologist P1/P2a/P3, LocalTherapist, Recruiter, Pharmacist P2b |
| **4. 整体与辅助支持** | 4.1营养, 4.2替代疗法 | Nutritionist P2a, IntegrativeMed P2a |
| **5. 复查和追踪方案** | 5.1常规复查To-Do, 5.2分子复查 | Geneticist P1 + Oncologist P3 |
| **6. 核心建议汇总** | Exec summary + recommendations | Chair synthesis |
| **附录A** | 完整证据引用列表 | Auto-generated from EvidenceGraph |
| **附录B** | 证据等级说明 (CIViC A-E + L1-L5) | Fixed content |
| **附录C** | Agent 原始报告 | HTML appendix (all 11 reports) |

### Report Validation

Reports must contain **8 mandatory sections** (defined in `config/settings.py:REQUIRED_SECTIONS`):
1. 病情概要
2. 治疗史回顾
3. 治疗方案探索
4. 整体与辅助支持
5. 复查和追踪方案
6. 核心建议汇总
7. 完整证据引用列表
8. 证据等级说明

`FormatChecker` in [src/validators/format_checker.py](src/validators/format_checker.py) validates these sections + subsections with fuzzy matching.

### HTML Generation

[src/renderers/html_generator.py](src/renderers/html_generator.py) supports:
- Custom block markers: `:::exec-summary`, `:::timeline`, `:::roadmap`
- Inline references: `[[ref:ID;;Title;;URL;;Note]]`
- Evidence badges: `[Evidence A]` → colored badge, `[L1 直接循证]` → L-tier badge
- **TOC**: Auto-generated table of contents from h2/h3 headings
- **Agent Appendix**: All 11 agent reports rendered as HTML appendix
- **Print styles**: Page breaks for chapters and agent reports

### Monitoring & Logging

Logging configured with Loguru ([src/utils/logger.py](src/utils/logger.py)):
- **Output**: `logs/mtb.log`
- **Rotation**: 10MB trigger, 7-day retention, zip compression

**Log Tags**:
| Tag | Description |
|-----|-------------|
| `[PHASE1]` / `[PHASE2A]` / `[PHASE2B]` / `[PHASE3]` | Research loop iteration |
| `[PHASE1_CONVERGENCE]` etc. | Convergence check details |
| `[EVIDENCE]` | Evidence graph statistics |
| `[AgentName]` | Agent execution status |
| `[Tool:ToolName]` | Tool invocation details |

## Configuration

Environment variables (`.env`):
```
OPENROUTER_API_KEY=<required>
OPENROUTER_MODEL=google/gemini-3-pro-preview  # default
DASHSCOPE_API_KEY=<for embeddings>
NCBI_API_KEY=<optional, increases rate limits>
```

Key settings in `config/settings.py`:
- `AGENT_TEMPERATURE=0.2`
- `AGENT_TIMEOUT=120` seconds
- `MAX_RETRY_ITERATIONS=2`
- `MAX_PHASE1_ITERATIONS=3` - Phase 1 max iterations (轻量)
- `MAX_PHASE2A_ITERATIONS=7` - Phase 2a max iterations (完整)
- `MAX_PHASE2B_ITERATIONS=3` - Phase 2b max iterations (轻量)
- `MAX_PHASE3_ITERATIONS=7` - Phase 3 max iterations (完整)
- `MIN_EVIDENCE_PER_DIRECTION=20` - Minimum evidence per research direction
- `SUBGRAPH_MODEL` - Model for research subgraph (flash model for cost efficiency)

## Prompts

All agent prompts are in `config/prompts/`:
- `global_principles.txt` - shared rules (evidence grading, citation format, safety-first, L1-L5, no-truncation)
- `{agent}_prompt.txt` - role-specific instructions (10 agents)

Evidence grading (CIViC Evidence Level): A (Validated) / B (Clinical) / C (Case Study) / D (Preclinical) / E (Inferential)

Citation format: `[PMID: 12345678](url)` or `[NCT04123456](url)` or `[[ref:ID;;Title;;URL;;Note]]`

## Key Patterns

1. **State updates**: Nodes return `Dict[str, Any]` that gets merged into `MtbState`
2. **Tool invocation**: Agents can call tools during generation; results feed back into conversation
3. **Retry logic**: If format validation fails, workflow loops back to Chair node (max 2 times)
4. **Reference flow**: All 11 agent reports pass references to Chair; Chair preserves all citations
5. **Multi-mode agents**: Oncologist and Pharmacist switch behavior based on `phase_context.agent_mode`
6. **Phase context injection**: Each research agent receives `phase_context` dict with phase/iteration/mode info
7. **Logging**: All logs go to `logs/mtb.log` via Loguru
8. **Report saving**: Each agent saves `{n}_{agent}_report.md` to the run folder (numbered 1-13)
9. **No truncation**: Do NOT truncate strings (`[:N]`) or limit list sizes (`[:N]`) in evidence flow, reports, or prompt construction. All evidence, entity lists, observations, and reasoning content must be passed in full. Truncation is only acceptable in logger output.
10. **L1-L5 preservation**: Chair must preserve Oncologist Phase 3's L1-L5 annotations without modification
