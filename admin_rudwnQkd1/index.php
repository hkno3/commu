<?php
session_start();
require_once __DIR__ . '/../config.php';

define('ADMIN_HASH', 'e4a087445903115bf1a5f461a3b123b6ce48dae4e0e8c9f164894cda2b1ce004');

// ── 로그인 처리 ──
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['password'])) {
    if (hash('sha256', $_POST['password']) === ADMIN_HASH) {
        $_SESSION['admin_auth'] = true;
        header('Location: /admin_rudwnQkd1/');
        exit;
    } else {
        $error = '비밀번호가 틀렸습니다.';
    }
}

// ── 로그아웃 ──
if (isset($_GET['logout'])) {
    session_destroy();
    header('Location: /admin_rudwnQkd1/');
    exit;
}

// ── HEAD 코드 저장 ──
$head_codes_file = DATA_DIR . '/head_codes.txt';
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['head_codes']) && ($_SESSION['admin_auth'] ?? false)) {
    file_put_contents($head_codes_file, $_POST['head_codes']);
    $head_saved = true;
}
$head_codes = file_exists($head_codes_file) ? file_get_contents($head_codes_file) : '';

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

$all_cats = ["정치","경제","사회","생활/문화","세계","IT/과학","부동산","헬스/건강","스포츠","연예","자동차","날씨","가상화폐","주식","육아","여행","게임","패션/뷰티","음식/맛집","교육","환경","법률","취업/직장","반려동물","영화"];
$cur_cat = $_GET['cat'] ?? '전체';
$articles = [];
if ($is_auth) {
    $load_cats = $cur_cat === '전체' ? $all_cats : [$cur_cat];
    foreach ($load_cats as $cat) {
        $path = DATA_DIR . '/' . str_replace('/', '_', $cat) . '.json';
        if (file_exists($path)) {
            $items = json_decode(file_get_contents($path), true) ?: [];
            $articles = array_merge($articles, $items);
        }
    }
    usort($articles, fn($a, $b) => strcmp($b['pub_date'] ?? '', $a['pub_date'] ?? ''));
    $articles = array_slice($articles, 0, 30);
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

<?php if (!$is_auth): ?>
<div class="login-box">
  <h2>🔒 관리자 로그인</h2>
  <?php if (isset($error)): ?>
    <div class="error"><?= htmlspecialchars($error) ?></div>
  <?php endif; ?>
  <form method="POST">
    <input type="password" name="password" placeholder="비밀번호" autofocus>
    <button type="submit">로그인</button>
  </form>
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

  <!-- HEAD 코드 관리 -->
  <div style="background:#fff; border-radius:8px; padding:20px; margin-bottom:20px; box-shadow:0 1px 4px rgba(0,0,0,0.06);">
    <h2 style="font-size:16px; margin-bottom:12px;">🔧 &lt;head&gt; 코드 관리</h2>
    <p style="font-size:12px; color:#888; margin-bottom:10px;">구글 서치콘솔, 네이버 서치어드바이저, 애드센스, 애널리틱스 등 코드를 입력하세요. 모든 페이지 &lt;head&gt;에 자동 삽입됩니다.</p>
    <?php if (isset($head_saved)): ?>
      <div class="notice">✅ 저장되었습니다.</div>
    <?php endif; ?>
    <form method="POST">
      <textarea name="head_codes" rows="8" style="width:100%; padding:10px; border:1px solid #ddd; border-radius:8px; font-family:monospace; font-size:13px; resize:vertical;"><?= htmlspecialchars($head_codes) ?></textarea>
      <button type="submit" style="margin-top:8px; padding:8px 24px; background:#1a73e8; color:#fff; border:none; border-radius:6px; font-size:14px; font-weight:600; cursor:pointer;">저장</button>
    </form>
  </div>

  <!-- 카테고리 탭 -->
  <div style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:16px;">
    <?php foreach (array_merge(['전체'], $all_cats) as $cat): ?>
      <a href="?cat=<?= urlencode($cat) ?>" style="padding:4px 12px; border-radius:20px; font-size:13px; text-decoration:none;
        <?= $cur_cat === $cat ? 'background:#1a73e8; color:#fff;' : 'background:#eee; color:#333;' ?>">
        <?= htmlspecialchars($cat) ?>
      </a>
    <?php endforeach; ?>
  </div>
  <p style="color:#888; margin-bottom:16px;">총 <?= count($articles) ?>개 기사 (최신 30개)</p>

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
