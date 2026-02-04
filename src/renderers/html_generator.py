"""
HTML 报告生成器

支持自定义块标记解析:
- :::exec-summary ... ::: 执行摘要块
- :::timeline ... ::: 治疗时间线
- :::roadmap ... ::: 治疗路线图
- [[ref:ID;;Title;;URL;;Note]] 内联引用 4字段（兼容旧 | 分隔符）
- [[ref:ID;;Title;;URL]] 内联引用 3字段（无 Note）
"""
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import yaml
from jinja2 import Environment, FileSystemLoader
import markdown
from loguru import logger

from config.settings import REPORTS_DIR


class HtmlReportGenerator:
    """
    HTML 报告生成器

    将 Markdown 格式的 MTB 报告渲染为带交互式引用的 HTML 文件。
    使用蓝白配色的简洁医疗风格。
    """

    def __init__(self):
        # 模板目录
        self.template_dir = Path(__file__).parent / "templates"
        self.template_dir.mkdir(exist_ok=True)

        # 确保模板存在
        self._ensure_templates()

        # Jinja2 环境
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=True
        )

        # observation 索引（用于引用 tooltip），在 generate() 中按需填充
        self._observation_index: Dict[str, Dict[str, Any]] = {}

    def _ensure_templates(self):
        """确保模板文件存在"""
        report_template = self.template_dir / "report.html"

        if not report_template.exists():
            self._create_default_template()

    def _create_default_template(self):
        """创建默认模板"""
        template_content = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MTB 报告 - {{ patient_id }}</title>
    <style>
        :root {
            --primary-blue: #1e40af;
            --light-blue: #3b82f6;
            --bg-blue: #eff6ff;
            --bg-white: #ffffff;
            --text-dark: #1f2937;
            --text-gray: #6b7280;
            --border-gray: #e5e7eb;
            --warning-red: #dc2626;
            --warning-bg: #fef2f2;
            --warning-yellow: #f59e0b;
            --success-green: #10b981;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, var(--bg-blue) 0%, var(--bg-white) 100%);
            color: var(--text-dark);
            line-height: 1.6;
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: var(--bg-white);
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(30, 64, 175, 0.1);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, var(--primary-blue) 0%, var(--light-blue) 100%);
            color: white;
            padding: 30px 40px;
        }

        .header h1 {
            font-size: 2em;
            margin-bottom: 10px;
        }

        .meta-info {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-top: 15px;
            font-size: 0.95em;
            opacity: 0.9;
        }

        .meta-info span {
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .content {
            padding: 40px;
        }

        h2 {
            color: var(--primary-blue);
            font-size: 1.5em;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--bg-blue);
        }

        h3 {
            color: var(--light-blue);
            font-size: 1.2em;
            margin-top: 20px;
            margin-bottom: 10px;
        }

        p {
            margin-bottom: 15px;
        }

        ul, ol {
            margin-left: 25px;
            margin-bottom: 15px;
        }

        li {
            margin-bottom: 8px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 0.95em;
        }

        th {
            background: var(--primary-blue);
            color: white;
            padding: 12px 15px;
            text-align: left;
            font-weight: 500;
        }

        td {
            padding: 12px 15px;
            border-bottom: 1px solid var(--border-gray);
        }

        tr:hover td {
            background: var(--bg-blue);
        }

        .warning-box {
            background: var(--warning-bg);
            border-left: 4px solid var(--warning-red);
            padding: 15px 20px;
            margin: 20px 0;
            border-radius: 0 8px 8px 0;
        }

        .warning-box strong {
            color: var(--warning-red);
        }

        .info-box {
            background: var(--bg-blue);
            border-left: 4px solid var(--light-blue);
            padding: 15px 20px;
            margin: 20px 0;
            border-radius: 0 8px 8px 0;
        }

        .reference {
            color: var(--light-blue);
            text-decoration: none;
            position: relative;
            cursor: pointer;
            transition: color 0.2s;
        }

        .reference:hover {
            color: var(--primary-blue);
            text-decoration: underline;
        }

        .tooltip {
            position: absolute;
            background: var(--text-dark);
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.85em;
            z-index: 100;
            max-width: 300px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }

        .evidence-tag {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: 500;
            margin-left: 5px;
        }

        .evidence-a { background: #dcfce7; color: #166534; }
        .evidence-b { background: #dbeafe; color: #1e40af; }
        .evidence-c { background: #fef3c7; color: #92400e; }
        .evidence-d { background: #fee2e2; color: #991b1b; }

        .footer {
            background: var(--bg-blue);
            padding: 20px 40px;
            text-align: center;
            color: var(--text-gray);
            font-size: 0.9em;
        }

        code {
            background: #f3f4f6;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Consolas', 'Monaco', monospace;
        }

        blockquote {
            border-left: 4px solid var(--light-blue);
            padding-left: 20px;
            margin: 15px 0;
            color: var(--text-gray);
            font-style: italic;
        }

        @media print {
            body { background: white; }
            .container { box-shadow: none; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>分子肿瘤委员会（MTB）报告</h1>
            <div class="meta-info">
                <span><strong>患者编号:</strong> {{ patient_id }}</span>
                <span><strong>肿瘤类型:</strong> {{ cancer_type }}</span>
                <span><strong>生成日期:</strong> {{ generation_date }}</span>
            </div>
        </div>

        <div class="content">
            {{ report_content | safe }}

            {% if warnings %}
            <div class="warning-box">
                <strong>⚠️ 安全警告</strong>
                <ul>
                {% for warning in warnings %}
                    <li>{{ warning }}</li>
                {% endfor %}
                </ul>
            </div>
            {% endif %}
        </div>

        <div class="footer">
            <p>本报告由 MTB 多智能体系统自动生成 | {{ generation_date }}</p>
            <p>⚠️ 本报告仅供参考，所有临床决策应由具有资质的医疗专业人员做出</p>
        </div>
    </div>
</body>
</html>'''

        template_path = self.template_dir / "report.html"
        with open(template_path, "w", encoding="utf-8") as f:
            f.write(template_content)

    # 证据等级排序（用于 observation index 去重时保留最高等级）
    _GRADE_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}

    def _build_observation_index(self, eg_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        从证据图数据构建 observation 索引

        用于根据 provenance / source_url 查找 observation 内容，
        在 HTML 渲染时为引用添加 tooltip 文本。

        Args:
            eg_data: 序列化的证据图字典 {entities: {...}, edges: {...}}

        Returns:
            {key: {statement, grade, source_tool, civic_type, provenance, source_url}}
            key 为 provenance 或 source_url
        """
        index: Dict[str, Dict[str, Any]] = {}

        def _index_observation(obs_data: Dict[str, Any]):
            prov = obs_data.get("provenance")
            url = obs_data.get("source_url")
            grade = obs_data.get("evidence_grade")
            entry = {
                "statement": obs_data.get("statement", ""),
                "grade": grade,
                "source_tool": obs_data.get("source_tool"),
                "civic_type": obs_data.get("civic_type"),
                "provenance": prov,
                "source_url": url,
                "source_agent": obs_data.get("source_agent"),
            }
            grade_rank = self._GRADE_ORDER.get(grade, 5) if grade else 5

            # 按 provenance 索引
            if prov:
                existing = index.get(prov)
                if not existing or grade_rank < self._GRADE_ORDER.get(existing.get("grade"), 5):
                    index[prov] = entry

            # 按 source_url 索引（额外索引路径）
            if url and url != prov:
                existing = index.get(url)
                if not existing or grade_rank < self._GRADE_ORDER.get(existing.get("grade"), 5):
                    index[url] = entry

        # 遍历所有实体的 observations
        for entity_data in eg_data.get("entities", {}).values():
            for obs_data in entity_data.get("observations", []):
                _index_observation(obs_data)

        # 遍历所有边的 observations
        for edge_data in eg_data.get("edges", {}).values():
            for obs_data in edge_data.get("observations", []):
                _index_observation(obs_data)

        return index

    def generate(
        self,
        raw_pdf_text: str,
        chair_synthesis: str,
        run_folder: str = None,
        evidence_graph_data: Dict[str, Any] = None
    ) -> str:
        """
        生成 HTML 报告

        Args:
            raw_pdf_text: 原始病历文本（用于提取患者信息）
            chair_synthesis: Chair 综合报告（Markdown，含完整证据引用列表）
            run_folder: 本次运行的报告文件夹路径（可选，若不提供则使用默认目录）
            evidence_graph_data: 序列化的证据图字典（可选，用于 observation tooltip）

        Returns:
            生成的 HTML 文件路径
        """
        # 构建 observation 索引（用于引用 tooltip）
        self._observation_index: Dict[str, Dict[str, Any]] = {}
        if evidence_graph_data and isinstance(evidence_graph_data, dict):
            self._observation_index = self._build_observation_index(evidence_graph_data)

        # 获取模板
        template = self.env.get_template("report.html")

        # 处理报告内容
        html_content = self._markdown_to_html(chair_synthesis)
        html_content = self._add_reference_links(html_content)
        html_content = self._add_evidence_tags(html_content)

        # 提取警告
        warnings = self._extract_warnings(chair_synthesis)

        # 从原始文本提取患者信息
        patient_id, cancer_type = self._extract_patient_info(raw_pdf_text, chair_synthesis)

        # 准备上下文
        context = {
            "patient_id": patient_id,
            "cancer_type": cancer_type,
            "generation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "report_content": html_content,
            "warnings": warnings
        }

        # 渲染模板
        final_html = template.render(context)

        # 确定保存目录
        if run_folder:
            output_dir = Path(run_folder)
            filename = "6_final_report.html"
        else:
            output_dir = REPORTS_DIR
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_patient_id = (context.get("patient_id") or "Unknown").replace("/", "_").replace("\\", "_")
            filename = f"MTB_Report_{safe_patient_id}_{timestamp}.html"

        filepath = output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(final_html)

        return str(filepath)

    def _markdown_to_html(self, md_text: str) -> str:
        """
        Markdown 转 HTML

        支持自定义块标记:
        - :::exec-summary ... ::: 执行摘要
        - :::timeline ... ::: 治疗时间线
        - :::roadmap ... ::: 治疗路线图
        - [[ref:ID;;Title;;URL;;Note]] 内联引用（4字段，兼容旧 | 分隔符）
        - [[ref:ID;;Title;;URL]] 内联引用（3字段，无 Note）

        Pipeline:
        1. 解析自定义块标记 → HTML，用占位符保护（防止 markdown 转义内部 HTML）
        2. 注入 markdown="1" 到用户编写的 <div> 标签（自定义块已被替换为占位符，不受影响）
        3. 标准 markdown 转换（tables 扩展原生处理表格，含单元格内 **bold** 等）
        4. 恢复自定义块 HTML
        5. 解析 [[ref:...]] 内联引用（在 markdown 转换之后，避免生成的 HTML 干扰表格解析）
        """
        # 1. 解析自定义块标记，输出的 HTML 用占位符保护
        #    防止 _inject_markdown_attr_to_divs 和 markdown 处理器破坏已渲染的 HTML
        _protected_blocks = {}
        _block_counter = [0]

        def _protect_block(html_block):
            key = f'\x00CUSTOMBLOCK{_block_counter[0]}\x00'
            _block_counter[0] += 1
            _protected_blocks[key] = html_block
            return key

        md_text = self._parse_custom_blocks(md_text, protect_fn=_protect_block)

        # 2. 注入 markdown="1" 到用户编写的 <div> 标签（自定义块已为占位符，不受影响）
        md_text = self._inject_markdown_attr_to_divs(md_text)

        # 3. 标准 Markdown 转换
        #    - tables: 原生处理 markdown 表格（含单元格内 inline markdown）
        #    - md_in_html: 处理 <div markdown="1"> 内部的 markdown 内容
        #    - nl2br: 作为 tree processor 在 tables block processor 之后运行，不会破坏表格
        html = markdown.markdown(
            md_text,
            extensions=[
                'tables',
                'fenced_code',
                'nl2br',
                'sane_lists',
                'md_in_html'
            ]
        )

        # 4. 恢复自定义块 HTML
        for key, value in _protected_blocks.items():
            html = html.replace(key, value)

        # 5. 解析 [[ref:...]] 内联引用（post-markdown，避免 HTML 片段干扰表格解析）
        html = self._parse_inline_refs(html)

        return html

    def _inject_markdown_attr_to_divs(self, md_text: str) -> str:
        """
        为 raw HTML <div> 标签注入 markdown="1" 属性。

        Python markdown 默认不处理 raw HTML 块（如 <div>）内部的 markdown 内容。
        添加 markdown="1" 属性后，md_in_html 扩展会处理这些块内的标题、表格、加粗等。
        """
        def add_markdown_attr(m):
            tag = m.group(0)
            if 'markdown=' in tag:
                return tag  # 已有属性，跳过
            return tag[:-1] + ' markdown="1">'

        return re.sub(r'<div\b[^>]*>', add_markdown_attr, md_text)

    def _parse_custom_blocks(self, text: str, protect_fn=None) -> str:
        """
        解析自定义块标记为 HTML。

        Args:
            text: 包含 ::: 块标记的 markdown 文本
            protect_fn: 可选回调函数。若提供，渲染后的 HTML 会传入此函数，
                        返回占位符字符串（防止后续 markdown 处理器破坏已渲染的 HTML）。
        """
        def _wrap(renderer):
            """包装渲染器，若有 protect_fn 则保护输出"""
            def replacer(m):
                html = renderer(m.group(1))
                return protect_fn(html) if protect_fn else html
            return replacer

        # 解析 :::exec-summary 块
        text = re.sub(
            r':::exec-summary\s*\n(.*?)\n?:::',
            _wrap(self._render_exec_summary),
            text,
            flags=re.DOTALL
        )

        # 解析 :::timeline 块
        text = re.sub(
            r':::timeline\s*\n(.*?)\n?:::',
            _wrap(self._render_timeline),
            text,
            flags=re.DOTALL
        )

        # 解析 :::roadmap 块
        text = re.sub(
            r':::roadmap\s*\n(.*?)\n?:::',
            _wrap(self._render_roadmap),
            text,
            flags=re.DOTALL
        )

        return text

    def _parse_yaml_content(self, content: str) -> Any:
        """安全解析 YAML 内容"""
        try:
            # Strip whitespace and parse
            cleaned_content = content.strip()
            result = yaml.safe_load(cleaned_content)
            return result
        except Exception as e:
            # Log the actual error for debugging
            logger.warning(f"YAML parsing failed: {e}\nContent preview: {content[:200]}")
            return None

    def _render_exec_summary(self, content: str) -> str:
        """渲染执行摘要块"""
        data = self._parse_yaml_content(content)

        if not data or not isinstance(data, dict):
            # 回退：简单文本解析
            lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
            html = '<div class="exec-summary"><h3>执行摘要</h3><ul>'
            for line in lines:
                if ':' in line:
                    key, val = line.split(':', 1)
                    html += f'<li><strong>{key.strip()}:</strong> {val.strip()}</li>'
                else:
                    html += f'<li>{line}</li>'
            html += '</ul></div>'
            return html

        # YAML 解析成功
        html = '<div class="exec-summary"><h3>执行摘要</h3><ul>'
        for key, val in data.items():
            html += f'<li><strong>{key}:</strong> {val}</li>'
        html += '</ul></div>'
        return html

    def _parse_timeline_items(self, content: str) -> List[Dict[str, str]]:
        """
        自定义时间线解析器（替代 yaml.safe_load）

        逐行解析 YAML-like 时间线格式，避免 yaml.safe_load 在特殊值
        （如 response: - 裸横杠、包含冒号的值）上的解析失败。

        Args:
            content: :::timeline 块内的文本

        Returns:
            解析后的时间线项目列表
        """
        items: List[Dict[str, str]] = []
        current_item: Dict[str, str] = {}
        known_keys = {"line", "date", "regimen", "response", "type", "note"}

        for raw_line in content.split('\n'):
            stripped = raw_line.strip()
            if not stripped:
                continue

            # 新条目起始: "- key: value"
            if stripped.startswith('- '):
                if current_item:
                    items.append(current_item)
                current_item = {}
                stripped = stripped[2:].strip()  # 去掉 "- "

            # 解析 "key: value"（用 partition 处理值中包含冒号的情况）
            if ':' in stripped:
                key, _, value = stripped.partition(':')
                key = key.strip().lower()
                value = value.strip()
                if key in known_keys:
                    # 处理 yaml 特殊值：裸横杠 "-" 表示无数据
                    if value == '-':
                        value = '-'
                    current_item[key] = value

        # 最后一个条目
        if current_item:
            items.append(current_item)

        return items

    def _render_timeline(self, content: str) -> str:
        """渲染治疗时间线"""
        # 优先使用自定义解析器（更健壮）
        data = self._parse_timeline_items(content)

        # 回退：尝试 yaml.safe_load
        if not data:
            yaml_data = self._parse_yaml_content(content)
            if yaml_data and isinstance(yaml_data, list):
                data = yaml_data

        # 最终回退：格式化文本显示
        if not data:
            # 将原始文本按条目格式化，而非显示为一段纯文本
            lines = [l.strip() for l in content.strip().split('\n') if l.strip()]
            html = '<div class="treatment-timeline">'
            for line in lines:
                if line.startswith('- '):
                    line = line[2:]
                html += f'<div class="treatment-item"><div class="treatment-content"><p>{line}</p></div></div>'
            html += '</div>'
            return html

        html = '<div class="treatment-timeline">'

        for item in data:
            if not isinstance(item, dict):
                continue

            item_type = str(item.get('type', ''))
            line = str(item.get('line', ''))
            date = str(item.get('date', ''))
            regimen = str(item.get('regimen', ''))
            response = str(item.get('response', ''))
            note = str(item.get('note', ''))

            # 确定标记样式类
            marker_class = self._get_marker_class(item_type)
            badge_class = self._get_response_badge(response)

            html += f'''
            <div class="treatment-item {item_type}">
              <div class="treatment-marker {marker_class}">{line}</div>
              <div class="treatment-content">
                <div class="treatment-header">
                  <span class="treatment-date">{date}</span>
                  <span class="badge {badge_class}">{response}</span>
                </div>
                <div class="treatment-body"><strong>{regimen}</strong></div>
                {f'<div class="treatment-note">{note}</div>' if note else ''}
              </div>
            </div>'''

        html += '</div>'
        return html

    def _render_roadmap(self, content: str) -> str:
        """渲染治疗路线图卡片"""
        data = self._parse_yaml_content(content)

        if not data or not isinstance(data, list):
            # 回退：简单文本显示
            return f'<div class="card-grid"><div class="card"><p>{content}</p></div></div>'

        html = '<div class="card-grid">'

        for item in data:
            if not isinstance(item, dict):
                continue

            title = item.get('title', '')
            status = item.get('status', '')
            regimen = item.get('regimen', '')
            actions = item.get('actions', [])

            # 根据状态确定边框颜色
            color = self._get_status_color(status)

            actions_html = ''
            if actions:
                items = []
                for a in actions:
                    if isinstance(a, dict):
                        # YAML parsed "key: value" as dict; flatten back to string
                        items.extend(f'{k}: {v}' for k, v in a.items())
                    else:
                        items.append(str(a))
                actions_html = '<ul>' + ''.join(f'<li>{item}</li>' for item in items) + '</ul>'

            html += f'''
            <div class="card" style="border-left: 4px solid {color};">
              <div class="card-header">{title}</div>
              <p><strong>{regimen}</strong></p>
              {actions_html}
            </div>'''

        html += '</div>'
        return html

    def _is_nccn_citation(self, ref_id: str, url: str, title: str) -> bool:
        """判断是否为 NCCN 引用（需要特殊处理：仅 tooltip，不可点击跳转）"""
        ref_id_upper = ref_id.strip().upper()
        if ref_id_upper.startswith("NCCN"):
            return True
        if url and "nccn.org" in url.lower():
            return True
        if title and title.strip().upper().startswith("NCCN"):
            return True
        # 检查 observation index 中是否为 NCCN 工具来源
        obs = self._observation_index.get(url) or self._observation_index.get(ref_id)
        if obs and obs.get("source_tool") == "search_nccn":
            return True
        return False

    def _get_tooltip_text(self, ref_id: str, url: str, title: str, note: str) -> str:
        """
        获取引用的 tooltip 文本

        优先从 observation index 查找 statement + grade，
        否则回退到 title: note 格式。
        """
        # 尝试从 observation index 查找
        obs = (self._observation_index.get(ref_id) or
               self._observation_index.get(url) or
               self._observation_index.get(title))
        if obs and obs.get("statement"):
            # 去除 HTML 标签，防止嵌套 tooltip
            statement = re.sub(r'<[^>]+>', '', obs['statement'])
            grade = obs.get("grade")
            grade_str = f" [{grade}]" if grade else ""
            tool = obs.get("source_tool") or ""
            tool_str = f" ({tool})" if tool else ""
            return f"{statement}{grade_str}{tool_str}"

        # 回退：使用 citation 自带的 title + note
        if title and note:
            return f"{title}: {note}"
        return title or note or ref_id

    def _render_nccn_citation(self, ref_id: str, tooltip_text: str) -> str:
        """渲染 NCCN 引用（tooltip-only，不可点击跳转）"""
        safe_tooltip = tooltip_text.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
        return (
            f'<span class="ref-tooltip nccn-ref">'
            f'<span class="cite cite-nccn">[NCCN]</span>'
            f'<span class="ref-text">{safe_tooltip}</span>'
            f'</span>'
        )

    def _render_standard_citation(self, ref_id: str, url: str, tooltip_text: str) -> str:
        """渲染标准引用（可点击跳转 + hover tooltip）"""
        safe_tooltip = tooltip_text.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
        safe_url = url.replace('"', '&quot;')
        safe_id = ref_id.replace('<', '&lt;').replace('>', '&gt;')
        return (
            f'<span class="ref-tooltip">'
            f'<a class="cite" href="{safe_url}" target="_blank">[{safe_id}]</a>'
            f'<span class="ref-text">{safe_tooltip}</span>'
            f'</span>'
        )

    def _render_citation(self, ref_id: str, title: str, url: str, note: str) -> str:
        """根据引用类型渲染为 NCCN 或标准引用 HTML"""
        tooltip_text = self._get_tooltip_text(ref_id, url, title, note)
        if self._is_nccn_citation(ref_id, url, title):
            return self._render_nccn_citation(ref_id, tooltip_text)
        return self._render_standard_citation(ref_id, url, tooltip_text)

    def _convert_markdown_tables(self, md_text: str) -> str:
        """
        [DEPRECATED] 不再使用。原生 tables 扩展已能正确处理表格。

        原设计：将 Markdown 表格预转换为 HTML <table>，防止 nl2br 破坏表格。
        问题：跳过了单元格内的 inline markdown（如 **bold**），且与 [[ref:]] 解析冲突。
        """
        lines = md_text.split('\n')
        result = []
        i = 0

        while i < len(lines):
            stripped = lines[i].strip()

            # 检测表格起始：行以 | 开头且包含多个 |
            if stripped.startswith('|') and stripped.count('|') >= 3:
                table_lines = []
                # 收集连续的表格行
                while i < len(lines) and lines[i].strip().startswith('|'):
                    table_lines.append(lines[i].strip())
                    i += 1

                # 至少需要 2 行（表头 + 分隔符）才算有效表格
                if len(table_lines) >= 2:
                    html_table = self._markdown_table_to_html(table_lines)
                    result.append(html_table)
                else:
                    result.extend(table_lines)
            else:
                result.append(lines[i])
                i += 1

        return '\n'.join(result)

    def _markdown_table_to_html(self, table_lines: list) -> str:
        """[DEPRECATED] 不再使用。由 _convert_markdown_tables 调用，现已废弃。"""

        def parse_row(line: str) -> list:
            """解析一行表格，返回单元格列表。"""
            # 去掉首尾 |，按 | 分割
            line = line.strip()
            if line.startswith('|'):
                line = line[1:]
            if line.endswith('|'):
                line = line[:-1]
            return [cell.strip() for cell in line.split('|')]

        def is_separator(line: str) -> bool:
            """判断是否为分隔行（如 |---|---|---|）"""
            cells = parse_row(line)
            return all(re.match(r'^:?-+:?$', c.strip()) for c in cells if c.strip())

        html_parts = ['<table>']

        # 查找分隔行位置
        sep_idx = None
        for idx, line in enumerate(table_lines):
            if is_separator(line):
                sep_idx = idx
                break

        if sep_idx is not None and sep_idx > 0:
            # 有表头：分隔行之前为 thead，之后为 tbody
            html_parts.append('<thead>')
            for h_line in table_lines[:sep_idx]:
                cells = parse_row(h_line)
                html_parts.append('<tr>' + ''.join(f'<th>{c}</th>' for c in cells) + '</tr>')
            html_parts.append('</thead>')

            html_parts.append('<tbody>')
            for d_line in table_lines[sep_idx + 1:]:
                if is_separator(d_line):
                    continue
                cells = parse_row(d_line)
                html_parts.append('<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>')
            html_parts.append('</tbody>')
        else:
            # 无分隔行：全部为 tbody
            html_parts.append('<tbody>')
            for d_line in table_lines:
                if is_separator(d_line):
                    continue
                cells = parse_row(d_line)
                html_parts.append('<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>')
            html_parts.append('</tbody>')

        html_parts.append('</table>')
        return '\n'.join(html_parts)

    def _parse_inline_refs_in_markdown(self, md_text: str) -> str:
        """
        [DEPRECATED] 不再使用。[[ref:...]] 解析已移至 _parse_inline_refs()（post-markdown）。

        原设计：在 markdown 转换前解析引用，避免 | 与表格冲突。
        问题：生成的 HTML 片段干扰了后续表格单元格解析，导致 <a href="...]] 等残缺标签。
        现在 [[ref:...]] 使用 ;; 分隔符，不与表格 | 冲突，可在 markdown 转换后安全解析。
        """
        # 4字段格式：;; 分隔符（优先匹配，避免3字段模式吞掉4字段的前3组）
        pattern_4field = r'\[\[ref:([^;]+);;([^;]+);;([^;]+);;([^\]]+)\]\]'

        def replacer_4field(m):
            ref_id, title, url, note = [s.strip() for s in m.groups()]
            return self._render_citation(ref_id, title, url, note)

        md_text = re.sub(pattern_4field, replacer_4field, md_text)

        # 3字段格式：;; 分隔符，无 Note（Chair LLM 常生成此格式）
        pattern_3field = r'\[\[ref:([^;]+);;([^;]+);;([^\]]+)\]\]'

        def replacer_3field(m):
            ref_id, title, url = [s.strip() for s in m.groups()]
            return self._render_citation(ref_id, title, url, "")

        md_text = re.sub(pattern_3field, replacer_3field, md_text)

        # 旧格式：| 分隔符（向后兼容，仅在非表格行中匹配）
        # 使用更严格的匹配：要求 URL 以 http 开头
        pattern_legacy = r'\[\[ref:([^|\]]+)\|([^|\]]+)\|(https?://[^|\]]+)\|([^\]]+)\]\]'

        def replacer_legacy(m):
            ref_id, title, url, note = [s.strip() for s in m.groups()]
            return self._render_citation(ref_id, title, url, note)

        md_text = re.sub(pattern_legacy, replacer_legacy, md_text)

        return md_text

    def _parse_inline_refs(self, html: str) -> str:
        """
        解析 [[ref:...]] 内联引用标记，转换为 tooltip HTML。

        在 markdown 转 HTML 之后运行。[[ref:...]] 使用 ;; 分隔符，
        不与 markdown 表格的 | 分隔符冲突，因此可安全地在 post-markdown 阶段解析。

        支持格式（按优先级）：
        - 4字段: [[ref:ID;;Title;;URL;;Note]]
        - 3字段: [[ref:ID;;Title;;URL]]（无 Note）
        - 旧格式: [[ref:ID|Title|URL|Note]]（向后兼容）
        """
        # 4字段格式 ;; 分隔符
        # 注意：中间组使用 [^;\]]+ 排除 ; 和 ]，防止跨 ]] 边界贪婪匹配多个 ref
        pattern_4field = r'\[\[ref:([^;\]]+);;([^;\]]+);;([^;\]]+);;([^\]]+)\]\]'

        def replacer_4field(m):
            ref_id, title, url, note = [s.strip() for s in m.groups()]
            return self._render_citation(ref_id, title, url, note)

        html = re.sub(pattern_4field, replacer_4field, html)

        # 3字段格式 ;; 分隔符（无 Note）
        # 注意：中间组使用 [^;\]]+ 排除 ; 和 ]，防止跨 ]] 边界贪婪匹配
        pattern_3field = r'\[\[ref:([^;\]]+);;([^;\]]+);;([^\]]+)\]\]'

        def replacer_3field(m):
            ref_id, title, url = [s.strip() for s in m.groups()]
            return self._render_citation(ref_id, title, url, "")

        html = re.sub(pattern_3field, replacer_3field, html)

        # 旧格式 | 分隔符（兜底）
        pattern_legacy = r'\[\[ref:([^|]+)\|([^|]+)\|([^|]+)\|([^\]]+)\]\]'
        html = re.sub(pattern_legacy, replacer_4field, html)

        return html

    def _get_marker_class(self, item_type: str) -> str:
        """获取时间线标记的 CSS 类"""
        type_map = {
            'neoadjuvant': 'neoadjuvant',
            'surgery': 'surgery',
            'adjuvant': 'adjuvant',
            'maint': 'maint',
            'pd': 'pd',
            'current': 'current',
            'event': 'event',
        }
        return type_map.get(item_type.lower(), '')

    def _get_response_badge(self, response: str) -> str:
        """获取疗效响应的 badge 类"""
        response_lower = response.lower() if response else ''
        if response_lower in ['cr', 'pr', 'sd', 'trg1', 'trg2']:
            return 'badge-success'
        elif response_lower in ['pd', 'progression']:
            return 'badge-danger'
        elif response_lower in ['ne', 'unknown']:
            return 'badge-secondary'
        else:
            return 'badge-info'

    def _get_status_color(self, status: str) -> str:
        """获取路线图卡片的状态颜色"""
        status_map = {
            'current': 'var(--warning)',
            'success': 'var(--success)',
            'danger': 'var(--danger)',
            'pending': 'var(--secondary)',
            'completed': 'var(--success)',
        }
        return status_map.get(status.lower(), 'var(--primary)')

    def _add_reference_links(self, html: str) -> str:
        """
        将剩余的引用模式转换为上标 tooltip 格式

        处理未被 [[ref:...]] 覆盖的引用：
        - 裸 [PMID: xxx] → 上标 tooltip（observation lookup）
        - 裸 [NCTxxx] → 上标 tooltip（observation lookup）
        - 裸 [NCCN: xxx] → NCCN tooltip（仅 hover）
        - markdown 生成的 <a> 引用链接 → 上标 tooltip
        """
        # 0. 保护已有 ref-tooltip span 整体内容，防止嵌套 tooltip
        _protected_spans = {}
        _protect_counter = [0]

        def _protect_ref_tooltip(m):
            key = f'\x00REFTOOLTIP{_protect_counter[0]}\x00'
            _protect_counter[0] += 1
            _protected_spans[key] = m.group(0)
            return key

        html = re.sub(
            r'<span class="ref-tooltip[^"]*">.*?</span>\s*</span>',
            _protect_ref_tooltip,
            html,
            flags=re.DOTALL
        )

        # 1. 转换裸 [PMID: xxx]（未被 markdown 转为链接的）
        def _pmid_replacer(m):
            pmid = m.group(1)
            prov_key = f"PMID:{pmid}"
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            tooltip = self._get_tooltip_text(prov_key, url, f"PMID: {pmid}", "")
            return self._render_standard_citation(f"PMID: {pmid}", url, tooltip)

        html = re.sub(r'\[PMID:\s*(\d+)\](?!\()', _pmid_replacer, html)

        # 2. 转换裸 [NCTxxx]（未被 markdown 转为链接的）
        def _nct_replacer(m):
            nct_id = m.group(1)
            url = f"https://clinicaltrials.gov/study/{nct_id}"
            tooltip = self._get_tooltip_text(nct_id, url, nct_id, "")
            return self._render_standard_citation(nct_id, url, tooltip)

        html = re.sub(r'\[(NCT\d+)\](?!\()', _nct_replacer, html)

        # 3. 转换裸 [NCCN: xxx]（未被 markdown 转为链接的）
        def _nccn_replacer(m):
            nccn_text = m.group(1)
            tooltip = self._get_tooltip_text(f"NCCN:{nccn_text}", "", f"NCCN: {nccn_text}", "")
            return self._render_nccn_citation("NCCN", tooltip)

        html = re.sub(r'\[NCCN:\s*([^\]]+)\](?!\()', _nccn_replacer, html)

        # 4. 转换 markdown 生成的 <a> 引用链接为上标 tooltip
        # 匹配: <a href="url">PMID: xxx</a> 或 <a href="url">NCTxxx</a> 或 <a href="url">NCCN: xxx</a>
        def _anchor_replacer(m):
            url = m.group(1)
            text = m.group(2)

            # PMID 链接
            pmid_match = re.match(r'PMID:\s*(\d+)', text)
            if pmid_match:
                prov_key = f"PMID:{pmid_match.group(1)}"
                tooltip = self._get_tooltip_text(prov_key, url, text, "")
                return self._render_standard_citation(text, url, tooltip)

            # NCT 链接
            nct_match = re.match(r'(NCT\d+)', text)
            if nct_match:
                tooltip = self._get_tooltip_text(nct_match.group(1), url, text, "")
                return self._render_standard_citation(text, url, tooltip)

            # NCCN 链接
            nccn_match = re.match(r'NCCN[:\s]', text, re.IGNORECASE)
            if nccn_match or 'nccn.org' in url.lower():
                tooltip = self._get_tooltip_text(text, url, text, "")
                return self._render_nccn_citation("NCCN", tooltip)

            # CIViC 链接
            if 'civicdb.org' in url.lower() or text.lower().startswith('civic'):
                tooltip = self._get_tooltip_text(text, url, text, "")
                return self._render_standard_citation(text, url, tooltip)

            # cBioPortal 链接
            if 'cbioportal.org' in url.lower() or text.lower().startswith('cbioportal'):
                tooltip = self._get_tooltip_text(text, url, text, "")
                return self._render_standard_citation(text, url, tooltip)

            # FDA 链接
            if 'fda.gov' in url.lower() or text.lower().startswith('fda'):
                tooltip = self._get_tooltip_text(text, url, text, "")
                return self._render_standard_citation(text, url, tooltip)

            # 其他链接保持原样
            return m.group(0)

        html = re.sub(
            r'<a\s+href="([^"]+)"[^>]*>([^<]+)</a>',
            _anchor_replacer,
            html
        )

        # 5. 恢复被保护的 ref-tooltip span 内容
        for key, value in _protected_spans.items():
            html = html.replace(key, value)

        return html

    def _add_evidence_tags(self, html: str) -> str:
        """添加证据等级标签"""
        evidence_map = {
            r'\[Evidence A\]': '<span class="evidence-tag evidence-a">Evidence A</span>',
            r'\[Evidence B\]': '<span class="evidence-tag evidence-b">Evidence B</span>',
            r'\[Evidence C\]': '<span class="evidence-tag evidence-c">Evidence C</span>',
            r'\[Evidence D\]': '<span class="evidence-tag evidence-d">Evidence D</span>',
        }

        for pattern, replacement in evidence_map.items():
            html = re.sub(pattern, replacement, html, flags=re.IGNORECASE)

        return html

    def _extract_warnings(self, text: str) -> List[str]:
        """提取安全警告"""
        warnings = []
        lines = text.split('\n')

        for line in lines:
            stripped = line.strip()
            # 跳过 markdown 表格行（以 | 开头），避免将表格内容误提取为警告
            if stripped.startswith('|'):
                continue
            if '⚠️' in stripped or '❌' in stripped:
                clean = stripped.lstrip('#').strip()
                if clean and clean not in warnings:
                    warnings.append(clean)

        return warnings[:5]  # 限制数量

    def _extract_patient_info(self, raw_pdf_text: str, chair_synthesis: str) -> tuple:
        """
        从原始文本或综合报告中提取患者信息

        Args:
            raw_pdf_text: 原始病历文本
            chair_synthesis: Chair 综合报告

        Returns:
            (patient_id, cancer_type) 元组
        """
        patient_id = "Unknown"
        cancer_type = "未知"

        # 合并文本进行搜索
        combined_text = f"{raw_pdf_text}\n{chair_synthesis}"

        # 尝试提取患者编号 (多种格式)
        id_patterns = [
            r'患者编号[：:]\s*([A-Za-z0-9\-_]+)',
            r'病历号[：:]\s*([A-Za-z0-9\-_]+)',
            r'住院号[：:]\s*([A-Za-z0-9\-_]+)',
            r'门诊号[：:]\s*([A-Za-z0-9\-_]+)',
            r'Patient\s*ID[：:]\s*([A-Za-z0-9\-_]+)',
        ]

        for pattern in id_patterns:
            match = re.search(pattern, combined_text, re.IGNORECASE)
            if match:
                patient_id = match.group(1)
                break

        # 尝试提取肿瘤类型
        cancer_patterns = [
            r'(?:诊断|肿瘤类型|癌症类型)[：:]\s*([^\n,，。]+)',
            r'((?:非小细胞|小细胞)?肺癌|乳腺癌|结直肠癌|胃癌|肝癌|胰腺癌|卵巢癌|前列腺癌|食管癌|甲状腺癌|膀胱癌|肾癌|黑色素瘤)',
            r'(NSCLC|SCLC|Lung\s*Cancer|Breast\s*Cancer|Colorectal\s*Cancer)',
        ]

        for pattern in cancer_patterns:
            match = re.search(pattern, combined_text, re.IGNORECASE)
            if match:
                cancer_type = match.group(1).strip()
                break

        return patient_id, cancer_type


if __name__ == "__main__":
    print("HTML 报告生成器模块加载成功")
    print(f"报告目录: {REPORTS_DIR}")

    # 创建生成器实例（确保模板存在）
    generator = HtmlReportGenerator()
    print(f"模板目录: {generator.template_dir}")
