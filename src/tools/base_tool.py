"""
工具基类

只使用真实 API 数据
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import json
from src.utils.logger import mtb_logger as logger


class BaseTool(ABC):
    """
    工具基类

    所有工具继承此类，实现 _call_real_api 方法调用真实 API。
    """

    def __init__(self, name: str, description: str):
        """
        初始化工具

        Args:
            name: 工具名称 (用于 OpenAI function calling)
            description: 工具描述
        """
        self.name = name
        self.description = description

    def invoke(self, **kwargs) -> str:
        """
        调用工具

        Args:
            **kwargs: 工具参数

        Returns:
            工具响应 (字符串格式)
        """
        logger.debug(f"[Tool:{self.name}] 调用参数: {kwargs}")

        try:
            result = self._call_real_api(**kwargs)
            if result:
                logger.info(f"[Tool:{self.name}] API 调用成功")
                return result
            else:
                error_msg = f"[Tool:{self.name}] API 返回空结果"
                logger.warning(error_msg)
                return f"错误: {self.name} 未返回数据，请检查输入参数或稍后重试。"
        except Exception as e:
            error_msg = f"[Tool:{self.name}] API 调用失败: {e}"
            logger.error(error_msg)
            return f"错误: {self.name} 调用失败 - {str(e)}"

    @abstractmethod
    def _call_real_api(self, **kwargs) -> Optional[str]:
        """
        调用真实 API (子类实现)

        Args:
            **kwargs: API 参数

        Returns:
            API 响应字符串，失败返回 None
        """
        pass

    @abstractmethod
    def _get_parameters_schema(self) -> Dict[str, Any]:
        """
        获取参数 JSON Schema (子类实现)

        Returns:
            参数 schema
        """
        pass

    def to_openai_function(self) -> Dict[str, Any]:
        """
        转换为 OpenAI Function Calling 格式

        Returns:
            OpenAI function schema
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self._get_parameters_schema()
            }
        }


if __name__ == "__main__":
    # 测试

    class TestTool(BaseTool):
        def __init__(self):
            super().__init__(
                name="test_tool",
                description="测试工具"
            )

        def _call_real_api(self, query: str = "", **kwargs) -> Optional[str]:
            if query == "error":
                raise ValueError("模拟错误")
            return f"API 响应: {query}"

        def _get_parameters_schema(self) -> Dict[str, Any]:
            return {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "查询内容"}
                },
                "required": ["query"]
            }

    tool = TestTool()

    print("=== 测试工具 ===")
    print(f"工具名称: {tool.name}")
    print(f"OpenAI 格式: {json.dumps(tool.to_openai_function(), indent=2, ensure_ascii=False)}")

    print(f"\n正常调用: {tool.invoke(query='test')}")
    print(f"错误调用: {tool.invoke(query='error')}")
