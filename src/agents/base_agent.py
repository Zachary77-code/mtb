"""
Agent 基类（OpenRouter API + LangGraph）

使用 requests 调用 OpenRouter API 实现 LLM 调用。
"""
import json
import re
import requests
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from config.settings import (
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    OPENROUTER_BASE_URL,
    AGENT_TEMPERATURE,
    AGENT_TIMEOUT,
    PROMPTS_DIR,
    load_prompt,
    GLOBAL_PRINCIPLES_FILE
)
from src.utils.logger import mtb_logger as logger


@dataclass
class ToolCallRecord:
    """记录单次工具调用的详细信息"""
    tool_name: str
    parameters: Dict[str, Any]
    reasoning: str  # LLM 调用工具前的推理/说明
    result: str
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


class ReferenceManager:
    """管理引用：支持内联链接和末尾汇总（带跳转锚点）"""

    def __init__(self):
        self.references: List[Dict[str, Any]] = []
        self.ref_map: Dict[str, int] = {}  # key -> index

    def add_reference(self, ref_type: str, ref_id: str, url: str, title: str = "") -> str:
        """
        添加引用并返回内联 markdown 链接

        Args:
            ref_type: 引用类型 (PMID, NCT, CIViC, cBioPortal 等)
            ref_id: 引用 ID
            url: 引用 URL
            title: 引用标题（可选）

        Returns:
            内联 markdown 链接，如 [[1]](#ref-pmid-12345678)
        """
        key = f"{ref_type}-{ref_id}".lower()
        if key not in self.ref_map:
            self.ref_map[key] = len(self.references) + 1
            self.references.append({
                "index": self.ref_map[key],
                "type": ref_type,
                "id": ref_id,
                "url": url,
                "title": title,
                "anchor": f"ref-{key}"
            })
        idx = self.ref_map[key]
        anchor = f"ref-{key}"
        return f"[[{idx}]](#{anchor})"

    def get_all_references(self) -> List[Dict[str, Any]]:
        """获取所有引用"""
        return self.references

    def generate_reference_section(self) -> str:
        """
        生成末尾引用汇总章节（带锚点）

        Returns:
            Markdown 格式的引用章节
        """
        if not self.references:
            return ""

        lines = ["", "---", "", "## References", ""]
        for ref in self.references:
            anchor = ref["anchor"]
            idx = ref["index"]
            ref_type = ref["type"]
            ref_id = ref["id"]
            url = ref["url"]
            title = ref.get("title", "")

            # 创建锚点目标
            if title:
                lines.append(f'<a id="{anchor}"></a>**[{idx}]** [{ref_type}: {ref_id}]({url}) - {title}')
            else:
                lines.append(f'<a id="{anchor}"></a>**[{idx}]** [{ref_type}: {ref_id}]({url})')
            lines.append("")

        return "\n".join(lines)


class BaseAgent:
    """
    Agent 基类

    提供 OpenRouter API 调用、工具执行、消息管理等基础功能。
    所有专业 Agent 继承此类。
    """

    def __init__(
        self,
        role: str,
        prompt_file: str,
        tools: Optional[List[Any]] = None,
        temperature: Optional[float] = None
    ):
        """
        初始化 Agent

        Args:
            role: Agent 角色名称
            prompt_file: 角色特定提示词文件名
            tools: 可用工具列表（BaseTool 实例）
            temperature: LLM 温度参数（可选，默认使用全局配置）
        """
        self.role = role
        self.model = OPENROUTER_MODEL
        self.api_url = OPENROUTER_BASE_URL
        self.api_key = OPENROUTER_API_KEY
        self.temperature = temperature or AGENT_TEMPERATURE
        self.tools = tools or []

        # 构建系统提示词（全局原则 + 角色特定）
        self.system_prompt = self._build_system_prompt(prompt_file)

        # 工具注册表（name -> tool instance）
        self.tool_registry = {tool.name: tool for tool in self.tools}

        # 工具调用历史记录（每次 invoke 重置）
        self.tool_call_history: List[ToolCallRecord] = []

        # 引用管理器（每次 invoke 重置）
        self.reference_manager = ReferenceManager()

    def _build_system_prompt(self, prompt_file: str) -> str:
        """构建完整的系统提示词"""
        global_principles = load_prompt(GLOBAL_PRINCIPLES_FILE)
        role_prompt = load_prompt(prompt_file)
        return f"{global_principles}\n\n---\n\n{role_prompt}"

    def _get_tools_schema(self) -> List[Dict[str, Any]]:
        """获取所有工具的 OpenAI Function Calling 格式"""
        return [tool.to_openai_function() for tool in self.tools]

    def _call_api(self, messages: List[Dict[str, Any]], include_tools: bool = False) -> Dict[str, Any]:
        """
        调用 OpenRouter API

        Args:
            messages: 消息列表
            include_tools: 是否包含工具定义

        Returns:
            API 响应 JSON
        """
        logger.debug(f"[{self.role}] 调用 API，消息数: {len(messages)}, 工具: {include_tools}")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature
        }

        # 如果有工具且模型支持，添加工具定义
        if include_tools and self.tools:
            payload["tools"] = self._get_tools_schema()
            payload["tool_choice"] = "auto"

        response = requests.post(
            url=self.api_url,
            headers=headers,
            data=json.dumps(payload, ensure_ascii=False),
            timeout=AGENT_TIMEOUT
        )

        # 检查 HTTP 状态
        if response.status_code != 200:
            error_detail = response.text
            logger.error(f"[{self.role}] API 错误 (HTTP {response.status_code}): {error_detail[:200]}")
            raise Exception(f"API 调用失败 (HTTP {response.status_code}): {error_detail}")

        logger.debug(f"[{self.role}] API 响应成功")
        return response.json()

    def invoke(self, user_message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        调用 Agent

        Args:
            user_message: 用户消息/任务描述
            context: 额外上下文信息（如 structured_case）

        Returns:
            包含 output 和 references 的字典
        """
        logger.info(f"[{self.role}] 开始处理...")
        logger.debug(f"[{self.role}] 输入: {user_message[:100]}...")

        # 重置工具调用历史和引用管理器
        self.tool_call_history = []
        self.reference_manager = ReferenceManager()

        # 准备消息
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self._format_user_message(user_message, context)}
        ]

        # 调用 API（尝试带工具）
        try:
            result = self._call_api(messages, include_tools=bool(self.tools))
        except Exception as e:
            # 如果带工具调用失败，尝试不带工具
            if self.tools:
                logger.warning(f"[{self.role}] 带工具调用失败，重试无工具模式")
                result = self._call_api(messages, include_tools=False)
            else:
                raise e

        # 解析响应
        if "choices" not in result or len(result["choices"]) == 0:
            raise Exception(f"API 响应格式错误: {result}")

        message = result["choices"][0].get("message", {})

        # 检查是否有工具调用
        tool_calls = message.get("tool_calls")
        if tool_calls:
            logger.info(f"[{self.role}] 检测到工具调用: {len(tool_calls)} 个")
            return self._handle_tool_calls(message, messages)

        # 直接返回文本响应
        content = message.get("content", "")
        logger.info(f"[{self.role}] 完成，输出长度: {len(content)} 字符")
        logger.debug(f"[{self.role}] 输出预览: {content[:200]}...")

        return {
            "output": content,
            "references": self._extract_references(content)
        }

    def _format_user_message(self, user_message: str, context: Optional[Dict[str, Any]]) -> str:
        """格式化用户消息（添加上下文）"""
        if context:
            context_str = json.dumps(context, ensure_ascii=False, indent=2)
            return f"{user_message}\n\n**上下文数据**:\n```json\n{context_str}\n```"
        return user_message

    def _handle_tool_calls(
        self,
        assistant_message: Dict[str, Any],
        messages: List[Dict[str, Any]],
        iteration: int = 1,
        max_iterations: int = 5
    ) -> Dict[str, Any]:
        """
        处理工具调用（支持多轮工具调用）

        Args:
            assistant_message: 包含 tool_calls 的助手消息
            messages: 当前消息历史
            iteration: 当前迭代次数
            max_iterations: 最大迭代次数

        Returns:
            最终响应
        """
        tool_calls = assistant_message.get("tool_calls", [])

        logger.info(f"[{self.role}] 工具调用轮次 {iteration}/{max_iterations}，调用数: {len(tool_calls)}")

        # 添加助手消息到历史
        messages.append({
            "role": "assistant",
            "content": assistant_message.get("content") or "",
            "tool_calls": [
                {
                    "id": tc.get("id"),
                    "type": "function",
                    "function": {
                        "name": tc.get("function", {}).get("name"),
                        "arguments": tc.get("function", {}).get("arguments")
                    }
                }
                for tc in tool_calls
            ]
        })

        # 获取 LLM 的推理内容（工具调用前的说明）
        reasoning_content = assistant_message.get("content") or ""

        # 执行每个工具调用
        for tool_call in tool_calls:
            tool_name = tool_call.get("function", {}).get("name")
            tool_args_str = tool_call.get("function", {}).get("arguments", "{}")

            try:
                tool_args = json.loads(tool_args_str)
            except json.JSONDecodeError:
                tool_args = {}

            logger.debug(f"[{self.role}] 执行工具: {tool_name}, 参数: {tool_args}")

            # 查找并执行工具
            if tool_name in self.tool_registry:
                tool = self.tool_registry[tool_name]
                tool_result = tool.invoke(**tool_args)
                logger.debug(f"[{self.role}] 工具 {tool_name} 返回: {tool_result[:100] if tool_result else 'None'}...")
            else:
                tool_result = f"错误：未找到工具 '{tool_name}'"
                logger.warning(f"[{self.role}] 未找到工具: {tool_name}")

            # 记录工具调用历史（完整信息，不截断）
            self.tool_call_history.append(ToolCallRecord(
                tool_name=tool_name,
                parameters=tool_args,
                reasoning=reasoning_content,
                result=tool_result or ""
            ))

            # 添加工具结果
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.get("id"),
                "content": tool_result
            })

        # 继续生成响应（保持工具可用，以支持多轮调用）
        next_result = self._call_api(messages, include_tools=bool(self.tools))

        if "choices" not in next_result or len(next_result["choices"]) == 0:
            raise Exception(f"API 响应格式错误: {next_result}")

        next_message = next_result["choices"][0].get("message", {})
        next_tool_calls = next_message.get("tool_calls")
        next_content = next_message.get("content", "")

        # 如果模型还想调用工具，递归处理
        if next_tool_calls and iteration < max_iterations:
            logger.info(f"[{self.role}] 模型请求继续调用工具，进入下一轮")
            return self._handle_tool_calls(next_message, messages, iteration + 1, max_iterations)

        # 如果达到最大迭代或模型返回了内容
        if not next_content:
            logger.warning(f"[{self.role}] 警告：达到最大迭代或无内容，finish_reason: {next_result['choices'][0].get('finish_reason')}")

        logger.info(f"[{self.role}] 工具调用完成，最终输出长度: {len(next_content)} 字符")

        return {
            "output": next_content,
            "references": self._extract_references(next_content)
        }

    def _extract_references(self, text: str) -> List[Dict[str, str]]:
        """
        从文本中提取引用

        Args:
            text: 报告文本

        Returns:
            引用列表
        """
        import re

        references = []

        if not text:
            return references

        # 匹配 PMID 引用
        pmid_pattern = r'\[PMID:\s*(\d+)\]\((https?://[^\)]+)\)'
        for match in re.finditer(pmid_pattern, text):
            references.append({
                "type": "PMID",
                "id": match.group(1),
                "url": match.group(2)
            })

        # 匹配 NCT 引用
        nct_pattern = r'\[(NCT\d+)\]\((https?://[^\)]+)\)'
        for match in re.finditer(nct_pattern, text):
            references.append({
                "type": "NCT",
                "id": match.group(1),
                "url": match.group(2)
            })

        return references

    def get_tool_call_report(self) -> str:
        """
        生成工具调用历史的 Markdown 报告

        Returns:
            格式化的工具调用历史，包含每次调用的推理、参数和完整结果
        """
        if not self.tool_call_history:
            return ""

        lines = ["", "---", "", "## Tool Call Details", ""]

        for i, record in enumerate(self.tool_call_history, 1):
            lines.append(f"### Tool Call {i}: `{record.tool_name}`")
            lines.append(f"**Timestamp:** {record.timestamp}")
            lines.append("")

            if record.reasoning:
                lines.append("**Reasoning:**")
                lines.append(f"> {record.reasoning}")
                lines.append("")

            lines.append("**Parameters:**")
            lines.append("```json")
            lines.append(json.dumps(record.parameters, ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")

            lines.append("**Result:**")
            lines.append("```")
            lines.append(record.result)
            lines.append("```")
            lines.append("")

        return "\n".join(lines)

    def _process_inline_references(self, content: str) -> str:
        """
        后处理内容，将 [PMID: xxxxx](url) 和 [NCTxxxxxxxx](url) 格式
        转换为内联引用格式 [[n]](#ref-xxx)，并注册到 ReferenceManager

        Args:
            content: LLM 生成的原始内容

        Returns:
            处理后的内容，引用已转换为内联链接格式
        """
        if not content:
            return content

        # Pattern 1: [PMID: 12345678](https://pubmed.ncbi.nlm.nih.gov/12345678/)
        pmid_pattern = r'\[PMID:\s*(\d+)\]\((https?://[^\)]+)\)'

        def replace_pmid(match):
            pmid = match.group(1)
            url = match.group(2)
            return self.reference_manager.add_reference("PMID", pmid, url)

        content = re.sub(pmid_pattern, replace_pmid, content)

        # Pattern 2: [NCT12345678](https://clinicaltrials.gov/...)
        nct_pattern = r'\[(NCT\d+)\]\((https?://[^\)]+)\)'

        def replace_nct(match):
            nct_id = match.group(1)
            url = match.group(2)
            return self.reference_manager.add_reference("NCT", nct_id, url)

        content = re.sub(nct_pattern, replace_nct, content)

        # Pattern 3: [[ref:ID|Title|URL|Note]] (Chair 的 tooltip 格式)
        # 保留原样，不转换（HTML 渲染器会处理）

        return content

    def generate_full_report(self, main_content: str, title: str = None) -> str:
        """
        生成完整的 Markdown 报告，包含主内容、工具调用详情和引用

        Args:
            main_content: 主要分析内容
            title: 报告标题（可选）

        Returns:
            完整的 Markdown 报告
        """
        sections = []

        # 标题
        if title:
            sections.append(f"# {title}")
            sections.append("")

        # 主内容
        sections.append("## Analysis Output")
        sections.append("")

        # 后处理：转换引用格式并注册到 ReferenceManager
        processed_content = self._process_inline_references(main_content)
        sections.append(processed_content)

        # 工具调用详情
        tool_report = self.get_tool_call_report()
        if tool_report:
            sections.append(tool_report)

        # 引用章节（带锚点）
        ref_section = self.reference_manager.generate_reference_section()
        if ref_section:
            sections.append(ref_section)

        return "\n".join(sections)


if __name__ == "__main__":
    # 测试基类（需要配置 API Key）
    print("BaseAgent 模块加载成功")
    print(f"模型: {OPENROUTER_MODEL}")
    print(f"API URL: {OPENROUTER_BASE_URL}")
    print(f"温度: {AGENT_TEMPERATURE}")
