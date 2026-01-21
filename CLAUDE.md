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
PDF Input → PDF Parser
                ↓
    ┌───────────┼───────────┐
    ↓           ↓           ↓
Pathologist  Geneticist  Recruiter   ← Run in PARALLEL (subgraph)
    └───────────┼───────────┘
                ↓ (fan-in, all complete)
           Oncologist
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
- **Subgraph**: [src/graph/mtb_subgraph.py](src/graph/mtb_subgraph.py) - parallel execution of 3 analysis agents
- **Nodes**: [src/graph/nodes.py](src/graph/nodes.py) - each node calls an agent and updates state
- **Edges**: [src/graph/edges.py](src/graph/edges.py) - conditional logic for retry decisions

### Agent Architecture

Agents inherit from `BaseAgent` in [src/agents/base_agent.py](src/agents/base_agent.py):
- Direct OpenRouter API calls via `requests` (not OpenAI SDK)
- System prompt = global_principles.txt + role-specific prompt
- Support for multi-turn tool calling (up to 5 iterations)
- Reference management with `ReferenceManager` class

Five specialist agents in `src/agents/`:

| Agent | Role | Tools | Temp |
|-------|------|-------|------|
| **Pathologist** | Pathology/imaging analysis | PubMed, cBioPortal | 0.3 |
| **Geneticist** | Molecular profile analysis | CIViC, ClinVar, cBioPortal, PubMed | 0.2 |
| **Recruiter** | Clinical trial matching | ClinicalTrials.gov, NCCN, PubMed | 0.2 |
| **Oncologist** | Treatment planning, safety | NCCN, FDA Label, RxNorm, PubMed | 0.2 |
| **Chair** | Final synthesis (12 modules) | NCCN, FDA Label, PubMed | 0.3 |

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

## Prompts

All agent prompts are in `config/prompts/`:
- `global_principles.txt` - shared rules (evidence grading, citation format, safety-first)
- `{agent}_prompt.txt` - role-specific instructions

Evidence grading: A (Phase III RCT), B (Phase I-II), C (Retrospective), D (Preclinical)

Citation format: `[PMID: 12345678](url)` or `[NCT04123456](url)`

## Key Patterns

1. **State updates**: Nodes return `Dict[str, Any]` that gets merged into `MtbState`
2. **Tool invocation**: Agents can call tools during generation; results feed back into conversation
3. **Retry logic**: If format validation fails, workflow loops back to Chair node (max 2 times)
4. **Reference flow**: Upstream agents generate `*_references` arrays; Chair merges all into `chair_final_references`
5. **Logging**: All logs go to `logs/mtb.log` via Loguru
6. **Report saving**: Each agent saves `{n}_{agent}_report.md` to the run folder
