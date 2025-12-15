// API設定
const API_BASE_URL = 'http://localhost:5000/api';

// DOM要素の取得
const newsList = document.getElementById('newsList');
const categoryFilter = document.getElementById('categoryFilter');
const newsCount = document.getElementById('newsCount');
const loading = document.getElementById('loading');
const errorElement = document.getElementById('error');
const toast = document.getElementById('toast');

// 状態管理
let currentNews = [];

/**
 * 初期化
 */
async function init() {
    try {
        await loadCategories();
        setupEventListeners();
    } catch (error) {
        showError('アプリケーションの初期化に失敗しました: ' + error.message);
    }
}

/**
 * イベントリスナーのセットアップ
 */
function setupEventListeners() {
    categoryFilter.addEventListener('change', handleCategoryChange);
}

/**
 * カテゴリ一覧の読み込み
 */
async function loadCategories() {
    try {
        const response = await fetch(`${API_BASE_URL}/categories`);
        if (!response.ok) throw new Error('カテゴリの取得に失敗しました');

        const categories = await response.json();
        populateCategoryFilter(categories);
    } catch (error) {
        console.error('カテゴリ読み込みエラー:', error);
        showError('カテゴリの読み込みに失敗しました');
    }
}

/**
 * カテゴリフィルタのオプション設定
 */
function populateCategoryFilter(categories) {
    // 既存のオプション（デフォルト）を保持
    const defaultOption = categoryFilter.querySelector('option[value=""]');
    categoryFilter.innerHTML = '';
    categoryFilter.appendChild(defaultOption);

    categories.forEach(category => {
        const option = document.createElement('option');
        option.value = category;
        option.textContent = category;
        categoryFilter.appendChild(option);
    });
}

/**
 * カテゴリフィルタ変更時の処理
 */
async function handleCategoryChange() {
    const selectedCategory = categoryFilter.value;

    if (!selectedCategory) {
        // カテゴリー未選択時は空の状態を表示
        displayEmptyState();
        updateNewsCount(0);
        return;
    }

    await loadNews(selectedCategory);
}

/**
 * ニュースの読み込み
 */
async function loadNews(category) {
    showLoading();
    hideError();

    try {
        const response = await fetch(`${API_BASE_URL}/news?category=${encodeURIComponent(category)}`);
        if (!response.ok) throw new Error('ニュースの取得に失敗しました');

        currentNews = await response.json();
        displayNews(currentNews);
        updateNewsCount(currentNews.length);
        showToast(`${category}のニュースを${currentNews.length}件取得しました`, 'success');
    } catch (error) {
        showError('ニュースの読み込みに失敗しました: ' + error.message);
        currentNews = [];
        displayNews([]);
        updateNewsCount(0);
    } finally {
        hideLoading();
    }
}

/**
 * ニュース一覧の表示
 */
function displayNews(newsArray) {
    newsList.innerHTML = '';

    if (newsArray.length === 0) {
        displayEmptyState();
        return;
    }

    newsArray.forEach((news, index) => {
        const newsCard = createNewsCard(news, index);
        newsList.appendChild(newsCard);
    });
}

/**
 * 空の状態を表示
 */
function displayEmptyState() {
    newsList.innerHTML = `
        <div class="empty-state">
            <span class="empty-icon">📰</span>
            <p>カテゴリーを選択してニュースを表示</p>
        </div>
    `;
}

/**
 * ニュースカードの生成
 */
function createNewsCard(news, index) {
    const card = document.createElement('a');
    card.href = news.link;
    card.target = '_blank';
    card.rel = 'noopener noreferrer';
    card.className = 'news-card';
    card.style.animationDelay = `${index * 0.05}s`;

    // タグバッジの生成
    const tagsHtml = news.tags.map(tag =>
        `<span class="tag-badge">${escapeHtml(tag)}</span>`
    ).join('');

    // 公開日時のフォーマット
    const publishedTime = news.published
        ? `<div class="published-time">📅 ${formatPublishedDate(news.published)}</div>`
        : '';

    card.innerHTML = `
        <div class="news-card-header">
            <div class="tags-container">${tagsHtml}</div>
            <span class="external-link-icon">🔗</span>
        </div>
        <h3 class="news-title">${escapeHtml(news.title)}</h3>
        <p class="news-summary">${escapeHtml(news.summary)}</p>
        <div class="news-footer">
            ${publishedTime}
        </div>
    `;

    return card;
}

/**
 * ニュース件数の更新
 */
function updateNewsCount(count) {
    newsCount.textContent = `${count} 件`;
}

/**
 * ローディング表示
 */
function showLoading() {
    loading.classList.remove('hidden');
    newsList.style.opacity = '0.3';
}

/**
 * ローディング非表示
 */
function hideLoading() {
    loading.classList.add('hidden');
    newsList.style.opacity = '1';
}

/**
 * エラー表示
 */
function showError(message) {
    errorElement.textContent = message;
    errorElement.classList.remove('hidden');
}

/**
 * エラー非表示
 */
function hideError() {
    errorElement.classList.add('hidden');
}

/**
 * トースト通知の表示
 */
function showToast(message, type = 'success') {
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.classList.remove('hidden');

    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}

/**
 * 公開日時のフォーマット
 */
function formatPublishedDate(dateString) {
    try {
        const date = new Date(dateString);
        return date.toLocaleString('ja-JP', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (error) {
        return dateString;
    }
}

/**
 * HTMLエスケープ
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ページ読み込み時に初期化
document.addEventListener('DOMContentLoaded', init);
