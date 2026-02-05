#!/usr/bin/env python3
"""
SignalFeed - 静态网站生成脚本（支持 AI 增强）
读取文章数据，生成 HTML 页面
"""

import json
from datetime import datetime
from pathlib import Path
from email.utils import parsedate_to_datetime

def load_all_articles():
    """加载所有文章数据（合并原始文章和 AI 增强数据）"""
    # 加载原始文章
    articles_dir = Path(__file__).parent.parent / "data" / "articles"
    all_articles = []

    if articles_dir.exists():
        for json_file in sorted(articles_dir.glob("*.json"), reverse=True):
            with open(json_file, 'r', encoding='utf-8') as f:
                articles = json.load(f)
                all_articles.extend(articles)

    # 加载 AI 增强数据（如果存在）
    enhanced_file = Path(__file__).parent.parent / "data" / "articles_enhanced.json"
    if enhanced_file.exists():
        print("📊 Loading AI-enhanced articles...")
        with open(enhanced_file, 'r', encoding='utf-8') as f:
            enhanced_articles = json.load(f)

        # 创建哈希到增强数据的映射
        enhanced_map = {a.get('url_hash'): a.get('ai_enhanced', {}) for a in enhanced_articles if a.get('url_hash')}

        # 合并 AI 增强数据到原始文章
        for article in all_articles:
            url_hash = article.get('url_hash')
            if url_hash in enhanced_map:
                article['ai_enhanced'] = enhanced_map[url_hash]

    return all_articles

def parse_pub_date(date_str):
    """解析不同格式的发布时间"""
    from datetime import timezone

    if not date_str:
        return datetime.min.replace(tzinfo=timezone.utc)

    try:
        # 尝试解析 ISO 格式 (2026-02-05T00:23:38+00:00)
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        # 确保有时区信息
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except:
        pass

    try:
        # 尝试解析 RFC 格式 (Wed, 05 Feb 2026 00:23:38 GMT)
        dt = parsedate_to_datetime(date_str)
        # 确保有时区信息
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except:
        pass

    # 如果都失败，返回最小时间（带时区）
    return datetime.min.replace(tzinfo=timezone.utc)

def generate_html(articles):
    """生成 HTML 页面（支持 AI 增强内容）"""

    # 按发布时间倒序排列（最新的在前）
    articles.sort(key=lambda x: parse_pub_date(x.get('pub_date', '')), reverse=True)

    # 收集所有作者（用于筛选）
    sources = sorted(set(article.get('source', 'Unknown') for article in articles))

    # 收集所有标签（用于筛选）
    all_tags = set()
    for article in articles:
        keywords = article.get('ai_enhanced', {}).get('keywords', [])
        all_tags.update(keywords)
    tags = sorted(all_tags)

    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SignalFeed - 技术信息流</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <header>
        <div class="container">
            <h1>📡 SignalFeed</h1>
            <p class="tagline">从噪音中提取信号 · 精选技术资讯</p>
        </div>
    </header>

    <main class="container">
        <div class="stats">
            <span id="article-count">📊 共 """ + str(len(articles)) + """ 篇文章</span>
            <span>🕐 最后更新: """ + datetime.now().strftime('%Y-%m-%d %H:%M') + """</span>
        </div>

        <div class="filters">
            <label for="source-filter">📝 按作者筛选：</label>
            <select id="source-filter">
                <option value="all">全部作者</option>
"""

    # 添加作者选项
    for source in sources:
        html += f"""                <option value="{source}">{source}</option>
"""

    html += """            </select>

            <label for="tag-filter">🏷️ 按标签筛选：</label>
            <select id="tag-filter">
                <option value="all">全部标签</option>
"""

    # 添加标签选项
    for tag in tags:
        html += f"""                <option value="{tag}">{tag}</option>
"""

    html += """            </select>
        </div>

        <div class="articles" id="articles-container">
"""

    for i, article in enumerate(articles, 1):
        title = article.get('title', 'No Title')
        link = article.get('link', '#')
        source = article.get('source', 'Unknown')
        description = article.get('description', '')
        
        # 检查是否有 AI 增强内容
        ai_enhanced = article.get('ai_enhanced', {})
        keywords = ai_enhanced.get('keywords', [])
        summary = ai_enhanced.get('summary', '')
        key_points = ai_enhanced.get('key_points', [])

        html += f"""
            <article class="article-card" data-source="{source}" data-tags="{','.join(keywords)}">
                <div class="article-header">
                    <span class="article-number">{i}</span>
                    <div class="article-title-group">
                        <h2><a href="{link}" target="_blank" rel="noopener">{title}</a></h2>
                    </div>
                </div>
                <div class="article-meta">
                    <span class="source">📝 {source}</span>
"""

        # 显示关键词
        if keywords:
            html += """
                    <div class="keywords">
"""
            for keyword in keywords:
                html += f"""
                        <span class="keyword">🏷️ {keyword}</span>
"""
            html += """
                    </div>
"""

        html += """
                </div>
"""

        # 显示 AI 摘要
        if summary:
            html += f"""
                <div class="ai-summary">
                    <strong>📌 AI 摘要:</strong> {summary}
                </div>
"""

        # 显示核心要点
        if key_points:
            html += """
                <div class="key-points">
                    <strong>💡 核心要点:</strong>
                    <ul>
"""
            for point in key_points:
                html += f"""
                        <li>{point}</li>
"""
            html += """
                    </ul>
                </div>
"""

        # 如果没有 AI 增强内容，显示原始描述
        if not summary and description:
            html += f"""
                <p class="description">{description[:200]}...</p>
"""

        html += """
            </article>
"""

    html += """
        </div>

        <div class="pagination" id="pagination">
            <button id="prev-page" class="page-btn">← 上一页</button>
            <span id="page-info">第 1 页</span>
            <button id="next-page" class="page-btn">下一页 →</button>
        </div>
    </main>

    <footer>
        <div class="container">
            <p>SignalFeed - Powered by RSS & AI</p>
            <p><a href="https://github.com/xxxxxthhh/SignalFeed" target="_blank">View on GitHub</a></p>
        </div>
    </footer>

    <script src="js/app.js"></script>
</body>
</html>
"""

    return html

if __name__ == "__main__":
    print("🎨 Generating website (AI-enhanced version)...")

    # 加载文章
    articles = load_all_articles()
    print(f"📊 Loaded {len(articles)} articles")

    # 生成 HTML
    html = generate_html(articles)

    # 保存到 site/index.html
    output_file = Path(__file__).parent.parent / "site" / "index.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Website generated: {output_file}")
