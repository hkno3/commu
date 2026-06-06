<?php
require_once __DIR__ . '/config.php';

require_once __DIR__ . '/includes/rss_helper.php';

$rss_body    = fetch_rss('https://bodyandwell.com/feed/', 'body');
$rss_biz     = fetch_rss('https://bizachieve.com/feed/', 'biz');

// slug 또는 id로 조회
$lookup_slug = preg_replace('/[^a-z0-9-]/', '', strtolower(trim($_GET['slug'] ?? '')));
$article_id  = preg_replace('/[^a-f0-9]/i', '', trim($_GET['id'] ?? ''));

if ($lookup_slug === '' && $article_id === '') {
    header('Location: /');
    exit;
}

// -----------------------------------------------------------------
// Try to load article from JSON data files
// -----------------------------------------------------------------
$article = null;

function match_article(array $a, string $slug, string $id): bool {
    if ($slug !== '' && ($a['slug'] ?? '') === $slug) return true;
    if ($id   !== '' && ($a['article_id'] ?? '') === $id)   return true;
    return false;
}

// Check latest.json first (fastest)
$latest_path = DATA_DIR . '/latest.json';
if (file_exists($latest_path)) {
    $all = json_decode(file_get_contents($latest_path), true) ?: [];
    foreach ($all as $a) {
        if (match_article($a, $lookup_slug, $article_id)) {
            $article = $a;
            break;
        }
    }
}

// If not found, search all category files
if (!$article) {
    $files = glob(DATA_DIR . '/*.json');
    foreach ($files as $file) {
        if (basename($file) === 'latest.json') continue;
        $items = json_decode(file_get_contents($file), true) ?: [];
        foreach ($items as $a) {
            if (match_article($a, $lookup_slug, $article_id)) {
                $article = $a;
                break 2;
            }
        }
    }
}

// article_id 보정 (slug로 찾은 경우)
if ($article) $article_id = $article['article_id'] ?? $article_id;

// If still not found, try article_cache table
if (!$article) {
    try {
        require_once __DIR__ . '/db/init.php';
        $pdo = db_connect();
        $stmt = $pdo->prepare(
            "SELECT article_id, title, summary, url, source, category, pub_date
             FROM article_cache WHERE article_id = ? LIMIT 1"
        );
        $stmt->execute([$article_id]);
        $row = $stmt->fetch();
        if ($row) {
            $article = [
                'article_id'   => $row['article_id'],
                'title'        => $row['title'],
                'summary'      => $row['summary'],
                'original_url' => $row['url'],
                'source'       => $row['source'],
                'category'     => $row['category'],
                'pubDate'      => $row['pub_date'],
            ];
        }
    } catch (Exception $e) {
        // DB unavailable
    }
}

if (!$article) {
    header('HTTP/1.0 404 Not Found');
    ?><!DOCTYPE html>
    <html lang="ko"><head><meta charset="UTF-8"><title>기사를 찾을 수 없습니다 - <?= htmlspecialchars(SITE_NAME) ?></title><link rel="icon" type="image/png" href="/assets/images/favicon.png"></head>
    <body style="font-family:sans-serif; text-align:center; padding:80px 20px;">
    <h1>404</h1><p>기사를 찾을 수 없습니다.</p><a href="/">홈으로 돌아가기</a>
    </body></html>
    <?php
    exit;
}

// -----------------------------------------------------------------
// Category metadata
// -----------------------------------------------------------------
$CATEGORY_META = [
    '정치'     => ['color' => '#c0392b', 'bg' => '#fff0f0'],
    '경제'     => ['color' => '#27ae60', 'bg' => '#f0fff4'],
    '사회'     => ['color' => '#2980b9', 'bg' => '#f0f4ff'],
    '생활_문화'=> ['color' => '#e67e22', 'bg' => '#fff8f0'],
    '세계'     => ['color' => '#8e44ad', 'bg' => '#f5f0ff'],
    'IT_과학'  => ['color' => '#16a085', 'bg' => '#f0fffe'],
    '부동산'   => ['color' => '#d35400', 'bg' => '#fffbf0'],
    '헬스_건강'=> ['color' => '#1abc9c', 'bg' => '#f0fff8'],
    '스포츠'   => ['color' => '#2471a3', 'bg' => '#f0f8ff'],
    '연예'     => ['color' => '#c0392b', 'bg' => '#fff0fb'],
];

$cat_raw  = $article['category'] ?? '';
$cat_key  = str_replace('/', '_', $cat_raw);
$cat_meta = $CATEGORY_META[$cat_key] ?? ['color' => '#1a73e8', 'bg' => '#e8f0fe'];

// Normalise fields
$title       = htmlspecialchars($article['title'] ?? '', ENT_QUOTES, 'UTF-8');
$summary     = htmlspecialchars($article['summary'] ?? '', ENT_QUOTES, 'UTF-8');
// content: HTML with h2/h3/p tags. Fall back to summary if not present.
$raw_content = $article['content'] ?? '';
if ($raw_content) {
    $content_html = strip_tags($raw_content, '<h2><h3><p><br><strong><em><details><summary><table><thead><tbody><tr><th><td>');
} else {
    $content_html = '<p>' . nl2br($summary) . '</p>';
}
$orig_url    = $article['original_url'] ?? $article['url'] ?? '#';
$source      = htmlspecialchars($article['source'] ?? '', ENT_QUOTES, 'UTF-8');
$pub_date_raw = $article['pubDate'] ?? $article['pub_date'] ?? '';

try {
    $dt       = new DateTime($pub_date_raw);
    $pub_date = $dt->format('Y년 n월 j일 H:i');
} catch (Exception $e) {
    $pub_date = $pub_date_raw;
}

$article_slug = $article['slug'] ?? '';
$is_hex_slug  = $article_slug && preg_match('/^[0-9a-f]{8,}$/i', $article_slug);
$og_url = ($article_slug && !$is_hex_slug)
    ? SITE_URL . '/article.php?slug=' . urlencode($article_slug)
    : SITE_URL . '/article.php?id=' . urlencode($article_id);
?>
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title><?= $title ?> - <?= htmlspecialchars(SITE_NAME) ?></title>
  <meta name="description" content="<?= mb_substr(strip_tags($summary), 0, 160) ?>">
  <?php
    $kw_title = $article['original_title'] ?? $article['title'] ?? '';
    $kw_words = preg_split('/[\s,·\-\[\]「」『』【】〔〕\/…]+/u', $kw_title, -1, PREG_SPLIT_NO_EMPTY);
    $kw_words = array_values(array_unique(array_filter($kw_words, fn($w) => mb_strlen($w) >= 2)));
    $kw_words = array_slice($kw_words, 0, 6);
    array_unshift($kw_words, $article['category_label'] ?? '');
    $kw_words[] = 'newscommu';
    $keywords = implode(', ', array_filter($kw_words));
  ?>
  <meta name="keywords" content="<?= htmlspecialchars($keywords) ?>">

  <!-- Open Graph -->
  <meta property="og:title"       content="<?= $title ?>">
  <meta property="og:description" content="<?= mb_substr(strip_tags($summary), 0, 200) ?>">
  <meta property="og:url"         content="<?= htmlspecialchars($og_url) ?>">
  <meta property="og:type"        content="article">
  <meta property="og:site_name"   content="<?= htmlspecialchars(SITE_NAME) ?>">
  <link rel="canonical" href="<?= htmlspecialchars($og_url) ?>">

  <!-- Author / Publisher -->
  <meta name="author" content="pyo1211">
  <link rel="publisher" href="https://newscommu.com">

  <!-- JSON-LD Structured Data -->
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    "headline": <?= json_encode($article['title'] ?? '') ?>,
    "description": <?= json_encode(mb_substr(strip_tags($article['summary'] ?? ''), 0, 160)) ?>,
    "url": <?= json_encode($og_url) ?>,
    "datePublished": <?= json_encode(($article['pubDate'] ?? $article['pub_date'] ?? '')) ?>,
    "author": {
      "@type": "Person",
      "name": "pyo1211"
    },
    "publisher": {
      "@type": "Organization",
      "name": "newscommu.com",
      "url": "https://newscommu.com",
      "logo": {
        "@type": "ImageObject",
        "url": "https://newscommu.com/assets/images/favicon.png"
      }
    }
  }
  </script>

  <!-- Twitter Card -->
  <meta name="twitter:card"  content="summary">
  <meta name="twitter:title" content="<?= $title ?>">

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700&display=swap" rel="stylesheet">
  <link rel="icon" type="image/png" href="/assets/images/favicon.png">
  <link rel="apple-touch-icon" href="/assets/images/favicon.png">
  <link rel="stylesheet" href="/assets/css/style.css">
  <?php require_once __DIR__ . '/includes/head_codes.php'; ?>

  <!-- Kakao SDK -->
  <script src="https://t1.kakaocdn.net/kakao_js_sdk/2.7.2/kakao.min.js" crossorigin="anonymous"></script>

  <!-- AdSense -->
  <!-- <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=<?= ADSENSE_PUBLISHER_ID ?>" crossorigin="anonymous"></script> -->
</head>
<body>

<header>
  <div class="header-inner">
    <a class="logo" href="/"><img src="/assets/images/favicon.png" alt="로고" style="width:28px;height:28px;vertical-align:middle;margin-right:6px;border-radius:6px;"> <?= htmlspecialchars(SITE_NAME) ?></a>
    <a href="/" style="margin-left:auto; font-size:13px; color:var(--text-muted);">← 전체 뉴스</a>
  </div>
</header>

<nav class="cat-nav">
  <div class="cat-nav-inner" id="cat-nav-inner"></div>
</nav>

<div class="main-wrap">
  <!-- AdSense Banner Top -->
  <!-- <ins class="adsbygoogle" style="display:block" data-ad-client="<?= ADSENSE_PUBLISHER_ID ?>" data-ad-slot="XXXXXXXXXX" data-ad-format="auto"></ins> -->

  <div class="shorts-container">
    <!-- 왼쪽: 기사 상세 -->
    <div class="article-panel">
      <div id="article-detail">
        <div class="article-detail-header">
          <div class="article-detail-meta">
            <span class="cat-badge cat-<?= htmlspecialchars($cat_key) ?>"
                  style="background:<?= htmlspecialchars($cat_meta['bg']) ?>; color:<?= htmlspecialchars($cat_meta['color']) ?>;">
              <?= htmlspecialchars($cat_raw) ?>
            </span>
            <?php if ($pub_date): ?>
              <span><?= htmlspecialchars($pub_date) ?></span>
            <?php endif; ?>
          </div>
          <h1><?= $title ?></h1>
        </div>

        <?php if (!empty($article['image_url'])): ?>
        <div class="article-thumb">
          <img src="<?= htmlspecialchars($article['image_url'], ENT_QUOTES, 'UTF-8') ?>"
               alt="<?= $title ?>"
               style="width:100%; border-radius:10px; margin-bottom:20px; max-height:400px; object-fit:cover;">
        </div>
        <?php endif; ?>

        <div class="article-body">
          <?= $content_html ?>
        </div>

        <!-- Share buttons -->
        <div style="display:flex; gap:8px; margin-top:16px; flex-wrap:wrap;">
          <button onclick="shareKakao()"
            style="padding:7px 14px; border:none; border-radius:6px; background:#FEE500; font-size:12px; cursor:pointer; color:#000; font-weight:600;">
            💬 카카오톡
          </button>
          <a href="https://www.threads.net/intent/post?text=<?= urlencode(html_entity_decode($title) . ' ' . $og_url) ?>"
             target="_blank" rel="noopener"
             style="padding:7px 14px; border:none; border-radius:6px; background:#000; font-size:12px; color:#fff; text-decoration:none; font-weight:600;">
            🧵 스레드
          </a>
          <a href="https://www.facebook.com/sharer/sharer.php?u=<?= urlencode($og_url) ?>"
             target="_blank" rel="noopener"
             style="padding:7px 14px; border:none; border-radius:6px; background:#1877F2; font-size:12px; color:#fff; text-decoration:none; font-weight:600;">
            f 페이스북
          </a>
          <a href="https://twitter.com/intent/tweet?url=<?= urlencode($og_url) ?>&text=<?= urlencode(html_entity_decode($title)) ?>"
             target="_blank" rel="noopener"
             style="padding:7px 14px; border:none; border-radius:6px; background:#000; font-size:12px; color:#fff; text-decoration:none; font-weight:600;">
            𝕏 트위터
          </a>
          <button onclick="copyLink()"
            style="padding:7px 14px; border:1px solid var(--border); border-radius:6px; background:#fff; font-size:12px; cursor:pointer;">
            🔗 링크 복사
          </button>
        </div>

        <script>
          Kakao.init('35a152dc3d0307c3f0422c801712153d');
          function shareKakao() {
            Kakao.Share.sendScrap({
              requestUrl: <?= json_encode($og_url) ?>,
              templateId: undefined
            });
          }
        </script>

        <!-- AdSense Rectangle -->
        <!-- <ins class="adsbygoogle" style="display:block; margin:20px 0;" data-ad-client="<?= ADSENSE_PUBLISHER_ID ?>" data-ad-slot="XXXXXXXXXX" data-ad-format="rectangle"></ins> -->

        <!-- Related / Back navigation -->
        <div style="margin-top:32px; padding-top:20px; border-top:1px solid var(--border);">
          <a href="javascript:history.back()" style="font-size:13px; color:var(--text-muted);">← 이전 페이지</a>
          &nbsp;&nbsp;
          <a href="/?cat=<?= urlencode($cat_raw) ?>" style="font-size:13px; color:var(--primary);">
            <?= htmlspecialchars($cat_raw) ?> 뉴스 더 보기 →
          </a>
        </div>
      </div>
    </div>

    <!-- 오른쪽: 사이드 패널 -->
    <div class="comment-panel">

      <!-- 추천 글 -->
      <?php if ($rss_body || $rss_biz): ?>
      <div class="rss-panel">
        <?php if ($rss_body): ?>
        <div class="rss-section">
          <div class="rss-site-label">
            <a href="https://bodyandwell.com" target="_blank" rel="noopener">💪 bodyandwell.com</a>
          </div>
          <ul class="rss-list">
            <?php foreach ($rss_body as $item): ?>
            <li><a href="<?= htmlspecialchars($item['link']) ?>" target="_blank" rel="noopener">
              <?= htmlspecialchars($item['title']) ?>
            </a></li>
            <?php endforeach; ?>
          </ul>
        </div>
        <?php endif; ?>
        <?php if ($rss_biz): ?>
        <div class="rss-section">
          <div class="rss-site-label">
            <a href="https://bizachieve.com" target="_blank" rel="noopener">💼 bizachieve.com</a>
          </div>
          <ul class="rss-list">
            <?php foreach ($rss_biz as $item): ?>
            <li><a href="<?= htmlspecialchars($item['link']) ?>" target="_blank" rel="noopener">
              <?= htmlspecialchars($item['title']) ?>
            </a></li>
            <?php endforeach; ?>
          </ul>
        </div>
        <?php endif; ?>
      </div>
      <?php endif; ?>

      <!-- 댓글 -->
      <div class="comment-panel-header">
        💬 댓글
        <span id="comment-count-badge" style="font-size:12px; color:var(--text-muted); font-weight:400; margin-left:6px;"></span>
      </div>
      <div class="comment-list" id="comment-list">
        <div class="loading">댓글 불러오는 중...</div>
      </div>
      <div id="load-more-comments" style="display:none; text-align:center; padding:8px;">
        <button onclick="loadMoreComments()"
                style="padding:6px 20px; border:1px solid var(--border); border-radius:20px; background:#fff; cursor:pointer; font-size:12px;">
          댓글 더 보기
        </button>
      </div>
      <div class="comment-form">
        <form onsubmit="submitComment(event)" id="comment-form">
          <input type="text" name="nickname" placeholder="닉네임 (선택, 기본: 익명)" maxlength="20">
          <textarea name="content" placeholder="댓글을 입력하세요..." rows="3" maxlength="500" required></textarea>
          <div id="comment-error" style="color:#e74c3c; font-size:12px; margin-bottom:6px; display:none;"></div>
          <button type="submit" class="comment-submit-btn" id="comment-btn">댓글 등록</button>
        </form>
      </div>
    </div>
  </div>
</div>

<script>
  // Article context for JS
  const ARTICLE_ID = <?= json_encode($article_id) ?>;
  const INITIAL_CATEGORY = <?= json_encode($cat_key) ?>;

  function copyLink() {
    const url = window.location.href;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(url).then(() => showToast('링크가 복사되었습니다.'));
    } else {
      const el = document.createElement('textarea');
      el.value = url;
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      showToast('링크가 복사되었습니다.');
    }
  }

  function showToast(msg) {
    let t = document.getElementById('toast');
    if (!t) {
      t = document.createElement('div');
      t.id = 'toast';
      t.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#333;color:#fff;padding:8px 20px;border-radius:20px;font-size:13px;z-index:9999;';
      document.body.appendChild(t);
    }
    t.textContent = msg;
    t.style.opacity = 1;
    setTimeout(() => { t.style.opacity = 0; }, 2500);
  }
</script>
<script src="/assets/js/main.js"></script>
<script>
  // Auto-load comments on article page
  document.addEventListener('DOMContentLoaded', () => {
    if (typeof loadComments === 'function' && ARTICLE_ID) {
      loadComments(ARTICLE_ID);
    }
    if (typeof buildCategoryNav === 'function') {
      buildCategoryNav();
    }
  });
</script>
</body>
</html>
