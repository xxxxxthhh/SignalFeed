#!/usr/bin/env python3
"""
SignalFeed - AI 增强脚本
使用 DeepSeek API 为文章添加关键词和核心要点
支持批量处理和断点续传
"""

import json
import os
from datetime import datetime
from pathlib import Path
import time
import sys

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

    # 定义固定的标签分类
    STANDARD_TAGS = [
        "AI/机器学习", "编程语言", "Web开发", "移动开发", "DevOps",
        "云计算", "数据库", "网络安全", "开源项目", "软件工程",
        "系统架构", "性能优化", "测试", "工具", "硬件",
        "产品设计", "职业发展", "技术趋势", "其他"
    ]

    # 构建优化后的 prompt
    prompt = f"""请分析以下技术文章，提供标签和核心要点：

标题：{title}
描述：{description[:500]}

请按以下 JSON 格式输出：
{{
  "tags": ["标签1", "标签2"],
  "summary": "用1-2句话总结文章核心内容（中文）",
  "key_points": ["要点1", "要点2", "要点3"]
}}

要求：
1. tags: 从以下标签中选择1-2个最相关的：
   {', '.join(STANDARD_TAGS)}
2. summary: 简洁明了，抓住核心
3. key_points: 3个最重要的要点，每个不超过30字
"""

    print(f"Processing: {title[:50]}...")
    result = call_deepseek_api(prompt, max_tokens=600)

    if result:
        try:
            # 清理 markdown 代码块
            cleaned = result.strip()
            if cleaned.startswith('```'):
                lines = cleaned.split('\n')
                json_start = -1
                json_end = -1
                for i, line in enumerate(lines):
                    if '{' in line and json_start == -1:
                        json_start = i
                    if '}' in line:
                        json_end = i

                if json_start != -1 and json_end != -1:
                    cleaned = '\n'.join(lines[json_start:json_end+1])

            # 解析 JSON
            enhanced = json.loads(cleaned)
            print(f"✓ Successfully enhanced")
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

def load_processed_hashes():
    """加载已处理的文章哈希列表（用于断点续传）"""
    progress_file = Path(__file__).parent.parent / "data" / "ai_processed.txt"
    if progress_file.exists():
        with open(progress_file, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_processed_hash(url_hash):
    """保存已处理的文章哈希"""
    progress_file = Path(__file__).parent.parent / "data" / "ai_processed.txt"
    with open(progress_file, 'a', encoding='utf-8') as f:
        f.write(f"{url_hash}\n")

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

    # 解析命令行参数
    batch_size = 20  # 每批处理的文章数
    if len(sys.argv) > 1:
        try:
            batch_size = int(sys.argv[1])
        except:
            print(f"Invalid batch size, using default: {batch_size}")

    # 加载文章
    articles = load_articles()
    print(f"📊 Loaded {len(articles)} articles")

    # 加载已处理的文章
    processed_hashes = load_processed_hashes()
    print(f"📝 Already processed: {len(processed_hashes)} articles")

    # 筛选未处理的文章
    unprocessed = [a for a in articles if a.get('url_hash') not in processed_hashes]
    print(f"🔄 To process: {len(unprocessed)} articles")

    if not unprocessed:
        print("✅ All articles already processed!")
        exit(0)

    # 批量处理
    total = len(unprocessed)
    batch_to_process = unprocessed[:batch_size]
    print(f"\n🔄 Processing batch: {len(batch_to_process)} articles")
    print(f"   Remaining after this batch: {total - len(batch_to_process)}")

    # 加载现有的增强文章（如果存在）
    enhanced_file = Path(__file__).parent.parent / "data" / "articles_enhanced.json"
    if enhanced_file.exists():
        with open(enhanced_file, 'r', encoding='utf-8') as f:
            all_enhanced = json.load(f)
        print(f"📂 Loaded {len(all_enhanced)} existing enhanced articles")
    else:
        all_enhanced = []

    # 创建哈希到文章的映射
    enhanced_map = {a.get('url_hash'): a for a in all_enhanced if a.get('url_hash')}

    # 处理当前批次
    success_count = 0
    for i, article in enumerate(batch_to_process, 1):
        print(f"\n[{i}/{len(batch_to_process)}] ", end='')
        enhanced = enhance_article(article)

        if enhanced:
            article['ai_enhanced'] = enhanced
            enhanced_map[article['url_hash']] = article
            save_processed_hash(article['url_hash'])
            success_count += 1
        else:
            # 即使失败也添加到映射中（避免重复处理）
            enhanced_map[article['url_hash']] = article
            save_processed_hash(article['url_hash'])

        # 避免 API 限流
        time.sleep(1.5)

    # 保存所有增强后的文章
    all_enhanced = list(enhanced_map.values())
    save_enhanced_articles(all_enhanced)

    print(f"\n✅ Batch complete!")
    print(f"   Successfully enhanced: {success_count}/{len(batch_to_process)}")
    print(f"   Total enhanced articles: {len(all_enhanced)}")
    print(f"   Remaining to process: {total - len(batch_to_process)}")

    if total > len(batch_to_process):
        print(f"\n💡 Run again to process the next batch")
