const CATEGORIES = ['전체','정치','경제','사회','생활/문화','세계','IT/과학','부동산','헬스/건강','스포츠','연예'];
const CAT_MAP = {
  '전체': 'all', '정치': '정치', '경제': '경제', '사회': '사회',
  '생활/문화': '생활문화', '세계': '세계', 'IT/과학': 'IT과학',
  '부동산': '부동산', '헬스/건강': '헬스건강', '스포츠': '스포츠', '연예': '연예'
};

let currentCategory = 'all';
let currentArticle = null;
let articles = [];
let page = 1;
let loading = false;

document.addEventListener('DOMContentLoaded', () => {
  buildCategoryNav();
  loadArticles();
});

function buildCategoryNav() {
  const nav = document.getElementById('cat-nav-inner');
  if (!nav) return;
  CATEGORIES.forEach(cat => {
    const btn = document.createElement('button');
    btn.className = 'cat-btn' + (CAT_MAP[cat] === currentCategory ? ' active' : '');
    btn.textContent = cat;
    btn.onclick = () => switchCategory(CAT_MAP[cat], btn);
    nav.appendChild(btn);
  });
}

function switchCategory(cat, btnEl) {
  currentCategory = cat;
  page = 1;
  articles = [];
  document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
  btnEl.classList.add('active');
  loadArticles(true);
}

async function loadArticles(reset = false) {
  if (loading) return;
  loading = true;

  const listEl = document.getElementById('article-list');
  if (reset && listEl) listEl.innerHTML = '<div class="loading">불러오는 중...</div>';

  try {
    const params = new URLSearchParams({ page, limit: 20 });
    if (currentCategory !== 'all') params.set('category', currentCategory);
    const res = await fetch(`/api/articles.php?${params}`);
    const data = await res.json();

    if (data.articles && data.articles.length > 0) {
      articles = reset ? data.articles : [...articles, ...data.articles];
      renderArticleList();
      if (reset && articles.length > 0) selectArticle(articles[0]);
      page++;
    } else if (reset) {
      listEl.innerHTML = '<div class="empty-state">기사가 없습니다.</div>';
    }
  } catch (e) {
    if (reset && listEl) listEl.innerHTML = '<div class="empty-state">데이터를 불러올 수 없습니다.</div>';
  }
  loading = false;
}

function renderArticleList() {
  const listEl = document.getElementById('article-list');
  if (!listEl) return;
  listEl.innerHTML = '';
  articles.forEach(article => {
    const card = document.createElement('div');
    card.className = 'article-card' + (currentArticle?.article_id === article.article_id ? ' active' : '');
    card.dataset.id = article.article_id;
    const catClass = article.category ? 'cat-' + article.category : '';
    card.innerHTML = `
      <div class="article-card-meta">
        <span class="cat-badge ${catClass}">${article.category_label || article.category}</span>
        <span class="source-name">${escHtml(article.source || '')}</span>
        <span class="pub-date">${formatDate(article.pub_date)}</span>
      </div>
      <h3>${escHtml(article.title)}</h3>
      <p>${escHtml(article.summary || '')}</p>
      <div class="article-card-footer">
        <span class="comment-count">💬 <span id="cnt-${article.article_id}">0</span></span>
      </div>
    `;
    card.onclick = () => selectArticle(article);
    listEl.appendChild(card);
  });
  loadCommentCounts();
}

async function loadCommentCounts() {
  for (const article of articles) {
    try {
      const res = await fetch(`/api/comment.php?article_id=${encodeURIComponent(article.article_id)}&count=1`);
      const data = await res.json();
      const el = document.getElementById('cnt-' + article.article_id);
      if (el) el.textContent = data.count || 0;
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
  const catClass = article.category ? 'cat-' + article.category : '';
  panel.innerHTML = `
    <div class="article-detail-header">
      <div class="article-detail-meta">
        <span class="cat-badge ${catClass}">${article.category_label || article.category}</span>
        <span>${escHtml(article.source || '')}</span>
        <span>${formatDate(article.pub_date)}</span>
      </div>
      <h2>${escHtml(article.title)}</h2>
      <a class="original-link" href="${escHtml(article.url)}" target="_blank" rel="noopener">원문 보기 →</a>
    </div>
    <div class="article-summary">${escHtml(article.summary || '')}</div>
  `;
}

async function loadComments(articleId) {
  const listEl = document.getElementById('comment-list');
  if (!listEl) return;
  listEl.innerHTML = '<div class="loading">댓글 불러오는 중...</div>';
  try {
    const res = await fetch(`/api/comment.php?article_id=${encodeURIComponent(articleId)}`);
    const data = await res.json();
    const comments = data.comments || [];
    if (comments.length === 0) {
      listEl.innerHTML = '<div class="empty-state">첫 댓글을 남겨보세요!</div>';
    } else {
      listEl.innerHTML = comments.map(c => `
        <div class="comment-item">
          <div class="comment-item-meta">
            <span class="comment-nick">${escHtml(c.nickname)}</span>
            <span class="comment-time">${formatDate(c.created_at)}</span>
          </div>
          <div class="comment-content">${escHtml(c.content)}</div>
        </div>
      `).join('');
    }
  } catch (e) {
    listEl.innerHTML = '<div class="empty-state">댓글을 불러올 수 없습니다.</div>';
  }
}

async function submitComment(e) {
  e.preventDefault();
  if (!currentArticle) return;
  const form = e.target;
  const nickname = form.nickname.value.trim() || '익명';
  const content = form.content.value.trim();
  if (!content) return;

  const btn = form.querySelector('.comment-submit-btn');
  btn.disabled = true;
  btn.textContent = '등록 중...';

  try {
    const res = await fetch('/api/comment.php', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ article_id: currentArticle.article_id, nickname, content })
    });
    const data = await res.json();
    if (data.success) {
      form.content.value = '';
      loadComments(currentArticle.article_id);
    } else {
      alert(data.message || '댓글 등록에 실패했습니다.');
    }
  } catch (e) {
    alert('댓글 등록에 실패했습니다.');
  }
  btn.disabled = false;
  btn.textContent = '댓글 등록';
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
