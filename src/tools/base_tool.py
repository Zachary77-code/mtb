"""
工具基类（占位符实现）
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
import json


class BaseMockTool(ABC):
    """
    占位符工具基类

    所有工具都继承此类，并实现 _generate_mock_response 方法。
    未来替换为真实 API 时，只需修改子类实现。
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def invoke(self, **kwargs) -> str:
        """
        调用工具

        Args:
            **kwargs: 工具参数（如 gene, variant, cancer_type 等）

        Returns:
            工具响应（字符串格式）
        """
        return self._generate_mock_response(**kwargs)

    @abstractmethod
    def _generate_mock_response(self, **kwargs) -> str:
        """
        生成模拟响应（子类实现）

        Args:
            **kwargs: 工具参数

        Returns:
            模拟的响应内容
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

    @abstractmethod
    def _get_parameters_schema(self) -> Dict[str, Any]:
        """
        获取参数 JSON Schema（子类实现）

        Returns:
            参数 schema
        """
        pass


if __name__ == "__main__":
    # 测试基类
    class TestTool(BaseMockTool):
        def __init__(self):
            super().__init__(
                name="test_tool",
                description="测试工具"
            )

        def _generate_mock_response(self, **kwargs) -> str:
            return f"测试响应: {kwargs}"

        def _get_parameters_schema(self) -> Dict[str, Any]:
            return {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }

    tool = TestTool()
    print("工具名称:", tool.name)
    print("OpenAI 格式:", json.dumps(tool.to_openai_function(), indent=2, ensure_ascii=False))
    print("调用结果:", tool.invoke(query="测试"))
