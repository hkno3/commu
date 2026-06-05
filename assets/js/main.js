const CATEGORIES = [
  '전체','정치','경제','사회','생활/문화','세계','IT/과학','부동산','헬스/건강','스포츠','연예',
  '자동차','날씨','가상화폐','주식','육아','여행','게임','패션/뷰티','음식/맛집','교육','환경','법률','취업/직장','반려동물','영화'
];
const CAT_MAP = {
  '전체': 'all', '정치': '정치', '경제': '경제', '사회': '사회',
  '생활/문화': '생활_문화', '세계': '세계', 'IT/과학': 'IT_과학',
  '부동산': '부동산', '헬스/건강': '헬스_건강', '스포츠': '스포츠', '연예': '연예',
  '자동차': '자동차', '날씨': '날씨', '가상화폐': '가상화폐', '주식': '주식',
  '육아': '육아', '여행': '여행', '게임': '게임', '패션/뷰티': '패션_뷰티',
  '음식/맛집': '음식_맛집', '교육': '교육', '환경': '환경', '법률': '법률',
  '취업/직장': '취업_직장', '반려동물': '반려동물', '영화': '영화'
};
const CAT_COLORS = {
  '정치': '#c0392b', '경제': '#27ae60', '사회': '#2980b9',
  '생활_문화': '#e67e22', '세계': '#8e44ad', 'IT_과학': '#16a085',
  '부동산': '#d35400', '헬스_건강': '#1abc9c', '스포츠': '#2471a3', '연예': '#c0392b',
  '자동차': '#7f8c8d', '날씨': '#2980b9', '가상화폐': '#f39c12', '주식': '#27ae60',
  '육아': '#e91e8c', '여행': '#00897b', '게임': '#6c3483', '패션_뷰티': '#e91e63',
  '음식_맛집': '#e74c3c', '교육': '#1565c0', '환경': '#2e7d32', '법률': '#4a235a',
  '취업_직장': '#1a237e', '반려동물': '#ff6f00', '영화': '#880e4f',
};
const CAT_BG = {
  '정치': '#fff0f0', '경제': '#f0fff4', '사회': '#f0f4ff',
  '생활_문화': '#fff8f0', '세계': '#f5f0ff', 'IT_과학': '#f0fffe',
  '부동산': '#fffbf0', '헬스_건강': '#f0fff8', '스포츠': '#f0f8ff', '연예': '#fff0fb',
  '자동차': '#f5f5f5', '날씨': '#e3f2fd', '가상화폐': '#fff8e1', '주식': '#f1f8e9',
  '육아': '#fce4ec', '여행': '#e0f2f1', '게임': '#f3e5f5', '패션_뷰티': '#fce4ec',
  '음식_맛집': '#fff3e0', '교육': '#e8eaf6', '환경': '#e8f5e9', '법률': '#f3e5f5',
  '취업_직장': '#e8eaf6', '반려동물': '#fff3e0', '영화': '#fce4ec',
};

// Allow category to be preset from PHP (category.php / article.php)
let currentCategory = (typeof INITIAL_CATEGORY !== 'undefined') ? INITIAL_CATEGORY : 'all';
let currentArticle = null;
let articles = [];
let page = 1;
let loading = false;
let hasMore = true;
let commentPage = 1;
let commentHasMore = false;

document.addEventListener('DOMContentLoaded', () => {
  buildCategoryNav();
  // On article.php, ARTICLE_ID is defined; don't auto-load articles list
  if (typeof ARTICLE_ID === 'undefined') {
    loadArticles(true);
    setupInfiniteScroll();
  }
});

let catExpanded = false;

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
    btn.onclick = () => switchCategory(key, btn);
    nav.appendChild(btn);
  });

  // 더보기 버튼 - nav 바깥 별도 행에 배치
  let moreRow = document.getElementById('cat-more-row');
  if (!moreRow) {
    moreRow = document.createElement('div');
    moreRow.id = 'cat-more-row';
    moreRow.className = 'cat-more-row';
    nav.parentElement.appendChild(moreRow);
  }
  moreRow.innerHTML = '';
  const moreBtn = document.createElement('button');
  moreBtn.className = 'cat-more-btn';
  moreBtn.textContent = '더보기 ▼';
  moreBtn.onclick = () => {
    catExpanded = !catExpanded;
    nav.classList.toggle('expanded', catExpanded);
    moreBtn.textContent = catExpanded ? '접기 ▲' : '더보기 ▼';
  };
  moreRow.appendChild(moreBtn);
}

function switchCategory(cat, btnEl) {
  currentCategory = cat;
  page = 1;
  articles = [];
  document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
  btnEl.classList.add('active');
  // 기사 상세 초기화
  const detail = document.getElementById('article-detail');
  if (detail) detail.innerHTML = '<div class="empty-state">기사를 선택하세요.</div>';
  loadArticles(true);
}

async function loadArticles(reset = false) {
  if (loading || (!reset && !hasMore)) return;
  loading = true;

  const listEl = document.getElementById('article-list');
  if (reset) {
    if (listEl) listEl.innerHTML = '<div class="loading">불러오는 중...</div>';
    page = 1;
    hasMore = true;
  }

  try {
    const params = new URLSearchParams({ page, limit: 20 });
    if (currentCategory !== 'all') params.set('category', currentCategory);
    const res = await fetch(`/api/articles.php?${params}`);
    const data = await res.json();

    hasMore = !!data.has_more;
    if (data.articles && data.articles.length > 0) {
      if (reset) {
        articles = data.articles;
        if (listEl) listEl.innerHTML = '';
      } else {
        articles = [...articles, ...data.articles];
      }
      appendArticleCards(data.articles, reset);
      page++;
    } else if (reset) {
      if (listEl) listEl.innerHTML = '<div class="empty-state">기사가 없습니다.</div>';
    }
  } catch (e) {
    if (reset && listEl) listEl.innerHTML = '<div class="empty-state">데이터를 불러올 수 없습니다.</div>';
  }
  loading = false;
}

function setupInfiniteScroll() {
  const sentinel = document.getElementById('scroll-sentinel');
  if (!sentinel) return;
  const observer = new IntersectionObserver(entries => {
    if (entries[0].isIntersecting && !loading && hasMore) {
      loadArticles(false);
    }
  }, { rootMargin: '200px' });
  observer.observe(sentinel);
}

function loadMore() {
  loadArticles(false);
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
  const card = document.createElement('div');
  card.className = 'article-card' + (currentArticle?.article_id === article.article_id ? ' active' : '');
  card.dataset.id = article.article_id;
  const catKey = article.category ? article.category.replace(/\//g, '_') : '';
  const color = CAT_COLORS[catKey] || '#1a73e8';
  const bg    = CAT_BG[catKey]    || '#e8f0fe';
  card.innerHTML = `
    <div class="article-card-meta">
      <span class="cat-badge" style="background:${bg}; color:${color};">${escHtml(article.category_label || article.category || '')}</span>
      <span class="source-name">${escHtml(article.source || '')}</span>
      <span class="pub-date">${formatDate(article.pub_date || article.pubDate)}</span>
    </div>
    <h3>${escHtml(article.title)}</h3>
    <p>${escHtml(article.summary || '')}</p>
    <div class="article-card-footer">
      <span class="comment-count">💬 <span id="cnt-${article.article_id}">${article.comment_count || 0}</span></span>
    </div>
  `;
  card.onclick = () => {
    window.location.href = `/article.php?id=${encodeURIComponent(article.article_id)}`;
  };
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
