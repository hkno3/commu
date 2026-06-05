<?php
session_start();
require_once __DIR__ . '/../config.php';

define('ADMIN_HASH', 'e4a087445903115bf1a5f461a3b123b6ce48dae4e0e8c9f164894cda2b1ce004');
define('ADMIN_EMAIL', 'across1211@naver.com');
define('SMTP_HOST', 'smtp.naver.com');
define('SMTP_PORT', 465);
define('SMTP_USER', 'across1211@naver.com');
define('SMTP_PASS', 'KH9RQE3PXYVJ');

// SMTP 메일 발송 함수
function send_otp_email(string $otp): bool {
    $to      = ADMIN_EMAIL;
    $subject = '[newscommu] 관리자 인증 코드: ' . $otp;
    $message = "관리자 인증 코드입니다.\n\n코드: {$otp}\n\n5분 내에 입력하세요.\n\n본인이 아니라면 즉시 비밀번호를 변경하세요.";
    $headers = "From: newscommu@newscommu.com\r\nContent-Type: text/plain; charset=UTF-8";
    return mail($to, '=?UTF-8?B?' . base64_encode($subject) . '?=', $message, $headers);
}

// ── 1단계: 비밀번호 확인 ──
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['password']) && !isset($_SESSION['admin_pass_ok'])) {
    if (hash('sha256', $_POST['password']) === ADMIN_HASH) {
        $otp = str_pad(random_int(0, 999999), 6, '0', STR_PAD_LEFT);
        $_SESSION['admin_otp'] = $otp;
        $_SESSION['admin_otp_time'] = time();
        $_SESSION['admin_pass_ok'] = true;
        $sent = send_otp_email($otp);
        if (!$sent) {
            unset($_SESSION['admin_pass_ok'], $_SESSION['admin_otp'], $_SESSION['admin_otp_time']);
            $error = '이메일 발송 실패. 잠시 후 다시 시도해주세요.';
        }
    } else {
        $error = '비밀번호가 틀렸습니다.';
    }
}

// ── 2단계: OTP 확인 ──
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['otp']) && isset($_SESSION['admin_pass_ok'])) {
    $otp_input = trim($_POST['otp']);
    $otp_expired = (time() - ($_SESSION['admin_otp_time'] ?? 0)) > 300; // 5분
    if (!$otp_expired && $otp_input === $_SESSION['admin_otp']) {
        $_SESSION['admin_auth'] = true;
        unset($_SESSION['admin_otp'], $_SESSION['admin_otp_time'], $_SESSION['admin_pass_ok']);
        header('Location: /admin_rudwnQkd1/');
        exit;
    } else {
        $otp_error = $otp_expired ? '인증 코드가 만료되었습니다. 다시 로그인해주세요.' : '인증 코드가 틀렸습니다.';
        if ($otp_expired) unset($_SESSION['admin_pass_ok'], $_SESSION['admin_otp'], $_SESSION['admin_otp_time']);
    }
}

// ── 로그아웃 ──
if (isset($_GET['logout'])) {
    session_destroy();
    header('Location: /admin_rudwnQkd1/');
    exit;
}

// ── 기사 삭제 ──
if (isset($_GET['delete']) && ($_SESSION['admin_auth'] ?? false)) {
    $del_id  = preg_replace('/[^a-f0-9]/i', '', $_GET['delete']);
    $del_cat = preg_replace('/[^a-zA-Z_\/가-힣]/', '', $_GET['cat'] ?? '');
    if ($del_id && $del_cat) {
        $path = DATA_DIR . '/' . $del_cat . '.json';
        if (file_exists($path)) {
            $articles = json_decode(file_get_contents($path), true) ?: [];
            $articles = array_values(array_filter($articles, fn($a) => ($a['article_id'] ?? '') !== $del_id));
            file_put_contents($path, json_encode($articles, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
        }
        $latest_path = DATA_DIR . '/latest.json';
        if (file_exists($latest_path)) {
            $latest = json_decode(file_get_contents($latest_path), true) ?: [];
            $latest = array_values(array_filter($latest, fn($a) => ($a['article_id'] ?? '') !== $del_id));
            file_put_contents($latest_path, json_encode($latest, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
        }
        header('Location: /admin_rudwnQkd1/?deleted=1');
        exit;
    }
}

$is_auth = $_SESSION['admin_auth'] ?? false;
$pass_ok = $_SESSION['admin_pass_ok'] ?? false;

$articles = [];
if ($is_auth) {
    $latest_path = DATA_DIR . '/latest.json';
    if (file_exists($latest_path)) {
        $articles = json_decode(file_get_contents($latest_path), true) ?: [];
    }
}
?>
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>관리자 - <?= htmlspecialchars(SITE_NAME) ?></title>
<link rel="icon" type="image/png" href="/assets/images/favicon.png">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Apple SD Gothic Neo', sans-serif; background: #f5f7fa; color: #1a1a1a; font-size: 14px; }
.wrap { max-width: 1000px; margin: 40px auto; padding: 0 20px; }
h1 { font-size: 22px; margin-bottom: 24px; color: #1a73e8; }
.login-box { background: #fff; padding: 40px; border-radius: 12px; max-width: 400px; margin: 100px auto; box-shadow: 0 2px 12px rgba(0,0,0,0.1); }
.login-box h2 { margin-bottom: 8px; font-size: 18px; }
.login-box p { font-size: 13px; color: #888; margin-bottom: 20px; }
.login-box input { width: 100%; padding: 10px 14px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; margin-bottom: 12px; }
.login-box button { width: 100%; padding: 12px; background: #1a73e8; color: #fff; border: none; border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; }
.login-box button:hover { background: #1557b0; }
.error { color: #e74c3c; font-size: 13px; margin-bottom: 10px; }
.topbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.logout-btn { padding: 6px 16px; background: #eee; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; }
.article-row { background: #fff; border-radius: 8px; padding: 16px; margin-bottom: 10px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); display: flex; gap: 12px; align-items: flex-start; }
.article-info { flex: 1; }
.article-title { font-size: 15px; font-weight: 600; margin-bottom: 6px; }
.article-meta { font-size: 12px; color: #888; }
.article-summary { font-size: 13px; color: #555; margin-top: 6px; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.del-btn { padding: 6px 14px; background: #e74c3c; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; white-space: nowrap; }
.del-btn:hover { background: #c0392b; }
.cat-badge { display: inline-block; font-size: 11px; padding: 2px 8px; border-radius: 20px; background: #e8f0fe; color: #1a73e8; font-weight: 600; margin-right: 6px; }
.notice { background: #d4edda; color: #155724; padding: 10px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 13px; }
.back-link { font-size: 13px; color: #888; display: block; text-align: center; margin-top: 12px; cursor: pointer; text-decoration: underline; }
</style>
</head>
<body>

<?php if (!$is_auth && !$pass_ok): ?>
<!-- 1단계: 비밀번호 입력 -->
<div class="login-box">
  <h2>🔒 관리자 로그인</h2>
  <p>1단계: 비밀번호를 입력하세요</p>
  <?php if (isset($error)): ?>
    <div class="error"><?= htmlspecialchars($error) ?></div>
  <?php endif; ?>
  <form method="POST">
    <input type="password" name="password" placeholder="비밀번호" autofocus>
    <button type="submit">다음</button>
  </form>
</div>

<?php elseif (!$is_auth && $pass_ok): ?>
<!-- 2단계: OTP 입력 -->
<div class="login-box">
  <h2>📧 이메일 인증</h2>
  <p><?= htmlspecialchars(ADMIN_EMAIL) ?>로 발송된<br>6자리 코드를 입력하세요 (5분 유효)</p>
  <?php if (isset($otp_error)): ?>
    <div class="error"><?= htmlspecialchars($otp_error) ?></div>
  <?php endif; ?>
  <form method="POST">
    <input type="text" name="otp" placeholder="인증 코드 6자리" maxlength="6" autofocus inputmode="numeric">
    <button type="submit">확인</button>
  </form>
  <a class="back-link" href="?logout=1">← 처음으로</a>
</div>

<?php else: ?>
<!-- 관리자 메인 -->
<div class="wrap">
  <div class="topbar">
    <h1>📋 기사 관리</h1>
    <a href="?logout=1"><button class="logout-btn">로그아웃</button></a>
  </div>

  <?php if (isset($_GET['deleted'])): ?>
    <div class="notice">✅ 기사가 삭제되었습니다.</div>
  <?php endif; ?>

  <p style="color:#888; margin-bottom:16px;">총 <?= count($articles) ?>개 기사 (최신 50개 기준)</p>

  <?php foreach ($articles as $a): ?>
    <?php
      $cat_file  = $a['category'] ?? '';
      $cat_label = $a['category_label'] ?? $cat_file;
    ?>
    <div class="article-row">
      <div class="article-info">
        <div class="article-title">
          <span class="cat-badge"><?= htmlspecialchars($cat_label) ?></span>
          <?= htmlspecialchars($a['title'] ?? '') ?>
        </div>
        <div class="article-summary"><?= htmlspecialchars($a['summary'] ?? '') ?></div>
        <div class="article-meta">
          <?= htmlspecialchars($a['source'] ?? '') ?> · <?= htmlspecialchars(substr($a['pub_date'] ?? '', 0, 16)) ?>
        </div>
      </div>
      <a href="?delete=<?= urlencode($a['article_id']) ?>&cat=<?= urlencode($cat_file) ?>"
         onclick="return confirm('정말 삭제하시겠습니까?')">
        <button class="del-btn">삭제</button>
      </a>
    </div>
  <?php endforeach; ?>
</div>
<?php endif; ?>

</body>
</html>
