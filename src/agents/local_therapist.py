"""
Local Therapist Agent（局部治疗专家: 外科/放疗/介入）

负责基于病历原文评估手术、放疗和介入治疗方案，使用 NCCN 和 PubMed 工具查询相关指南和文献。
"""
from typing import Dict, Any

from src.agents.base_agent import BaseAgent
from src.tools.guideline_tools import NCCNTool
from src.tools.literature_tools import PubMedTool
from config.settings import LOCAL_THERAPIST_PROMPT_FILE


class LocalTherapistAgent(BaseAgent):
    """
    局部治疗专家 Agent（外科/放疗/介入）

    负责基于病历原文评估三大局部治疗方向:
    - 手术评估: 根治性手术/姑息性手术(缓解梗阻等)可行性
    - 放疗方案: 普通外照射/SBRT-SRS/质子/BNCT 适应证对比
    - 介入治疗: RFA/MWA/cryo 消融、放射性粒子(I-125/Pd-103)、HIFU
    - 局部-全身联合治疗评估
    - 使用 NCCN 查询指南推荐的局部治疗方案
    - 使用 PubMed 查询局部治疗相关文献
    """

    def __init__(self):
        tools = [
            NCCNTool(),        # NCCN 指南（局部治疗推荐）
            PubMedTool(),      # 文献检索（局部治疗相关）
        ]
        super().__init__(
            role="LocalTherapist",
            prompt_file=LOCAL_THERAPIST_PROMPT_FILE,
            tools=tools,
            temperature=0.3
        )

    def analyze(self, raw_pdf_text: str, **kwargs) -> Dict[str, Any]:
        """
        基于病历原文评估手术、放疗和介入治疗方案

        Args:
            raw_pdf_text: PDF 解析后的完整病历原文
            **kwargs: 额外参数

        Returns:
            包含分析报告和引用的字典
        """
        task_prompt = f"""
请基于以下病历原文评估局部治疗方案（手术、放疗、介入）:

**病历原文**:
{raw_pdf_text}

**分析任务**:
1. 首先从病历中提取局部治疗决策相关信息（肿瘤位置、大小、数量、与重要结构关系、分期、体能状态等）
2. 使用 search_nccn 查询该癌种的局部治疗指南推荐
3. 使用 search_pubmed 查询相关局部治疗文献

4. **手术评估**:
   - 根治性手术可行性评估（R0 切除可能性）
   - 姑息性手术需求评估（梗阻、出血、穿孔等急症处理）
   - 手术风险评估（合并症、体能状态、解剖因素）

5. **放疗方案评估**:
   - 普通外照射适应证和方案
   - SBRT/SRS 适应证和方案（寡转移、局部复发等）
   - 质子治疗适应证和优势分析
   - BNCT 适应证评估（如适用）
   - 各放疗技术适应证对比

6. **介入治疗评估**:
   - 消融治疗: RFA/MWA/冷冻消融适应证和对比
   - 放射性粒子植入: I-125/Pd-103 适应证
   - HIFU（超声聚焦刀）适应证
   - 介入栓塞治疗（TACE/HAIC 等，如适用）

7. **局部-全身联合评估**:
   - 局部治疗与全身治疗的时序安排
   - 联合治疗的增效/减毒考量

**输出格式**:
请输出完整的局部治疗评估报告，包含:
- 手术评估（根治/姑息，可行性分析）
- 放疗方案评估（各技术适应证对比）
- 介入治疗评估（各技术适应证对比）
- 局部-全身联合治疗评估
- 相关文献/指南支持（附 PMID 引用）

请确保报告完整详尽，不要省略任何重要信息。
"""
        result = self.invoke(task_prompt)

        # 生成完整报告（含工具调用详情和引用）
        full_report = self.generate_full_report(
            main_content=result["output"],
            title="Local Therapist Analysis Report"
        )

        return {
            "report": result["output"],
            "references": result["references"],
            "full_report_md": full_report
        }


if __name__ == "__main__":
    print("LocalTherapistAgent 模块加载成功")
