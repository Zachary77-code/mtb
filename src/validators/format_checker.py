"""
格式验证器（6 章节 + 2 附录完整性检查）
"""
import re
from typing import List, Tuple, Dict
from difflib import SequenceMatcher

from config.settings import REQUIRED_SECTIONS, REQUIRED_SUBSECTIONS
from src.utils.logger import mtb_logger as logger


class FormatChecker:
    """
    报告格式验证器

    检查 Chair 生成的报告是否包含全部必选章节和子章节。
    """

    def __init__(self):
        self.required_sections = REQUIRED_SECTIONS
        self.required_subsections = REQUIRED_SUBSECTIONS

        # 中英文别名映射（6章节 + 2附录）
        self.aliases = {
            "病情概要": ["Patient Summary", "病情摘要", "Case Summary", "患者概况"],
            "治疗史回顾": ["Treatment History", "治疗历史", "Prior Treatment"],
            "治疗方案探索": ["Treatment Exploration", "治疗方案", "Treatment Options", "治疗路线图"],
            "整体与辅助支持": ["Supportive Care", "辅助支持", "整合支持", "Integrative Support"],
            "复查和追踪方案": ["Follow-up Plan", "复查方案", "追踪方案", "Monitoring Plan"],
            "核心建议汇总": ["Core Recommendations", "建议汇总", "Key Recommendations", "执行摘要"],
            "完整证据引用列表": ["Evidence Reference List", "证据引用", "完整引用列表", "References", "参考文献"],
            "证据等级说明": ["Evidence Grading", "证据等级", "Evidence Level", "L1-L5"],
        }

        # 子章节别名映射
        self.subsection_aliases = {
            "基础信息": ["Basic Information", "基本信息"],
            "诊断信息": ["Diagnosis", "诊断"],
            "分子信息": ["Molecular Profile", "分子特征", "分子图谱"],
            "合并症": ["Comorbidities", "合并疾病"],
            "过敏史": ["Allergy History", "药物过敏"],
            "过往治疗分析": ["Past Treatment Analysis", "过往治疗分析评价", "治疗分析"],
            "治疗手段Mapping": ["Treatment Mapping", "治疗Mapping", "全方位治疗手段", "全身治疗"],
            "治疗方案制定": ["Treatment Planning", "方案制定"],
            "治疗路径规划": ["Treatment Pathway", "路径规划", "治疗路线图"],
            "营养学方案": ["Nutrition Plan", "营养方案", "营养"],
            "替代疗法": ["Alternative Therapy", "替代医学", "整合医学", "CAM"],
            "常规复查时间线": ["Follow-up Timeline", "复查时间线", "常规复查"],
            "分子复查": ["Molecular Monitoring", "分子复查建议", "液体活检", "Re-biopsy"],
        }

    def validate(self, report_text: str) -> Tuple[bool, List[str]]:
        """
        验证报告是否包含所有必需章节

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

        logger.debug(f"[FORMAT] 已找到章节: {found}")
        if missing:
            logger.warning(f"[FORMAT] 缺失章节 ({len(missing)}/{len(self.required_sections)}): {missing}")
        else:
            logger.info(f"[FORMAT] 全部 {len(self.required_sections)} 个章节验证通过")

        return (len(missing) == 0, missing)

    def validate_subsections(self, report_text: str) -> Dict[str, List[str]]:
        """
        验证报告是否包含各章节的必选子章节

        Args:
            report_text: Chair 生成的报告文本

        Returns:
            {chapter: [missing_subsections]} — 空 dict 表示全部通过
        """
        if not report_text:
            return {ch: subs[:] for ch, subs in self.required_subsections.items()}

        missing_map = {}
        for chapter, subsections in self.required_subsections.items():
            missing_subs = []
            for sub in subsections:
                if not self._subsection_exists(sub, report_text):
                    missing_subs.append(sub)
            if missing_subs:
                missing_map[chapter] = missing_subs
                logger.warning(f"[FORMAT] 章节 '{chapter}' 缺失子章节: {missing_subs}")

        if not missing_map:
            logger.info("[FORMAT] 全部子章节验证通过")

        return missing_map

    def _section_exists(self, section: str, text: str) -> bool:
        """
        检查章节是否存在

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
            rf"##\s*\d*\.?\s*{re.escape(section)}",  # ## 1. 病情概要
            rf"###\s*\d*\.?\s*{re.escape(section)}",  # ### 病情概要
            rf"#\s*{re.escape(section)}",  # # 病情概要
            rf"##\s*附录\s*[A-Z]\.?\s*{re.escape(section)}",  # ## 附录A. 完整证据引用列表
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
                clean_line = re.sub(r'^#+\s*(?:附录\s*[A-Z]\.?\s*)?\d*\.?\s*', '', line).strip().lower()

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

    def _subsection_exists(self, subsection: str, text: str) -> bool:
        """检查子章节是否存在（精确 + 别名 + 标题匹配）"""
        text_lower = text.lower()

        # 精确匹配
        if subsection in text:
            return True

        # Markdown 标题匹配
        patterns = [
            rf"###\s*\d*\.?\d*\.?\s*{re.escape(subsection)}",
            rf"####\s*{re.escape(subsection)}",
        ]
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        # 别名匹配
        aliases = self.subsection_aliases.get(subsection, [])
        for alias in aliases:
            if alias.lower() in text_lower:
                return True

        return False

    def generate_feedback(self, missing_sections: List[str]) -> str:
        """
        生成反馈提示

        Args:
            missing_sections: 缺失的章节列表

        Returns:
            反馈提示文本
        """
        if not missing_sections:
            return f"报告格式验证通过，包含全部 {len(self.required_sections)} 个必需章节。"

        feedback = f"""
报告格式验证失败！

**缺少以下必需章节** ({len(missing_sections)}/{len(self.required_sections)})：
"""
        for i, section in enumerate(missing_sections, 1):
            feedback += f"\n{i}. {section}"

        feedback += f"""

**请重新生成报告，确保包含所有 {len(self.required_sections)} 个必需章节。**

参考格式：
## 1. 病情概要
[内容]

## 2. 治疗史回顾
[内容]

## 3. 治疗方案探索
[内容]

## 4. 整体与辅助支持
[内容]

## 5. 复查和追踪方案
[内容]

## 6. 核心建议汇总
[内容]

## 附录A. 完整证据引用列表
[由系统自动生成]

## 附录B. 证据等级说明
[内容]
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

        # 匹配 [[ref:...]] 标记
        ref_matches = re.findall(r'\[\[ref:', report_text)

        total = len(pmid_matches) + len(nct_matches) + len(ref_matches)

        return (total > 0, total)


if __name__ == "__main__":
    # 测试验证器
    checker = FormatChecker()

    # 测试完整报告 (新 6 章节 + 2 附录)
    test_report = """
    ## 1. 病情概要

    ### 1.1 基础信息
    患者信息。

    ### 1.2 诊断信息
    诊断详情。

    ### 1.3 分子信息
    分子特征。

    ### 1.4 合并症
    合并症信息。

    ### 1.5 过敏史
    无已知过敏。

    ## 2. 治疗史回顾
    既往治疗。

    ## 3. 治疗方案探索

    ### 3.1 过往治疗分析
    分析内容。

    ### 3.2 治疗手段Mapping
    矩阵内容。

    ### 3.3 治疗方案制定
    方案详情。

    ### 3.4 治疗路径规划
    路径详情。

    ## 4. 整体与辅助支持

    ### 4.1 营养学方案
    营养方案。

    ### 4.2 替代疗法
    替代疗法评估。

    ## 5. 复查和追踪方案

    ### 5.1 常规复查时间线
    复查计划。

    ### 5.2 分子复查
    分子监测。

    ## 6. 核心建议汇总
    核心建议。

    ## 附录A. 完整证据引用列表
    [PMID: 12345678]

    ## 附录B. 证据等级说明
    证据等级表。
    """

    is_valid, missing = checker.validate(test_report)
    print(f"章节验证: {'通过' if is_valid else '失败'}")
    print(f"缺失章节: {missing if missing else '无'}")

    missing_subs = checker.validate_subsections(test_report)
    print(f"子章节验证: {'通过' if not missing_subs else '失败'}")
    if missing_subs:
        for ch, subs in missing_subs.items():
            print(f"  {ch}: 缺失 {subs}")

    has_refs, count = checker.check_references(test_report)
    print(f"引用检查: {'通过' if has_refs else '失败'}, 数量: {count}")
