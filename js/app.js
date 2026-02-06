// SignalFeed - 增强筛选与分页

const ARTICLES_PER_PAGE = 10;
const TAG_KEY_DELIMITER = "|||";

let currentPage = 1;
let currentSourceFilter = "all";
let tagMatchMode = "or";
let selectedTagFilters = new Set();

let allArticles = [];
let filteredArticles = [];

let sourceFilterElement = null;
let sourceSearchElement = null;
let tagSearchElement = null;
let activeFilterSummaryElement = null;
let filtersPanelElement = null;
let filtersContentElement = null;
let toggleFiltersElement = null;
let filtersToggleIconElement = null;
let filtersToggleHintElement = null;
let filtersActiveBadgeElement = null;
let allSourceOptionElement = null;
let sourceOptionElements = [];
let tagChipElements = [];

const sourceLabelMap = new Map();
const tagLabelMap = new Map();

document.addEventListener("DOMContentLoaded", () => {
    initializeArticleData();
    cacheFilterElements();
    hydrateStateFromUrl();
    setupEventListeners();
    refreshFilterControls();
    initializeFiltersPanelState();
    applyFilters({ resetPage: false, syncUrl: false });
});

function initializeArticleData() {
    const articleElements = Array.from(document.querySelectorAll(".article-card"));
    allArticles = articleElements.map((element) => {
        const sourceLabel = normalizeText(element.dataset.source || "Unknown");
        const sourceKey = normalizeKey(element.dataset.sourceKey || sourceLabel);
        const tagKeys = parseTagKeys(element.dataset.tagKeys || "");

        sourceLabelMap.set(sourceKey, sourceLabel);

        return {
            element,
            sourceLabel,
            sourceKey,
            tagKeys,
        };
    });

    filteredArticles = allArticles;
}

function cacheFilterElements() {
    filtersPanelElement = document.getElementById("filters-panel");
    filtersContentElement = document.getElementById("filters-content");
    toggleFiltersElement = document.getElementById("toggle-filters");
    filtersToggleIconElement = document.querySelector(".filters-toggle-icon");
    filtersToggleHintElement = document.querySelector(".filters-toggle-hint");
    filtersActiveBadgeElement = document.getElementById("filters-active-badge");

    sourceFilterElement = document.getElementById("source-filter");
    sourceSearchElement = document.getElementById("source-search");
    tagSearchElement = document.getElementById("tag-search");
    activeFilterSummaryElement = document.getElementById("active-filter-summary");

    if (sourceFilterElement) {
        allSourceOptionElement = sourceFilterElement.querySelector('option[value="all"]');
        sourceOptionElements = Array.from(sourceFilterElement.querySelectorAll('option:not([value="all"])'));

        if (allSourceOptionElement) {
            allSourceOptionElement.dataset.baseLabel = allSourceOptionElement.dataset.sourceLabel || "全部来源";
        }

        sourceOptionElements.forEach((option) => {
            const baseLabel = normalizeText(option.dataset.sourceLabel || stripCountSuffix(option.textContent));
            option.dataset.baseLabel = baseLabel;
            sourceLabelMap.set(option.value, baseLabel);
        });
    }

    tagChipElements = Array.from(document.querySelectorAll(".tag-chip-filter"));
    tagChipElements.forEach((chip) => {
        const baseLabel = normalizeText(
            chip.dataset.tagLabel ||
                chip.querySelector(".tag-chip-name")?.textContent ||
                ""
        );
        const tagKey = normalizeKey(chip.dataset.tagKey || baseLabel);

        chip.dataset.tagKey = tagKey;
        chip.dataset.baseLabel = baseLabel;
        tagLabelMap.set(tagKey, baseLabel);
    });
}

function hydrateStateFromUrl() {
    const params = new URLSearchParams(window.location.search);

    const source = params.get("source");
    if (source) {
        currentSourceFilter = normalizeKey(source);
    }

    const tags = params.get("tags");
    if (tags) {
        tags.split(",").forEach((tag) => {
            const key = normalizeKey(tag);
            if (key) {
                selectedTagFilters.add(key);
            }
        });
    }

    const mode = params.get("mode");
    if (mode === "and" || mode === "or") {
        tagMatchMode = mode;
    }

    const page = Number.parseInt(params.get("page"), 10);
    if (Number.isInteger(page) && page > 0) {
        currentPage = page;
    }
}

function setupEventListeners() {
    if (toggleFiltersElement) {
        toggleFiltersElement.addEventListener("click", () => {
            const expanded = !toggleFiltersElement.classList.contains("is-expanded");
            setFiltersPanelExpanded(expanded);
        });
    }

    if (sourceFilterElement) {
        sourceFilterElement.addEventListener("change", function handleSourceChange() {
            currentSourceFilter = this.value;
            applyFilters();
        });
    }

    if (sourceSearchElement) {
        sourceSearchElement.addEventListener("input", () => {
            filterSourceOptionsBySearchTerm();
        });
    }

    if (tagSearchElement) {
        tagSearchElement.addEventListener("input", () => {
            filterTagChipsBySearchTerm();
        });
    }

    tagChipElements.forEach((chip) => {
        chip.addEventListener("click", () => {
            const tagKey = chip.dataset.tagKey;
            if (!tagKey) {
                return;
            }

            if (selectedTagFilters.has(tagKey)) {
                selectedTagFilters.delete(tagKey);
            } else {
                selectedTagFilters.add(tagKey);
            }

            applyFilters();
        });
    });

    document.querySelectorAll('input[name="tag-match-mode"]').forEach((input) => {
        input.addEventListener("change", function handleTagModeChange() {
            if (this.checked) {
                tagMatchMode = this.value;
                applyFilters();
            }
        });
    });

    const clearFiltersButton = document.getElementById("clear-filters");
    if (clearFiltersButton) {
        clearFiltersButton.addEventListener("click", () => {
            clearFilters();
        });
    }

    const prevButton = document.getElementById("prev-page");
    const nextButton = document.getElementById("next-page");

    if (prevButton) {
        prevButton.addEventListener("click", () => {
            if (currentPage > 1) {
                goToPage(currentPage - 1);
            }
        });
    }

    if (nextButton) {
        nextButton.addEventListener("click", () => {
            const totalPages = Math.ceil(filteredArticles.length / ARTICLES_PER_PAGE);
            if (currentPage < totalPages) {
                goToPage(currentPage + 1);
            }
        });
    }
}

function refreshFilterControls() {
    const validSourceValues = new Set(["all", ...sourceOptionElements.map((option) => option.value)]);
    if (!validSourceValues.has(currentSourceFilter)) {
        currentSourceFilter = "all";
    }

    if (sourceFilterElement) {
        sourceFilterElement.value = currentSourceFilter;
    }

    const validTagKeys = new Set(tagChipElements.map((chip) => chip.dataset.tagKey));
    selectedTagFilters = new Set(
        Array.from(selectedTagFilters).filter((key) => validTagKeys.has(key))
    );

    document.querySelectorAll('input[name="tag-match-mode"]').forEach((input) => {
        input.checked = input.value === tagMatchMode;
    });

    filterSourceOptionsBySearchTerm();
    filterTagChipsBySearchTerm();
}

function initializeFiltersPanelState() {
    let shouldExpand = hasActiveFilters();

    if (!shouldExpand) {
        try {
            const persisted = window.localStorage.getItem("signalfeed_filters_expanded");
            if (persisted === "1" || persisted === "0") {
                shouldExpand = persisted === "1";
            }
        } catch (_error) {
            // Ignore storage access failures.
        }
    }

    setFiltersPanelExpanded(shouldExpand, { persist: false });
}

function hasActiveFilters() {
    return currentSourceFilter !== "all" || selectedTagFilters.size > 0;
}

function getActiveFilterCount() {
    let count = 0;
    if (currentSourceFilter !== "all") {
        count += 1;
    }
    count += selectedTagFilters.size;
    return count;
}

function updateFiltersToggleBadge() {
    if (!filtersActiveBadgeElement || !toggleFiltersElement) {
        return;
    }

    const count = getActiveFilterCount();
    const hasActive = count > 0;

    filtersActiveBadgeElement.hidden = !hasActive;
    filtersActiveBadgeElement.textContent = String(count);
    toggleFiltersElement.classList.toggle("has-active-filters", hasActive);

    if (hasActive) {
        filtersActiveBadgeElement.setAttribute("aria-label", `当前已启用 ${count} 个筛选条件`);
    } else {
        filtersActiveBadgeElement.removeAttribute("aria-label");
    }
}

function setFiltersPanelExpanded(expanded, options = {}) {
    const { persist = true } = options;
    if (!filtersPanelElement || !filtersContentElement || !toggleFiltersElement) {
        return;
    }

    filtersPanelElement.classList.toggle("is-collapsed", !expanded);
    filtersContentElement.hidden = !expanded;
    toggleFiltersElement.classList.toggle("is-expanded", expanded);
    toggleFiltersElement.setAttribute("aria-expanded", expanded ? "true" : "false");

    if (filtersToggleIconElement) {
        filtersToggleIconElement.textContent = expanded ? "▾" : "▸";
    }

    if (filtersToggleHintElement) {
        filtersToggleHintElement.textContent = expanded ? "点击收起" : "点击展开";
    }

    if (persist) {
        try {
            window.localStorage.setItem("signalfeed_filters_expanded", expanded ? "1" : "0");
        } catch (_error) {
            // Ignore storage access failures.
        }
    }
}

function applyFilters(options = {}) {
    const { resetPage = true, syncUrl = true } = options;

    if (resetPage) {
        currentPage = 1;
    }

    filteredArticles = allArticles.filter((article) => matchesAllFilters(article));

    updateArticleCount();
    updateActiveFilterSummary();
    updateFiltersToggleBadge();
    updateSourceOptionCounts();
    updateTagChipCounts();
    showPage(currentPage);

    if (syncUrl) {
        syncStateToUrl();
    }
}

function matchesAllFilters(article) {
    const sourceMatch =
        currentSourceFilter === "all" || article.sourceKey === currentSourceFilter;
    if (!sourceMatch) {
        return false;
    }

    return matchesTagSelection(article.tagKeys);
}

function matchesTagSelection(articleTagKeys) {
    if (selectedTagFilters.size === 0) {
        return true;
    }

    const selected = Array.from(selectedTagFilters);
    if (tagMatchMode === "and") {
        return selected.every((tagKey) => articleTagKeys.includes(tagKey));
    }

    return selected.some((tagKey) => articleTagKeys.includes(tagKey));
}

function updateSourceOptionCounts() {
    if (!sourceFilterElement) {
        return;
    }

    const totalForAll = allArticles.filter((article) => matchesTagSelection(article.tagKeys)).length;
    if (allSourceOptionElement) {
        const baseLabel = allSourceOptionElement.dataset.baseLabel || "全部来源";
        allSourceOptionElement.textContent = `${baseLabel} (${totalForAll})`;
    }

    sourceOptionElements.forEach((option) => {
        const baseLabel = option.dataset.baseLabel || stripCountSuffix(option.textContent);
        const count = allArticles.filter(
            (article) =>
                article.sourceKey === option.value &&
                matchesTagSelection(article.tagKeys)
        ).length;

        option.textContent = `${baseLabel} (${count})`;
        option.disabled = count === 0 && option.value !== currentSourceFilter;
    });
}

function updateTagChipCounts() {
    const sourceScopedArticles = allArticles.filter(
        (article) => currentSourceFilter === "all" || article.sourceKey === currentSourceFilter
    );

    tagChipElements.forEach((chip) => {
        const tagKey = chip.dataset.tagKey;
        const count = sourceScopedArticles.filter((article) =>
            article.tagKeys.includes(tagKey)
        ).length;
        const isSelected = selectedTagFilters.has(tagKey);

        chip.classList.toggle("is-selected", isSelected);
        chip.setAttribute("aria-pressed", isSelected ? "true" : "false");
        chip.disabled = count === 0 && !isSelected;

        const countElement = chip.querySelector(".tag-chip-count");
        if (countElement) {
            countElement.textContent = String(count);
        }
    });
}

function showPage(page) {
    allArticles.forEach((article) => {
        article.element.style.display = "none";
    });

    if (filteredArticles.length === 0) {
        updatePagination(0, 0);
        toggleEmptyState(true);
        return;
    }

    const totalPages = Math.ceil(filteredArticles.length / ARTICLES_PER_PAGE);
    currentPage = Math.min(Math.max(page, 1), totalPages);

    const startIndex = (currentPage - 1) * ARTICLES_PER_PAGE;
    const endIndex = startIndex + ARTICLES_PER_PAGE;

    filteredArticles.slice(startIndex, endIndex).forEach((article) => {
        article.element.style.display = "block";
    });

    updatePagination(currentPage, totalPages);
    toggleEmptyState(false);
}

function goToPage(page) {
    currentPage = page;
    showPage(currentPage);
    syncStateToUrl();
    scrollToTop();
}

function updatePagination(page, totalPages) {
    const pageInfo = document.getElementById("page-info");
    const prevButton = document.getElementById("prev-page");
    const nextButton = document.getElementById("next-page");

    if (pageInfo) {
        pageInfo.textContent = totalPages === 0 ? "第 0 / 0 页" : `第 ${page} / ${totalPages} 页`;
    }

    if (prevButton) {
        prevButton.disabled = totalPages === 0 || page <= 1;
    }

    if (nextButton) {
        nextButton.disabled = totalPages === 0 || page >= totalPages;
    }
}

function updateArticleCount() {
    const countElement = document.getElementById("article-count");
    if (countElement) {
        countElement.textContent = `📊 显示 ${filteredArticles.length} / ${allArticles.length} 篇文章`;
    }
}

function updateActiveFilterSummary() {
    if (!activeFilterSummaryElement) {
        return;
    }

    const sourceLabel =
        currentSourceFilter === "all"
            ? "全部来源"
            : sourceLabelMap.get(currentSourceFilter) || "未知来源";

    let tagSummary = "全部标签";
    if (selectedTagFilters.size > 0) {
        const labels = Array.from(selectedTagFilters)
            .map((key) => tagLabelMap.get(key) || key)
            .sort((left, right) => left.localeCompare(right, "zh-CN"));
        tagSummary = labels.join("、");

        if (selectedTagFilters.size > 1) {
            const modeLabel = tagMatchMode === "and" ? "全部匹配" : "任一匹配";
            tagSummary = `${tagSummary}（${modeLabel}）`;
        }
    }

    activeFilterSummaryElement.textContent = `当前筛选：${sourceLabel} · ${tagSummary}`;
}

function filterSourceOptionsBySearchTerm() {
    if (!sourceSearchElement || sourceOptionElements.length === 0) {
        return;
    }

    const keyword = normalizeKey(sourceSearchElement.value);
    sourceOptionElements.forEach((option) => {
        const label = normalizeKey(option.dataset.baseLabel || "");
        option.hidden = Boolean(keyword) && !label.includes(keyword);
    });

    if (currentSourceFilter !== "all") {
        const selectedOption = sourceOptionElements.find(
            (option) => option.value === currentSourceFilter
        );
        if (selectedOption && selectedOption.hidden) {
            currentSourceFilter = "all";
            if (sourceFilterElement) {
                sourceFilterElement.value = "all";
            }
            applyFilters();
        }
    }
}

function filterTagChipsBySearchTerm() {
    if (!tagSearchElement || tagChipElements.length === 0) {
        return;
    }

    const keyword = normalizeKey(tagSearchElement.value);
    tagChipElements.forEach((chip) => {
        const label = normalizeKey(chip.dataset.baseLabel || "");
        chip.hidden = Boolean(keyword) && !label.includes(keyword);
    });
}

function clearFilters() {
    currentSourceFilter = "all";
    selectedTagFilters.clear();
    tagMatchMode = "or";
    currentPage = 1;

    if (sourceFilterElement) {
        sourceFilterElement.value = "all";
    }
    if (sourceSearchElement) {
        sourceSearchElement.value = "";
    }
    if (tagSearchElement) {
        tagSearchElement.value = "";
    }

    sourceOptionElements.forEach((option) => {
        option.hidden = false;
    });
    tagChipElements.forEach((chip) => {
        chip.hidden = false;
    });

    document.querySelectorAll('input[name="tag-match-mode"]').forEach((input) => {
        input.checked = input.value === "or";
    });

    applyFilters();
}

function toggleEmptyState(showEmptyState) {
    const emptyStateElement = document.getElementById("empty-state");
    if (emptyStateElement) {
        emptyStateElement.hidden = !showEmptyState;
    }
}

function syncStateToUrl() {
    const params = new URLSearchParams();

    if (currentSourceFilter !== "all") {
        params.set("source", currentSourceFilter);
    }

    if (selectedTagFilters.size > 0) {
        const tags = Array.from(selectedTagFilters).sort();
        params.set("tags", tags.join(","));
    }

    if (tagMatchMode !== "or" && selectedTagFilters.size > 1) {
        params.set("mode", tagMatchMode);
    }

    if (currentPage > 1) {
        params.set("page", String(currentPage));
    }

    const query = params.toString();
    const base = `${window.location.pathname}${window.location.hash}`;
    const nextUrl = query
        ? `${window.location.pathname}?${query}${window.location.hash}`
        : base;

    window.history.replaceState(null, "", nextUrl);
}

function parseTagKeys(rawValue) {
    if (!rawValue) {
        return [];
    }

    return rawValue
        .split(TAG_KEY_DELIMITER)
        .map((tag) => normalizeKey(tag))
        .filter(Boolean);
}

function normalizeText(value) {
    return String(value || "")
        .replace(/\s+/g, " ")
        .trim();
}

function normalizeKey(value) {
    return normalizeText(value).toLocaleLowerCase();
}

function stripCountSuffix(text) {
    return normalizeText(text).replace(/\s+\(\d+\)$/, "");
}

function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: "smooth",
    });
}
