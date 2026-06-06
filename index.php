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
    'lifestyle' => '생활_문화', 'world' => '세계', 'tech' => 'IT_과학',
    'realestate' => '부동산', 'health' => '헬스_건강', 'sports' => '스포츠',
    'entertainment' => '연예', 'auto' => '자동차', 'weather' => '날씨',
    'crypto' => '가상화폐', 'stock' => '주식', 'parenting' => '육아',
    'travel' => '여행', 'game' => '게임', 'fashion' => '패션_뷰티',
    'food' => '음식_맛집', 'education' => '교육', 'environment' => '환경',
    'law' => '법률', 'jobs' => '취업_직장', 'pets' => '반려동물', 'movies' => '영화',
];
$cat_param = $_GET['cat'] ?? '';
$initial_cat = $CAT_SLUG_MAP[$cat_param] ?? ($cat_param ?: 'all');
?>
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title><?= SITE_NAME ?> - 실시간 뉴스 커뮤니티</title>
  <meta name="description" content="<?= SITE_DESC ?>">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700&display=swap" rel="stylesheet">
  <link rel="icon" type="image/png" href="/assets/images/favicon.png">
  <link rel="apple-touch-icon" href="/assets/images/favicon.png">
  <link rel="stylesheet" href="/assets/css/style.css">
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

<div class="main-wrap">
  <div class="main-index-layout">

    <!-- 왼쪽: 기사 목록 -->
    <div class="index-article-col">
      <div class="article-list" id="article-list">
        <div class="loading">기사 불러오는 중...</div>
      </div>
      <div id="scroll-sentinel" style="height:20px;"></div>
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

      <!-- 광고 자리 -->
      <div class="sidebar-box sidebar-ad">
        <div class="sidebar-box-title">광고</div>
        <div style="min-height:250px; display:flex; align-items:center; justify-content:center; color:#bbb; font-size:13px;">
          <!-- AdSense 코드 여기에 -->
          광고 영역
        </div>
      </div>

    </aside>
  </div>
</div>

<script>const INITIAL_CATEGORY = <?= json_encode($initial_cat) ?>;</script>
<script src="/assets/js/main.js"></script>

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
</body>
</html>
