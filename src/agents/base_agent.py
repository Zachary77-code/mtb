"""
Agent 基类（OpenRouter API + LangGraph）

使用 requests 调用 OpenRouter API 实现 LLM 调用。
"""
import json
import requests
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
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        处理工具调用

        Args:
            assistant_message: 包含 tool_calls 的助手消息
            messages: 当前消息历史

        Returns:
            最终响应
        """
        tool_calls = assistant_message.get("tool_calls", [])

        # 添加助手消息到历史
        messages.append({
            "role": "assistant",
            "content": assistant_message.get("content"),
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
                logger.debug(f"[{self.role}] 工具 {tool_name} 返回: {tool_result[:100]}...")
            else:
                tool_result = f"错误：未找到工具 '{tool_name}'"
                logger.warning(f"[{self.role}] 未找到工具: {tool_name}")

            # 添加工具结果
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.get("id"),
                "content": tool_result
            })

        # 继续生成最终响应
        final_result = self._call_api(messages, include_tools=False)

        if "choices" not in final_result or len(final_result["choices"]) == 0:
            raise Exception(f"API 响应格式错误: {final_result}")

        final_content = final_result["choices"][0].get("message", {}).get("content", "")

        return {
            "output": final_content,
            "references": self._extract_references(final_content)
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


if __name__ == "__main__":
    # 测试基类（需要配置 API Key）
    print("BaseAgent 模块加载成功")
    print(f"模型: {OPENROUTER_MODEL}")
    print(f"API URL: {OPENROUTER_BASE_URL}")
    print(f"温度: {AGENT_TEMPERATURE}")
