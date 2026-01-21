# MTB - 虚拟分子肿瘤委员会 (Virtual Molecular Tumor Board)

基于 LangGraph 的多智能体系统，用于生成结构化的肿瘤委员会会诊报告。

## 项目概述

MTB 系统通过 5 个专业 AI Agent 协作，处理患者病历 PDF 文件，生成包含 12 个标准模块的临床报告。

### 工作流程

```
PDF 输入 → PDF 解析
                ↓
    ┌───────────┼───────────┐
    ↓           ↓           ↓
Pathologist  Geneticist  Recruiter   ← 并行执行
    └───────────┼───────────┘
                ↓ (汇聚)
           Oncologist
                ↓
             Chair  ← 接收上游引用
                ↓
           格式验证
         ↓         ↓
      [通过]    [失败 → 重试, 最多2次]
         ↓
      HTML 报告
```

### Agent 角色

| Agent | 职责 | 工具 | 温度 |
|-------|------|------|------|
| **Pathologist** | 病理/影像分析 | PubMed, cBioPortal | 0.3 |
| **Geneticist** | 分子特征分析 | CIViC, ClinVar, cBioPortal, PubMed | 0.2 |
| **Recruiter** | 临床试验匹配 | ClinicalTrials.gov, NCCN, PubMed | 0.2 |
| **Oncologist** | 治疗方案制定 | NCCN, FDA Label, RxNorm, PubMed | 0.2 |
| **Chair** | 汇总整合，生成报告 | NCCN, FDA Label, PubMed | 0.3 |

**引用保留机制**: Chair 接收来自 Pathologist、Geneticist、Recruiter 的上游引用，合并去重后生成最终参考文献。

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/Zachary77-code/mtb_basic.git
cd mtb_basic
```

### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

创建 `.env` 文件：

```env
# 必需
OPENROUTER_API_KEY=your_openrouter_api_key

# 可选 (提高 API 速率限制)
NCBI_API_KEY=your_ncbi_api_key

# 可选 (用于 NCCN RAG 嵌入)
DASHSCOPE_API_KEY=your_dashscope_api_key

# 模型配置 (可选)
OPENROUTER_MODEL=google/gemini-2.5-pro-preview
```

### 5. 初始化 NCCN 向量数据库 (可选)

如需使用 NCCN 指南 RAG 功能：

```bash
python scripts/build_nccn_vectors.py
```

## 使用方法

### 运行完整工作流

```bash
python main.py <病历PDF文件路径>

# 示例
python main.py tests/fixtures/test_report.pdf
```

### 测试外部 API 工具

```bash
python tests/test_all_tools.py
```

### 验证配置

```bash
python config/settings.py
```

### 运行测试

```bash
pytest tests/
```

## 项目结构

```
MTB/
├── main.py                 # 入口文件
├── config/
│   ├── settings.py         # 配置参数
│   └── prompts/            # Agent 提示词
│       ├── global_principles.txt
│       ├── pathologist_prompt.txt
│       ├── geneticist_prompt.txt
│       ├── recruiter_prompt.txt
│       ├── oncologist_prompt.txt
│       └── chair_prompt.txt
├── src/
│   ├── agents/             # Agent 实现
│   │   ├── base_agent.py
│   │   ├── pathologist.py
│   │   ├── geneticist.py
│   │   ├── recruiter.py
│   │   ├── oncologist.py
│   │   └── chair.py
│   ├── graph/              # LangGraph 工作流
│   │   ├── state_graph.py
│   │   ├── nodes.py
│   │   └── edges.py
│   ├── models/             # 数据模型
│   │   └── state.py
│   ├── tools/              # 外部 API 工具
│   │   ├── variant_tools.py    # CIViC, ClinVar, cBioPortal
│   │   ├── literature_tools.py # PubMed
│   │   ├── trial_tools.py      # ClinicalTrials.gov
│   │   └── guideline_tools.py  # FDA, RxNorm, NCCN RAG
│   ├── renderers/          # 报告渲染
│   │   └── html_generator.py
│   └── validators/         # 格式验证
│       └── format_checker.py
├── data/
│   └── nccn_vectors/       # ChromaDB 向量数据库 (本地生成, 不上传)
├── reports/                # 生成的报告 (运行时)
├── logs/                   # 日志文件
└── tests/
    └── fixtures/           # 测试数据
```

## 报告模块

生成的报告包含以下 **12 个必需模块**：

1. **执行摘要** (Executive Summary)
2. **患者概况** (Patient Profile)
3. **分子特征** (Molecular Profile)
4. **治疗史回顾** (Treatment History)
5. **药物/方案对比** (Regimen Comparison)
6. **器官功能与剂量** (Organ Function & Dosing)
7. **治疗路线图** (Treatment Roadmap)
8. **分子复查建议** (Re-biopsy/Liquid Biopsy)
9. **临床试验推荐** (Clinical Trials)
10. **局部治疗建议** (Local Therapy)
11. **核心建议汇总** (Core Recommendations)
12. **参考文献** (References)

## 证据等级

| 等级 | 描述 |
|------|------|
| **A** | Phase III 随机对照试验 |
| **B** | Phase I-II 临床试验 |
| **C** | 回顾性研究 |
| **D** | 临床前研究 |

## 引用格式

- PubMed: `[PMID: 12345678](https://pubmed.ncbi.nlm.nih.gov/12345678/)`
- 临床试验: `[NCT12345678](https://clinicaltrials.gov/study/NCT12345678)`
- NCCN: `[NCCN: Guidelines](https://www.nccn.org/guidelines)`

## 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `AGENT_TEMPERATURE` | 0.2 | LLM 生成温度 |
| `AGENT_TIMEOUT` | 120 | API 调用超时 (秒) |
| `MAX_RETRY_ITERATIONS` | 2 | 格式验证失败最大重试次数 |

## 技术栈

- **LangGraph 1.0.6** - 工作流编排 (不使用 LangChain)
- **OpenRouter API** - LLM 调用
- **ChromaDB** - 向量数据库 (NCCN RAG)
- **Jinja2** - HTML 模板渲染

## 许可证

MIT License

## 免责声明

本系统生成的报告仅供临床参考。所有治疗决策应由具有资质的医疗专业人员根据患者实际情况做出。
