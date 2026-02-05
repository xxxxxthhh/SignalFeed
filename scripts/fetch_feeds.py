#!/usr/bin/env python3
"""
SignalFeed - RSS 抓取脚本
每天定时抓取 RSS 订阅源，保存文章数据
"""

import urllib.request
import xml.etree.ElementTree as ET
import json
import hashlib
from datetime import datetime
from pathlib import Path
import time
import re

def parse_rss_feed(url):
    """解析 RSS/Atom 订阅源"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 SignalFeed/1.0'}
        req = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read()

        root = ET.fromstring(content)

        # 尝试解析 RSS 2.0
        if root.tag == 'rss' or root.find('channel') is not None:
            return parse_rss_2_0(root, url)
        # 尝试解析 Atom
        elif 'atom' in root.tag.lower():
            return parse_atom(root, url)
        else:
            return None

    except Exception as e:
        print(f"Error parsing {url}: {e}")
        return None

def parse_rss_2_0(root, url):
    """解析 RSS 2.0 格式"""
    channel = root.find('channel')
    if channel is None:
        return None

    feed_title = channel.find('title')
    feed_title = feed_title.text if feed_title is not None else 'Unknown'

    items = []
    for item in channel.findall('item')[:1]:  # 每个源只抓取最新 1 篇
        title = item.find('title')
        link = item.find('link')
        description = item.find('description')
        pub_date = item.find('pubDate')

        # 优先读取 content:encoded 字段（全文）
        content_encoded = item.find('{http://purl.org/rss/1.0/modules/content/}encoded')

        # 确定内容和是否为全文
        if content_encoded is not None and content_encoded.text:
            content = content_encoded.text
            is_fulltext = True
        elif description is not None and description.text:
            content = description.text
            is_fulltext = len(description.text) > 1000  # 超过1000字符认为是全文
        else:
            content = ''
            is_fulltext = False

        items.append({
            'title': title.text if title is not None else 'No Title',
            'link': link.text if link is not None else '',
            'content': content,
            'description': description.text if description is not None else '',
            'is_fulltext': is_fulltext,
            'pub_date': pub_date.text if pub_date is not None else ''
        })

    return {
        'feed_title': feed_title,
        'url': url,
        'items': items
    }

def parse_atom(root, url):
    """解析 Atom 格式"""
    ns = {'atom': 'http://www.w3.org/2005/Atom'}

    feed_title = root.find('atom:title', ns)
    if feed_title is None:
        feed_title = root.find('title')
    feed_title = feed_title.text if feed_title is not None else 'Unknown'

    items = []
    entries = root.findall('atom:entry', ns)
    if not entries:
        entries = root.findall('entry')

    for entry in entries[:1]:  # 每个源只抓取最新 1 篇
        title = entry.find('atom:title', ns)
        if title is None:
            title = entry.find('title')

        link = entry.find('atom:link', ns)
        if link is None:
            link = entry.find('link')
        link_href = link.get('href') if link is not None else ''

        # 优先读取 content 字段（全文）
        content_elem = entry.find('atom:content', ns)
        if content_elem is None:
            content_elem = entry.find('content')

        summary = entry.find('atom:summary', ns)
        if summary is None:
            summary = entry.find('summary')

        updated = entry.find('atom:updated', ns)
        if updated is None:
            updated = entry.find('updated')

        # 确定内容和是否为全文
        if content_elem is not None and content_elem.text:
            content = content_elem.text
            is_fulltext = True
        elif summary is not None and summary.text:
            content = summary.text
            is_fulltext = len(summary.text) > 1000  # 超过1000字符认为是全文
        else:
            content = ''
            is_fulltext = False

        items.append({
            'title': title.text if title is not None else 'No Title',
            'link': link_href,
            'content': content,
            'description': summary.text if summary is not None else '',
            'is_fulltext': is_fulltext,
            'pub_date': updated.text if updated is not None else ''
        })

    return {
        'feed_title': feed_title,
        'url': url,
        'items': items
    }

def clean_html(text):
    """清理 HTML 标签"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_url_hash(url):
    """生成 URL 的哈希值用于去重"""
    return hashlib.md5(url.encode()).hexdigest()

def load_processed_urls():
    """加载已处理的 URL"""
    processed_file = Path(__file__).parent.parent / "data" / "processed_urls.txt"
    if processed_file.exists():
        with open(processed_file, 'r') as f:
            return set(line.strip() for line in f)
    return set()

def save_processed_url(url_hash):
    """保存已处理的 URL"""
    processed_file = Path(__file__).parent.parent / "data" / "processed_urls.txt"
    with open(processed_file, 'a') as f:
        f.write(f"{url_hash}\n")

if __name__ == "__main__":
    print("🚀 SignalFeed - Starting RSS fetch...")

    # 加载订阅源
    feeds_file = Path(__file__).parent.parent / "data" / "feeds.json"
    with open(feeds_file) as f:
        feeds = json.load(f)

    print(f"📡 Fetching {len(feeds)} feeds...")

    # 加载已处理的 URL
    processed_urls = load_processed_urls()
    print(f"📝 Already processed: {len(processed_urls)} articles")

    # 抓取所有订阅源
    all_articles = []
    new_count = 0

    for i, feed_url in enumerate(feeds, 1):
        print(f"[{i}/{len(feeds)}] Fetching {feed_url[:50]}...")
        result = parse_rss_feed(feed_url)

        if result and result['items']:
            for item in result['items']:
                url_hash = get_url_hash(item['link'])

                # 去重检查
                if url_hash not in processed_urls:
                    # 使用完整内容，不再限制字符数
                    content = item.get('content', item.get('description', ''))

                    article = {
                        'title': clean_html(item['title']),
                        'link': item['link'],
                        'content': content,  # 完整内容（可能包含 HTML）
                        'description': clean_html(item.get('description', ''))[:500],  # 纯文本摘要，用于预览
                        'is_fulltext': item.get('is_fulltext', False),
                        'source': result['feed_title'],
                        'pub_date': item['pub_date'],
                        'fetched_at': datetime.now().isoformat(),
                        'url_hash': url_hash
                    }
                    all_articles.append(article)
                    processed_urls.add(url_hash)
                    save_processed_url(url_hash)
                    new_count += 1

        time.sleep(0.3)  # 避免请求过快

    print(f"\n✅ Fetch complete!")
    print(f"📊 New articles: {new_count}")
    print(f"📊 Total processed: {len(processed_urls)}")

    # 保存文章数据
    if all_articles:
        date_str = datetime.now().strftime('%Y-%m-%d')
        output_file = Path(__file__).parent.parent / "data" / "articles" / f"{date_str}.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=2)

        print(f"💾 Saved to: {output_file}")
    else:
        print("ℹ️  No new articles to save")
