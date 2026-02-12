"""
Agent 基类（OpenRouter API + LangGraph）

使用 requests 调用 OpenRouter API 实现 LLM 调用。
"""
import json
import re
import requests
import time
import threading
from collections import deque
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
    GLOBAL_PRINCIPLES_FILE,
    SUBGRAPH_MODEL,
    ORCHESTRATOR_MODEL,
    CONVERGENCE_JUDGE_MODEL,
    CHAIR_MODEL,
    ORCHESTRATOR_REASONING_EFFORT,
    SUBGRAPH_REASONING_EFFORT,
    MAX_TOKENS_MAIN,
    MAX_TOKENS_SUBGRAPH,
    MAX_TOKENS_ORCHESTRATOR,
    MAX_TOKENS_CHAIR,
)
from src.utils.logger import mtb_logger as logger, log_tool_call


@dataclass
class ToolCallRecord:
    """记录单次工具调用的详细信息"""
    tool_name: str
    parameters: Dict[str, Any]
    reasoning: str  # LLM 调用工具前的推理/说明（reasoning_details）
    result: str
    round_number: int = 0    # API 调用轮次（1-based）
    round_content: str = ""  # 该轮次模型的 content 文本（结构化推理）
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
            ref_type: 引用类型 (PMID, NCT, CIViC, GDC 等)
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

        注意：此方法仅用于 generate_full_report() 的调试/开发输出。
        生产报告依赖 Evidence Graph 自动生成附录A（完整证据引用列表）。

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

    # OpenRouter 全局速率限制器（所有Agent实例共享）
    _rate_limiter_lock = threading.Lock()
    _request_timestamps = deque()  # 请求时间戳队列
    _RATE_LIMIT_WINDOW = 10  # 时间窗口：10秒
    _RATE_LIMIT_MAX_REQUESTS = 20  # 窗口内最大请求数：10次（应对Google上游限制）

    def __init__(
        self,
        role: str,
        prompt_file: str,
        tools: Optional[List[Any]] = None,
        temperature: Optional[float] = None,
        model: Optional[str] = None
    ):
        """
        初始化 Agent

        Args:
            role: Agent 角色名称
            prompt_file: 角色特定提示词文件名
            tools: 可用工具列表（BaseTool 实例）
            temperature: LLM 温度参数（可选，默认使用全局配置）
            model: LLM 模型名称（可选，默认使用 OPENROUTER_MODEL）
        """
        self.role = role
        self.model = model or OPENROUTER_MODEL
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

    @classmethod
    def _check_rate_limit(cls):
        """
        检查OpenRouter速率限制（10秒内最多20次请求）
        如果达到限制，阻塞等待直到有空闲配额
        """
        while True:  # 使用循环代替递归，避免锁问题
            wait_time = 0
            with cls._rate_limiter_lock:
                current_time = time.time()
                cutoff_time = current_time - cls._RATE_LIMIT_WINDOW

                # 清理过期的时间戳（>10秒前）
                while cls._request_timestamps and cls._request_timestamps[0] < cutoff_time:
                    cls._request_timestamps.popleft()

                # 检查是否达到限制
                if len(cls._request_timestamps) >= cls._RATE_LIMIT_MAX_REQUESTS:
                    # 计算需要等待的时间（直到最早的请求过期）
                    oldest_request = cls._request_timestamps[0]
                    wait_time = oldest_request + cls._RATE_LIMIT_WINDOW - current_time
                    if wait_time > 0:
                        logger.info(
                            f"[RateLimiter] 达到速率限制 ({len(cls._request_timestamps)}/{cls._RATE_LIMIT_MAX_REQUESTS})"
                            f"，等待 {wait_time:.1f}s"
                        )
                    # 锁会在此处自动释放（退出with块）
                else:
                    # 未达到限制，记录本次请求时间戳并返回
                    cls._request_timestamps.append(current_time)
                    logger.debug(
                        f"[RateLimiter] 当前速率：{len(cls._request_timestamps)}/{cls._RATE_LIMIT_MAX_REQUESTS} "
                        f"(过去{cls._RATE_LIMIT_WINDOW}秒)"
                    )
                    return  # 成功，退出方法

            # 在锁外等待（此时锁已释放）
            if wait_time > 0:
                time.sleep(wait_time)
                # 继续循环，重新检查

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

        # ========== 全局速率限制检查 ==========
        self._check_rate_limit()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # 根据模型选择 max_tokens（max output tokens）
        if self.model == CHAIR_MODEL:
            max_tokens = MAX_TOKENS_CHAIR
        elif self.model == SUBGRAPH_MODEL:
            max_tokens = MAX_TOKENS_SUBGRAPH
        elif self.model in (ORCHESTRATOR_MODEL, CONVERGENCE_JUDGE_MODEL):
            max_tokens = MAX_TOKENS_ORCHESTRATOR
        else:
            max_tokens = MAX_TOKENS_MAIN

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": max_tokens,
        }

        # 根据模型选择 reasoning effort（Pro → high, Flash → medium）
        reasoning_effort = ""
        if self.model == SUBGRAPH_MODEL:
            reasoning_effort = SUBGRAPH_REASONING_EFFORT
        elif self.model in (ORCHESTRATOR_MODEL, CONVERGENCE_JUDGE_MODEL, CHAIR_MODEL):
            reasoning_effort = ORCHESTRATOR_REASONING_EFFORT
        if reasoning_effort:
            payload["reasoning"] = {"effort": reasoning_effort}

        # 如果有工具且模型支持，添加工具定义
        if include_tools and self.tools:
            payload["tools"] = self._get_tools_schema()
            payload["tool_choice"] = "auto"

        # 重试逻辑（网络错误、API 错误都重试）
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url=self.api_url,
                    headers=headers,
                    data=json.dumps(payload, ensure_ascii=False),
                    timeout=AGENT_TIMEOUT
                )

                # 检查 HTTP 状态
                if response.status_code != 200:
                    error_detail = response.text
                    raise Exception(f"HTTP {response.status_code}: {error_detail[:200]}")

                result = response.json()

                # 检查 API 错误响应（HTTP 200 但返回错误）
                if "error" in result:
                    error_msg = result.get("error", {})
                    error_code = error_msg.get("code", "unknown") if isinstance(error_msg, dict) else "unknown"
                    raise Exception(f"API error (code={error_code}): {error_msg}")

                logger.debug(f"[{self.role}] API 响应成功")
                return result

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"[{self.role}] API 请求失败 ({type(e).__name__})，等待 10s 后重试 ({attempt + 1}/{max_retries - 1})...")
                    time.sleep(10)
                else:
                    logger.error(f"[{self.role}] API 请求失败，重试已用尽: {e}")
                    raise
            except Exception as e:
                # ========== 检测429错误并特殊处理 ==========
                if "429" in str(e) or "Too Many Requests" in str(e):
                    if attempt < max_retries - 1:
                        # 指数退避：5s, 15s, 45s
                        retry_after = 5 * (2 ** attempt)
                        logger.warning(
                            f"[{self.role}] OpenRouter 429限流，等待 {retry_after}s 后重试 "
                            f"({attempt + 1}/{max_retries})"
                        )
                        time.sleep(retry_after)
                        continue  # 跳过下面的代码，直接进入下一次循环
                    else:
                        logger.error(f"[{self.role}] OpenRouter 429限流，重试已用尽: {e}")
                        raise

                # ========== 其他错误的原有处理逻辑 ==========
                if attempt < max_retries - 1:
                    logger.warning(f"[{self.role}] API 错误，等待 10s 后重试 ({attempt + 1}/{max_retries - 1}): {e}")
                    time.sleep(10)
                else:
                    logger.error(f"[{self.role}] API 错误，重试已用尽: {e}")
                    raise

    def invoke(self, user_message: str, context: Optional[Dict[str, Any]] = None, max_tool_iterations: int = 5) -> Dict[str, Any]:
        """
        调用 Agent

        Args:
            user_message: 用户消息/任务描述
            context: 额外上下文信息（如 structured_case）
            max_tool_iterations: 最大工具调用轮次（默认 5）

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
            return self._handle_tool_calls(message, messages, max_iterations=max_tool_iterations)

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

    def _extract_reasoning_text(self, message: Dict[str, Any]) -> str:
        """从 API 响应 message 中提取推理内容

        优先从 reasoning_details 提取（Gemini 3 / Claude 等支持 reasoning 的模型），
        退回到 content 字段（某些模型在 content 中包含推理说明）。
        """
        reasoning_details = message.get("reasoning_details", [])
        if reasoning_details:
            texts = []
            for detail in reasoning_details:
                detail_type = detail.get("type", "")
                if detail_type == "reasoning.text":
                    texts.append(detail.get("text", ""))
                elif detail_type == "reasoning.summary":
                    texts.append(detail.get("summary", ""))
            if texts:
                return "\n".join(texts)

        # 退回到 content
        return message.get("content") or ""

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
        assistant_msg = {
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
        }
        # 注意：不要将 reasoning_details 回传给 API，Gemini 的 thinking tokens 带签名，
        # 回传会导致 "Thought signature is not valid" 错误。
        # reasoning 内容已在下方通过 _extract_reasoning_text() 提取用于内部记录。
        messages.append(assistant_msg)

        # 获取 LLM 的推理内容（优先从 reasoning_details 提取）
        reasoning_content = self._extract_reasoning_text(assistant_message)
        # 获取模型的 content 文本（结构化推理，区别于 reasoning_details 的 thinking tokens）
        round_content = assistant_message.get("content") or ""

        # 执行每个工具调用
        pending_images = []  # 收集本轮多模态工具返回的图片

        for tool_call in tool_calls:
            tool_name = tool_call.get("function", {}).get("name")
            tool_args_str = tool_call.get("function", {}).get("arguments", "{}")

            try:
                tool_args = json.loads(tool_args_str)
            except json.JSONDecodeError:
                tool_args = {}

            # 显示工具调用信息
            query_display = json.dumps(tool_args, ensure_ascii=False)
            logger.info(f"[{self.role}] 工具调用: {tool_name}")
            logger.info(f"[{self.role}]   参数: {query_display[:100]}{'...' if len(query_display) > 100 else ''}")

            # 查找并执行工具
            if tool_name in self.tool_registry:
                tool = self.tool_registry[tool_name]
                tool_result = tool.invoke(**tool_args)
            else:
                tool_result = f"错误：未找到工具 '{tool_name}'"
                log_tool_call(self.role, tool_name, query_display, False, 0)
                logger.warning(f"[{self.role}] 未找到工具: {tool_name}")

            # 检测多模态结果 (dict with "images" key)
            if isinstance(tool_result, dict) and "images" in tool_result:
                tool_text = tool_result.get("text", "")
                images = tool_result.get("images", [])
                pending_images.extend(images)

                log_tool_call(self.role, tool_name, query_display, True, len(tool_text))
                logger.info(f"[{self.role}]   多模态结果: {len(images)} 张图片")

                # 工具调用历史只记录文本部分
                self.tool_call_history.append(ToolCallRecord(
                    tool_name=tool_name,
                    parameters=tool_args,
                    reasoning=reasoning_content,
                    result=tool_text,
                    round_number=iteration,
                    round_content=round_content,
                ))

                # tool message 只放文本
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id"),
                    "content": tool_text
                })
            elif not isinstance(tool_result, dict):
                # 标准文本结果（原有逻辑，跳过已在上方 log 过的 "未找到工具" 情况）
                if tool_name in self.tool_registry:
                    result_len = len(tool_result) if tool_result else 0
                    log_tool_call(self.role, tool_name, query_display, True, result_len)

                self.tool_call_history.append(ToolCallRecord(
                    tool_name=tool_name,
                    parameters=tool_args,
                    reasoning=reasoning_content,
                    result=tool_result or "",
                    round_number=iteration,
                    round_content=round_content,
                ))

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id"),
                    "content": tool_result
                })

        # 如有多模态图片，追加一条 user message 让 agent 直接读图
        if pending_images:
            image_content = [
                {"type": "text", "text": f"以下是 NCCN 指南检索到的 {len(pending_images)} 个相关页面图片，请仔细阅读并提取相关信息:"}
            ]
            for img in pending_images:
                image_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img['base64']}"}
                })
            messages.append({"role": "user", "content": image_content})
            logger.info(f"[{self.role}] 已注入 {len(pending_images)} 张 NCCN 指南页面图片到对话")

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
                # 处理多行 reasoning，每行加 blockquote 前缀
                for line in record.reasoning.split("\n"):
                    lines.append(f"> {line}")
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
        后处理内容，将各种数据源引用格式转换为内联引用格式 [[n]](#ref-xxx)，
        并注册到 ReferenceManager

        支持的数据源（共 8 个）：
        - PMID (PubMed)
        - NCT (ClinicalTrials.gov)
        - GDC (NCI Genomic Data Commons)
        - CIViC
        - NCCN
        - FDA
        - ClinVar
        - RxNorm

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

        # Pattern 3: [GDC xxx](https://portal.gdc.cancer.gov/...)
        # 或 [GDC: xxx](url) 或 [cBioPortal xxx](url)（兼容旧格式）
        gdc_pattern = r'\[(?:GDC|cBioPortal)[:\s]+([^\]]+)\]\((https?://[^\)]+)\)'

        def replace_gdc(match):
            ref_id = match.group(1).strip()
            url = match.group(2)
            return self.reference_manager.add_reference("GDC", ref_id, url)

        content = re.sub(gdc_pattern, replace_gdc, content, flags=re.IGNORECASE)

        # Pattern 4: [CIViC xxx](https://civicdb.org/...)
        # 或 [CIViC: xxx](url)
        civic_pattern = r'\[CIViC[:\s]+([^\]]+)\]\((https?://[^\)]+)\)'

        def replace_civic(match):
            variant_id = match.group(1).strip()
            url = match.group(2)
            return self.reference_manager.add_reference("CIViC", variant_id, url)

        content = re.sub(civic_pattern, replace_civic, content, flags=re.IGNORECASE)

        # Pattern 5: [NCCN xxx](https://www.nccn.org/...)
        # 或 [NCCN: xxx](url) 或 [NCCN Guidelines xxx](url)
        nccn_pattern = r'\[NCCN[:\s]+([^\]]+)\]\((https?://[^\)]+)\)'

        def replace_nccn(match):
            guideline_id = match.group(1).strip()
            url = match.group(2)
            return self.reference_manager.add_reference("NCCN", guideline_id, url)

        content = re.sub(nccn_pattern, replace_nccn, content, flags=re.IGNORECASE)

        # Pattern 6: [FDA Label](https://www.accessdata.fda.gov/...)
        # 或 [FDA xxx](url) 或 [FDA: xxx](url)
        fda_pattern = r'\[FDA[:\s]*([^\]]*)\]\((https?://[^\)]+)\)'

        def replace_fda(match):
            label_id = match.group(1).strip() or "Label"
            url = match.group(2)
            return self.reference_manager.add_reference("FDA", label_id, url)

        content = re.sub(fda_pattern, replace_fda, content, flags=re.IGNORECASE)

        # Pattern 7: [ClinVar VCV000000](https://www.ncbi.nlm.nih.gov/clinvar/...)
        # 或 [ClinVar: xxx](url)
        clinvar_pattern = r'\[ClinVar[:\s]+([^\]]+)\]\((https?://[^\)]+)\)'

        def replace_clinvar(match):
            variant_id = match.group(1).strip()
            url = match.group(2)
            return self.reference_manager.add_reference("ClinVar", variant_id, url)

        content = re.sub(clinvar_pattern, replace_clinvar, content, flags=re.IGNORECASE)

        # Pattern 8: [RxNorm xxx](https://rxnav.nlm.nih.gov/...)
        # 或 [RxNorm: xxx](url)
        rxnorm_pattern = r'\[RxNorm[:\s]+([^\]]+)\]\((https?://[^\)]+)\)'

        def replace_rxnorm(match):
            drug_id = match.group(1).strip()
            url = match.group(2)
            return self.reference_manager.add_reference("RxNorm", drug_id, url)

        content = re.sub(rxnorm_pattern, replace_rxnorm, content, flags=re.IGNORECASE)

        # Pattern 9: [[ref:ID|Title|URL|Note]] (Chair 的 tooltip 格式)
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
