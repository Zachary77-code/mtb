"""
格式验证器（12 模块完整性检查）
"""
import re
from typing import List, Tuple
from difflib import SequenceMatcher

from config.settings import REQUIRED_SECTIONS
from src.utils.logger import mtb_logger as logger


class FormatChecker:
    """
    报告格式验证器

    检查 Chair 生成的报告是否包含全部 12 个必选模块。
    """

    def __init__(self):
        self.required_sections = REQUIRED_SECTIONS

        # 中英文别名映射
        self.aliases = {
            "执行摘要": ["Executive Summary", "摘要", "Summary"],
            "患者概况": ["Patient Profile", "病人信息", "Patient Information"],
            "分子特征": ["Molecular Profile", "分子图谱", "Genomic Profile"],
            "治疗史回顾": ["Treatment History", "治疗历史", "Prior Treatment"],
            "药物/方案对比": ["Regimen Comparison", "方案对比", "Drug Comparison"],
            "器官功能与剂量": ["Organ Function & Dosing", "器官功能", "Dose Adjustment"],
            "治疗路线图": ["Treatment Roadmap", "治疗路径", "Treatment Plan"],
            "分子复查建议": ["Re-biopsy", "Liquid Biopsy", "分子监测", "复查建议"],
            "临床试验推荐": ["Clinical Trials", "临床试验", "Trial Recommendations"],
            "局部治疗建议": ["Local Therapy", "局部治疗", "Radiation", "手术"],
            "核心建议汇总": ["Core Recommendations", "建议汇总", "Key Recommendations"],
            "完整证据引用列表": ["Evidence Reference List", "证据引用", "完整引用列表", "References", "参考文献"],
            "证据等级说明": ["Evidence Grading", "证据等级", "Evidence Level"]
        }

    def validate(self, report_text: str) -> Tuple[bool, List[str]]:
        """
        验证报告是否包含所有必需模块

        Args:
            report_text: Chair 生成的报告文本

        Returns:
            (is_compliant, missing_sections)
        """
        logger.debug(f"[FORMAT] 开始验证，报告长度: {len(report_text) if report_text else 0}")

        if not report_text:
            logger.warning("[FORMAT] 报告为空，验证失败")
            return False, self.required_sections.copy()

        missing = []
        found = []

        for section in self.required_sections:
            if self._section_exists(section, report_text):
                found.append(section)
            else:
                missing.append(section)

        logger.debug(f"[FORMAT] 已找到模块: {found}")
        if missing:
            logger.warning(f"[FORMAT] 缺失模块 ({len(missing)}/12): {missing}")
        else:
            logger.info("[FORMAT] 全部 12 个模块验证通过")

        return (len(missing) == 0, missing)

    def _section_exists(self, section: str, text: str) -> bool:
        """
        检查模块是否存在

        支持:
        - 精确匹配
        - Markdown 标题匹配（## 或 ###）
        - 英文别名匹配
        - 模糊匹配（相似度 > 0.8）
        """
        # 预处理文本
        text_lower = text.lower()
        section_lower = section.lower()

        # 1. 精确匹配
        if section in text:
            return True

        # 2. Markdown 标题匹配
        patterns = [
            rf"##\s*\d*\.?\s*{re.escape(section)}",  # ## 1. 执行摘要
            rf"###\s*\d*\.?\s*{re.escape(section)}",  # ### 执行摘要
            rf"#\s*{re.escape(section)}",  # # 执行摘要
        ]

        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        # 3. 别名匹配
        aliases = self.aliases.get(section, [])
        for alias in aliases:
            if alias.lower() in text_lower:
                return True

            # Markdown 标题别名
            alias_patterns = [
                rf"##\s*\d*\.?\s*{re.escape(alias)}",
                rf"###\s*\d*\.?\s*{re.escape(alias)}",
            ]
            for pattern in alias_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return True

        # 4. 模糊匹配（检查每一行）
        lines = text.split('\n')
        for line in lines:
            # 只检查可能是标题的行（以 # 开头或较短）
            if line.startswith('#') or len(line) < 50:
                # 清理行
                clean_line = re.sub(r'^#+\s*\d*\.?\s*', '', line).strip().lower()

                # 计算相似度
                ratio = SequenceMatcher(None, section_lower, clean_line).ratio()
                if ratio > 0.8:
                    return True

                # 检查别名的模糊匹配
                for alias in aliases:
                    ratio = SequenceMatcher(None, alias.lower(), clean_line).ratio()
                    if ratio > 0.8:
                        return True

        return False

    def generate_feedback(self, missing_sections: List[str]) -> str:
        """
        生成反馈提示

        Args:
            missing_sections: 缺失的模块列表

        Returns:
            反馈提示文本
        """
        if not missing_sections:
            return "报告格式验证通过，包含全部 12 个必需模块。"

        feedback = f"""
报告格式验证失败！

**缺少以下必需模块** ({len(missing_sections)}/{len(self.required_sections)})：
"""
        for i, section in enumerate(missing_sections, 1):
            feedback += f"\n{i}. {section}"

        feedback += """

**请重新生成报告，确保包含所有 12 个必需章节。**

参考格式：
## 1. 执行摘要
[内容]

## 2. 患者概况
[内容]

...（共 13 个章节）

## 12. 完整证据引用列表
[由系统自动生成]
"""
        return feedback

    def check_references(self, report_text: str) -> Tuple[bool, int]:
        """
        检查引用是否存在

        Args:
            report_text: 报告文本

        Returns:
            (has_references, reference_count)
        """
        # 匹配 PMID 引用
        pmid_matches = re.findall(r'\[PMID:\s*\d+\]', report_text)

        # 匹配 NCT 引用
        nct_matches = re.findall(r'\[NCT\d+\]', report_text)

        # 匹配 [Ref] 标记
        ref_matches = re.findall(r'\[Ref\]', report_text)

        total = len(pmid_matches) + len(nct_matches) + len(ref_matches)

        return (total > 0, total)


if __name__ == "__main__":
    # 测试验证器
    checker = FormatChecker()

    # 测试完整报告
    test_report = """
    ## 1. 执行摘要
    这是摘要内容。

    ## 2. 患者概况
    患者信息。

    ## 3. 分子特征
    分子图谱。

    ## 4. 治疗史回顾
    既往治疗。

    ## 5. 药物/方案对比
    方案对比表。

    ## 6. 器官功能与剂量
    器官评估。

    ## 7. 治疗路线图
    治疗路径。

    ## 8. 分子复查建议
    复查计划。

    ## 9. 临床试验推荐
    试验列表。

    ## 10. 局部治疗建议
    局部治疗。

    ## 11. 核心建议汇总
    核心建议。

    ## 12. 参考文献
    [PMID: 12345678]
    """

    is_valid, missing = checker.validate(test_report)
    print(f"验证结果: {'通过' if is_valid else '失败'}")
    print(f"缺失模块: {missing if missing else '无'}")

    has_refs, count = checker.check_references(test_report)
    print(f"引用检查: {'通过' if has_refs else '失败'}, 数量: {count}")
