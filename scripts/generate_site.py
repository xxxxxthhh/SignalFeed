#!/usr/bin/env python3
"""
SignalFeed - 静态网站生成脚本
读取文章数据，生成 HTML 页面
"""

import json
from datetime import datetime
from pathlib import Path

def load_all_articles():
    """加载所有文章数据"""
    articles_dir = Path(__file__).parent.parent / "data" / "articles"
    all_articles = []

    if not articles_dir.exists():
        return []

    for json_file in sorted(articles_dir.glob("*.json"), reverse=True):
        with open(json_file, 'r', encoding='utf-8') as f:
            articles = json.load(f)
            all_articles.extend(articles)

    return all_articles

def generate_html(articles):
    """生成 HTML 页面"""

    # 按时间倒序排列
    articles.sort(key=lambda x: x.get('fetched_at', ''), reverse=True)

    # 限制显示最近 100 篇
    articles = articles[:100]

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
            <span>📊 共 """ + str(len(articles)) + """ 篇文章</span>
            <span>🕐 最后更新: """ + datetime.now().strftime('%Y-%m-%d %H:%M') + """</span>
        </div>

        <div class="articles">
"""

    for i, article in enumerate(articles, 1):
        title = article.get('title', 'No Title')
        link = article.get('link', '#')
        source = article.get('source', 'Unknown')
        description = article.get('description', '')

        html += f"""
            <article class="article-card">
                <div class="article-header">
                    <span class="article-number">{i}</span>
                    <h2><a href="{link}" target="_blank" rel="noopener">{title}</a></h2>
                </div>
                <div class="article-meta">
                    <span class="source">📝 {source}</span>
                </div>
"""

        if description:
            html += f"""
                <p class="description">{description[:200]}...</p>
"""

        html += """
            </article>
"""

    html += """
        </div>
    </main>

    <footer>
        <div class="container">
            <p>SignalFeed - Powered by RSS & GitHub Actions</p>
            <p><a href="https://github.com/xxxxxthhh/SignalFeed" target="_blank">View on GitHub</a></p>
        </div>
    </footer>
</body>
</html>
"""

    return html

if __name__ == "__main__":
    print("🎨 Generating website...")

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
