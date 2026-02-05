#!/usr/bin/env python3
"""
检查 RSS 源是否提供全文内容
"""

import urllib.request
import xml.etree.ElementTree as ET
import json
from pathlib import Path
import random

def check_feed_content(url):
    """检查单个 RSS 源的内容类型"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 SignalFeed/1.0'}
        req = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read()

        root = ET.fromstring(content)

        # 检查是否有 content:encoded 或其他全文字段
        has_content_encoded = False
        has_full_content = False
        description_length = 0
        content_length = 0

        # RSS 2.0
        if root.tag == 'rss' or root.find('channel') is not None:
            channel = root.find('channel')
            if channel:
                item = channel.find('item')
                if item:
                    # 检查 content:encoded
                    content_elem = item.find('{http://purl.org/rss/1.0/modules/content/}encoded')
                    if content_elem is not None and content_elem.text:
                        has_content_encoded = True
                        content_length = len(content_elem.text)

                    # 检查 description 长度
                    desc = item.find('description')
                    if desc is not None and desc.text:
                        description_length = len(desc.text)

        # Atom
        elif 'atom' in root.tag.lower():
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            entry = root.find('atom:entry', ns)
            if not entry:
                entry = root.find('entry')

            if entry:
                # 检查 content
                content_elem = entry.find('atom:content', ns)
                if not content_elem:
                    content_elem = entry.find('content')

                if content_elem is not None and content_elem.text:
                    content_length = len(content_elem.text)
                    has_full_content = True

                # 检查 summary
                summary = entry.find('atom:summary', ns)
                if not summary:
                    summary = entry.find('summary')

                if summary is not None and summary.text:
                    description_length = len(summary.text)

        # 判断是否提供全文（内容长度 > 1000 字符认为是全文）
        is_fulltext = (has_content_encoded or has_full_content) and (content_length > 1000 or description_length > 1000)

        return {
            'url': url,
            'has_content_encoded': has_content_encoded,
            'has_full_content': has_full_content,
            'description_length': description_length,
            'content_length': content_length,
            'is_fulltext': is_fulltext,
            'status': 'success'
        }

    except Exception as e:
        return {
            'url': url,
            'status': 'error',
            'error': str(e)
        }

if __name__ == "__main__":
    # 加载订阅源
    feeds_file = Path(__file__).parent.parent / "data" / "feeds.json"
    with open(feeds_file) as f:
        feeds = json.load(f)

    # 随机抽样 20 个源进行检查
    sample_size = min(20, len(feeds))
    sample_feeds = random.sample(feeds, sample_size)

    print(f"🔍 Checking {sample_size} random RSS feeds for full-text content...\n")

    results = []
    fulltext_count = 0

    for i, feed_url in enumerate(sample_feeds, 1):
        print(f"[{i}/{sample_size}] Checking {feed_url[:60]}...")
        result = check_feed_content(feed_url)
        results.append(result)

        if result['status'] == 'success':
            if result['is_fulltext']:
                fulltext_count += 1
                print(f"  ✅ Full-text (content: {result['content_length']} chars, desc: {result['description_length']} chars)")
            else:
                print(f"  ❌ Summary only (content: {result['content_length']} chars, desc: {result['description_length']} chars)")
        else:
            print(f"  ⚠️  Error: {result['error']}")

    print(f"\n📊 Summary:")
    print(f"  Total checked: {sample_size}")
    print(f"  Full-text feeds: {fulltext_count} ({fulltext_count/sample_size*100:.1f}%)")
    print(f"  Summary-only feeds: {sample_size - fulltext_count} ({(sample_size-fulltext_count)/sample_size*100:.1f}%)")

    # 保存详细结果
    output_file = Path(__file__).parent.parent / "data" / "fulltext_check.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Detailed results saved to: {output_file}")
