"""
工具基类

支持真实 API 调用和模拟数据降级
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import json
from config.settings import USE_REAL_APIS
from src.utils.logger import mtb_logger as logger


class BaseTool(ABC):
    """
    工具基类

    所有工具继承此类，支持:
    1. 真实 API 调用 (_call_real_api)
    2. 模拟数据降级 (_generate_mock_response)

    根据 USE_REAL_APIS 配置自动选择调用方式。
    当真实 API 调用失败时，自动降级到模拟数据。
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
        self._use_real_api = USE_REAL_APIS

    def invoke(self, **kwargs) -> str:
        """
        调用工具

        Args:
            **kwargs: 工具参数

        Returns:
            工具响应 (字符串格式)
        """
        logger.debug(f"[Tool:{self.name}] 调用参数: {kwargs}")

        if self._use_real_api:
            try:
                result = self._call_real_api(**kwargs)
                if result:
                    logger.info(f"[Tool:{self.name}] 真实 API 调用成功")
                    return result
                else:
                    logger.warning(f"[Tool:{self.name}] API 返回空，降级到模拟数据")
            except Exception as e:
                logger.warning(f"[Tool:{self.name}] API 调用失败: {e}，降级到模拟数据")

        # 降级到模拟数据
        logger.debug(f"[Tool:{self.name}] 使用模拟数据")
        return self._generate_mock_response(**kwargs)

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
    def _generate_mock_response(self, **kwargs) -> str:
        """
        生成模拟响应 (子类实现)

        Args:
            **kwargs: 工具参数

        Returns:
            模拟的响应内容
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

    def set_use_real_api(self, use_real: bool):
        """设置是否使用真实 API"""
        self._use_real_api = use_real
        logger.info(f"[Tool:{self.name}] 切换到 {'真实 API' if use_real else '模拟数据'}")


# 保留旧的基类名称以兼容
class BaseMockTool(BaseTool):
    """
    兼容旧版的基类

    新代码请直接使用 BaseTool
    """

    def _call_real_api(self, **kwargs) -> Optional[str]:
        """旧版工具不实现真实 API，直接返回 None"""
        return None


if __name__ == "__main__":
    # 测试

    class TestTool(BaseTool):
        def __init__(self):
            super().__init__(
                name="test_tool",
                description="测试工具"
            )

        def _call_real_api(self, query: str = "", **kwargs) -> Optional[str]:
            # 模拟 API 调用
            if query == "error":
                raise ValueError("模拟错误")
            return f"真实 API 响应: {query}"

        def _generate_mock_response(self, query: str = "", **kwargs) -> str:
            return f"模拟响应: {query}"

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

    print(f"\n使用真实 API: {tool._use_real_api}")
    print(f"正常调用: {tool.invoke(query='test')}")

    print(f"\n强制降级测试:")
    tool.set_use_real_api(False)
    print(f"模拟调用: {tool.invoke(query='test')}")

    print(f"\n错误降级测试:")
    tool.set_use_real_api(True)
    print(f"错误调用: {tool.invoke(query='error')}")
