# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MTB (Molecular Tumor Board) is a multi-agent workflow system for generating clinical tumor board reports. It processes patient case files (PDF) through specialized AI agents and produces structured HTML reports.

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
                    ┌────────────────┐
                    │ EvidenceGraph  │ ← Global evidence graph (Entity-Edge-Observation)
                    │   (empty)      │
                    └───────┬────────┘
                            ↓
              ┌──────────────────────────────────────┐
              │ Research Subgraph (Two-Phase Loop)   │
              │                                      │
              │ ┌────────── Phase 1 Loop ──────────┐ │
              │ │    (max MAX_PHASE1_ITERATIONS=7) │ │
              │ │ [Pathologist][Geneticist][Recruiter]│
              │ │        ↓ (parallel BFRS/DFRS)     │ │
              │ │   ┌─────────────────────┐         │ │
              │ │   │ Update EvidenceGraph│         │ │
              │ │   │ (entity extraction) │         │ │
              │ │   └─────────────────────┘         │ │
              │ │        ↓                          │ │
              │ │      Phase1 Aggregator            │ │
              │ │        ↓                          │ │
              │ │  PlanAgent.evaluate_and_update()  │ │
              │ │    continue ↺    ↓ converged      │ │
              │ └───────────────────┘               │
              │                     ↓               │
              │          generate_phase1_reports()  │ ← saves 1_pathologist/2_geneticist/3_recruiter
              │                     ↓               │
              │          phase2_plan_init()         │ ← generates Oncologist directions from Phase 1
              │                     ↓               │
              │ ┌────────── Phase 2 Loop ──────────┐ │
              │ │    (max MAX_PHASE2_ITERATIONS=7) │ │
              │ │         Oncologist               │ │
              │ │        ↓ (solo BFRS/DFRS)        │ │
              │ │   ┌─────────────────────┐         │ │
              │ │   │ Update EvidenceGraph│         │ │
              │ │   └─────────────────────┘         │ │
              │ │        ↓                          │ │
              │ │  PlanAgent.evaluate_and_update()  │ │
              │ │    continue ↺    ↓ converged      │ │
              │ └───────────────────┘               │
              │                     ↓               │
              │          generate_phase2_reports()  │ ← saves 4_oncologist_report
              │                     ↓               │
              │          generate_agent_reports()   │ ← extracts references, trial info
              └──────────────────────────────────────┘
                             ↓
                    ┌────────────────┐
                    │ EvidenceGraph  │ ← Complete graph passed to Chair
                    │  (88 entities) │
                    └───────┬────────┘
                            ↓
                          Chair  ← generates final report from EvidenceGraph + agent reports
                            ↓
                   Format Verification
                     ↓           ↓
                  [Pass]      [Fail → Chair Retry, max 2x]
                     ↓
                 HTML Report
```

- **State**: `MtbState` TypedDict in [src/models/state.py](src/models/state.py) - all data flows through this state object
- **Graph**: [src/graph/state_graph.py](src/graph/state_graph.py) - workflow definition with `StateGraph`
- **Research Subgraph**: [src/graph/research_subgraph.py](src/graph/research_subgraph.py) - two-phase BFRS/DFRS research loop
- **Nodes**: [src/graph/nodes.py](src/graph/nodes.py) - each node calls an agent and updates state
- **Edges**: [src/graph/edges.py](src/graph/edges.py) - conditional logic for retry decisions

### Agent Architecture

Agents inherit from `BaseAgent` in [src/agents/base_agent.py](src/agents/base_agent.py):
- Direct OpenRouter API calls via `requests` (not OpenAI SDK)
- System prompt = global_principles.txt + role-specific prompt
- Support for multi-turn tool calling (up to 5 iterations)
- Reference management with `ReferenceManager` class
- **ResearchMixin** ([src/agents/research_mixin.py](src/agents/research_mixin.py)) adds BFRS/DFRS research capabilities

Six agents in `src/agents/`:

| Agent | Role | Tools | Temp |
|-------|------|-------|------|
| **Pathologist** | Pathology/imaging analysis | PubMed, cBioPortal | 0.3 |
| **Geneticist** | Molecular profile analysis | CIViC, ClinVar, cBioPortal, PubMed | 0.2 |
| **Recruiter** | Clinical trial matching | ClinicalTrials.gov, NCCN, PubMed | 0.2 |
| **Oncologist** | Treatment planning, safety | NCCN, FDA Label, RxNorm, PubMed | 0.2 |
| **Chair** | Final synthesis (12 modules) | NCCN, FDA Label, PubMed | 0.3 |
| **PlanAgent** | Research plan generation + convergence evaluation | - | 0.3 |

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

Two-phase research loop implementing BFRS/DFRS research modes ([src/graph/research_subgraph.py](src/graph/research_subgraph.py)):

**Research Modes**:
- **BFRS (Breadth-First Research)**: 1-2 tool calls per direction, collecting broad preliminary evidence
- **DFRS (Depth-First Research)**: 3-5 consecutive tool calls for high-priority findings

**Convergence Check**: `PlanAgent.evaluate_and_update()`
- Unified convergence judgment by PlanAgent (ConvergenceJudge deprecated)
- Computes evidence quality stats per direction (count, grade distribution, weighted score)
- LLM evaluates research quality, decides whether to converge
- Dynamically updates research plan: adjusts priorities, sets direction's preferred_mode (breadth_first/depth_first/skip)

**Research Iteration Output** (each `research_iterate()` returns):
```python
{
    "evidence_graph": Dict,        # Updated evidence graph
    "research_plan": Dict,         # Updated research plan
    "new_entity_ids": List[str],   # Newly added entity canonical IDs
    "direction_updates": Dict,     # Direction status updates {id: "pending"|"completed"}
    "needs_deep_research": List,   # Findings requiring deep research
    "summary": str
}
```

### Evidence Graph (Entity-Edge-Observation Architecture)

Global evidence graph uses DeepEvidence paper's entity-centric architecture ([src/models/evidence_graph.py](src/models/evidence_graph.py)):

**Architecture Overview**:
```
Finding: "Gefitinib improves survival in EGFR L858R NSCLC"
    ↓ LLM Entity Extraction
┌─────────────────────────────────────────────────────┐
│ Entities:                                           │
│   GENE:EGFR, EGFR_L858R, DRUG:GEFITINIB, DISEASE:NSCLC │
│                                                     │
│ Edges:                                              │
│   EGFR_L858R → SENSITIZES → GEFITINIB              │
│   GEFITINIB → TREATS → NSCLC                        │
│                                                     │
│ Observation (on edge):                              │
│   "Gefitinib improves OS (human, Phase III, n=347) │
│    [PMID:12345678]"                                 │
└─────────────────────────────────────────────────────┘
```

**Data Structures**:
- `Entity`: Node (canonical_id, entity_type, name, aliases, observations)
- `Edge`: Relationship (source_id, target_id, predicate, observations, confidence, conflict_group)
- `Observation`: Factual statement (statement, evidence_grade, civic_type, provenance, source_url)

**Entity Types** (`EntityType`): gene, variant, drug, disease, pathway, biomarker, paper, trial, guideline, regimen, finding

**Predicate Types** (`Predicate`):
- Molecular mechanisms: ACTIVATES, INHIBITS, BINDS, PHOSPHORYLATES, REGULATES, AMPLIFIES, MUTATES_TO
- Drug relationships: TREATS, SENSITIZES, CAUSES_RESISTANCE, INTERACTS_WITH, CONTRAINDICATED_FOR
- Evidence relationships: SUPPORTS, CONTRADICTS, CITES, DERIVED_FROM
- Membership/annotation: MEMBER_OF, EXPRESSED_IN, ASSOCIATED_WITH, BIOMARKER_FOR
- Guidelines/trials: RECOMMENDS, EVALUATES, INCLUDES_ARM

**Evidence Grades** (`EvidenceGrade`): A, B, C, D, E (CIViC standard)

**Lifecycle**:
| When | Operation | Location |
|------|-----------|----------|
| Creation | `plan_agent_node()` initializes empty graph | nodes.py |
| Update | `research_iterate()` → LLM entity extraction → merge | research_mixin.py |
| Entity Extraction | `extract_entities_from_finding()` | entity_extractors.py |
| Convergence Check | `check_direction_evidence_sufficiency()` | research_subgraph.py |
| Report Generation | `generate_agent_reports()` extracts by agent | research_subgraph.py |
| Visualization | `graph.to_mermaid()` generates flowchart | evidence_graph.py |

**Key Methods**:
- `get_or_create_entity(canonical_id, ...)`: Get or create entity (auto-merge)
- `add_observation_to_entity(canonical_id, observation)`: Add observation
- `add_edge(source_id, target_id, predicate, ...)`: Add relationship edge
- `find_entity_by_name(name)`: Fuzzy entity lookup
- `summary()`: Returns stats summary (entities_by_type, best_grades, edges_by_predicate)
- `to_mermaid()`: Generate Mermaid format diagram

### Monitoring & Logging

Logging configured with Loguru ([src/utils/logger.py](src/utils/logger.py)):
- **Output**: `logs/mtb.log`
- **Rotation**: 10MB trigger, 7-day retention, zip compression

**Log Tags**:
| Tag | Description |
|-----|-------------|
| `[PHASE1]` / `[PHASE2]` | Research loop iteration |
| `[PHASE1_CONVERGENCE]` | Convergence check details |
| `[EVIDENCE]` | Evidence graph statistics |
| `[AgentName]` | Agent execution status |
| `[Tool:ToolName]` | Tool invocation details |

**Helper Functions**:
- `log_phase_progress()` - Progress bar `[████░░] 4/7`
- `log_evidence_stats()` - Evidence graph stats (type distribution, agent distribution)
- `log_convergence_status()` - Convergence status snapshot

**Monitoring Intermediate Process**:
1. View `logs/mtb.log` real-time logs
2. Check `[EVIDENCE]` tag for evidence collection progress
3. Check `[PHASE1_CONVERGENCE]` / `[PHASE2_CONVERGENCE]` tags for convergence decisions

### Report Validation

Reports must contain **12 mandatory modules** (defined in `config/settings.py:REQUIRED_SECTIONS`):
1. Executive Summary
2. Patient Profile
3. Molecular Profile
4. Treatment History
5. Regimen Comparison
6. Organ Function & Dosing
7. Treatment Roadmap
8. Re-biopsy/Liquid Biopsy
9. Clinical Trials
10. Local Therapy
11. Core Recommendations
12. References

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
OPENROUTER_MODEL=google/gemini-3-pro-preview  # default
DASHSCOPE_API_KEY=<for embeddings>
NCBI_API_KEY=<optional, increases rate limits>
```

Key settings in `config/settings.py`:
- `AGENT_TEMPERATURE=0.2`
- `AGENT_TIMEOUT=120` seconds
- `MAX_RETRY_ITERATIONS=2`
- `MAX_PHASE1_ITERATIONS=7` - Phase 1 max iterations
- `MAX_PHASE2_ITERATIONS=7` - Phase 2 max iterations
- `MIN_EVIDENCE_PER_DIRECTION=20` - Minimum evidence per research direction
- `SUBGRAPH_MODEL` - Model for research subgraph (flash model for cost efficiency)

## Prompts

All agent prompts are in `config/prompts/`:
- `global_principles.txt` - shared rules (evidence grading, citation format, safety-first)
- `{agent}_prompt.txt` - role-specific instructions

Evidence grading (CIViC Evidence Level):
- A: Validated - supported by multiple independent studies or meta-analyses
- B: Clinical - from clinical trials or large-scale clinical studies
- C: Case Study - from case reports or small case series
- D: Preclinical - from cell lines, animal models, etc.
- E: Inferential - indirect evidence or based on biological principles

CIViC Evidence Types (Clinical Significance):
- Predictive: Predicts response to a treatment
- Diagnostic: Used for disease diagnosis
- Prognostic: Related to disease prognosis
- Predisposing: Related to cancer risk
- Oncogenic: Variant's oncogenic function

Citation format: `[PMID: 12345678](url)` or `[NCT04123456](url)`

## Key Patterns

1. **State updates**: Nodes return `Dict[str, Any]` that gets merged into `MtbState`
2. **Tool invocation**: Agents can call tools during generation; results feed back into conversation
3. **Retry logic**: If format validation fails, workflow loops back to Chair node (max 2 times)
4. **Reference flow**: Upstream agents generate `*_references` arrays; Chair merges all into `chair_final_references`
5. **Logging**: All logs go to `logs/mtb.log` via Loguru
6. **Report saving**: Each agent saves `{n}_{agent}_report.md` to the run folder
7. **No truncation**: Do NOT truncate strings (`[:N]`) or limit list sizes (`[:N]`) in evidence flow, reports, or prompt construction for the purpose of saving tokens or context length. All evidence, entity lists, observations, and reasoning content must be passed in full. Truncation is only acceptable in logger output.
