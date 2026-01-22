"""
PlanAgent - 研究计划生成 Agent

分析病例，生成结构化的研究计划，指导 BFRS/DFRS 研究循环。
使用 gemini-3-pro-preview 模型。
"""
import json
from typing import Dict, List, Any, Optional

from src.agents.base_agent import BaseAgent, ORCHESTRATOR_MODEL
from src.models.research_plan import (
    ResearchPlan,
    ResearchQuestion,
    ResearchDirection,
    ResearchMode,
    DirectionStatus,
    QuestionPriority,
    create_research_plan
)
from src.utils.logger import mtb_logger as logger
from config.settings import PLAN_AGENT_PROMPT_FILE


# 必须覆盖的 Chair 模块列表
REQUIRED_MODULE_COVERAGE = [
    "患者概况",
    "分子特征",
    "方案对比",
    "器官功能与剂量",
    "治疗路线图",
    "分子复查建议",
    "临床试验推荐",
    "局部治疗建议",
]


class PlanAgent(BaseAgent):
    """
    研究计划 Agent

    职责：
    1. 分析病例，提取关键实体（基因、变异、癌种、治疗史）
    2. 生成研究问题列表
    3. 为每个 Agent 分配研究方向
    4. 设置收敛条件
    """

    def __init__(self):
        """初始化 PlanAgent，使用 ORCHESTRATOR_MODEL"""
        super().__init__(
            role="PlanAgent",
            prompt_file=PLAN_AGENT_PROMPT_FILE,
            tools=[],  # PlanAgent 不需要外部工具
            temperature=0.3,
            model=ORCHESTRATOR_MODEL  # 使用 pro 模型
        )

    def analyze_case(self, case_text: str) -> Dict[str, Any]:
        """
        分析病例并生成研究计划

        Args:
            case_text: 病例文本

        Returns:
            研究计划字典（可序列化到 State）
        """
        logger.info(f"[{self.role}] 开始分析病例...")

        # 构建任务提示
        task_prompt = self._build_analysis_prompt(case_text)

        # 调用 LLM
        result = self.invoke(task_prompt)
        output = result.get("output", "")

        # 解析 LLM 输出
        plan = self._parse_plan_output(output, case_text)

        logger.info(f"[{self.role}] 研究计划生成完成: {plan.summary()}")

        return plan.to_dict()

    def _build_analysis_prompt(self, case_text: str) -> str:
        """构建分析任务提示"""
        return f"""请分析以下病例，生成结构化的研究计划。

## 病例内容
{case_text}

## 输出要求
请以 JSON 格式输出研究计划，包含以下字段：

```json
{{
    "case_summary": "病例摘要（50-100字）",
    "key_entities": {{
        "genes": ["基因列表"],
        "variants": ["变异列表"],
        "cancer_type": ["癌症类型"],
        "drugs_mentioned": ["提及的药物"],
        "treatment_history": ["治疗史要点"]
    }},
    "questions": [
        {{
            "id": "Q1",
            "text": "研究问题",
            "priority": 1,  // 1-4，1最高
            "target_agents": ["Geneticist", "Oncologist"],
            "related_entities": ["相关实体"]
        }}
    ],
    "directions": [
        {{
            "id": "D1",
            "topic": "研究方向主题",
            "target_agent": "Geneticist",  // Pathologist/Geneticist/Recruiter/Oncologist
            "target_modules": ["分子特征"],  // 目标 Chair 模块
            "priority": 1,  // 1-5，1最高
            "queries": ["建议的查询关键词"],
            "completion_criteria": "完成标准描述",
            "related_question_ids": ["Q1"]
        }}
    ]
}}
```

## 研究方向分配指南

### Pathologist（病理学家）
- 病理学形态特征分析
- 影像学发现解读
- 免疫组化结果意义
- 病理分期评估

### Geneticist（遗传学家）
- 基因变异致病性评估
- 变异-药物敏感性关系
- 耐药机制分析
- 分子分型确认

### Recruiter（临床试验招募员）
- 适用临床试验匹配
- 入排标准评估
- 试验阶段和状态

### Oncologist（肿瘤学家）
- 治疗方案制定
- 药物相互作用
- 剂量调整建议
- 安全性评估

## 注意事项
1. 每个 Agent 分配 2-5 个研究方向
2. 研究问题应覆盖诊断、治疗、预后等方面
3. 优先级 1 为最关键问题
4. 确保 JSON 格式正确，可以被解析
"""

    def _parse_plan_output(self, output: str, original_case: str) -> ResearchPlan:
        """
        解析 LLM 输出为 ResearchPlan

        Args:
            output: LLM 原始输出
            original_case: 原始病例文本（用于备用）

        Returns:
            ResearchPlan 实例
        """
        # 尝试提取 JSON
        json_str = self._extract_json(output)

        if json_str:
            try:
                data = json.loads(json_str)
                plan = create_research_plan(
                    case_summary=data.get("case_summary", ""),
                    key_entities=data.get("key_entities", {}),
                    questions=data.get("questions", []),
                    directions=data.get("directions", [])
                )

                # 验证模块覆盖
                missing = plan.validate_module_coverage(REQUIRED_MODULE_COVERAGE)
                if missing:
                    logger.warning(f"[{self.role}] 模块覆盖不完整，缺失: {missing}")

                return plan
            except json.JSONDecodeError as e:
                logger.warning(f"[{self.role}] JSON 解析失败: {e}")

        # 如果解析失败，创建默认计划
        logger.warning(f"[{self.role}] 使用默认研究计划")
        return self._create_default_plan(original_case)

    def _extract_json(self, text: str) -> Optional[str]:
        """从文本中提取 JSON 块"""
        import re

        # 尝试匹配 ```json ... ``` 格式
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if json_match:
            return json_match.group(1).strip()

        # 尝试匹配 { ... } 格式
        brace_match = re.search(r'\{[\s\S]*\}', text)
        if brace_match:
            return brace_match.group(0)

        return None

    def _create_default_plan(self, case_text: str) -> ResearchPlan:
        """创建默认研究计划（当解析失败时）"""
        return create_research_plan(
            case_summary=case_text[:200] + "..." if len(case_text) > 200 else case_text,
            key_entities={
                "genes": [],
                "variants": [],
                "cancer_type": [],
                "drugs_mentioned": [],
                "treatment_history": []
            },
            questions=[
                {
                    "id": "Q1",
                    "text": "患者的主要分子特征是什么？",
                    "priority": 1,
                    "target_agents": ["Geneticist", "Pathologist"],
                    "related_entities": []
                },
                {
                    "id": "Q2",
                    "text": "有哪些推荐的治疗方案？",
                    "priority": 1,
                    "target_agents": ["Oncologist"],
                    "related_entities": []
                },
                {
                    "id": "Q3",
                    "text": "有哪些适用的临床试验？",
                    "priority": 2,
                    "target_agents": ["Recruiter"],
                    "related_entities": []
                }
            ],
            directions=[
                # 模块2: 患者概况
                {
                    "id": "D1",
                    "topic": "患者基础信息与影像评估",
                    "target_agent": "Pathologist",
                    "target_modules": ["患者概况", "局部治疗建议"],
                    "priority": 2,
                    "queries": ["pathology findings", "immunohistochemistry", "imaging"],
                    "completion_criteria": "完成患者基础信息、病理学和影像学评估",
                    "related_question_ids": ["Q1"]
                },
                # 模块3: 分子特征 + 模块8: 分子复查建议
                {
                    "id": "D2",
                    "topic": "分子特征与液体活检计划",
                    "target_agent": "Geneticist",
                    "target_modules": ["分子特征", "分子复查建议", "治疗路线图"],
                    "priority": 1,
                    "queries": ["gene mutations", "variant pathogenicity", "resistance mutations", "liquid biopsy"],
                    "completion_criteria": "完成分子特征分析和分子复查计划",
                    "related_question_ids": ["Q1"]
                },
                # 模块9: 临床试验推荐
                {
                    "id": "D3",
                    "topic": "临床试验匹配",
                    "target_agent": "Recruiter",
                    "target_modules": ["临床试验推荐", "治疗路线图"],
                    "priority": 2,
                    "queries": ["clinical trials"],
                    "completion_criteria": "找到至少 3 个相关临床试验",
                    "related_question_ids": ["Q3"]
                },
                # 模块5-7, 10: 方案对比、器官功能、治疗路线图、局部治疗
                {
                    "id": "D4",
                    "topic": "治疗方案与安全性评估",
                    "target_agent": "Oncologist",
                    "target_modules": ["方案对比", "器官功能与剂量", "治疗路线图", "局部治疗建议", "分子复查建议"],
                    "priority": 1,
                    "queries": ["treatment guidelines", "drug therapy", "organ function", "dose adjustment", "local therapy"],
                    "completion_criteria": "制定完整治疗方案、剂量调整和局部治疗建议",
                    "related_question_ids": ["Q2"]
                }
            ]
        )


if __name__ == "__main__":
    # 测试
    print("PlanAgent 模块加载成功")
    print(f"使用模型: {ORCHESTRATOR_MODEL}")

    # 测试实例化
    try:
        agent = PlanAgent()
        print(f"PlanAgent 初始化成功，角色: {agent.role}")
        print(f"模型: {agent.model}")
    except Exception as e:
        print(f"初始化失败: {e}")
