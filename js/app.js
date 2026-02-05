// SignalFeed - 分页和筛选功能

const ARTICLES_PER_PAGE = 10;
let currentPage = 1;
let currentSourceFilter = 'all';
let currentTagFilter = 'all';
let allArticles = [];
let filteredArticles = [];

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    // 获取所有文章
    allArticles = Array.from(document.querySelectorAll('.article-card'));
    filteredArticles = allArticles;

    // 设置事件监听器
    setupEventListeners();

    // 显示第一页
    showPage(1);
});

// 设置事件监听器
function setupEventListeners() {
    // 作者筛选
    const sourceFilter = document.getElementById('source-filter');
    if (sourceFilter) {
        sourceFilter.addEventListener('change', function() {
            currentSourceFilter = this.value;
            filterArticles();
            currentPage = 1;
            showPage(1);
        });
    }

    // 标签筛选
    const tagFilter = document.getElementById('tag-filter');
    if (tagFilter) {
        tagFilter.addEventListener('change', function() {
            currentTagFilter = this.value;
            filterArticles();
            currentPage = 1;
            showPage(1);
        });
    }

    // 分页按钮
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');

    if (prevBtn) {
        prevBtn.addEventListener('click', function() {
            if (currentPage > 1) {
                currentPage--;
                showPage(currentPage);
                scrollToTop();
            }
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', function() {
            const totalPages = Math.ceil(filteredArticles.length / ARTICLES_PER_PAGE);
            if (currentPage < totalPages) {
                currentPage++;
                showPage(currentPage);
                scrollToTop();
            }
        });
    }
}

// 筛选文章
function filterArticles() {
    filteredArticles = allArticles.filter(article => {
        // 按作者筛选
        const sourceMatch = currentSourceFilter === 'all' || article.dataset.source === currentSourceFilter;

        // 按标签筛选
        const articleTags = article.dataset.tags ? article.dataset.tags.split(',') : [];
        const tagMatch = currentTagFilter === 'all' || articleTags.includes(currentTagFilter);

        return sourceMatch && tagMatch;
    });

    // 更新文章计数
    updateArticleCount();
}

// 显示指定页面
function showPage(page) {
    const startIndex = (page - 1) * ARTICLES_PER_PAGE;
    const endIndex = startIndex + ARTICLES_PER_PAGE;

    // 隐藏所有文章
    allArticles.forEach(article => {
        article.style.display = 'none';
    });

    // 显示当前页的文章
    filteredArticles.slice(startIndex, endIndex).forEach(article => {
        article.style.display = 'block';
    });

    // 更新分页信息
    updatePagination(page);
}

// 更新分页信息
function updatePagination(page) {
    const totalPages = Math.ceil(filteredArticles.length / ARTICLES_PER_PAGE);
    const pageInfo = document.getElementById('page-info');
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');

    if (pageInfo) {
        pageInfo.textContent = `第 ${page} / ${totalPages} 页`;
    }

    // 更新按钮状态
    if (prevBtn) {
        prevBtn.disabled = page === 1;
    }

    if (nextBtn) {
        nextBtn.disabled = page === totalPages;
    }
}

// 更新文章计数
function updateArticleCount() {
    const countElement = document.getElementById('article-count');
    if (countElement) {
        countElement.textContent = `📊 共 ${filteredArticles.length} 篇文章`;
    }
}

// 滚动到顶部
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

