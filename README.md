# 📡 SignalFeed

> 从噪音中提取信号 · 精选技术资讯

SignalFeed 是一个自动化的 RSS 聚合器，每天从 90+ 技术博客中抓取最新文章，自动去重，并生成优雅的阅读界面。

## ✨ 特性

- 🤖 **自动化抓取** - GitHub Actions 每天 2 次自动抓取
- 🔄 **智能去重** - 基于 URL 哈希的去重机制
- 🎨 **优雅界面** - 简洁的阅读体验，支持深色模式
- 📱 **响应式设计** - 完美适配移动端和桌面端
- 🚀 **零成本部署** - 使用 GitHub Pages 免费托管

## 🏗️ 项目结构

```
SignalFeed/
├── .github/workflows/
│   └── fetch-feeds.yml          # GitHub Actions 工作流
├── data/
│   ├── feeds.json               # RSS 订阅源列表
│   ├── articles/                # 文章数据（按日期）
│   └── processed_urls.txt       # 已处理的 URL（去重）
├── scripts/
│   ├── fetch_feeds.py           # RSS 抓取脚本
│   └── generate_site.py         # 网站生成脚本
├── site/
│   ├── index.html               # 主页
│   └── css/style.css            # 样式文件
└── README.md
```

## 🚀 快速开始

### 1. Fork 本仓库

点击右上角的 "Fork" 按钮

### 2. 启用 GitHub Pages

1. 进入仓库设置 (Settings)
2. 找到 "Pages" 选项
3. Source 选择 "gh-pages" 分支
4. 保存

### 3. 手动触发第一次运行

1. 进入 "Actions" 标签
2. 选择 "Fetch RSS Feeds and Deploy"
3. 点击 "Run workflow"

### 4. 访问你的网站

几分钟后，访问：`https://[你的用户名].github.io/SignalFeed/`

## 📝 自定义订阅源

编辑 `data/feeds.json` 文件，添加或删除 RSS 订阅源：

```json
[
  "https://example.com/feed.xml",
  "https://another-blog.com/rss"
]
```

## 🔧 本地开发

```bash
# 克隆仓库
git clone https://github.com/[你的用户名]/SignalFeed.git
cd SignalFeed

# 抓取 RSS
python scripts/fetch_feeds.py

# 生成网站
python scripts/generate_site.py

# 在浏览器中打开 site/index.html
```

## 📅 更新频率

- 每天早上 8:00 AM (CST)
- 每天晚上 8:00 PM (CST)

可以在 `.github/workflows/fetch-feeds.yml` 中修改 cron 表达式来调整频率。

## 🛠️ 技术栈

- Python 3.10
- GitHub Actions
- GitHub Pages
- 纯 HTML/CSS（无 JavaScript 框架）

## 📄 许可证

MIT License

## 🙏 致谢

灵感来源于 Hacker News 和 Lobsters
