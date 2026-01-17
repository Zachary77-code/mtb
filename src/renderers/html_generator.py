"""
HTML 报告生成器

支持自定义块标记解析:
- :::exec-summary ... ::: 执行摘要块
- :::timeline ... ::: 治疗时间线
- :::roadmap ... ::: 治疗路线图
- [[ref:ID|Title|URL|Note]] 内联引用
"""
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import yaml
from jinja2 import Environment, FileSystemLoader
import markdown

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

            {% if references %}
            <h2>参考文献</h2>
            <ol>
            {% for ref in references %}
                <li>
                    <a href="{{ ref.url }}" class="reference" target="_blank">
                        [{{ ref.type }}: {{ ref.id }}]
                    </a>
                </li>
            {% endfor %}
            </ol>
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

    def generate(
        self,
        structured_case: Dict[str, Any],
        chair_synthesis: str,
        references: List[Dict[str, str]]
    ) -> str:
        """
        生成 HTML 报告

        Args:
            structured_case: 结构化病例数据
            chair_synthesis: Chair 综合报告（Markdown）
            references: 引用列表

        Returns:
            生成的 HTML 文件路径
        """
        # 获取模板
        template = self.env.get_template("report.html")

        # 处理报告内容
        html_content = self._markdown_to_html(chair_synthesis)
        html_content = self._add_reference_links(html_content)
        html_content = self._add_evidence_tags(html_content)

        # 提取警告
        warnings = self._extract_warnings(chair_synthesis)

        # 准备上下文
        context = {
            "patient_id": structured_case.get("patient_id", "Unknown"),
            "cancer_type": structured_case.get("primary_cancer", "未知"),
            "generation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "report_content": html_content,
            "references": references,
            "warnings": warnings
        }

        # 渲染模板
        final_html = template.render(context)

        # 保存文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        patient_id = context.get("patient_id") or "Unknown"
        patient_id = patient_id.replace("/", "_").replace("\\", "_")
        filename = f"MTB_Report_{patient_id}_{timestamp}.html"
        filepath = REPORTS_DIR / filename

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
        - [[ref:ID|Title|URL|Note]] 内联引用
        """
        # 1. 先解析自定义块标记
        md_text = self._parse_custom_blocks(md_text)

        # 2. 标准 Markdown 转换
        html = markdown.markdown(
            md_text,
            extensions=[
                'tables',
                'fenced_code',
                'nl2br',
                'sane_lists'
            ]
        )

        # 3. 解析内联引用
        html = self._parse_inline_refs(html)

        return html

    def _parse_custom_blocks(self, text: str) -> str:
        """解析自定义块标记为 HTML"""
        # 解析 :::exec-summary 块
        text = re.sub(
            r':::exec-summary\s*\n(.*?)\n:::',
            lambda m: self._render_exec_summary(m.group(1)),
            text,
            flags=re.DOTALL
        )

        # 解析 :::timeline 块
        text = re.sub(
            r':::timeline\s*\n(.*?)\n:::',
            lambda m: self._render_timeline(m.group(1)),
            text,
            flags=re.DOTALL
        )

        # 解析 :::roadmap 块
        text = re.sub(
            r':::roadmap\s*\n(.*?)\n:::',
            lambda m: self._render_roadmap(m.group(1)),
            text,
            flags=re.DOTALL
        )

        return text

    def _parse_yaml_content(self, content: str) -> Any:
        """安全解析 YAML 内容"""
        try:
            return yaml.safe_load(content)
        except Exception:
            # 如果 YAML 解析失败，返回空
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

    def _render_timeline(self, content: str) -> str:
        """渲染治疗时间线"""
        data = self._parse_yaml_content(content)

        if not data or not isinstance(data, list):
            # 回退：简单文本显示
            return f'<div class="treatment-timeline"><p>{content}</p></div>'

        html = '<div class="treatment-timeline">'

        for item in data:
            if not isinstance(item, dict):
                continue

            item_type = item.get('type', '')
            line = item.get('line', '')
            date = item.get('date', '')
            regimen = item.get('regimen', '')
            response = item.get('response', '')
            note = item.get('note', '')

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
                actions_html = '<ul>' + ''.join(f'<li>{a}</li>' for a in actions) + '</ul>'

            html += f'''
            <div class="card" style="border-left: 4px solid {color};">
              <div class="card-header">{title}</div>
              <p><strong>{regimen}</strong></p>
              {actions_html}
            </div>'''

        html += '</div>'
        return html

    def _parse_inline_refs(self, html: str) -> str:
        """
        解析内联引用标记为带 tooltip 的 HTML

        格式: [[ref:ID|Title|URL|Note]]
        输出: <span class="ref-tooltip"><a class="cite">[ID]</a><span class="ref-text">...</span></span>
        """
        pattern = r'\[\[ref:([^|]+)\|([^|]+)\|([^|]+)\|([^\]]+)\]\]'

        def replacer(m):
            ref_id, title, url, note = m.groups()
            return f'''<span class="ref-tooltip">
              <a class="cite" href="{url}" target="_blank">[{ref_id}]</a>
              <span class="ref-text">{title}: {note}</span>
            </span>'''

        return re.sub(pattern, replacer, html)

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
        """添加引用链接"""
        # 转换 [PMID: xxx] 为链接
        html = re.sub(
            r'\[PMID:\s*(\d+)\]',
            r'<a href="https://pubmed.ncbi.nlm.nih.gov/\1/" class="reference" target="_blank">[PMID: \1]</a>',
            html
        )

        # 转换 [NCTxxx] 为链接
        html = re.sub(
            r'\[(NCT\d+)\]',
            r'<a href="https://clinicaltrials.gov/study/\1" class="reference" target="_blank">[\1]</a>',
            html
        )

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
            if '⚠️' in line or '❌' in line:
                clean = line.strip().lstrip('#').strip()
                if clean and clean not in warnings:
                    warnings.append(clean)

        return warnings[:5]  # 限制数量


if __name__ == "__main__":
    print("HTML 报告生成器模块加载成功")
    print(f"报告目录: {REPORTS_DIR}")

    # 创建生成器实例（确保模板存在）
    generator = HtmlReportGenerator()
    print(f"模板目录: {generator.template_dir}")
