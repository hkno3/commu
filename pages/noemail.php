<?php $title = '이메일무단수집거부'; ?>
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title><?= $title ?> - newscommu.com</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700&display=swap" rel="stylesheet">
<link rel="icon" type="image/png" href="/assets/images/favicon.png">
<link rel="stylesheet" href="/assets/css/style.css">
  <?php require_once __DIR__ . '/../includes/head_codes.php'; ?>
<style>
.page-wrap { max-width: 860px; margin: 40px auto; padding: 0 20px 60px; }
.page-wrap h1 { font-size: 24px; font-weight: 700; margin-bottom: 30px; padding-bottom: 12px; border-bottom: 2px solid #1a73e8; }
.page-wrap p, .page-wrap li { font-size: 14px; line-height: 1.9; color: #333; }
.notice-box { background: #fff8e1; border-left: 4px solid #f59e0b; padding: 16px 20px; border-radius: 6px; margin: 20px 0; }
.notice-box p { font-weight: 600; color: #92400e; margin: 0; }
</style>
</head>
<body>
<header>
  <div class="header-inner">
    <a class="logo" href="/"><img src="/assets/images/favicon.png" alt="로고" style="width:28px;height:28px;vertical-align:middle;margin-right:6px;border-radius:6px;"> newscommu.com</a>
  </div>
</header>
<div class="page-wrap">
  <h1>이메일무단수집거부</h1>

  <div class="notice-box">
    <p>본 사이트에 게시된 이메일 주소가 전자우편 수집 프로그램이나 그 밖의 기술적 장치를 이용하여 무단으로 수집되는 것을 거부하며, 이를 위반 시 정보통신망법에 의해 형사처벌됨을 유념하시기 바랍니다.</p>
  </div>

  <p>
    정보통신망 이용촉진 및 정보보호 등에 관한 법률 제 50조의 2 (전자우편주소의 무단 수집행위 등 금지)에 의거하여,
    newscommu.com에 게시된 이메일 주소의 무단 수집을 거부합니다.
  </p>

  <p>이를 위반 시 관련 법률에 의거 처벌을 받을 수 있습니다.</p>

  <p style="margin-top:30px; color:#888; font-size:13px;">게시일 : 2026년 6월 5일</p>
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
    <div class="footer-info">운영자 : 표경덕 &nbsp;|&nbsp; 문의 : across1211@naver.com</div>
    <div class="footer-copy">Copyright © 2026 newscommu.com. All rights reserved.</div>
  </div>
</footer>
</body>
</html>
