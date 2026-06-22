<?php
/**
 * newscommu.com - Category page
 * Shows articles filtered by a specific category.
 */
require_once __DIR__ . '/config.php';

$raw_cat = trim($_GET['cat'] ?? '');

// Allowed categories
$CATEGORIES = [
    '정치'      => ['label' => '정치',     'color' => '#7a2e2e', 'bg' => 'none'],
    '경제'      => ['label' => '경제',     'color' => '#2f5d4f', 'bg' => 'none'],
    '사회'      => ['label' => '사회',     'color' => '#2c4a63', 'bg' => 'none'],
    '생활_문화'  => ['label' => '생활/문화', 'color' => '#8a5a2e', 'bg' => 'none'],
    'IT_과학'    => ['label' => 'IT/과학',   'color' => '#2e6b66', 'bg' => 'none'],
    '천천히_늙자' => ['label' => '천천히 늙자','color' => '#5e3d7a', 'bg' => 'none'],
];

// Normalise incoming param (/ → _)
$cat_key = str_replace('/', '_', $raw_cat);
if ($cat_key !== '' && !isset($CATEGORIES[$cat_key])) {
    header('Location: /');
    exit;
}

$cat_info = $CATEGORIES[$cat_key] ?? null;
$page_title = $cat_info ? $cat_info['label'] . ' 뉴스 - ' . SITE_NAME : SITE_NAME . ' - 실시간 뉴스';
?>
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title><?= htmlspecialchars($page_title) ?></title>
  <meta name="description" content="<?= htmlspecialchars($cat_info ? $cat_info['label'] . ' 분야 최신 뉴스 모음' : SITE_DESC) ?>">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700&family=Noto+Serif+KR:wght@600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/assets/css/style.css?v=<?= @filemtime(__DIR__ . '/assets/css/style.css') ?: time() ?>">
  <!-- AdSense -->
  <!-- <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=<?= ADSENSE_PUBLISHER_ID ?>" crossorigin="anonymous"></script> -->
</head>
<body>

<header>
  <div class="header-inner">
    <a class="logo" href="/">📰 <?= htmlspecialchars(SITE_NAME) ?></a>
    <div style="margin-left:auto; display:flex; gap:10px; align-items:center;">
      <?php if ($cat_info): ?>
        <span class="cat-badge cat-<?= htmlspecialchars($cat_key) ?>" style="font-size:14px; padding:4px 12px;">
          <?= htmlspecialchars($cat_info['label']) ?>
        </span>
      <?php endif; ?>
      <a href="/" style="font-size:13px; color:var(--text-muted);">← 전체보기</a>
    </div>
  </div>
</header>

<nav class="cat-nav">
  <div class="cat-nav-inner" id="cat-nav-inner"></div>
</nav>

<div class="main-wrap">
  <div class="shorts-container">
    <!-- 왼쪽: 기사 목록 + 상세 -->
    <div class="article-panel">
      <div id="article-detail">
        <?php if ($cat_info): ?>
          <div style="padding:20px 0 10px;">
            <h1 style="font-size:24px; font-weight:700; color:<?= htmlspecialchars($cat_info['color']) ?>;">
              <?= htmlspecialchars($cat_info['label']) ?> 뉴스
            </h1>
            <p style="font-size:13px; color:var(--text-muted); margin-top:4px;">최신 <?= htmlspecialchars($cat_info['label']) ?> 뉴스를 확인하세요</p>
          </div>
        <?php else: ?>
          <div class="empty-state">기사를 선택하면 내용이 여기에 표시됩니다.</div>
        <?php endif; ?>
      </div>
      <div class="article-list" id="article-list">
        <div class="loading">기사 불러오는 중...</div>
      </div>
      <!-- Infinite scroll sentinel -->
      <div id="pagination" class="pagination"></div>
    </div>
    <!-- 오른쪽: 댓글 -->
    <div class="comment-panel">
      <div class="comment-panel-header">💬 실시간 토론
        <span id="comment-count-badge" style="font-size:12px; color:var(--text-muted); font-weight:400;"></span>
      </div>
      <div class="comment-list" id="comment-list">
        <div class="empty-state">기사를 선택하면 댓글이 표시됩니다.</div>
      </div>
      <div class="comment-form">
        <form onsubmit="submitComment(event)">
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
  // Pass PHP category to JS
  const INITIAL_CATEGORY = <?= json_encode($cat_key !== '' ? $cat_key : 'all') ?>;
  const CAT_LABELS = <?= json_encode(array_map(fn($v) => $v['label'], $CATEGORIES)) ?>;
</script>
<script src="/assets/js/main.js?v=<?= @filemtime(__DIR__ . '/assets/js/main.js') ?: time() ?>"></script>
<script>
  // category.php: auto-load after main.js
  document.addEventListener('DOMContentLoaded', () => {
    buildCategoryNav();
    loadArticles(true);
  });
</script>
<?php include __DIR__ . '/includes/body_codes.php'; ?>
</body>
</html>
