# MTB 多智能体工作流系统

自动化分子肿瘤委员会（MTB）系统，基于 LangGraph 1.0.6 和 OpenAI GPT-5.2 构建。

## 系统架构

本系统通过 4 个专业 Agent 协作处理非结构化病历，生成符合临床标准的 HTML 报告：

```
病历文本 → Pathologist → Geneticist → Recruiter → Oncologist → Chair → HTML 报告
```

### 核心特性

- **LangGraph 状态机工作流**：顺序执行 + 条件回退
- **4 个专业 Agent**：
  - Pathologist（病理医生）：病例解析
  - Geneticist（遗传学家）：变异分析
  - Recruiter（试验专员）：临床试验匹配
  - Oncologist（肿瘤学家）：治疗方案制定
  - Chair（MTB 主席）：综合决策
- **12 模块强制格式验证**
- **蓝白配色 HTML 报告**（带交互式引用）
- **MCP 工具占位符**（模拟真实数据库）

## 技术栈

- **框架**：LangGraph 1.0.6（纯 LangGraph，不使用 LangChain）
- **LLM**：OpenAI GPT-5.2
- **数据验证**：Pydantic 2.9.2
- **模板引擎**：Jinja2 3.1.4
- **日志**：Loguru 0.7.2

## 安装步骤

### 1. 克隆或下载项目

```bash
cd d:\MTB
```

### 2. 创建虚拟环境（推荐）

```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

复制 `.env.example` 为 `.env` 并填写您的 OpenAI API Key：

```bash
copy .env.example .env
```

编辑 `.env` 文件：

```
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-5.2
```

## 使用方法

### 基本用法

```bash
python main.py <病例文件路径>
```

示例：

```bash
python main.py tests/fixtures/sample_case.txt
```

### 输入格式

输入文件应为包含患者完整病历的文本文件，包括：

- 肿瘤类型和分期
- 分子检测结果（基因变异、TMB、MSI 等）
- 既往治疗史
- 器官功能指标（肾功能、肝功能、ECOG PS 等）

示例：

```
患者男性，65岁，诊断为非小细胞肺癌（腺癌）。
分期：IV期，多发骨转移和肝转移。
分子检测：EGFR外显子21 L858R突变，TMB 5.2 mut/Mb，MSS。
既往治疗：一线吉非替尼12个月，最佳疗效PR，现疾病进展。
ECOG PS 1分，肾功能正常（CrCl 85 mL/min），ALT 45 U/L，AST 38 U/L。
```

### 输出

系统将生成 HTML 报告并保存到 `reports/` 文件夹，文件名格式：

```
MTB_Report_<患者ID>_<时间戳>.html
```

## 项目结构

```
d:\MTB\
├── config/                         # 配置文件
│   ├── settings.py                 # 全局配置
│   └── prompts/                    # 提示词库
│       ├── global_principles.txt
│       ├── pathologist_prompt.txt
│       ├── geneticist_prompt.txt
│       ├── recruiter_prompt.txt
│       ├── oncologist_prompt.txt
│       └── chair_prompt.txt
│
├── src/                            # 核心源代码
│   ├── models/                     # 数据模型
│   ├── tools/                      # 工具库（占位符）
│   ├── agents/                     # Agent 实现
│   ├── graph/                      # LangGraph 工作流
│   ├── validators/                 # 格式验证
│   ├── renderers/                  # HTML 渲染
│   └── utils/                      # 工具函数
│
├── main.py                         # 主入口
├── requirements.txt                # 依赖清单
├── .env                            # 环境变量
└── reports/                        # 输出目录
```

## 报告格式

生成的 HTML 报告包含以下 12 个必选模块：

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

## GLOBAL OUTPUT PRINCIPLES

所有 Agent 遵循以下原则：

1. **Case-First Extraction** - 先重构病例概况
2. **Evidence Grading** - 每条建议标注证据等级（A/B/C/D）
3. **Negative Recommendation Rule** - 必须包含"不建议"章节
4. **Safety-First Rule** - 器官功能优先
5. **China-Specific Realism** - 优先中国可及药物/试验

## 开发说明

### 架构特点

本系统**完全不使用 LangChain**，仅依赖：

- **LangGraph 1.0.6**：状态图工作流
- **OpenAI Python SDK**：直接调用 GPT-5.2 API
- **Pydantic**：数据验证

### Agent 实现方式

Agent 不是传统的 LangChain AgentExecutor，而是：

```python
def agent_node(state: MtbState) -> MtbState:
    # 直接调用 OpenAI API
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-5.2",
        messages=[...],
        tools=[...]  # OpenAI function calling
    )
    state["output_field"] = response.choices[0].message.content
    return state
```

## 故障排查

### 常见问题

1. **模块导入错误**：确保已激活虚拟环境并安装所有依赖
2. **API Key 错误**：检查 `.env` 文件中的 `OPENAI_API_KEY`
3. **中文乱码**：确保输入文件保存为 UTF-8 编码
4. **报告生成失败**：检查 `reports/` 文件夹权限

### 日志

系统日志保存在 `logs/mtb.log`，包含详细的执行过程信息。

## 许可证

本项目仅供学术研究和医疗教育使用。

## 联系方式

如有问题，请提交 Issue 或联系项目维护者。

---

**⚠️ 免责声明**：本系统生成的报告仅供参考，不能替代专业医疗建议。所有临床决策应由具有资质的医疗专业人员做出。
