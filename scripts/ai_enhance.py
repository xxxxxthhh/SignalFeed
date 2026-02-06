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
import re
import html

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'
MAX_ANALYSIS_INPUT_CHARS = 7000
MIN_FULLTEXT_LENGTH = 900

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

def normalize_text(value):
    """压缩空白并去除首尾空白"""
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value))
    return text.strip()

def clean_content_text(value):
    """将 HTML 内容转换为更易分析的纯文本"""
    text = str(value or "")
    if not text.strip():
        return ""

    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|h[1-6]|li|blockquote|section|article|tr)>", "\n", text)
    text = re.sub(r"(?i)<li[^>]*>", "\n- ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def build_analysis_input(article):
    """优先使用 RSS 原文作为分析输入，摘要作为回退"""
    raw_content = article.get("content", "")
    raw_description = article.get("description", "")

    cleaned_content = clean_content_text(raw_content)
    cleaned_description = clean_content_text(raw_description)

    has_fulltext_signal = bool(article.get("is_fulltext")) or len(cleaned_content) >= MIN_FULLTEXT_LENGTH
    use_content = len(cleaned_content) >= 120

    selected = cleaned_content if use_content else cleaned_description
    source_type = "fulltext" if has_fulltext_signal and use_content else "summary"

    truncated = False
    if len(selected) > MAX_ANALYSIS_INPUT_CHARS:
        selected = selected[:MAX_ANALYSIS_INPUT_CHARS].rstrip()
        truncated = True

    if not selected:
        selected = normalize_text(article.get("title", ""))
        source_type = "summary"

    return selected, source_type, truncated

def build_prompt(title, source, analysis_input, source_type):
    """构建更强调深度分析的提示词"""
    # 定义固定的标签分类
    standard_tags = [
        "AI/机器学习", "编程语言", "Web开发", "移动开发", "DevOps",
        "云计算", "数据库", "网络安全", "开源项目", "软件工程",
        "系统架构", "性能优化", "测试", "工具", "硬件",
        "产品设计", "职业发展", "技术趋势", "其他"
    ]

    source_hint = "RSS全文" if source_type == "fulltext" else "RSS摘要"
    return f"""你是资深技术编辑。请基于下面的文章材料，输出结构化解读。

标题：{title}
来源：{source}
材料类型：{source_hint}

文章材料：
{analysis_input}

请严格输出 JSON（不要 markdown 代码块）：
{{
  "tags": ["标签1", "标签2"],
  "summary": "1-2句话总结核心结论（中文）",
  "key_points": ["要点1", "要点2", "要点3"],
  "analysis": ["分析1", "分析2", "分析3"]
}}

要求：
1. tags：只能从以下标签中选择 1-2 个最相关标签：
   {', '.join(standard_tags)}
2. summary：回答“这篇文章最核心讲了什么”，不要写泛泛空话。
3. key_points：给 3 条关键事实/观点；必须与 summary 明显不同，不能同义改写。
4. analysis：给 2-3 条“为什么重要/潜在影响/实践建议”的分析，可合理推断但不得编造原文不存在的具体事实。
5. 若材料较短或仅摘要，analysis 允许减少到 1-2 条，并明确使用谨慎表述。
6. 每条要点尽量控制在 18-40 字。
"""

def sanitize_list(items, max_items=3):
    """清理模型输出列表，避免脏数据污染页面"""
    if isinstance(items, str):
        items = [items]
    if not isinstance(items, list):
        return []

    cleaned = []
    seen = set()
    for item in items:
        text = normalize_text(item)
        if not text:
            continue
        # 清理常见项目符号，保持展示一致
        text = re.sub(r"^[\-\*\d\.\)\s]+", "", text).strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        cleaned.append(text[:120])
        if len(cleaned) >= max_items:
            break
    return cleaned

def sanitize_enhanced_result(parsed, source_type, input_chars, truncated):
    """规范化 AI 输出结构"""
    if not isinstance(parsed, dict):
        return None

    tags = sanitize_list(parsed.get("tags"), max_items=2)
    summary = normalize_text(parsed.get("summary"))[:220]
    key_points = sanitize_list(parsed.get("key_points"), max_items=3)
    analysis = sanitize_list(parsed.get("analysis"), max_items=3)

    if not summary:
        return None

    return {
        "tags": tags,
        "summary": summary,
        "key_points": key_points,
        "analysis": analysis,
        "analysis_source": source_type,
        "analysis_input_chars": input_chars,
        "analysis_truncated": bool(truncated),
    }

def enhance_article(article):
    """为单篇文章添加 AI 增强内容"""
    title = article.get('title', '')
    source = article.get('source', 'Unknown')
    analysis_input, source_type, truncated = build_analysis_input(article)
    prompt = build_prompt(title, source, analysis_input, source_type)

    print(f"Processing: {title[:50]}... [{source_type}, {len(analysis_input)} chars]")
    result = call_deepseek_api(prompt, max_tokens=900)

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

            # 解析 JSON 并规范化结果
            parsed = json.loads(cleaned)
            enhanced = sanitize_enhanced_result(
                parsed,
                source_type=source_type,
                input_chars=len(analysis_input),
                truncated=truncated,
            )
            if enhanced:
                print(f"✓ Successfully enhanced")
                return enhanced
            print("✗ Invalid structure after sanitize")
            return None
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
