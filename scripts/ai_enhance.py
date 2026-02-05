#!/usr/bin/env python3
"""
SignalFeed - AI 增强脚本
使用 DeepSeek API 为文章添加中文翻译、TL;DR 和 Takeaways
"""

import json
import os
from datetime import datetime
from pathlib import Path
import time

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'

def call_deepseek_api(prompt, max_tokens=500):
    """调用 DeepSeek API"""
    import urllib.request

    if not DEEPSEEK_API_KEY:
        print("Warning: DEEPSEEK_API_KEY not set")
        return None

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {DEEPSEEK_API_KEY}'
    }

    data = {
        'model': 'deepseek-chat',
        'messages': [
            {'role': 'user', 'content': prompt}
        ],
        'max_tokens': max_tokens,
        'temperature': 0.7
    }

    try:
        req = urllib.request.Request(
            DEEPSEEK_API_URL,
            data=json.dumps(data).encode('utf-8'),
            headers=headers
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['choices'][0]['message']['content']

    except Exception as e:
        print(f"API Error: {e}")
        return None

def enhance_article(article):
    """为单篇文章添加 AI 增强内容"""
    title = article.get('title', '')
    description = article.get('description', '')

    # 构建 prompt
    prompt = f"""请分析以下技术文章，提供：

标题：{title}
描述：{description}

请按以下格式输出（使用 JSON 格式）：
{{
  "title_zh": "中文标题翻译",
  "tldr": "用 2-3 句话总结文章核心内容（中文）",
  "takeaways": ["要点1", "要点2", "要点3"],
  "tags": ["标签1", "标签2"]
}}

要求：
1. 标题翻译要准确、简洁
2. TL;DR 要抓住核心要点
3. Takeaways 提取 3 个关键要点
4. Tags 从以下类别选择：AI、开发工具、安全、前端、后端、DevOps、数据库、云计算、其他
"""

    print(f"Processing: {title[:50]}...")
    result = call_deepseek_api(prompt, max_tokens=800)

    if result:
        try:
            # 清理 markdown 代码块
            cleaned = result.strip()
            if cleaned.startswith('```'):
                # 移除 ```json 和 ```
                lines = cleaned.split('\n')
                # 找到第一个 { 和最后一个 }
                json_start = -1
                json_end = -1
                for i, line in enumerate(lines):
                    if '{' in line and json_start == -1:
                        json_start = i
                    if '}' in line:
                        json_end = i

                if json_start != -1 and json_end != -1:
                    cleaned = '\n'.join(lines[json_start:json_end+1])

            # 尝试解析 JSON
            enhanced = json.loads(cleaned)
            print(f"✓ Successfully parsed")
            return enhanced
        except Exception as e:
            print(f"✗ Failed to parse: {e}")
            return None

    return None

def load_articles():
    """加载所有文章"""
    articles_dir = Path(__file__).parent.parent / "data" / "articles"
    all_articles = []

    if not articles_dir.exists():
        return []

    for json_file in sorted(articles_dir.glob("*.json")):
        with open(json_file, 'r', encoding='utf-8') as f:
            articles = json.load(f)
            all_articles.extend(articles)

    return all_articles

def save_enhanced_articles(articles):
    """保存增强后的文章"""
    output_file = Path(__file__).parent.parent / "data" / "articles_enhanced.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved enhanced articles to: {output_file}")

if __name__ == "__main__":
    print("🤖 SignalFeed AI Enhancement - Starting...")
    
    if not DEEPSEEK_API_KEY:
        print("❌ Error: DEEPSEEK_API_KEY environment variable not set")
        print("Please set it with: export DEEPSEEK_API_KEY='your-api-key'")
        exit(1)
    
    # 加载文章
    articles = load_articles()
    print(f"📊 Loaded {len(articles)} articles")
    
    # 处理前 10 篇文章（测试）
    enhanced_articles = []
    for i, article in enumerate(articles[:10], 1):
        print(f"\n[{i}/10] Processing article...")
        enhanced = enhance_article(article)
        
        if enhanced:
            article['ai_enhanced'] = enhanced
            enhanced_articles.append(article)
        else:
            enhanced_articles.append(article)
        
        # 避免 API 限流
        time.sleep(1)
    
    # 保存增强后的文章
    save_enhanced_articles(enhanced_articles)
    print(f"\n✅ AI Enhancement complete! Processed {len(enhanced_articles)} articles")
