<?php
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/includes/rss_helper.php';

$rss_body = fetch_rss('https://bodyandwell.com/feed/', 'body');
$rss_biz  = fetch_rss('https://bizachieve.com/feed/', 'biz');

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
    'politics' => '정치', 'economy' => '경제', 'society' => '사회',
    'lifestyle' => '생활_문화', 'tech' => 'IT_과학', 'animal' => '천천히_늘자',
];
$cat_param = $_GET['cat'] ?? '';
$initial_cat = $CAT_SLUG_MAP[$cat_param] ?? ($cat_param ?: 'all');

$hero_image_file = DATA_DIR . '/hero_image.txt';
$hero_image_url  = file_exists($hero_image_file) ? trim(file_get_contents($hero_image_file)) : '';
$default_hero    = 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1600&q=80';
$hero_bg_url     = $hero_image_url ?: $default_hero;
?>
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title><?= SITE_NAME ?> - 실시간 뉴스 커뮤니티</title>
  <meta name="description" content="<?= SITE_DESC ?>">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700&family=Noto+Serif+KR:wght@600;700&display=swap" rel="stylesheet">
  <link rel="icon" type="image/png" href="/assets/images/favicon.png">
  <link rel="apple-touch-icon" href="/assets/images/favicon.png">
  <link rel="stylesheet" href="/assets/css/style.css?v=<?= @filemtime(__DIR__ . '/assets/css/style.css') ?: time() ?>">
  <?php require_once __DIR__ . '/includes/head_codes.php'; ?>
</head>
<body>

<header>
  <div class="header-inner">
    <h1 style="margin:0; font-size:20px; font-weight:700; display:inline;"><a class="logo" href="/"><img src="/assets/images/favicon.png" alt="로고" style="width:28px;height:28px;vertical-align:middle;margin-right:6px;border-radius:6px;"> <?= SITE_NAME ?></a></h1>
  </div>
</header>

<nav class="cat-nav">
  <div class="cat-nav-inner" id="cat-nav-inner"></div>
</nav>

<section class="hero-section" style="background-image: linear-gradient(rgba(20,18,16,0.78), rgba(20,18,16,0.88)), url('<?= htmlspecialchars($hero_bg_url) ?>');">
  <div class="hero-inner">
    <p class="hero-eyebrow">실시간 뉴스 커뮤니티</p>
    <h2 class="hero-title">한국 주요 뉴스를<br>한눈에</h2>
    <p class="hero-desc">정치·경제·사회·문화·IT까지, 핵심만 추린 최신 뉴스와<br>실시간 댓글 토론을 한 곳에서 만나보세요.</p>
    <a href="#news-list" class="hero-cta">뉴스 바로보기 ↓</a>
  </div>
</section>

<section class="features-section">
  <div class="features-inner">
    <div class="feature-item">
      <div class="feature-icon">📝</div>
      <h3 class="feature-title">핵심 요약</h3>
      <p class="feature-desc">긴 기사도 핵심만 골라 짧게 정리해드립니다. 바쁜 일상에서 뉴스를 빠르게.</p>
    </div>
    <div class="feature-item">
      <div class="feature-icon">💬</div>
      <h3 class="feature-title">실시간 댓글 토론</h3>
      <p class="feature-desc">기사마다 독자들의 생생한 의견을 남기고 토론에 참여하세요.</p>
    </div>
    <div class="feature-item">
      <div class="feature-icon">📂</div>
      <h3 class="feature-title">6개 카테고리</h3>
      <p class="feature-desc">정치·경제·사회·문화·IT·건강까지, 관심 분야만 골라서 확인하세요.</p>
    </div>
  </div>
</section>

<div class="main-wrap" id="news-list">
  <div class="main-index-layout">

    <!-- 왼쪽: 기사 목록 -->
    <div class="index-article-col">
      <?php if (!empty($__b['list_top'])): ?>
      <div class="banner-wrap"><?= banner_html($__b['list_top']) ?></div>
      <?php endif; ?>
      <div class="article-list" id="article-list">
        <div class="loading">기사 불러오는 중...</div>
      </div>
      <div id="pagination" class="pagination"></div>
    </div>

    <!-- 오른쪽: 사이드바 -->
    <aside class="index-sidebar">

      <!-- RSS 피드 -->
      <?php if ($rss_body || $rss_biz): ?>
      <div class="sidebar-box">
        <div class="sidebar-box-title">🔗 추천 사이트</div>
        <?php if ($rss_body): ?>
        <div class="rss-section">
          <div class="rss-site-label">
            <a href="https://bodyandwell.com" target="_blank" rel="noopener">💪 bodyandwell.com</a>
          </div>
          <ul class="rss-list">
            <?php foreach ($rss_body as $item): ?>
            <li><a href="<?= htmlspecialchars($item['link']) ?>" title="<?= htmlspecialchars($item['title']) ?>" target="_blank" rel="noopener">
              <?= htmlspecialchars($item['title']) ?>
            </a></li>
            <?php endforeach; ?>
          </ul>
        </div>
        <?php endif; ?>
        <?php if ($rss_biz): ?>
        <div class="rss-section" style="margin-top:12px;">
          <div class="rss-site-label">
            <a href="https://bizachieve.com" target="_blank" rel="noopener">💼 bizachieve.com</a>
          </div>
          <ul class="rss-list">
            <?php foreach ($rss_biz as $item): ?>
            <li><a href="<?= htmlspecialchars($item['link']) ?>" title="<?= htmlspecialchars($item['title']) ?>" target="_blank" rel="noopener">
              <?= htmlspecialchars($item['title']) ?>
            </a></li>
            <?php endforeach; ?>
          </ul>
        </div>
        <?php endif; ?>
      </div>
      <?php endif; ?>

      <!-- 인기 기사 -->
      <?php if ($popular): ?>
      <div class="sidebar-box">
        <div class="sidebar-box-title">🔥 인기 기사</div>
        <ul class="popular-list">
          <?php foreach ($popular as $i => $a): ?>
          <li>
            <a href="/article.php?id=<?= urlencode($a['article_id']) ?>">
              <span class="popular-num"><?= $i + 1 ?></span>
              <?= htmlspecialchars($a['title'] ?? '') ?>
            </a>
            <span class="popular-cnt">💬 <?= $a['comment_count'] ?></span>
          </li>
          <?php endforeach; ?>
        </ul>
      </div>
      <?php endif; ?>

      <!-- 배너 광고 300x250 -->
      <?php $__b = get_banners(); if (!empty($__b['sidebar'])): ?>
      <div class="sidebar-box sidebar-ad" style="text-align:center; padding:12px; overflow:hidden;">
        <?= banner_html($__b['sidebar']) ?>
      </div>
      <?php endif; ?>

    </aside>
  </div>
</div>

<?php $__b = get_banners(); ?>
<script>
const INITIAL_CATEGORY = <?= json_encode($initial_cat) ?>;
const BANNER_LIST_MIDS = <?= json_encode([
    5  => $__b['list_mid1'] ?? '',
    10 => $__b['list_mid2'] ?? '',
    15 => $__b['list_mid3'] ?? '',
    20 => $__b['list_mid4'] ?? '',
]) ?>;
</script>
<?php include __DIR__ . '/includes/banner_scale.php'; ?>
<script src="/assets/js/main.js?v=<?= @filemtime(__DIR__ . '/assets/js/main.js') ?: time() ?>"></script>

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
<?php include __DIR__ . '/includes/body_codes.php'; ?>
</body>
</html>
