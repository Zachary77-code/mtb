"""
Pathologist Agent（病理学/影像学分析）

负责基于病历原文进行病理学和影像学分析，使用 PubMed 和 cBioPortal 工具查询相关数据。
"""
from typing import Dict, Any

from src.agents.base_agent import BaseAgent
from src.tools.literature_tools import PubMedTool
from src.tools.molecular_tools import cBioPortalTool
from config.settings import PATHOLOGIST_PROMPT_FILE


class PathologistAgent(BaseAgent):
    """
    病理医生 Agent

    负责基于病历原文进行病理学和影像学分析:
    - 分析病理学发现的临床意义
    - 解读影像学表现
    - 评估 IHC 标记物的意义
    - 使用 PubMed 查询病理相关文献
    - 使用 cBioPortal 查询组织学类型的突变频率
    """

    def __init__(self):
        tools = [
            PubMedTool(),      # 文献检索（病理相关）
            cBioPortalTool(),  # 组织学类型突变频率
        ]
        super().__init__(
            role="Pathologist",
            prompt_file=PATHOLOGIST_PROMPT_FILE,
            tools=tools,
            temperature=0.3  # 分析任务需要一定创造性
        )

    def analyze(self, raw_pdf_text: str) -> Dict[str, Any]:
        """
        基于病历原文进行病理学和影像学分析

        Args:
            raw_pdf_text: PDF 解析后的完整病历原文

        Returns:
            包含分析报告和引用的字典
        """
        task_prompt = f"""
请基于以下病历原文进行病理学和影像学分析:

**病历原文**:
{raw_pdf_text}

**分析任务**:
1. 首先从病历中提取关键病理信息（肿瘤类型、病理类型、分期、IHC 结果等）
2. 使用 search_pubmed 查询与该病理类型/组织学类型相关的文献（例如：特定组织学亚型的预后、治疗响应等）
3. 使用 search_cbioportal 查询该组织学类型在相应癌种中的突变频率分布
4. 分析病理学发现的临床意义
5. 解读影像学表现及其对分期/治疗的影响
6. 评估 IHC 标记物的意义（如 HER2、Ki-67、MMR 蛋白等）

**输出格式**:
请输出完整的病理学分析报告，包含:
- 病理学概况（肿瘤类型、组织学、分级、分期）
- IHC 标记物解读
- 影像学发现分析
- 相关文献支持（附 PMID 引用）
- 病理学角度的治疗提示

请确保报告完整详尽，不要省略任何重要信息。
"""
        result = self.invoke(task_prompt)
        return {
            "report": result["output"],
            "references": result["references"]
        }


if __name__ == "__main__":
    print("PathologistAgent 模块加载成功")
