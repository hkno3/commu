<?php
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/includes/rss_helper.php';

// 인기 기사 (DB 댓글 수 기준 Top 5)
$popular = [];
try {
    require_once __DIR__ . '/db/init.php';
    $pdo = db_connect();
    $stmt = $pdo->query(
        "SELECT article_id, COUNT(*) AS cnt FROM comments
         GROUP BY article_id ORDER BY cnt DESC LIMIT 5"
    );
    $top_ids = $stmt->fetchAll(PDO::FETCH_ASSOC);
    if ($top_ids) {
        $latest_path = DATA_DIR . '/latest.json';
        $all = file_exists($latest_path) ? (json_decode(file_get_contents($latest_path), true) ?: []) : [];
        $id_map = array_column($all, null, 'article_id');
        foreach ($top_ids as $row) {
            $a = $id_map[$row['article_id']] ?? null;
            if ($a) {
                $a['comment_count'] = (int)$row['cnt'];
                $popular[] = $a;
            }
        }
    }
} catch (Exception $e) {}

$CAT_SLUG_MAP = [
    'politics'    => '정치',    'economy'  => '경제',
    'society'     => '사회',    'lifestyle'=> '생활_문화',
    'tech'        => 'IT_과학', 'animal'   => '천천히_늙자',
    'travelguide' => '여행지',
];
$cat_param   = $_GET['cat'] ?? '';
$initial_cat = $CAT_SLUG_MAP[$cat_param] ?? ($cat_param ?: 'all');
$is_home     = ($initial_cat === 'all');

$__b = get_banners();
?>
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title><?= SITE_NAME ?> - 뉴스 &amp; 여행지 가이드</title>
  <meta name="description" content="<?= SITE_DESC ?>">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700;800&family=Noto+Serif+KR:wght@600;700&display=swap" rel="stylesheet">
  <link rel="icon" type="image/png" href="/assets/images/favicon.png">
  <link rel="apple-touch-icon" href="/assets/images/favicon.png">
  <link rel="stylesheet" href="/assets/css/style.css?v=<?= @filemtime(__DIR__ . '/assets/css/style.css') ?: time() ?>">
  <?php require_once __DIR__ . '/includes/head_codes.php'; ?>
</head>
<body>

<!-- ── 헤더 ── -->
<header>
  <div class="header-inner">
    <h1 class="site-logo">
      <a class="logo" href="/">
        <img src="/assets/images/favicon.png" alt="로고">
        <?= SITE_NAME ?>
      </a>
    </h1>
  </div>
</header>

<!-- ── 카테고리 탭 네비 ── -->
<nav class="cat-nav" id="cat-nav">
  <div class="cat-nav-inner" id="cat-nav-inner"></div>
</nav>

<!-- ── 배너 상단 ── -->
<?php if (!empty($__b['list_top'])): ?>
<div style="background:#fff; border-bottom:1px solid #ebebeb; text-align:center; padding:8px 0; overflow:hidden;">
  <div class="banner-wrap" style="display:inline-block; max-width:100%;">
    <?= banner_html($__b['list_top']) ?>
  </div>
</div>
<?php endif; ?>

<?php if ($is_home): ?>
<!-- ══════════════════════════════════════════
     홈: 카테고리별 가로 스크롤 섹션
════════════════════════════════════════════ -->
<main class="cat-sections" id="cat-sections">
  <!-- JS가 렌더링 -->
  <div class="loading" style="text-align:center; padding:60px 20px; color:#aaa;">콘텐츠 불러오는 중...</div>
</main>

<?php else: ?>
<!-- ══════════════════════════════════════════
     카테고리 필터 뷰
════════════════════════════════════════════ -->
<main class="filtered-wrap">
  <?php if (!empty($__b['list_top'])): ?>
  <div class="banner-wrap"><?= banner_html($__b['list_top']) ?></div>
  <?php endif; ?>
  <div class="article-list" id="article-list">
    <div class="loading">기사 불러오는 중...</div>
  </div>
  <div id="pagination" class="pagination"></div>
</main>
<?php endif; ?>

<!-- ── 푸터 ── -->
<footer class="site-footer">
  <div class="footer-inner">
    <div class="footer-links">
      <a href="/pages/about.php">매체소개</a>
      <a href="/pages/privacy.php">개인정보처리방침</a>
      <a href="/pages/terms.php">이용약관</a>
      <a href="/pages/youth.php">청소년보호정책</a>
      <a href="/pages/noemail.php">이메일무단수집거부</a>
    </div>
    <div class="footer-info">운영자 : 표경덕 &nbsp;|&nbsp; 문의 : across1211@naver.com</div>
    <div class="footer-copy">Copyright © 2026 newscommu.com. All rights reserved.</div>
  </div>
</footer>

<script>
const INITIAL_CATEGORY = <?= json_encode($initial_cat) ?>;
const IS_HOME = <?= $is_home ? 'true' : 'false' ?>;
const BANNER_LIST_MIDS = <?= json_encode([
    5  => $__b['list_mid1'] ?? '',
    10 => $__b['list_mid2'] ?? '',
    15 => $__b['list_mid3'] ?? '',
    20 => $__b['list_mid4'] ?? '',
]) ?>;
</script>
<?php include __DIR__ . '/includes/banner_scale.php'; ?>
<script src="/assets/js/main.js?v=<?= @filemtime(__DIR__ . '/assets/js/main.js') ?: time() ?>"></script>
<?php include __DIR__ . '/includes/body_codes.php'; ?>
</body>
</html>
