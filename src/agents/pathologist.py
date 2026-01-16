"""
Pathologist Agent（病例解析）
"""
import json
from typing import Dict, Any

from src.agents.base_agent import BaseAgent
from src.models.case_data import CaseData
from config.settings import PATHOLOGIST_PROMPT_FILE


class PathologistAgent(BaseAgent):
    """
    病理医生 Agent

    负责从非结构化病历文本中提取结构化数据。
    无需工具，直接使用 LLM 的信息提取能力。
    """

    def __init__(self):
        super().__init__(
            role="Pathologist",
            prompt_file=PATHOLOGIST_PROMPT_FILE,
            tools=[],  # 不需要工具
            temperature=0.0  # 结构化提取需要低温度
        )

    def parse_case(self, raw_text: str) -> Dict[str, Any]:
        """
        解析病例文本

        Args:
            raw_text: 原始病历文本

        Returns:
            结构化病例数据和解析错误
        """
        task_prompt = f"""
请从以下病历文本中提取结构化信息，输出为 JSON 格式。

**病历文本**:
{raw_text}

**要求**:
1. 严格按照 CaseData schema 输出
2. 缺失信息使用 null 或空列表
3. 不要添加解释，只输出 JSON
4. 确保 JSON 格式正确
"""

        result = self.invoke(task_prompt)
        output = result["output"]

        # 尝试解析 JSON
        try:
            # 提取 JSON 块（如果包裹在 ```json ``` 中）
            if "```json" in output:
                json_start = output.find("```json") + 7
                json_end = output.find("```", json_start)
                output = output[json_start:json_end].strip()
            elif "```" in output:
                json_start = output.find("```") + 3
                json_end = output.find("```", json_start)
                output = output[json_start:json_end].strip()

            parsed_data = json.loads(output)

            # 验证数据
            case_data = CaseData(**parsed_data)

            return {
                "structured_case": case_data.model_dump(),
                "parsing_errors": []
            }

        except json.JSONDecodeError as e:
            return {
                "structured_case": self._create_fallback_case(raw_text),
                "parsing_errors": [f"JSON解析错误: {str(e)}"]
            }

        except Exception as e:
            return {
                "structured_case": self._create_fallback_case(raw_text),
                "parsing_errors": [f"数据验证错误: {str(e)}"]
            }

    def _create_fallback_case(self, raw_text: str) -> Dict[str, Any]:
        """创建回退病例数据"""
        return {
            "primary_cancer": "未提取",
            "current_status": "unknown",
            "raw_text": raw_text,
            "molecular_profile": [],
            "treatment_lines": [],
            "organ_function": {}
        }


if __name__ == "__main__":
    print("PathologistAgent 模块加载成功")
