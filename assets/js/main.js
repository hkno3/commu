const CATEGORIES = [
  '전체','정치','경제','사회','생활/문화','IT/과학','헬스/건강','스포츠','연예',
  '가상화폐','주식'
];
const CAT_MAP = {
  '전체': 'all', '정치': '정치', '경제': '경제', '사회': '사회',
  '생활/문화': '생활_문화', 'IT/과학': 'IT_과학',
  '헬스/건강': '헬스_건강', '스포츠': '스포츠', '연예': '연예',
  '가상화폐': '가상화폐', '주식': '주식'
};
const CAT_COLORS = {
  '정치': '#c0392b', '경제': '#27ae60', '사회': '#2980b9',
  '생활_문화': '#e67e22', 'IT_과학': '#16a085',
  '헬스_건강': '#1abc9c', '스포츠': '#2471a3', '연예': '#c0392b',
  '가상화폐': '#f39c12', '주식': '#27ae60',
};
const CAT_BG = {
  '정치': '#fff0f0', '경제': '#f0fff4', '사회': '#f0f4ff',
  '생활_문화': '#fff8f0', 'IT_과학': '#f0fffe',
  '헬스_건강': '#f0fff8', '스포츠': '#f0f8ff', '연예': '#fff0fb',
  '가상화폐': '#fff8e1', '주식': '#f1f8e9',
};

// Allow category to be preset from PHP (category.php / article.php)
let currentCategory = (typeof INITIAL_CATEGORY !== 'undefined') ? INITIAL_CATEGORY : 'all';
let currentArticle = null;
let articles = [];
let page = 1;
let loading = false;
let totalArticles = 0;
const PAGE_SIZE = 20;
let commentPage = 1;
let commentHasMore = false;

document.addEventListener('DOMContentLoaded', () => {
  buildCategoryNav();
  // On article.php, ARTICLE_ID is defined; don't auto-load articles list
  if (typeof ARTICLE_ID === 'undefined') {
    loadArticles(true);
  }
});

function buildCategoryNav() {
  const nav = document.getElementById('cat-nav-inner');
  if (!nav) return;
  nav.innerHTML = '';
  CATEGORIES.forEach(cat => {
    const key = CAT_MAP[cat];
    const btn = document.createElement('button');
    btn.className = 'cat-btn' + (key === currentCategory ? ' active' : '');
    btn.textContent = cat;
    btn.dataset.catKey = key;
    btn.onclick = () => {
      if (document.getElementById('article-list')) {
        switchCategory(key, btn);
      } else {
        const slug = CAT_SLUG[key];
        window.location.href = key === 'all' ? '/' : (slug ? `/${slug}` : `/?cat=${encodeURIComponent(key)}`);
      }
    };
    nav.appendChild(btn);
  });
}

const CAT_SLUG = {
  '정치':'politics','경제':'economy','사회':'society','생활_문화':'lifestyle',
  'IT_과학':'tech','헬스_건강':'health',
  '스포츠':'sports','연예':'entertainment',
  '가상화폐':'crypto','주식':'stock',
};

function switchCategory(cat, btnEl) {
  currentCategory = cat;
  page = 1;
  articles = [];
  document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
  btnEl.classList.add('active');
  const detail = document.getElementById('article-detail');
  if (detail) detail.innerHTML = '<div class="empty-state">기사를 선택하세요.</div>';
  const slug = CAT_SLUG[cat];
  const newUrl = cat === 'all' ? '/' : (slug ? `/${slug}` : `/?cat=${encodeURIComponent(cat)}`);
  history.pushState({cat}, '', newUrl);
  loadArticles(true);
}

function goToPage(p) {
  if (loading || p === page || p < 1) return;
  page = p;
  loadArticles(false, true);
  const listEl = document.getElementById('article-list');
  if (listEl) listEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function loadArticles(reset = false, replace = false) {
  if (loading) return;
  loading = true;

  const listEl = document.getElementById('article-list');
  if (reset) {
    if (listEl) listEl.innerHTML = '<div class="loading">불러오는 중...</div>';
    page = 1;
  } else if (replace) {
    if (listEl) listEl.innerHTML = '<div class="loading">불러오는 중...</div>';
  }

  try {
    const params = new URLSearchParams({ page, limit: PAGE_SIZE });
    if (currentCategory !== 'all') params.set('category', currentCategory);
    const res = await fetch(`/api/articles.php?${params}`);
    const data = await res.json();

    totalArticles = data.total || 0;
    if (data.articles && data.articles.length > 0) {
      articles = data.articles;
      appendArticleCards(data.articles, true);
    } else {
      if (listEl) listEl.innerHTML = '<div class="empty-state">기사가 없습니다.</div>';
    }
    renderPagination();
  } catch (e) {
    if (listEl) listEl.innerHTML = '<div class="empty-state">데이터를 불러올 수 없습니다.</div>';
  }
  loading = false;
}

function renderPagination() {
  const wrap = document.getElementById('pagination');
  if (!wrap) return;
  const totalPages = Math.max(1, Math.ceil(totalArticles / PAGE_SIZE));
  if (totalPages <= 1) { wrap.innerHTML = ''; return; }

  const groupSize = 10;
  const groupStart = Math.floor((page - 1) / groupSize) * groupSize + 1;
  const groupEnd = Math.min(groupStart + groupSize - 1, totalPages);

  let html = '';
  html += `<button class="page-btn" ${groupStart === 1 ? 'disabled' : ''} onclick="goToPage(${groupStart - 1})">이전</button>`;
  for (let p = groupStart; p <= groupEnd; p++) {
    html += `<button class="page-btn${p === page ? ' active' : ''}" onclick="goToPage(${p})">${p}</button>`;
  }
  html += `<button class="page-btn" ${groupEnd === totalPages ? 'disabled' : ''} onclick="goToPage(${groupEnd + 1})">다음</button>`;
  wrap.innerHTML = html;
}

function appendArticleCards(newArticles, replace = false) {
  const listEl = document.getElementById('article-list');
  if (!listEl) return;
  if (replace) listEl.innerHTML = '';

  newArticles.forEach(article => {
    const card = createArticleCard(article);
    listEl.appendChild(card);
  });
  loadCommentCounts(newArticles);
}

function createArticleCard(article) {
  const slug = article.slug;
  const isHexId = slug && /^[0-9a-f]{8,}$/.test(slug);
  const href = (slug && !isHexId)
    ? `/article.php?slug=${encodeURIComponent(slug)}`
    : `/article.php?id=${encodeURIComponent(article.article_id)}`;

  const card = document.createElement('a');
  card.href = href;
  card.className = 'article-card' + (currentArticle?.article_id === article.article_id ? ' active' : '');
  card.dataset.id = article.article_id;
  const catKey = article.category ? article.category.replace(/\//g, '_') : '';
  const color = CAT_COLORS[catKey] || '#1a73e8';
  const bg    = CAT_BG[catKey]    || '#e8f0fe';
  const imgHtml = article.image_url
    ? `<div class="article-card-img"><img src="${escHtml(article.image_url)}" alt="" loading="lazy" onerror="this.parentElement.style.display='none'"></div>`
    : '';
  card.innerHTML = `
    ${imgHtml}
    <div class="article-card-body">
      <div class="article-card-meta">
        <span class="cat-badge" style="background:${bg}; color:${color};">${escHtml(article.category_label || article.category || '')}</span>
        <span class="pub-date">${formatDate(article.pub_date || article.pubDate)}</span>
      </div>
      <h3>${escHtml(article.title)}</h3>
      <p>${escHtml(article.summary || '')}</p>
      <div class="article-card-footer">
        <span class="comment-count">💬 <span id="cnt-${article.article_id}">${article.comment_count || 0}</span></span>
      </div>
    </div>
  `;
  return card;
}

// Keep renderArticleList for backwards compat
function renderArticleList() {
  appendArticleCards(articles, true);
}

async function loadCommentCounts(list) {
  const target = list || articles;
  for (const article of target) {
    try {
      const res = await fetch(`/api/comment.php?article_id=${encodeURIComponent(article.article_id)}&count=1`);
      const data = await res.json();
      const el = document.getElementById('cnt-' + article.article_id);
      if (el && data.count !== undefined) el.textContent = data.count;
    } catch (e) {}
  }
}

function selectArticle(article) {
  currentArticle = article;
  document.querySelectorAll('.article-card').forEach(c => {
    c.classList.toggle('active', c.dataset.id === article.article_id);
  });
  renderArticleDetail(article);
  loadComments(article.article_id);
}

function renderArticleDetail(article) {
  const panel = document.getElementById('article-detail');
  if (!panel) return;
  const catKey = article.category ? article.category.replace(/\//g, '_') : '';
  const color  = CAT_COLORS[catKey] || '#1a73e8';
  const bg     = CAT_BG[catKey]    || '#e8f0fe';
  const url    = article.original_url || article.url || '#';
  const pubDate = article.pub_date || article.pubDate || '';
  panel.innerHTML = `
    <div class="article-detail-header">
      <div class="article-detail-meta">
        <span class="cat-badge" style="background:${bg}; color:${color};">${escHtml(article.category_label || article.category || '')}</span>
        <span>${escHtml(article.source || '')}</span>
        <span>${formatDate(pubDate)}</span>
      </div>
      <h2>${escHtml(article.title)}</h2>
      ${url !== '#' ? `<a class="original-link" href="${escHtml(url)}" target="_blank" rel="noopener noreferrer">원문 보기 →</a>` : ''}
    </div>
    <div class="article-summary">${escHtml(article.summary || '').replace(/\n/g, '<br>')}</div>
    <div style="margin-top:12px;">
      <a href="/article.php?id=${encodeURIComponent(article.article_id)}"
         style="font-size:12px; color:var(--primary);">상세 페이지에서 보기 →</a>
    </div>
  `;
}

async function loadComments(articleId, reset = true) {
  const listEl = document.getElementById('comment-list');
  if (!listEl) return;

  if (reset) {
    commentPage = 1;
    commentHasMore = false;
    listEl.innerHTML = '<div class="loading">댓글 불러오는 중...</div>';
  }

  try {
    const res = await fetch(`/api/comment.php?article_id=${encodeURIComponent(articleId)}&page=${commentPage}`);
    const data = await res.json();
    const comments = data.comments || [];
    commentHasMore = !!data.has_more;

    // Update count badge
    const badge = document.getElementById('comment-count-badge');
    if (badge && data.total !== undefined) {
      badge.textContent = `(${data.total}개)`;
    }

    // Update card count badge
    const cardCnt = document.getElementById('cnt-' + articleId);
    if (cardCnt && data.total !== undefined) cardCnt.textContent = data.total;

    if (reset) listEl.innerHTML = '';

    if (comments.length === 0 && reset) {
      listEl.innerHTML = '<div class="empty-state">첫 댓글을 남겨보세요!</div>';
    } else {
      comments.forEach(c => {
        const el = document.createElement('div');
        el.className = 'comment-item';
        el.innerHTML = `
          <div class="comment-item-meta">
            <span class="comment-nick">${escHtml(c.nickname)}</span>
            <span class="comment-time">${formatDate(c.created_at)}</span>
          </div>
          <div class="comment-content">${escHtml(c.content)}</div>
        `;
        listEl.appendChild(el);
      });
    }

    // Show/hide load more
    const moreBtn = document.getElementById('load-more-comments');
    if (moreBtn) moreBtn.style.display = commentHasMore ? 'block' : 'none';

  } catch (e) {
    if (reset) listEl.innerHTML = '<div class="empty-state">댓글을 불러올 수 없습니다.</div>';
  }
}

async function loadMoreComments() {
  if (!currentArticle && typeof ARTICLE_ID === 'undefined') return;
  commentPage++;
  const aid = (typeof ARTICLE_ID !== 'undefined') ? ARTICLE_ID : currentArticle?.article_id;
  if (aid) await loadComments(aid, false);
}

async function submitComment(e) {
  e.preventDefault();

  // Determine article_id from context
  const articleId = (typeof ARTICLE_ID !== 'undefined')
    ? ARTICLE_ID
    : currentArticle?.article_id;

  if (!articleId) return;

  const form = e.target;
  const nickname = form.nickname.value.trim() || '익명';
  const content  = form.content.value.trim();
  const errEl    = document.getElementById('comment-error');

  if (!content) return;

  if (errEl) { errEl.textContent = ''; errEl.style.display = 'none'; }

  const btn = form.querySelector('.comment-submit-btn') || document.getElementById('comment-btn');
  if (btn) { btn.disabled = true; btn.textContent = '등록 중...'; }

  try {
    const res = await fetch('/api/comment.php', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ article_id: articleId, nickname, content })
    });
    const data = await res.json();
    if (data.success) {
      form.content.value = '';
      form.nickname.value = '';
      loadComments(articleId, true);
    } else {
      const msg = data.error || data.message || '댓글 등록에 실패했습니다.';
      if (errEl) { errEl.textContent = msg; errEl.style.display = 'block'; }
      else alert(msg);
    }
  } catch (err) {
    const msg = '댓글 등록에 실패했습니다.';
    if (errEl) { errEl.textContent = msg; errEl.style.display = 'block'; }
    else alert(msg);
  }

  if (btn) { btn.disabled = false; btn.textContent = '댓글 등록'; }
}

function escHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function formatDate(str) {
  if (!str) return '';
  const d = new Date(str);
  if (isNaN(d)) return str;
  const now = new Date();
  const diff = Math.floor((now - d) / 1000);
  if (diff < 60) return '방금 전';
  if (diff < 3600) return Math.floor(diff/60) + '분 전';
  if (diff < 86400) return Math.floor(diff/3600) + '시간 전';
  return `${d.getMonth()+1}월 ${d.getDate()}일`;
}

window.submitComment = submitComment;
