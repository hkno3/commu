<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>매체소개 - newscommu.com</title>
  <meta name="description" content="newscommu.com 매체소개 페이지입니다.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700&display=swap" rel="stylesheet">
  <link rel="icon" type="image/png" href="/assets/images/favicon.png">
  <link rel="stylesheet" href="/assets/css/style.css">
  <?php require_once __DIR__ . '/../includes/head_codes.php'; ?>
  <style>
    .page-wrap { max-width: 860px; margin: 0 auto; padding: 40px 20px 60px; }
    .page-title { font-size: 26px; font-weight: 700; margin-bottom: 32px; color: var(--text); border-bottom: 2px solid var(--primary); padding-bottom: 14px; }
    .section { background: #fff; border-radius: 12px; padding: 32px; margin-bottom: 24px; box-shadow: 0 1px 4px rgba(0,0,0,0.07); }
    .section h2 { font-size: 18px; font-weight: 700; color: var(--primary); margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
    .section p { font-size: 15px; line-height: 1.9; color: #333; margin-bottom: 12px; }
    .section p:last-child { margin-bottom: 0; }
    .feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-top: 12px; }
    .feature-item { background: #f5f7fa; border-radius: 10px; padding: 20px; }
    .feature-item .icon { font-size: 28px; margin-bottom: 10px; }
    .feature-item h3 { font-size: 15px; font-weight: 700; margin-bottom: 8px; }
    .feature-item p { font-size: 13px; color: var(--text-muted); line-height: 1.7; margin: 0; }
    .info-table { width: 100%; border-collapse: collapse; margin-top: 8px; }
    .info-table th, .info-table td { padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border); font-size: 14px; }
    .info-table th { width: 140px; color: var(--text-muted); font-weight: 600; background: #f8f9fa; }
    .info-table td { color: var(--text); }
  </style>
</head>
<body>

<header>
  <div class="header-inner">
    <a class="logo" href="/"><img src="/assets/images/favicon.png" alt="로고" style="width:28px;height:28px;vertical-align:middle;margin-right:6px;border-radius:6px;"> newscommu.com</a>
  </div>
</header>

<div class="page-wrap">
  <h1 class="page-title">매체소개</h1>

  <div class="section">
    <h2>🗞️ newscommu.com 소개</h2>
    <p>
      <strong>newscommu.com</strong>은 국내외 주요 뉴스와 이슈를 한눈에 확인하고, 누구나 자유롭게 의견을 나눌 수 있는 뉴스 커뮤니티입니다.
    </p>
    <p>
      정치, 경제, 사회, 생활/문화, IT/과학 등 핵심 카테고리의 뉴스를 에디터가 읽기 쉽게 재정리하여 제공하며,
      특별 코너 <strong>천천히 늙자</strong>에서는 국제 학술지 최신 논문을 바탕으로 동물과 인간의 수명·건강수명 연구를 따뜻한 시각으로 소개합니다.
      복잡한 가입 절차 없이 이슈를 살펴보고 생각을 나눌 수 있는 열린 공간을 지향합니다.
    </p>
  </div>

  <div class="section">
    <h2>✨ 주요 기능</h2>
    <div class="feature-grid">
      <div class="feature-item">
        <div class="icon">🗂️</div>
        <h3>5대 카테고리 뉴스</h3>
        <p>정치, 경제, 사회, 생활/문화, IT/과학 분야의 최신 뉴스를 에디터가 핵심만 뽑아 읽기 쉽게 정리해 제공합니다.</p>
      </div>
      <div class="feature-item">
        <div class="icon">🐾</div>
        <h3>천천히 늙자</h3>
        <p>국제 학술지 최신 논문을 한국어로 풀어써 동물 수명·노화 연구를 누구나 쉽게 이해할 수 있도록 소개합니다.</p>
      </div>
      <div class="feature-item">
        <div class="icon">🔬</div>
        <h3>주간 연구 기획서</h3>
        <p>매주 월요일, 한 주간 쌓인 논문들을 종합 분석해 실현 가능한 연구 아이디어를 제안합니다.</p>
      </div>
      <div class="feature-item">
        <div class="icon">💬</div>
        <h3>익명 자유 토론</h3>
        <p>회원가입 없이 누구나 익명으로 댓글을 남길 수 있습니다. 닉네임 미입력 시 '익명'으로 표시됩니다.</p>
      </div>
    </div>
  </div>

  <div class="section">
    <h2>📋 서비스 운영 목적</h2>
    <p>
      newscommu.com은 바쁜 일상 속에서도 중요한 뉴스를 빠르게 파악하고, 사회 현안에 대해 자유롭게 의견을 교환할 수 있는 공간을 제공하기 위해 운영됩니다.
    </p>
    <p>
      특정 정치 성향이나 이념을 지지하지 않으며, 다양한 주제를 균형 있게 다루고 건전한 토론 문화를 만들어 가는 것을 목표로 합니다.
      특히 <strong>천천히 늙자</strong> 코너를 통해 반려동물과 함께 더 오래, 더 건강하게 살아가는 방법을 최신 연구와 함께 탐구합니다.
    </p>
  </div>

  <div class="section">
    <h2>📌 운영 정보</h2>
    <table class="info-table">
      <tr><th>사이트명</th><td>newscommu.com</td></tr>
      <tr><th>운영자</th><td>표경덕</td></tr>
      <tr><th>문의 이메일</th><td>across1211@naver.com</td></tr>
      <tr><th>서비스 유형</th><td>뉴스 큐레이션 및 토론 커뮤니티</td></tr>
      <tr><th>개설일</th><td>2026년</td></tr>
    </table>
  </div>
</div>

<footer class="site-footer">
  <div class="footer-inner">
    <div class="footer-links">
      <a href="/pages/about.php">매체소개</a>
      <a href="/pages/privacy.php">개인정보처리방침</a>
      <a href="/pages/terms.php">이용약관</a>
      <a href="/pages/youth.php">청소년보호정책</a>
      <a href="/pages/noemail.php">이메일무단수집거부</a>
    </div>
    <div class="footer-info">
      운영자 : 표경덕 &nbsp;|&nbsp; 문의 : across1211@naver.com
    </div>
    <div class="footer-copy">
      Copyright &copy; 2026 newscommu.com. All rights reserved.
    </div>
  </div>
</footer>

<?php include __DIR__ . '/../includes/body_codes.php'; ?>
</body>
</html>
