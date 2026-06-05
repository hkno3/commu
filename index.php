<?php
require_once __DIR__ . '/config.php';
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
  <link rel="stylesheet" href="/assets/css/style.css">
  <!-- AdSense -->
  <!-- <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=<?= ADSENSE_PUBLISHER_ID ?>" crossorigin="anonymous"></script> -->
</head>
<body>

<header>
  <div class="header-inner">
    <a class="logo" href="/">📰 <?= SITE_NAME ?></a>
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
        <div class="empty-state">왼쪽에서 기사를 선택하세요.</div>
      </div>
      <div class="article-list" id="article-list">
        <div class="loading">기사 불러오는 중...</div>
      </div>
      <!-- Infinite scroll sentinel -->
      <div id="scroll-sentinel" style="height:20px;"></div>
    </div>

    <!-- 오른쪽: 댓글 -->
    <div class="comment-panel">
      <div class="comment-panel-header">💬 실시간 토론
        <span id="comment-count-badge" style="font-size:12px; color:var(--text-muted); font-weight:400;"></span>
      </div>
      <div class="comment-list" id="comment-list">
        <div class="empty-state">기사를 선택하면 댓글이 표시됩니다.</div>
      </div>
      <div id="load-more-comments" style="display:none; text-align:center; padding:8px;">
        <button onclick="loadMoreComments()" style="padding:6px 20px; border:1px solid var(--border); border-radius:20px; background:#fff; cursor:pointer; font-size:12px;">
          댓글 더 보기
        </button>
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
