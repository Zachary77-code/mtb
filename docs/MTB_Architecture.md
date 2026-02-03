# MTB 系统技术文档

## 目录

1. [系统概述](#1-系统概述)
2. [工作流管道](#2-工作流管道)
3. [状态管理 (MtbState)](#3-状态管理-mtbstate)
4. [Agent 架构](#4-agent-架构)
5. [Research Subgraph (深度研究循环)](#5-research-subgraph-深度研究循环)
6. [Evidence Graph (证据图)](#6-evidence-graph-证据图)
7. [Research Plan (研究计划)](#7-research-plan-研究计划)
8. [外部 API 工具](#8-外部-api-工具)
9. [报告验证](#9-报告验证)
10. [HTML 渲染](#10-html-渲染)
11. [配置参数](#11-配置参数)
12. [日志与监控](#12-日志与监控)
13. [API 参考](#13-api-参考)

---

## 1. 系统概述

### 1.1 项目目标

MTB (Virtual Molecular Tumor Board) 是一个基于 LangGraph 的多智能体系统，用于处理患者病历 PDF 文件，通过 6 个专业 AI Agent 协作，生成包含 12 个标准模块的结构化临床报告。

### 1.2 高层架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           MTB 系统架构                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────┐    ┌───────────┐    ┌──────────────────────────────────┐  │
│  │  PDF    │───▶│ PDF Parser │───▶│           PlanAgent              │  │
│  │  输入   │    │           │    │  (研究计划 + EvidenceGraph 初始化)  │  │
│  └─────────┘    └───────────┘    └──────────────┬───────────────────┘  │
│                                                  │                      │
│                                                  ▼                      │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                    Research Subgraph                               │ │
│  │  ┌─────────────────────────────────────────────────────────────┐  │ │
│  │  │ Phase 1: 并行研究 (最多 7 次迭代)                            │  │ │
│  │  │  ┌────────────┐ ┌────────────┐ ┌────────────┐               │  │ │
│  │  │  │Pathologist │ │ Geneticist │ │  Recruiter │  ←── BFRS/DFRS│  │ │
│  │  │  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘               │  │ │
│  │  │        └──────────────┼──────────────┘                      │  │ │
│  │  │                       ▼                                      │  │ │
│  │  │              ┌─────────────────┐                             │  │ │
│  │  │              │ EvidenceGraph   │ ← 更新证据图                │  │ │
│  │  │              └────────┬────────┘                             │  │ │
│  │  │                       ▼                                      │  │ │
│  │  │       PlanAgent.evaluate_and_update() → 收敛判断             │  │ │
│  │  └─────────────────────────────────────────────────────────────┘  │ │
│  │                          │ 收敛                                    │ │
│  │                          ▼                                        │ │
│  │  ┌─────────────────────────────────────────────────────────────┐  │ │
│  │  │ Phase 2: Oncologist 独立研究 (最多 7 次迭代)                 │  │ │
│  │  │                   ┌────────────┐                             │  │ │
│  │  │                   │ Oncologist │ ←── BFRS/DFRS               │  │ │
│  │  │                   └─────┬──────┘                             │  │ │
│  │  │                         ▼                                    │  │ │
│  │  │              ┌─────────────────┐                             │  │ │
│  │  │              │ EvidenceGraph   │ ← 更新证据图                │  │ │
│  │  │              └────────┬────────┘                             │  │ │
│  │  │                       ▼                                      │  │ │
│  │  │       PlanAgent.evaluate_and_update() → 收敛判断             │  │ │
│  │  └─────────────────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                  │                                      │
│                                  ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         ChairAgent                               │   │
│  │         (接收 EvidenceGraph + 4 份 Agent 报告 → 12 模块报告)      │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                  │                                      │
│                                  ▼                                      │
│  ┌────────────────┐    ┌────────────────┐    ┌────────────────┐        │
│  │  格式验证      │───▶│  Chair 重试    │───▶│  HTML 生成     │        │
│  │ (12 模块检查)  │    │  (最多 2 次)   │    │                │        │
│  └────────────────┘    └────────────────┘    └────────────────┘        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.3 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 工作流编排 | LangGraph 1.0.6 |  |
| LLM 调用 | OpenRouter API |  |
| 向量数据库 | ChromaDB | NCCN 指南 RAG |
| HTML 渲染 | Jinja2 | 自定义模板 |
| 证据架构 | Entity-Edge-Observation | 基于 DeepEvidence 论文 |
| 日志 | Loguru | 结构化日志 |

### 1.4 关键文件路径

```
MTB/
├── main.py                          # 入口文件
├── config/
│   ├── settings.py                  # 全局配置
│   └── prompts/                     # Agent 提示词
├── src/
│   ├── agents/
│   │   ├── base_agent.py            # Agent 基类
│   │   ├── research_mixin.py        # BFRS/DFRS 研究能力
│   │   ├── plan_agent.py            # 研究计划 + 收敛评估
│   │   ├── pathologist.py
│   │   ├── geneticist.py
│   │   ├── recruiter.py
│   │   ├── oncologist.py
│   │   └── chair.py
│   ├── graph/
│   │   ├── state_graph.py           # 主工作流
│   │   ├── research_subgraph.py     # 两阶段研究循环
│   │   ├── nodes.py                 # 节点实现
│   │   └── edges.py                 # 条件边逻辑
│   ├── models/
│   │   ├── state.py                 # MtbState 定义
│   │   ├── evidence_graph.py        # 证据图
│   │   └── research_plan.py         # 研究计划
│   ├── tools/                       # 外部 API 工具
│   ├── validators/
│   │   └── format_checker.py        # 格式验证
│   └── renderers/
│       └── html_generator.py        # HTML 生成
└── logs/
    └── mtb.log                      # 日志文件
```

---

## 2. 工作流管道

### 2.1 完整节点序列

```
INPUT (raw PDF text)
        │
        ▼
┌───────────────────┐
│  pdf_parser_node  │ ─── 提取 PDF 文本，创建运行目录
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  plan_agent_node  │ ─── 生成研究计划，初始化空 EvidenceGraph
└─────────┬─────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Research Subgraph                               │
│                                                                      │
│  ┌────────────────── Phase 1 Loop ──────────────────┐               │
│  │                (最多 7 次迭代)                    │               │
│  │                                                   │               │
│  │  [phase1_router] ─── 条件发送到各 Agent           │               │
│  │       │                                           │               │
│  │       ├──▶ [phase1_pathologist] ──┐               │               │
│  │       ├──▶ [phase1_geneticist]  ──┼──▶ [phase1_aggregator]       │
│  │       └──▶ [phase1_recruiter]  ───┘               │               │
│  │                                    │              │               │
│  │                                    ▼              │               │
│  │                    [plan_agent_evaluate_phase1]   │               │
│  │                          (收敛检查)               │               │
│  │                              │                    │               │
│  │                              ▼                    │               │
│  │                    [phase1_convergence_check]     │               │
│  │                   (条件边分支)                    │               │
│  │          continue ↺ /              \ converged    │               │
│  │           [router]                   │            │               │
│  └──────────────────────────────────────┘            │               │
│                              │                        │               │
│                              ▼                        │               │
│              [generate_phase1_reports]                │               │
│         (合成 P/G/R 领域报告 → 保存文件)              │               │
│                              │                        │               │
│                              ▼                        │               │
│              [phase2_plan_init]                       │               │
│         (生成 Oncologist 研究方向)                    │               │
│                              │                        │               │
│  ┌────────────────── Phase 2 Loop ──────────────────┐│               │
│  │                (最多 7 次迭代)                    ││               │
│  │                                                   ││               │
│  │  [phase2_oncologist] ─── 接收 P1 专家报告         ││               │
│  │        │                                          ││               │
│  │        ▼                                          ││               │
│  │  [plan_agent_evaluate_phase2] (收敛检查)          ││               │
│  │        │                                          ││               │
│  │        ▼                                          ││               │
│  │  [phase2_convergence_check] (条件边分支)          ││               │
│  │  continue ↺ /         \ converged                 ││               │
│  └───────────────────────────────────────────────────┘│               │
│                              │                        │               │
│                              ▼                        │               │
│              [generate_phase2_reports]                │               │
│         (合成 Oncologist 报告)                        │               │
│                              │                        │               │
│                              ▼                        │               │
│              [generate_agent_reports]                 │               │
│         (提取引用、试验信息、进度报告)                │               │
│                              │                        │               │
│                           [END]                       │               │
└─────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌───────────────────┐
│    chair_node     │ ─── 整合所有报告 + EvidenceGraph → 12 模块报告
└─────────┬─────────┘
          │
          ▼
┌─────────────────────────┐
│ format_verification_node │ ─── 验证 12 个必需模块
└─────────┬───────────────┘
          │
          ▼
    ┌─────────────┐
    │ should_retry │
    │   _chair    │
    └──────┬──────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
[regenerate]  [proceed]
    │             │
    ▼             ▼
┌────────────┐  ┌─────────────────────┐
│chair_retry │  │webpage_generator_node│
│   _node    │  │                     │
└─────┬──────┘  └──────────┬──────────┘
      │                    │
      └──────▶ verify ◀────┘
              format
              (最多 2 次)
                           │
                           ▼
                    OUTPUT (HTML Report)
```

### 2.2 主工作流 (state_graph.py)

主工作流定义在 `src/graph/state_graph.py`，包含 7 个节点：

| 节点 | 函数 | 职责 |
|------|------|------|
| `pdf_parser` | `pdf_parser_node()` | 提取 PDF 文本，创建 `run_folder` |
| `plan_agent` | `plan_agent_node()` | 生成研究计划，初始化空 EvidenceGraph |
| `research_analysis` | `create_research_subgraph()` | 两阶段研究子图 |
| `chair` | `chair_node()` | 整合报告生成 12 模块 |
| `verify_format` | `format_verification_node()` | 验证必需模块 |
| `chair_retry` | `chair_retry_node()` | 重新生成失败的报告 |
| `generate_html` | `webpage_generator_node()` | 生成 HTML 文件 |

### 2.3 条件边逻辑 (edges.py)

#### should_retry_chair 决策逻辑

```python
def should_retry_chair(state: MtbState) -> str:
    if state.get("is_compliant", False):
        return "proceed"  # 验证通过，继续生成 HTML

    validation_iteration = state.get("validation_iteration", 0)
    if validation_iteration >= MAX_RETRY_ITERATIONS:  # 默认 2
        logger.warning("达到最大重试次数，强制继续")
        return "proceed"

    return "regenerate"  # 重新生成报告
```

### 2.4 阶段转换

#### Phase 1 → Phase 2 转换条件

1. **PlanAgent 评估**: `plan_agent_evaluate_phase1()` 分析证据质量
2. **收敛判断**: 所有研究方向达到 80% 完成度且有高质量证据 (A/B 级)
3. **报告生成**: `generate_phase1_reports()` 保存 3 份领域报告
4. **Phase 2 初始化**: `phase2_plan_init()` 生成 Oncologist 研究方向

#### Phase 2 → Chair 转换条件

1. **PlanAgent 评估**: `plan_agent_evaluate_phase2()` 分析 Oncologist 证据
2. **收敛判断**: Oncologist 研究方向达到收敛标准
3. **报告生成**: `generate_phase2_reports()` 保存 Oncologist 报告
4. **信息提取**: `generate_agent_reports()` 提取引用和试验信息

---

## 3. 状态管理 (MtbState)

### 3.1 状态定义

`MtbState` 是一个 TypedDict，定义在 `src/models/state.py`，包含 40+ 字段。

### 3.2 字段列表 (按阶段组织)

#### 输入阶段

| 字段 | 类型 | 说明 |
|------|------|------|
| `input_text` | `str` | 原始 PDF 文本 |

#### 解析阶段

| 字段 | 类型 | 说明 |
|------|------|------|
| `raw_pdf_text` | `str` | 提取的完整文本 |
| `run_folder` | `str` | 运行目录路径 |

#### 研究循环阶段 (核心 DeepEvidence 字段)

| 字段 | 类型 | 说明 |
|------|------|------|
| `research_plan` | `Annotated[Dict, merge_research_plans]` | 结构化研究方向 |
| `research_mode` | `str` | 当前研究模式 |
| `evidence_graph` | `Annotated[Dict, merge_evidence_graphs]` | 全局证据图 |

#### Phase 1 状态

| 字段 | 类型 | 说明 |
|------|------|------|
| `phase1_iteration` | `int` | 当前迭代次数 (0-7) |
| `phase1_new_findings` | `int` | 最近迭代的证据数量 |
| `pathologist_converged` | `bool` | Pathologist 收敛状态 |
| `geneticist_converged` | `bool` | Geneticist 收敛状态 |
| `recruiter_converged` | `bool` | Recruiter 收敛状态 |
| `phase1_all_converged` | `bool` | 三个 Agent 全部收敛 |
| `phase1_decision` | `str` | "continue" 或 "converged" |
| `pathologist_research_result` | `Dict` | Pathologist 迭代结果 |
| `geneticist_research_result` | `Dict` | Geneticist 迭代结果 |
| `recruiter_research_result` | `Dict` | Recruiter 迭代结果 |
| `pathologist_report` | `str` | Phase1 合成报告 (Markdown) |
| `geneticist_report` | `str` | Phase1 合成报告 |
| `recruiter_report` | `str` | Phase1 合成报告 |
| `pathologist_references` | `List[Dict]` | 引用元数据 |
| `geneticist_references` | `List[Dict]` | 引用元数据 |
| `recruiter_trials` | `List[Dict]` | 临床试验详情 |

#### Phase 2 状态

| 字段 | 类型 | 说明 |
|------|------|------|
| `phase2_iteration` | `int` | 当前迭代次数 (0-7) |
| `phase2_new_findings` | `int` | 最近迭代的证据数量 |
| `phase2_decision` | `str` | "continue" 或 "converged" |
| `oncologist_research_result` | `Dict` | Oncologist 迭代结果 |
| `oncologist_plan` | `str` | Phase2 合成报告 |
| `oncologist_safety_warnings` | `List[str]` | 安全警告 |

#### 收敛与历史

| 字段 | 类型 | 说明 |
|------|------|------|
| `research_converged` | `bool` | 整体研究是否完成 |
| `plan_agent_evaluation` | `Dict` | PlanAgent 最新评估 |
| `iteration_history` | `List[Dict]` | 每次迭代的详细记录 |
| `research_progress_report` | `str` | 迭代进度摘要 |

#### 合成阶段

| 字段 | 类型 | 说明 |
|------|------|------|
| `chair_synthesis` | `str` | 最终整合报告 (12 模块) |
| `chair_final_references` | `List[Dict]` | 合并去重的引用 |

#### 验证阶段

| 字段 | 类型 | 说明 |
|------|------|------|
| `is_compliant` | `bool` | 是否通过 12 模块验证 |
| `missing_sections` | `List[str]` | 缺失的模块 |
| `validation_iteration` | `int` | 重试次数 (0-2) |

#### 输出阶段

| 字段 | 类型 | 说明 |
|------|------|------|
| `final_html` | `str` | 生成的 HTML 内容 |
| `output_path` | `str` | HTML 文件路径 |

#### 元数据

| 字段 | 类型 | 说明 |
|------|------|------|
| `workflow_errors` | `List[str]` | 错误日志 |
| `execution_time` | `float` | 总执行时间 (秒) |

### 3.3 状态合并器 (Reducers)

为支持并行 Agent 更新同一状态字段，使用 `Annotated` 类型声明自定义合并函数：

#### merge_evidence_graphs

```python
def merge_evidence_graphs(left: Dict, right: Dict) -> Dict:
    """合并两个证据图，支持并行 Agent 更新"""
    # 实体合并: 按 canonical_id 去重，合并 observations
    for canonical_id, entity in right["entities"].items():
        if canonical_id in left["entities"]:
            # 合并 observations (去重)
            existing_obs_ids = {o["id"] for o in left["entities"][canonical_id]["observations"]}
            for obs in entity["observations"]:
                if obs["id"] not in existing_obs_ids:
                    left["entities"][canonical_id]["observations"].append(obs)
        else:
            left["entities"][canonical_id] = entity

    # 边合并: 按 (source_id, target_id, predicate) 去重
    for edge_key, edge in right["edges"].items():
        if edge_key in left["edges"]:
            # 更新 confidence 为最大值
            left["edges"][edge_key]["confidence"] = max(
                left["edges"][edge_key]["confidence"],
                edge["confidence"]
            )
            # 合并 observations
            # ...
        else:
            left["edges"][edge_key] = edge

    return left
```

#### merge_research_plans

```python
def merge_research_plans(left: Dict, right: Dict) -> Dict:
    """合并研究计划，支持并发方向状态更新"""
    # 方向按 ID 合并，right 覆盖 left
    left_dirs = {d["id"]: d for d in left.get("directions", [])}
    for direction in right.get("directions", []):
        left_dirs[direction["id"]] = direction

    left["directions"] = list(left_dirs.values())
    return left
```

### 3.4 节点间状态流

| 节点 | 输入字段 | 输出字段 |
|------|---------|---------|
| pdf_parser | `input_text` | `raw_pdf_text`, `run_folder` |
| plan_agent | `raw_pdf_text` | `research_plan`, `evidence_graph`, `research_mode`, `phase*_iteration` |
| phase1_* agents | `phase1_iteration`, `research_plan`, `evidence_graph` | `*_research_result`, `evidence_graph`, `research_plan` |
| phase1_aggregator | `*_research_result` | `phase1_iteration++`, `iteration_history` |
| phase1_plan_eval | `evidence_graph`, `research_plan` | `phase1_decision`, `*_converged`, `plan_agent_evaluation` |
| generate_phase1_reports | `evidence_graph`, `raw_pdf_text` | `pathologist_report`, `geneticist_report`, `recruiter_report` |
| phase2_plan_init | `*_report`, `evidence_graph` | `research_plan` (更新 P2_* 方向) |
| phase2_oncologist | `phase2_iteration`, `research_plan`, `evidence_graph`, `*_report` | `oncologist_research_result`, `evidence_graph`, `phase2_iteration++` |
| phase2_plan_eval | `evidence_graph`, `research_plan` | `phase2_decision`, `plan_agent_evaluation` |
| generate_phase2_reports | `evidence_graph`, `*_report`, `raw_pdf_text` | `oncologist_plan` |
| generate_agent_reports | `iteration_history`, `evidence_graph` | `recruiter_trials`, `oncologist_safety_warnings`, `research_progress_report` |
| chair | `raw_pdf_text`, `*_report`, `evidence_graph` | `chair_synthesis`, `chair_final_references` |
| verify_format | `chair_synthesis` | `is_compliant`, `missing_sections`, `validation_iteration` |
| webpage_generator | `chair_synthesis`, `chair_final_references`, `run_folder` | `output_path`, `final_html` |

---

## 4. Agent 架构

### 4.1 类层次结构

```
BaseAgent
├── PathologistAgent
├── GeneticistAgent
├── RecruiterAgent
├── OncologistAgent
├── ChairAgent
└── PlanAgent

ResearchMixin (混入类)
├── ResearchPathologist (BaseAgent + ResearchMixin)
├── ResearchGeneticist (BaseAgent + ResearchMixin)
├── ResearchRecruiter (BaseAgent + ResearchMixin)
└── ResearchOncologist (BaseAgent + ResearchMixin)
```

### 4.2 Agent 角色表

| Agent | 角色 | 可用工具 | 温度 | 模型 |
|-------|------|---------|------|------|
| **PlanAgent** | 研究计划生成 + 收敛评估 | - | 0.3 | ORCHESTRATOR_MODEL |
| **Pathologist** | 病理/影像分析 | PubMed, cBioPortal | 0.3 | SUBGRAPH_MODEL |
| **Geneticist** | 分子特征分析 | CIViC, ClinVar, cBioPortal, PubMed | 0.2 | SUBGRAPH_MODEL |
| **Recruiter** | 临床试验匹配 | ClinicalTrials.gov, NCCN, PubMed | 0.2 | SUBGRAPH_MODEL |
| **Oncologist** | 治疗方案制定 | NCCN, FDA Label, RxNorm, PubMed | 0.2 | SUBGRAPH_MODEL |
| **Chair** | 汇总整合 (12 模块) | NCCN, FDA Label, PubMed | 0.3 | ORCHESTRATOR_MODEL |

### 4.3 BaseAgent 核心实现

```python
class BaseAgent:
    def __init__(self, role: str, tools: List[BaseTool] = None):
        self.role = role
        self.model = OPENROUTER_MODEL
        self.temperature = AGENT_TEMPERATURE
        self.tools = tools or []
        self.tool_registry = {tool.name: tool for tool in self.tools}
        self.tool_call_history = []
        self.reference_manager = ReferenceManager()
        self.system_prompt = self._build_system_prompt()

    def invoke(self, user_message: str, context: str = "") -> Dict:
        """主调用方法"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self._format_user_message(user_message, context)}
        ]

        response = self._call_api(messages, include_tools=True)

        if response.get("tool_calls"):
            return self._handle_tool_calls(messages, response, iteration=0)

        return {
            "output": response.get("content", ""),
            "references": self._extract_references(response.get("content", ""))
        }

    def _handle_tool_calls(self, messages: List, response: Dict, iteration: int) -> Dict:
        """处理工具调用 (最多 5 次迭代)"""
        if iteration >= 5:
            return {"output": response.get("content", ""), "references": []}

        # 添加 assistant 消息
        messages.append({
            "role": "assistant",
            "content": response.get("content", ""),
            "tool_calls": response.get("tool_calls", [])
        })

        # 执行每个工具调用
        for tool_call in response.get("tool_calls", []):
            function_name = tool_call["function"]["name"]
            arguments = json.loads(tool_call["function"]["arguments"])

            tool = self.tool_registry.get(function_name)
            if tool:
                result = tool.invoke(**arguments)
                self.tool_call_history.append(ToolCallRecord(
                    tool_name=function_name,
                    arguments=arguments,
                    result=result,
                    reasoning=response.get("content", "")
                ))
            else:
                result = f"Unknown tool: {function_name}"

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": result
            })

        # 继续对话
        next_response = self._call_api(messages, include_tools=True)

        if next_response.get("tool_calls"):
            return self._handle_tool_calls(messages, next_response, iteration + 1)

        return {
            "output": next_response.get("content", ""),
            "references": self._extract_references(next_response.get("content", ""))
        }
```

### 4.4 ResearchMixin 研究能力

`ResearchMixin` 为 Agent 添加 BFRS/DFRS 研究迭代能力：

```python
class ResearchMixin:
    def research_iterate(
        self,
        research_plan: Dict,
        evidence_graph: Dict,
        raw_pdf_text: str,
        iteration: int
    ) -> Dict:
        """执行一次研究迭代"""

        # 1. 按 preferred_mode 分离研究方向
        bfrs_directions = [d for d in directions if d["preferred_mode"] == "breadth_first"]
        dfrs_directions = [d for d in directions if d["preferred_mode"] == "depth_first"]
        skip_directions = [d for d in directions if d["preferred_mode"] == "skip"]

        # 2. 执行 BFRS 研究 (如果有)
        if bfrs_directions:
            bfrs_prompt = self._build_bfrs_prompt(bfrs_directions, evidence_graph, iteration)
            bfrs_response = self.invoke(bfrs_prompt)
            bfrs_findings = self._parse_research_output(bfrs_response)

        # 3. 执行 DFRS 研究 (如果有)
        if dfrs_directions:
            dfrs_prompt = self._build_dfrs_prompt(dfrs_directions, evidence_graph, iteration)
            dfrs_response = self.invoke(dfrs_prompt)
            dfrs_findings = self._parse_research_output(dfrs_response)

        # 4. 更新证据图
        new_entity_ids = self._update_evidence_graph(
            evidence_graph,
            bfrs_findings + dfrs_findings
        )

        # 5. 返回迭代结果
        return {
            "evidence_graph": evidence_graph,
            "research_plan": updated_plan,
            "new_entity_ids": new_entity_ids,
            "direction_updates": direction_status_updates,
            "research_complete": all_complete,
            "needs_deep_research": needs_deep_items,
            "summary": combined_summary
        }
```

### 4.5 引用管理

`ReferenceManager` 类负责引用的收集和去重：

```python
class ReferenceManager:
    def __init__(self):
        self.references = {}  # {id: reference_dict}

    def add_reference(self, ref_type: str, ref_id: str, url: str = None):
        """添加引用 (自动去重)"""
        key = f"{ref_type}:{ref_id}"
        if key not in self.references:
            self.references[key] = {
                "type": ref_type,
                "id": ref_id,
                "url": url or self._generate_url(ref_type, ref_id)
            }

    def _extract_references(self, text: str) -> List[Dict]:
        """从文本中提取引用"""
        patterns = [
            r'\[PMID:\s*(\d+)\]',           # [PMID: 12345678]
            r'\[NCT(\d+)\]',                # [NCT04123456]
            r'\[(NCT\d+)\]',                # [NCT04123456]
        ]
        # ...
```

---

## 5. Research Subgraph (深度研究循环)

### 5.1 两阶段架构

Research Subgraph 实现了基于 DeepEvidence 论文的两阶段研究循环：

#### Phase 1: 并行研究

- **参与 Agent**: Pathologist, Geneticist, Recruiter
- **执行方式**: 并行 (通过 `Send()` 分发)
- **最大迭代**: 7 次
- **目标**: 收集广泛的初步证据

#### Phase 2: Oncologist 独立研究

- **参与 Agent**: Oncologist
- **执行方式**: 串行
- **最大迭代**: 7 次
- **目标**: 基于 Phase 1 结果深入治疗方案研究

### 5.2 BFRS vs DFRS 研究模式

| 模式 | 全称 | 工具调用次数 | 目的 |
|------|------|-------------|------|
| **BFRS** | Breadth-First Research | 1-2 次/方向 | 收集广泛初步证据 |
| **DFRS** | Depth-First Research | 3-5 次连续 | 深入高优先级发现 |

#### BFRS 提示词结构

```
## 研究模式: BFRS (广度优先研究)
- 迭代轮次: {iteration+1}/{max_iterations}
- 现有实体: {entity_count}
- 现有边: {edge_count}

### 分配研究方向
[列出所有 BFRS 方向及其查询建议]

### BFRS 执行指南
1. 对每个方向执行 1-2 次工具调用
2. 收集广泛初步证据，不深入追踪
3. 标记方向状态: pending/completed
4. 标记需要深入研究的发现

### 输出格式 (JSON)
{
    "summary": "摘要",
    "findings": [
        {
            "direction_id": "D1",
            "content": "完整发现",
            "evidence_type": "molecular|clinical|literature|trial|guideline|drug|pathology|imaging",
            "grade": "A|B|C|D|E",
            "civic_type": "predictive|diagnostic|prognostic|predisposing|oncogenic",
            "source_tool": "工具名",
            "gene": "基因名",
            "variant": "变异名",
            "drug": "药物名",
            "pmid": "PubMed ID",
            "nct_id": "NCT ID"
        }
    ],
    "direction_updates": {"D1": "pending|completed"},
    "needs_deep_research": [{"finding": "...", "reason": "..."}]
}
```

#### DFRS 提示词结构

```
## 研究模式: DFRS (深度优先研究)
- 迭代轮次: {iteration+1}/{max_iterations}
- 现有实体: {entity_count}

### 需要深入研究的项目
[深度研究项列表及原因]

### DFRS 执行指南
1. 针对高优先级发现执行多跳推理
2. 追踪引用链、相关研究、机制解释
3. 最多执行 3-5 次连续工具调用
4. 寻找更高级别证据支持

### 输出格式 (JSON)
{
    "summary": "深入研究摘要",
    "findings": [
        {
            "direction_id": "D1",
            "content": "深入发现",
            "depth_chain": ["引用1", "引用2", "推理步骤"],
            ...
        }
    ],
    "direction_updates": {"D1": "pending|completed"},
    "needs_deep_research": []
}
```

### 5.3 收敛评估 (PlanAgent)

PlanAgent 统一负责收敛判断，通过 `evaluate_and_update()` 方法：

#### 证据质量权重

```python
GRADE_WEIGHTS = {
    "A": 5.0,    # Validated - 多项独立研究/荟萃分析
    "B": 3.0,    # Clinical - 临床试验/大规模临床研究
    "C": 2.0,    # Case Study - 病例报告/小样本
    "D": 1.5,    # Preclinical - 细胞系、动物模型
    "E": 1.0,    # Inferential - 间接证据
}

TARGET_COMPLETENESS_SCORE = 10.0  # 相当于 2 个 A 级或 10 个 E 级
```

#### 每方向统计

```python
stats[direction_id] = {
    "evidence_count": len(obs_ids),  # 证据数 = 去重后的 observation 数量
    "entity_count": len(entity_ids), # 实体数 = entity_ids 数量
    "grade_distribution": {"A": 1, "B": 2, "C": 0, "D": 1, "E": 1},
    "weighted_score": 12.0,      # 所有证据 GRADE_WEIGHTS 之和
    "completeness": 100.0,       # min(100, weighted_score/TARGET × 100)
    "has_high_quality": True,    # 是否有 A/B 级证据
    "low_quality_only": False,   # 是否只有 D/E 级证据
    "topic": "方向主题",
    "target_agent": "Geneticist",
    "priority": 1,
    "status": "pending"
}
```

#### 收敛阈值

```python
CONVERGENCE_COMPLETENESS_THRESHOLD = 80   # >= 80% = "completed"
CONTINUE_COMPLETENESS_THRESHOLD = 60      # < 60% = "continue research"
```

#### 决策逻辑

```python
if all_complete (所有方向 >= 80%) AND not has_low_quality_only:
    decision = "converged"
else:
    decision = "continue"

# 每方向模式分配
if completeness >= 80% + has_high_quality:
    preferred_mode = "skip"         # 无需更多研究
elif completeness < 60%:
    preferred_mode = "breadth_first" # 收集更多种类
else:  # 60-80% 或 low_quality_only
    preferred_mode = "depth_first"   # 寻找 A/B 级证据
```

### 5.4 强制收敛

当达到最大迭代次数时强制收敛：

```python
if iteration >= MAX_PHASE1_ITERATIONS:  # 默认 7
    decision = "converged"
    reasoning = f"达到迭代上限 ({MAX_PHASE1_ITERATIONS})"
```

### 5.5 迭代历史记录

每次迭代记录完整信息：

```python
iteration_record = {
    "phase": "PHASE1" | "PHASE2",
    "iteration": int,
    "timestamp": str,
    "agent_findings": {
        "AgentName": {
            "count": int,
            "entity_ids": [...]
        }
    },
    "total_new_findings": int,
    "convergence_check": {...},  # PlanAgent 评估结果
    "final_decision": "continue" | "converged"
}
```

---

## 6. Evidence Graph (证据图)

### 6.1 Entity-Edge-Observation 架构

基于 DeepEvidence 论文的实体中心化证据图架构：

```
发现: "吉非替尼改善 EGFR L858R NSCLC 患者生存期"
    │
    ▼ LLM 实体提取
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  Entities (实体):                                           │
│    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│    │ GENE:EGFR   │  │ EGFR_L858R  │  │DRUG:GEFITINIB│       │
│    └─────────────┘  └─────────────┘  └─────────────┘       │
│                           │                │                │
│  Edges (边):              │                │                │
│                           │   SENSITIZES   │                │
│                           └───────────────▶│                │
│                                            │                │
│                           DRUG:GEFITINIB ──┼── TREATS ──▶ DISEASE:NSCLC
│                                            │                │
│  Observation (观察):                        │                │
│    ┌────────────────────────────────────────────────────┐  │
│    │ "吉非替尼改善 OS (人类, Phase III, n=347)          │  │
│    │  [PMID:12345678]"                                  │  │
│    │                                                    │  │
│    │  Grade: A | Type: predictive | Agent: Geneticist  │  │
│    └────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Entity 类

#### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `id` | `str` | 唯一标识符 `{source}_{uuid8}` |
| `canonical_id` | `str` | 去重键 (如 `GENE:EGFR`) |
| `entity_type` | `EntityType` | 实体类型枚举 |
| `name` | `str` | 规范化名称 (大写) |
| `aliases` | `List[str]` | 别名列表 |
| `observations` | `List[Observation]` | 附加的观察 |
| `created_at` | `datetime` | 创建时间 |
| `updated_at` | `datetime` | 更新时间 |

#### 11 种实体类型

| 类型 | 代码 | 示例 | 用途 |
|------|------|------|------|
| GENE | `gene` | `GENE:EGFR` | 基因实体 |
| VARIANT | `variant` | `EGFR_L858R` | 基因变异 (格式: GENE_MUTATION) |
| DRUG | `drug` | `DRUG:OSIMERTINIB` | 药物实体 |
| DISEASE | `disease` | `DISEASE:NSCLC` | 疾病/癌症类型 |
| PATHWAY | `pathway` | `PATHWAY:EGFR_SIGNALING` | 信号通路 |
| BIOMARKER | `biomarker` | `BIOMARKER:PD-L1` | 生物标志物 |
| PAPER | `paper` | `PMID:12345678` | 文献引用 |
| TRIAL | `trial` | `NCT:NCT04487080` | 临床试验 |
| GUIDELINE | `guideline` | `NCCN:NSCLC_2024` | 临床指南 |
| REGIMEN | `regimen` | `REGIMEN:PLATINUM_DOUBLET` | 治疗方案 |
| FINDING | `finding` | `{source}_{uuid}` | 临床发现 |

#### 命名规则

- 所有实体名称规范化为大写
- 变异格式: `GENE_MUTATION` (如 `EGFR_L858R`)
- 文献格式: `PMID:xxxxx`
- 试验格式: `NCT:NCTxxxxxxxx`
- 其他格式: `TYPE:NAME` (如 `GENE:EGFR`, `DRUG:OSIMERTINIB`)

### 6.3 Edge 类

#### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `id` | `str` | 唯一标识符 `edge_{uuid8}` |
| `source_id` | `str` | 源实体 canonical_id |
| `target_id` | `str` | 目标实体 canonical_id |
| `predicate` | `Predicate` | 关系类型 |
| `observations` | `List[Observation]` | 关系的证据 |
| `confidence` | `float` | 置信度 0-1 |
| `conflict_group` | `str` | 可选的冲突标记 |

#### 25 种关系类型 (Predicate)

**分子机制 (7)**

| 类型 | 说明 |
|------|------|
| `ACTIVATES` | 基因 A 激活基因 B |
| `INHIBITS` | 基因 A 抑制基因 B |
| `BINDS` | 蛋白结合靶点 |
| `PHOSPHORYLATES` | 磷酸化 |
| `REGULATES` | 基因调控 |
| `AMPLIFIES` | 基因扩增 |
| `MUTATES_TO` | 耐药突变 |

**药物-疾病关系 (5)**

| 类型 | 说明 |
|------|------|
| `TREATS` | 药物治疗疾病 |
| `SENSITIZES` | 变异使对药物敏感 |
| `CAUSES_RESISTANCE` | 变异导致耐药 |
| `INTERACTS_WITH` | 药物相互作用 |
| `CONTRAINDICATED_FOR` | 药物禁忌 |

**证据关系 (4)**

| 类型 | 说明 |
|------|------|
| `SUPPORTS` | 证据支持声明 |
| `CONTRADICTS` | 证据反驳 |
| `CITES` | 文献引用发现 |
| `DERIVED_FROM` | 证据来源 |

**成员/注释关系 (4)**

| 类型 | 说明 |
|------|------|
| `MEMBER_OF` | 基因属于通路 |
| `EXPRESSED_IN` | 基因在组织中表达 |
| `ASSOCIATED_WITH` | 一般关联 |
| `BIOMARKER_FOR` | 生物标志物关系 |

**指南/试验关系 (3)**

| 类型 | 说明 |
|------|------|
| `RECOMMENDS` | 指南推荐 |
| `EVALUATES` | 试验评估药物 |
| `INCLUDES_ARM` | 试验包含治疗组 |

### 6.4 Observation 类

#### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `id` | `str` | 唯一标识符 `obs_{uuid8}` |
| `statement` | `str` | 事实陈述 (包含嵌入上下文) |
| `source_agent` | `str` | 收集该观察的 Agent |
| `source_tool` | `str` | 使用的工具 |
| `provenance` | `str` | 引用标识符 (PMID:xxx, NCT:xxx) |
| `source_url` | `str` | 来源完整 URL |
| `evidence_grade` | `EvidenceGrade` | CIViC 证据等级 |
| `civic_type` | `CivicEvidenceType` | CIViC 证据类型 |
| `iteration` | `int` | 收集时的迭代次数 |
| `created_at` | `datetime` | 创建时间 |

#### 证据等级 (CIViC 标准)

| 等级 | 名称 | 定义 |
|------|------|------|
| **A** | Validated | 多项独立研究或荟萃分析支持 |
| **B** | Clinical | 临床试验或大规模临床研究 |
| **C** | Case Study | 病例报告或小样本病例系列 |
| **D** | Preclinical | 细胞系、动物模型等 |
| **E** | Inferential | 间接证据或基于生物学原理推断 |

#### CIViC 证据类型

| 类型 | 说明 |
|------|------|
| **Predictive** | 预测治疗反应 |
| **Diagnostic** | 用于疾病诊断 |
| **Prognostic** | 与疾病预后相关 |
| **Predisposing** | 与癌症风险相关 |
| **Oncogenic** | 变异的致癌功能 |

### 6.5 EvidenceGraph 核心操作

#### 实体管理

```python
# 获取或创建实体 (通过 canonical_id 自动去重)
entity = graph.get_or_create_entity(
    canonical_id="GENE:EGFR",
    entity_type=EntityType.GENE,
    name="EGFR",
    source="civic",
    aliases=["ERBB1", "HER1"]
)

# 添加观察到实体
graph.add_observation_to_entity(entity.canonical_id, observation)

# 按名称查找实体 (支持模糊匹配)
entity = graph.find_entity_by_name("EGFR")

# 按类型获取实体
genes = graph.get_entities_by_type(EntityType.GENE)
```

#### 边管理

```python
# 添加边 (通过 source_id|target_id|predicate 自动去重)
edge_id = graph.add_edge(
    source_id="EGFR_L858R",
    target_id="DRUG:OSIMERTINIB",
    predicate=Predicate.SENSITIZES,
    observation=obs,
    confidence=0.95
)

# 按关系类型获取边
sensitizing_edges = graph.get_edges_by_predicate(Predicate.SENSITIZES)

# 获取连接的实体
connected = graph.get_connected_entities(
    "EGFR_L858R",
    predicate=Predicate.SENSITIZES,
    direction="out"  # "in", "out", "both"
)
```

#### 查询方法

```python
# 获取药物敏感性映射: {variant_id: [{drug, edge, grade}, ...]}
sensitivity_map = graph.get_drug_sensitivity_map()

# 获取治疗证据
treatment_evidence = graph.get_treatment_evidence(
    drug_canonical_id="DRUG:OSIMERTINIB",
    disease_canonical_id="DISEASE:NSCLC"
)

# 按 Agent 获取观察
pathologist_obs = graph.get_observations_by_agent("Pathologist")

# 获取统计摘要
summary = graph.summary()
# 返回: total_entities, total_edges, total_observations,
#       entities_by_type, edges_by_predicate, best_grades, conflicts_count
```

#### 序列化

```python
# 序列化为字典 (用于状态存储)
data = graph.to_dict()

# 从字典加载
graph = EvidenceGraph.from_dict(data)

# 生成 Mermaid 图
mermaid_diagram = graph.to_mermaid()
```

---

## 7. Research Plan (研究计划)

### 7.1 ResearchDirection 结构

```python
@dataclass
class ResearchDirection:
    id: str                          # 方向 ID (如 "D1")
    topic: str                       # 研究主题
    target_agent: str                # 负责的 Agent
    priority: int                    # 优先级 1-5
    queries: List[str]               # 建议的搜索查询
    status: str                      # "pending" | "in_progress" | "completed"
    completion_criteria: str         # 完成标准
    entity_ids: List[str]          # 收集的证据 ID
    target_modules: List[str]        # 目标模块 (如 ["分子特征", "治疗路线图"])
    iterations_spent: int            # 已用迭代次数
    last_iteration: int              # 最后迭代编号
    needs_deep_research: bool        # 是否需要 DFRS
    deep_research_findings: List[Dict]  # 深入研究发现
    preferred_mode: str              # "breadth_first" | "depth_first" | "skip"
    mode_reason: str                 # 模式选择原因
```

### 7.2 ResearchPlan 结构

```python
@dataclass
class ResearchPlan:
    id: str                          # 计划 ID
    case_summary: str                # 病例摘要
    key_entities: Dict[str, List[str]]  # 关键实体 {type: [names]}
    directions: List[ResearchDirection]  # 研究方向列表
    initial_mode: ResearchMode       # 初始研究模式
    created_at: datetime             # 创建时间
```

### 7.3 方向模式分配

PlanAgent 根据证据质量为每个方向分配模式：

| 条件 | 分配模式 | 原因 |
|------|---------|------|
| 完成度 ≥ 80% + 有 A/B 级 | `skip` | 无需更多研究 |
| 完成度 < 60% | `breadth_first` | 收集更多种类证据 |
| 完成度 60-80% 或只有 D/E 级 | `depth_first` | 寻找高质量证据 |

### 7.4 模块覆盖跟踪

研究计划跟踪 9 个需要证据覆盖的模块：

```python
COVERAGE_REQUIRED_MODULES = [
    "分子特征",
    "治疗史回顾",
    "药物/方案对比",
    "器官功能与剂量",
    "治疗路线图",
    "分子复查建议",
    "临床试验推荐",
    "局部治疗建议",
    "核心建议汇总",
]
```

排除的模块：
- `执行摘要` - Chair 合成
- `患者概况` - PDF 提取
- `参考文献` - 聚合

---

## 8. 外部 API 工具

### 8.1 工具基础架构

所有工具继承自 `BaseTool`：

```python
class BaseTool(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def invoke(self, **kwargs) -> str:
        """主调用方法"""
        return self._call_real_api(**kwargs)

    @abstractmethod
    def _call_real_api(self, **kwargs) -> Optional[str]:
        """子类实现的实际 API 调用"""
        pass

    def to_openai_function(self) -> Dict[str, Any]:
        """转换为 OpenAI 函数调用格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self._get_parameters_schema()
            }
        }
```

### 8.2 分子工具 (molecular_tools.py)

#### CIViCTool

| 属性 | 值 |
|------|---|
| 函数名 | `search_civic` |
| API | CIViC GraphQL API |
| 参数 | `gene`, `variant`, `cancer_type` |
| 返回 | 证据等级 (A-E), 治疗证据, 链接 |

#### ClinVarTool

| 属性 | 值 |
|------|---|
| 函数名 | `search_clinvar` |
| API | NCBI ClinVar |
| 参数 | `gene`, `variant` |
| 返回 | 致病性分类, 评审状态 (星级), 链接 |

#### cBioPortalTool

| 属性 | 值 |
|------|---|
| 函数名 | `search_cbioportal` |
| API | cBioPortal REST API |
| 参数 | `gene`, `variant`, `cancer_type` |
| 返回 | 突变计数, 各癌种频率, 高频突变 |

### 8.3 文献工具 (literature_tools.py)

#### PubMedTool

| 属性 | 值 |
|------|---|
| 函数名 | `search_pubmed` |
| API | NCBI PubMed |
| 参数 | `query`, `max_results` (默认 20) |
| 架构 | LLM-API-LLM 三明治架构 |

**LLM-API-LLM 架构**:

```
Phase 1: LLM 查询优化
    ├── 输入: 用户原始查询
    └── 输出: 优化的 PubMed 搜索词

Phase 2: 广泛 API 搜索
    ├── 搜索: 100 条结果
    └── 获取: 标题, 摘要, PMID, 作者, 期刊

Phase 3: LLM 筛选
    ├── 输入: 100 条结果 + 原始查询
    └── 输出: 最相关的 20 条 + 相关性评分
```

### 8.4 临床试验工具 (trial_tools.py)

#### ClinicalTrialsTool

| 属性 | 值 |
|------|---|
| 函数名 | `search_clinical_trials` |
| API | ClinicalTrials.gov API v2 |
| 参数 | `cancer_type`, `biomarker`, `intervention`, `location` (默认 "China"), `max_results` |
| 状态筛选 | 仅 RECRUITING |
| 返回 | NCT ID, 阶段, 入组, 申办方, 干预措施, 入排标准, 中国站点 |

### 8.5 指南工具 (guideline_tools.py)

#### NCCNTool

| 属性 | 值 |
|------|---|
| 函数名 | `search_nccn` |
| 后端 | 本地 PDF RAG (ChromaDB) |
| 参数 | `cancer_type`, `biomarker`, `line` (first-line, second-line 等) |
| 返回 | 从本地向量存储检索的指南推荐 |

#### FDALabelTool

| 属性 | 值 |
|------|---|
| 函数名 | `search_fda_labels` |
| API | openFDA API |
| 参数 | `drug_name` |
| 返回 | 适应症, 用法用量, 黑框警告, 警告, 禁忌, 相互作用, 不良反应 |

#### RxNormTool

| 属性 | 值 |
|------|---|
| 函数名 | `search_rxnorm` |
| API | NLM RxNorm (缺失数据回退到 FDA) |
| 参数 | `drug_name`, `check_interactions` (其他药物列表) |
| 返回 | 药物分类, 已知相互作用, 严重程度, 多药相互作用 |

### 8.6 工具-Agent 分配

| Agent | 可用工具 |
|-------|---------|
| Pathologist | PubMed, cBioPortal |
| Geneticist | CIViC, ClinVar, cBioPortal, PubMed |
| Recruiter | ClinicalTrials.gov, NCCN, PubMed |
| Oncologist | NCCN, FDA Label, RxNorm, PubMed |
| Chair | NCCN, FDA Label, PubMed |

---

## 9. 报告验证

### 9.1 12 个必需模块

```python
REQUIRED_SECTIONS = [
    "执行摘要",        # Executive Summary
    "患者概况",        # Patient Profile
    "分子特征",        # Molecular Profile
    "治疗史回顾",      # Treatment History
    "药物/方案对比",   # Regimen Comparison
    "器官功能与剂量",  # Organ Function & Dosing
    "治疗路线图",      # Treatment Roadmap
    "分子复查建议",    # Re-biopsy/Liquid Biopsy
    "临床试验推荐",    # Clinical Trials
    "局部治疗建议",    # Local Therapy
    "核心建议汇总",    # Core Recommendations
    "参考文献"         # References
]
```

### 9.2 多级验证策略

`FormatChecker._section_exists()` 使用多级匹配：

1. **精确匹配**: 直接字符串匹配
2. **Markdown 标题匹配**: 正则表达式匹配 `##`, `###`, `#` 标题
3. **别名匹配**: 英文/中文别名 (每个模块可配置)
4. **模糊匹配**: `SequenceMatcher` 相似度 > 0.8

### 9.3 重试机制

```
验证失败
    │
    ▼
validation_iteration < MAX_RETRY_ITERATIONS (2)?
    │
    ├── 是 → chair_retry_node → 重新生成报告
    │              │
    │              ▼
    │         verify_format (再次验证)
    │
    └── 否 → 强制继续 (带警告)
```

### 9.4 FormatChecker 使用

```python
checker = FormatChecker()

# 验证报告
is_compliant, missing_sections = checker.validate(report_text)

# 生成反馈
feedback = checker.generate_feedback(missing_sections)

# 检查引用
has_refs, ref_count = checker.check_references(report_text)
```

---

## 10. HTML 渲染

### 10.1 自定义块标记

#### 执行摘要块

```markdown
:::exec-summary
key1: value1
key2: value2
:::
```

渲染为带样式的结构化列表。

#### 治疗时间线块

```markdown
:::timeline
- type: neoadjuvant
  line: 1L
  date: 2023-01-15
  regimen: Platinum doublet
  response: PR
  note: Good tolerance
:::
```

渲染为垂直时间线，标记类别包括：
- `neoadjuvant`, `surgery`, `adjuvant`, `maint`, `pd`, `current`, `event`

响应徽章：
- `badge-success`: CR/PR/SD/TRG1/TRG2
- `badge-danger`: PD
- `badge-secondary`: NE

#### 治疗路线图块

```markdown
:::roadmap
- title: First-line Osimertinib
  status: current
  regimen: Osimertinib 80 mg QD
  actions:
    - Baseline CT scan
    - Cardiac evaluation
    - Liver function
:::
```

渲染为带状态颜色边框的卡片网格。

#### 内联引用链接

```markdown
[[ref:PMID28854312|Rosell et al|https://pubmed.ncbi.nlm.nih.gov/28854312/|Key study on EGFR L858R]]
```

渲染为带工具提示的可点击引用。

### 10.2 引用链接自动转换

```markdown
[PMID: 12345678] → https://pubmed.ncbi.nlm.nih.gov/12345678/
[NCT04123456] → https://clinicaltrials.gov/study/NCT04123456
[Evidence A/B/C/D] → 彩色证据徽章
```

### 10.3 证据等级样式

| 等级 | 背景色 | 文字颜色 |
|------|--------|---------|
| A | #dcfce7 (浅绿) | #166534 (深绿) |
| B | #dbeafe (浅蓝) | #1e40af (深蓝) |
| C | #fef3c7 (浅黄) | #92400e (深棕) |
| D | #fee2e2 (浅红) | #991b1b (深红) |

### 10.4 HTML 模板特性

- **响应式设计**: 支持桌面和移动端
- **配色方案**: 蓝白医疗主题
- **章节**: 页眉 (患者信息)、内容、页脚、警告
- **表格**: 自动样式 + 悬停效果
- **警告框**: 红色边框用于安全警告
- **信息框**: 蓝色边框用于信息提示
- **打印友好**: CSS 媒体查询优化

---

## 11. 配置参数

### 11.1 环境变量

#### OpenRouter API

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `OPENROUTER_API_KEY` | 是 | - | OpenRouter API 密钥 |
| `OPENROUTER_MODEL` | 否 | `google/gemini-3-pro-preview` | 默认 LLM 模型 |

#### NCBI API

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `NCBI_API_KEY` | 否 | 内置默认 | 提高 PubMed/ClinVar 速率限制至 10 req/sec |
| `NCBI_EMAIL` | 否 | `mtb-workflow@example.com` | NCBI API 联系邮箱 |

#### 嵌入配置 (DashScope)

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `DASHSCOPE_API_KEY` | 否 | - | 阿里云 DashScope 嵌入 API |
| `EMBEDDING_MODEL` | 否 | `text-embedding-v4` | 嵌入模型 |
| `EMBEDDING_DIMENSIONS` | 否 | `1024` | 嵌入向量维度 |

### 11.2 模型选择

| 参数 | 默认值 | 用途 | 使用者 |
|------|--------|------|--------|
| `SUBGRAPH_MODEL` | `google/gemini-3-flash-preview` | 研究 Agent (成本效率) | P, G, R, O |
| `ORCHESTRATOR_MODEL` | `google/gemini-3-pro-preview` | 协调 Agent (高能力) | PlanAgent, Chair |

### 11.3 研究循环参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `MAX_PHASE1_ITERATIONS` | 7 | Phase 1 最大迭代次数 |
| `MAX_PHASE2_ITERATIONS` | 7 | Phase 2 最大迭代次数 |
| `MIN_EVIDENCE_PER_DIRECTION` | 20 | 每方向最少证据数 |
| `MIN_EVIDENCE_NODES` | 10 | 全局最少证据实体数 |

### 11.4 Agent 行为参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `AGENT_TEMPERATURE` | 0.2 | LLM 生成温度 (0.0-1.0) |
| `AGENT_TIMEOUT` | 120 | API 调用超时 (秒) |
| `MAX_RETRY_ITERATIONS` | 2 | 格式验证最大重试次数 |

### 11.5 目录结构

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `REPORTS_DIR` | `{BASE_DIR}/reports` | 生成报告存储目录 |
| `PROMPTS_DIR` | `{BASE_DIR}/config/prompts` | Agent 提示词目录 |
| `LOGS_DIR` | `{BASE_DIR}/logs` | 日志文件目录 |
| `NCCN_VECTOR_DIR` | `~/.mtb/nccn_vectors` | ChromaDB 向量索引目录 |

---

## 12. 日志与监控

### 12.1 日志配置

- **输出**: `logs/mtb.log`
- **轮转**: 10MB 触发
- **保留**: 7 天
- **压缩**: zip

### 12.2 日志标签

| 标签 | 说明 |
|------|------|
| `[PHASE1]` / `[PHASE2]` | 研究循环迭代 |
| `[PHASE1_CONVERGENCE]` | 收敛检查详情 |
| `[EVIDENCE]` | 证据图统计 |
| `[AgentName]` | Agent 执行状态 |
| `[Tool:ToolName]` | 工具调用详情 |

### 12.3 辅助函数

```python
# 进度条
log_phase_progress(phase, iteration, max_iterations)
# 输出: [████░░] 4/7

# 证据统计
log_evidence_stats(evidence_graph)
# 输出: 实体类型分布, Agent 分布

# 收敛状态
log_convergence_status(evaluation)
# 输出: 收敛状态快照
```

### 12.4 监控中间过程

1. 实时查看 `logs/mtb.log`
2. 检查 `[EVIDENCE]` 标签了解证据收集进度
3. 检查 `[PHASE1_CONVERGENCE]` / `[PHASE2_CONVERGENCE]` 了解收敛决策

---

## 13. API 参考

### 13.1 EvidenceGraph

```python
from src.models.evidence_graph import EvidenceGraph, Entity, Edge, Observation

# 创建空图
graph = EvidenceGraph()

# 获取或创建实体
entity = graph.get_or_create_entity(
    canonical_id: str,
    entity_type: EntityType,
    name: str,
    source: str,
    aliases: List[str] = None
) -> Entity

# 添加观察到实体
graph.add_observation_to_entity(
    canonical_id: str,
    observation: Observation
) -> None

# 添加边
edge_id = graph.add_edge(
    source_id: str,
    target_id: str,
    predicate: Predicate,
    observation: Observation = None,
    confidence: float = 0.5
) -> str

# 查找实体
entity = graph.find_entity_by_name(name: str) -> Optional[Entity]

# 获取统计摘要
summary = graph.summary() -> Dict

# 序列化
data = graph.to_dict() -> Dict
graph = EvidenceGraph.from_dict(data: Dict) -> EvidenceGraph

# 生成 Mermaid 图
mermaid = graph.to_mermaid() -> str
```

### 13.2 ResearchPlan

```python
from src.models.research_plan import ResearchPlan, ResearchDirection

# 创建研究计划
plan = ResearchPlan(
    id: str,
    case_summary: str,
    key_entities: Dict[str, List[str]],
    directions: List[ResearchDirection],
    initial_mode: ResearchMode
)

# 获取 Agent 的方向
directions = plan.get_directions_for_agent(agent_name: str) -> List[ResearchDirection]

# 获取模块的方向
directions = plan.get_directions_for_module(module_name: str) -> List[ResearchDirection]

# 验证模块覆盖
missing = plan.validate_module_coverage(required_modules: List[str]) -> List[str]

# 获取待处理方向
pending = plan.get_pending_directions(agent_name: str = None) -> List[ResearchDirection]

# 获取摘要
summary = plan.summary() -> Dict
```

### 13.3 BaseAgent

```python
from src.agents.base_agent import BaseAgent

class CustomAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            role="CustomRole",
            tools=[tool1, tool2]
        )

# 调用 Agent
result = agent.invoke(
    user_message: str,
    context: str = ""
) -> Dict[str, Any]
# 返回: {"output": str, "references": List[Dict]}
```

### 13.4 ResearchMixin

```python
from src.agents.research_mixin import ResearchMixin

class ResearchAgent(BaseAgent, ResearchMixin):
    pass

# 研究迭代
result = agent.research_iterate(
    research_plan: Dict,
    evidence_graph: Dict,
    raw_pdf_text: str,
    iteration: int
) -> Dict
# 返回: {
#     "evidence_graph": Dict,
#     "research_plan": Dict,
#     "new_entity_ids": List[str],
#     "direction_updates": Dict,
#     "research_complete": bool,
#     "needs_deep_research": List,
#     "summary": str
# }
```

### 13.5 FormatChecker

```python
from src.validators.format_checker import FormatChecker

checker = FormatChecker()

# 验证报告
is_compliant, missing = checker.validate(report_text: str) -> Tuple[bool, List[str]]

# 生成反馈
feedback = checker.generate_feedback(missing_sections: List[str]) -> str

# 检查引用
has_refs, count = checker.check_references(report_text: str) -> Tuple[bool, int]
```

### 13.6 HtmlReportGenerator

```python
from src.renderers.html_generator import HtmlReportGenerator

generator = HtmlReportGenerator()

# 生成 HTML 报告
html_path = generator.generate(
    raw_pdf_text: str,
    chair_synthesis: str,
    references: List[Dict],
    run_folder: str = None
) -> str
```

---

## 附录 A: 完整状态流图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           MTB 状态流图                                   │
└─────────────────────────────────────────────────────────────────────────┘

input_text ─────────────────────────────────────────────────────────────────┐
                                                                            │
                                    ┌───────────────────────────────────────┤
                                    │           pdf_parser_node             │
                                    │   ┌─────────────────────────────┐    │
                                    │   │ raw_pdf_text                │    │
                                    │   │ run_folder                  │    │
                                    │   └─────────────────────────────┘    │
                                    └───────────────────────────────────────┤
                                                                            │
                                    ┌───────────────────────────────────────┤
                                    │           plan_agent_node             │
                                    │   ┌─────────────────────────────┐    │
                                    │   │ research_plan               │    │
                                    │   │ evidence_graph (empty)      │    │
                                    │   │ research_mode               │    │
                                    │   │ phase1_iteration = 0        │    │
                                    │   └─────────────────────────────┘    │
                                    └───────────────────────────────────────┤
                                                                            │
┌───────────────────────────────────────────────────────────────────────────┤
│                        RESEARCH SUBGRAPH                                  │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                         PHASE 1 LOOP                                │ │
│  │                                                                     │ │
│  │  phase1_pathologist ──┐                                             │ │
│  │  phase1_geneticist  ──┼──▶ pathologist_research_result             │ │
│  │  phase1_recruiter   ──┘    geneticist_research_result              │ │
│  │                            recruiter_research_result               │ │
│  │                            evidence_graph (更新)                   │ │
│  │                            research_plan (更新)                    │ │
│  │                                    │                                │ │
│  │                                    ▼                                │ │
│  │                         phase1_aggregator                          │ │
│  │                            phase1_iteration++                      │ │
│  │                            iteration_history (追加)                │ │
│  │                                    │                                │ │
│  │                                    ▼                                │ │
│  │                      plan_agent_evaluate_phase1                    │ │
│  │                            phase1_decision                         │ │
│  │                            pathologist_converged                   │ │
│  │                            geneticist_converged                    │ │
│  │                            recruiter_converged                     │ │
│  │                            plan_agent_evaluation                   │ │
│  │                                                                     │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                    │                                      │
│                                    ▼                                      │
│                       generate_phase1_reports                             │
│                            pathologist_report                             │
│                            geneticist_report                              │
│                            recruiter_report                               │
│                            pathologist_references                         │
│                            geneticist_references                          │
│                                    │                                      │
│                                    ▼                                      │
│                          phase2_plan_init                                 │
│                            research_plan (P2_* 方向)                      │
│                            phase2_iteration = 0                           │
│                                    │                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                         PHASE 2 LOOP                                │ │
│  │                                                                     │ │
│  │  phase2_oncologist ──▶ oncologist_research_result                  │ │
│  │                        evidence_graph (更新)                       │ │
│  │                        phase2_iteration++                          │ │
│  │                                    │                                │ │
│  │                                    ▼                                │ │
│  │                      plan_agent_evaluate_phase2                    │ │
│  │                            phase2_decision                         │ │
│  │                            plan_agent_evaluation                   │ │
│  │                                                                     │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                    │                                      │
│                                    ▼                                      │
│                       generate_phase2_reports                             │
│                            oncologist_plan                                │
│                                    │                                      │
│                                    ▼                                      │
│                       generate_agent_reports                              │
│                            recruiter_trials                               │
│                            oncologist_safety_warnings                     │
│                            research_progress_report                       │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┤
                                                                            │
                                    ┌───────────────────────────────────────┤
                                    │             chair_node                │
                                    │   ┌─────────────────────────────┐    │
                                    │   │ chair_synthesis             │    │
                                    │   │ chair_final_references      │    │
                                    │   └─────────────────────────────┘    │
                                    └───────────────────────────────────────┤
                                                                            │
                                    ┌───────────────────────────────────────┤
                                    │       format_verification_node        │
                                    │   ┌─────────────────────────────┐    │
                                    │   │ is_compliant                │    │
                                    │   │ missing_sections            │    │
                                    │   │ validation_iteration        │    │
                                    │   └─────────────────────────────┘    │
                                    └───────────────────────────────────────┤
                                                                            │
                                    ┌───────────────────────────────────────┤
                                    │       webpage_generator_node          │
                                    │   ┌─────────────────────────────┐    │
                                    │   │ final_html                  │    │
                                    │   │ output_path                 │    │
                                    │   └─────────────────────────────┘    │
                                    └───────────────────────────────────────┘
```

---

*文档版本: 1.0*
*最后更新: 2025-01*
