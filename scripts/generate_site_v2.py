#!/usr/bin/env python3
"""
SignalFeed - 静态网站生成脚本（支持 AI 增强）
读取文章数据，生成 HTML 页面
"""

import html
import json
import re
from collections import Counter
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

TAG_KEY_DELIMITER = "|||"


def load_all_articles():
    """加载所有文章数据（优先使用 AI 增强数据）"""
    enhanced_file = Path(__file__).parent.parent / "data" / "articles_enhanced.json"
    if enhanced_file.exists():
        print("📊 Loading AI-enhanced articles...")
        with open(enhanced_file, "r", encoding="utf-8") as file:
            return json.load(file)

    articles_dir = Path(__file__).parent.parent / "data" / "articles"
    all_articles = []

    if articles_dir.exists():
        for json_file in sorted(articles_dir.glob("*.json"), reverse=True):
            with open(json_file, "r", encoding="utf-8") as file:
                articles = json.load(file)
                all_articles.extend(articles)

    return all_articles


def parse_pub_date(date_str):
    """解析不同格式的发布时间"""
    if not date_str:
        return datetime.min.replace(tzinfo=timezone.utc)

    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass

    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass

    return datetime.min.replace(tzinfo=timezone.utc)


def normalize_text(value):
    """规范化文本（去首尾空白 + 压缩空白字符）"""
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value))
    return text.strip()


def normalize_key(value):
    """生成用于筛选比较的 key"""
    return normalize_text(value).casefold()


def normalize_article(raw_article):
    """清洗单条文章数据，避免脏值污染前端筛选和 HTML"""
    source_label = normalize_text(raw_article.get("source")) or "Unknown"
    source_key = normalize_key(source_label)

    ai_enhanced = raw_article.get("ai_enhanced") or {}
    raw_tags = ai_enhanced.get("tags")
    raw_key_points = ai_enhanced.get("key_points")

    normalized_tags = []
    seen_tag_keys = set()
    if isinstance(raw_tags, list):
        for raw_tag in raw_tags:
            tag_label = normalize_text(raw_tag)
            if not tag_label:
                continue
            tag_key = normalize_key(tag_label)
            if tag_key in seen_tag_keys:
                continue
            seen_tag_keys.add(tag_key)
            normalized_tags.append({"label": tag_label, "key": tag_key})

    key_points = []
    if isinstance(raw_key_points, list):
        for point in raw_key_points:
            cleaned_point = normalize_text(point)
            if cleaned_point:
                key_points.append(cleaned_point)

    return {
        "title": normalize_text(raw_article.get("title")) or "No Title",
        "link": normalize_text(raw_article.get("link")) or "#",
        "description": normalize_text(raw_article.get("description")),
        "source_label": source_label,
        "source_key": source_key,
        "tags": normalized_tags,
        "summary": normalize_text(ai_enhanced.get("summary")),
        "key_points": key_points,
    }


def generate_html(articles):
    """生成 HTML 页面（支持 AI 增强内容）"""
    sorted_articles = sorted(
        articles,
        key=lambda article: parse_pub_date(article.get("pub_date", "")),
        reverse=True,
    )

    normalized_articles = []
    source_counts = Counter()
    tag_counts = Counter()
    source_labels = {}
    tag_labels = {}

    for raw_article in sorted_articles:
        article = normalize_article(raw_article)
        normalized_articles.append(article)

        source_counts[article["source_key"]] += 1
        source_labels.setdefault(article["source_key"], article["source_label"])

        for tag in article["tags"]:
            tag_counts[tag["key"]] += 1
            tag_labels.setdefault(tag["key"], tag["label"])

    sorted_sources = sorted(
        source_labels.items(),
        key=lambda item: (-source_counts[item[0]], item[1].casefold()),
    )
    sorted_tags = sorted(
        tag_labels.items(),
        key=lambda item: (-tag_counts[item[0]], item[1].casefold()),
    )

    total_articles = len(normalized_articles)
    last_updated = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")

    lines = [
        "<!DOCTYPE html>",
        '<html lang="zh-CN">',
        "<head>",
        '    <meta charset="UTF-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        "    <title>SignalFeed - 技术信息流</title>",
        '    <link rel="stylesheet" href="css/style.css">',
        "</head>",
        "<body>",
        "    <header>",
        '        <div class="container">',
        "            <h1>📡 SignalFeed</h1>",
        '            <p class="tagline">从噪音中提取信号 · 精选技术资讯</p>',
        "        </div>",
        "    </header>",
        "",
        '    <main class="container">',
        '        <div class="stats">',
        f'            <span id="article-count">📊 显示 {total_articles} / {total_articles} 篇文章</span>',
        f"            <span>🕐 最后更新: {last_updated}</span>",
        "        </div>",
        "",
        '        <section class="filters is-collapsed" id="filters-panel">',
        '            <div class="filters-toolbar">',
        '                <button id="toggle-filters" class="filters-toggle" type="button" aria-expanded="false" aria-controls="filters-content">',
        '                    <span class="filters-toggle-icon" aria-hidden="true">▸</span>',
        '                    <strong class="filters-title">🔎 智能筛选</strong>',
        '                    <span id="filters-active-badge" class="filters-active-badge" hidden>0</span>',
        '                    <span class="filters-toggle-hint">点击展开</span>',
        "                </button>",
        '                <button id="clear-filters" class="clear-filters-btn" type="button">清空筛选</button>',
        "            </div>",
        '            <div id="active-filter-summary" class="active-filter-summary">当前筛选：全部来源 · 全部标签</div>',
        "",
        '            <div class="filters-content" id="filters-content" hidden>',
        '            <div class="filter-grid">',
        '                <label for="source-search">📝 来源搜索：</label>',
        '                <input id="source-search" type="search" placeholder="输入来源关键词，快速定位来源" autocomplete="off">',
        "",
        '                <label for="source-filter">📚 来源选择：</label>',
        '                <select id="source-filter">',
        f'                    <option value="all" data-source-label="全部来源">全部来源 ({total_articles})</option>',
    ]

    for source_key, source_label in sorted_sources:
        lines.append(
            f'                    <option value="{html.escape(source_key, quote=True)}" '
            f'data-source-label="{html.escape(source_label, quote=True)}">'
            f"{html.escape(source_label)} ({source_counts[source_key]})</option>"
        )

    lines.extend(
        [
            "                </select>",
            "",
            '                <label for="tag-search">🏷️ 标签搜索：</label>',
            '                <input id="tag-search" type="search" placeholder="输入标签关键词，快速筛选标签按钮" autocomplete="off">',
            "            </div>",
            "",
            '            <div class="tag-mode">',
            '                <span class="tag-mode-label">标签逻辑：</span>',
            '                <label><input type="radio" name="tag-match-mode" value="or" checked> 匹配任一标签</label>',
            '                <label><input type="radio" name="tag-match-mode" value="and"> 同时匹配全部</label>',
            "            </div>",
            "",
            '            <div class="tag-filter-panel">',
            '                <span class="tag-filter-label">🏷️ 标签多选：</span>',
            '                <div class="tag-chip-list" id="tag-chip-list">',
        ]
    )

    for tag_key, tag_label in sorted_tags:
        lines.extend(
            [
                f'                    <button class="tag-chip-filter" type="button" data-tag-key="{html.escape(tag_key, quote=True)}" data-tag-label="{html.escape(tag_label, quote=True)}" aria-pressed="false">',
                f'                        <span class="tag-chip-name">{html.escape(tag_label)}</span>',
                f'                        <span class="tag-chip-count">{tag_counts[tag_key]}</span>',
                "                    </button>",
            ]
        )

    lines.extend(
        [
            "                </div>",
            "            </div>",
            "            </div>",
            "        </section>",
            "",
            '        <div class="articles" id="articles-container">',
            "",
        ]
    )

    for index, article in enumerate(normalized_articles, 1):
        tag_labels_for_article = [tag["label"] for tag in article["tags"]]
        tag_keys_for_article = [tag["key"] for tag in article["tags"]]

        lines.extend(
            [
                f'            <article class="article-card" data-source="{html.escape(article["source_label"], quote=True)}" '
                f'data-source-key="{html.escape(article["source_key"], quote=True)}" '
                f'data-tags="{html.escape(",".join(tag_labels_for_article), quote=True)}" '
                f'data-tag-keys="{html.escape(TAG_KEY_DELIMITER.join(tag_keys_for_article), quote=True)}">',
                '                <div class="article-header">',
                f'                    <span class="article-number">{index}</span>',
                '                    <div class="article-title-group">',
                f'                        <h2><a href="{html.escape(article["link"], quote=True)}" target="_blank" rel="noopener">{html.escape(article["title"])}</a></h2>',
                "                    </div>",
                "                </div>",
                '                <div class="article-meta">',
                f'                    <span class="source">📝 {html.escape(article["source_label"])}</span>',
            ]
        )

        if article["tags"]:
            lines.extend(
                [
                    "",
                    '                    <div class="tags">',
                    "",
                ]
            )
            for tag in article["tags"]:
                lines.append(f'                        <span class="tag">🏷️ {html.escape(tag["label"])}</span>')
                lines.append("")
            lines.extend(
                [
                    "                    </div>",
                    "",
                ]
            )

        lines.extend(
            [
                "                </div>",
                "",
            ]
        )

        if article["summary"]:
            lines.extend(
                [
                    '                <div class="ai-summary">',
                    f'                    <strong>📌 AI 摘要:</strong> {html.escape(article["summary"])}',
                    "                </div>",
                    "",
                ]
            )

        if article["key_points"]:
            lines.extend(
                [
                    '                <div class="key-points">',
                    "                    <strong>💡 核心要点:</strong>",
                    "                    <ul>",
                    "",
                ]
            )
            for point in article["key_points"]:
                lines.append(f"                        <li>{html.escape(point)}</li>")
                lines.append("")
            lines.extend(
                [
                    "                    </ul>",
                    "                </div>",
                    "",
                ]
            )

        if not article["summary"] and article["description"]:
            lines.extend(
                [
                    f'                <p class="description">{html.escape(article["description"][:200])}...</p>',
                    "",
                ]
            )

        lines.extend(
            [
                "            </article>",
                "",
            ]
        )

    lines.extend(
        [
            "        </div>",
            "",
            '        <div class="empty-state" id="empty-state" hidden>',
            "            <p>没有匹配的文章，试试放宽来源或标签条件。</p>",
            "        </div>",
            "",
            '        <div class="pagination" id="pagination">',
            '            <button id="prev-page" class="page-btn">← 上一页</button>',
            '            <span id="page-info">第 1 / 1 页</span>',
            '            <button id="next-page" class="page-btn">下一页 →</button>',
            "        </div>",
            "    </main>",
            "",
            "    <footer>",
            '        <div class="container">',
            "            <p>SignalFeed - Powered by RSS & AI</p>",
            '            <p><a href="https://github.com/xxxxxthhh/SignalFeed" target="_blank">View on GitHub</a></p>',
            "        </div>",
            "    </footer>",
            "",
            '    <script src="js/app.js"></script>',
            "</body>",
            "</html>",
            "",
        ]
    )

    return "\n".join(lines)


if __name__ == "__main__":
    print("🎨 Generating website (AI-enhanced version)...")

    articles = load_all_articles()
    print(f"📊 Loaded {len(articles)} articles")

    html_content = generate_html(articles)

    output_file = Path(__file__).parent.parent / "site" / "index.html"
    with open(output_file, "w", encoding="utf-8") as file:
        file.write(html_content)

    print(f"✅ Website generated: {output_file}")
