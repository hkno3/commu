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

// ── BODY 코드 저장 (</body> 직전 삽입) ──
$body_codes_file = DATA_DIR . '/body_codes.txt';
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['body_codes']) && ($_SESSION['admin_auth'] ?? false)) {
    file_put_contents($body_codes_file, $_POST['body_codes']);
    $body_saved = true;
}
$body_codes = file_exists($body_codes_file) ? file_get_contents($body_codes_file) : '';

// ── 기사 수정 ──
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['edit_id']) && ($_SESSION['admin_auth'] ?? false)) {
    $edit_id      = preg_replace('/[^a-f0-9]/i', '', $_POST['edit_id']);
    $old_cat      = trim($_POST['old_cat'] ?? '');
    $new_cat      = trim($_POST['new_cat'] ?? '');
    $new_title    = trim($_POST['new_title'] ?? '');
    $new_summary  = trim($_POST['new_summary'] ?? '');
    $new_content  = trim($_POST['new_content'] ?? '');
    $new_cat_label = trim($_POST['new_cat_label'] ?? $new_cat);
    $new_image_url = trim($_POST['new_image_url'] ?? '');
    $new_image_url = ($new_image_url !== '') ? $new_image_url : null;

    if ($edit_id && $old_cat && $new_cat) {
        // 기존 카테고리에서 기사 찾기
        $old_path = DATA_DIR . '/' . cat_to_filename($old_cat) . '.json';
        $article_data = null;
        if (file_exists($old_path)) {
            $old_articles = json_decode(file_get_contents($old_path), true) ?: [];
            foreach ($old_articles as &$a) {
                if (($a['article_id'] ?? '') === $edit_id) {
                    $a['title']          = $new_title ?: $a['title'];
                    $a['summary']        = $new_summary ?: $a['summary'];
                    $a['content']        = $new_content !== '' ? $new_content : ($a['content'] ?? '');
                    $a['category']       = $new_cat;
                    $a['category_label'] = $new_cat_label;
                    $a['image_url']      = $new_image_url;
                    $article_data = $a;
                    break;
                }
            }
            unset($a);
            // 카테고리 변경 시 기존 파일에서 제거
            if ($old_cat !== $new_cat) {
                $old_articles = array_values(array_filter($old_articles, fn($a) => ($a['article_id'] ?? '') !== $edit_id));
            }
            file_put_contents($old_path, json_encode($old_articles, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
        }
        // 새 카테고리 파일에 추가 (카테고리 변경 시)
        if ($article_data && $old_cat !== $new_cat) {
            $new_path = DATA_DIR . '/' . cat_to_filename($new_cat) . '.json';
            $new_articles = file_exists($new_path) ? (json_decode(file_get_contents($new_path), true) ?: []) : [];
            array_unshift($new_articles, $article_data);
            file_put_contents($new_path, json_encode($new_articles, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
        }
        // latest.json 업데이트
        $latest_path = DATA_DIR . '/latest.json';
        if (file_exists($latest_path)) {
            $latest = json_decode(file_get_contents($latest_path), true) ?: [];
            foreach ($latest as &$a) {
                if (($a['article_id'] ?? '') === $edit_id) {
                    $a['title']          = $new_title ?: $a['title'];
                    $a['summary']        = $new_summary ?: $a['summary'];
                    $a['category']       = $new_cat;
                    $a['category_label'] = $new_cat_label;
                    $a['image_url']      = $new_image_url;
                    break;
                }
            }
            unset($a);
            file_put_contents($latest_path, json_encode($latest, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
        }
        // 수정한 카테고리 탭으로 이동 (category_label = display name with /)
        $redirect_cat = $new_cat_label ?: str_replace('_', '/', $new_cat);
        header('Location: /admin_rudwnQkd1/?edited=1&cat=' . urlencode($redirect_cat));
        exit;
    }
}

// ── 기사 삭제 ──
if (isset($_GET['delete']) && ($_SESSION['admin_auth'] ?? false)) {
    $del_id  = preg_replace('/[^a-f0-9]/i', '', $_GET['delete']);
    $del_cat = preg_replace('/[^a-zA-Z_\/가-힣]/', '', $_GET['cat'] ?? '');
    $del_error = '';
    if ($del_id && $del_cat) {
        $path = DATA_DIR . '/' . cat_to_filename($del_cat) . '.json';
        if (!file_exists($path)) {
            $del_error = "파일 없음: $path";
        } else {
            $articles = json_decode(file_get_contents($path), true) ?: [];
            $articles = array_values(array_filter($articles, fn($a) => ($a['article_id'] ?? '') !== $del_id));
            $r1 = file_put_contents($path, json_encode($articles, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
            if ($r1 === false) $del_error = "쓰기 실패: $path";
        }
        $latest_path = DATA_DIR . '/latest.json';
        if (file_exists($latest_path)) {
            $latest = json_decode(file_get_contents($latest_path), true) ?: [];
            $latest = array_values(array_filter($latest, fn($a) => ($a['article_id'] ?? '') !== $del_id));
            file_put_contents($latest_path, json_encode($latest, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
        }
        if ($del_error) {
            header('Location: /admin_rudwnQkd1/?del_error=' . urlencode($del_error));
        } else {
            header('Location: /admin_rudwnQkd1/?deleted=1');
        }
        exit;
    }
}

$is_auth = $_SESSION['admin_auth'] ?? false;

$all_cats = ["정치","경제","사회","생활/문화","IT/과학","부동산","헬스/건강","스포츠","연예","자동차","가상화폐","주식"];
$cur_cat = $_GET['cat'] ?? '전체';
$articles = [];
if ($is_auth) {
    if ($cur_cat === '전체') {
        // 전체: latest.json 우선 사용 (안정적)
        $latest_path = DATA_DIR . '/latest.json';
        if (file_exists($latest_path)) {
            $articles = json_decode(file_get_contents($latest_path), true) ?: [];
        }
        // latest.json 없으면 카테고리 파일 병합
        if (empty($articles)) {
            foreach ($all_cats as $cat) {
                $path = DATA_DIR . '/' . cat_to_filename($cat) . '.json';
                if (file_exists($path)) {
                    $items = json_decode(file_get_contents($path), true) ?: [];
                    $articles = array_merge($articles, $items);
                }
            }
            usort($articles, fn($a, $b) => strcmp($b['pub_date'] ?? $b['pubDate'] ?? '', $a['pub_date'] ?? $a['pubDate'] ?? ''));
        }
    } else {
        $path = DATA_DIR . '/' . cat_to_filename($cur_cat) . '.json';
        if (file_exists($path)) {
            $articles = json_decode(file_get_contents($path), true) ?: [];
        }
    }
    $articles = array_slice($articles, 0, 50);
}

// 조회수 데이터 로드
$view_stats = [];
if ($is_auth && !empty($articles)) {
    try {
        require_once __DIR__ . '/../db/init.php';
        $pdo = db_connect();
        $ids = array_map(fn($a) => $a['article_id'] ?? '', $articles);
        $ids = array_filter($ids);
        if ($ids) {
            $placeholders = implode(',', array_fill(0, count($ids), '?'));
            $stmt = $pdo->prepare("SELECT article_id, COUNT(*) AS total, SUM(DATE(viewed_at)=CURDATE()) AS today FROM page_views WHERE article_id IN ($placeholders) GROUP BY article_id");
            $stmt->execute(array_values($ids));
            foreach ($stmt->fetchAll() as $row) {
                $view_stats[$row['article_id']] = ['today' => (int)$row['today'], 'total' => (int)$row['total']];
            }
        }
    } catch (Exception $e) {}
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
.edit-btn { padding: 6px 14px; background: #1a73e8; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; white-space: nowrap; }
.edit-btn:hover { background: #1557b0; }
.btn-group { display: flex; flex-direction: column; gap: 6px; }
.modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 1000; align-items: center; justify-content: center; }
.modal-overlay.open { display: flex; }
.modal { background: #fff; border-radius: 12px; padding: 28px; width: 100%; max-width: 760px; max-height: 90vh; overflow-y: auto; box-shadow: 0 8px 32px rgba(0,0,0,0.2); }
.modal h3 { font-size: 17px; margin-bottom: 20px; }
.modal label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 4px; color: #444; }
.modal input, .modal textarea, .modal select { width: 100%; padding: 9px 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; margin-bottom: 14px; font-family: inherit; }
.modal textarea { resize: vertical; }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 4px; }
.btn-save { padding: 9px 24px; background: #1a73e8; color: #fff; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; }
.btn-save:hover { background: #1557b0; }
.btn-cancel { padding: 9px 20px; background: #eee; color: #333; border: none; border-radius: 8px; font-size: 14px; cursor: pointer; }
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
  <?php if (isset($_GET['edited'])): ?>
    <div class="notice">✅ 기사가 수정되었습니다.</div>
  <?php endif; ?>
  <?php if (isset($_GET['del_error'])): ?>
    <div class="notice" style="background:#f8d7da; color:#721c24;">❌ 삭제 오류: <?= htmlspecialchars($_GET['del_error']) ?><br>DATA_DIR: <?= DATA_DIR ?></div>
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

  <!-- BODY 코드 관리 -->
  <div style="background:#fff; border-radius:8px; padding:20px; margin-bottom:20px; box-shadow:0 1px 4px rgba(0,0,0,0.06);">
    <h2 style="font-size:16px; margin-bottom:12px;">🔧 &lt;/body&gt; 코드 관리</h2>
    <p style="font-size:12px; color:#888; margin-bottom:10px;">네이버 애널리틱스 등 &lt;/body&gt; 직전 삽입이 필요한 코드를 입력하세요. 모든 페이지의 &lt;/body&gt; 바로 앞에 자동 삽입됩니다.</p>
    <?php if (isset($body_saved)): ?>
      <div class="notice">✅ 저장되었습니다.</div>
    <?php endif; ?>
    <form method="POST">
      <textarea name="body_codes" rows="8" style="width:100%; padding:10px; border:1px solid #ddd; border-radius:8px; font-family:monospace; font-size:13px; resize:vertical;"><?= htmlspecialchars($body_codes) ?></textarea>
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
  <p style="color:#888; margin-bottom:16px;">총 <?= count($articles) ?>개 기사</p>

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
          &nbsp;·&nbsp; <?= !empty($a['image_url']) ? '🖼 이미지 있음' : '🚫 이미지 없음' ?>
          <?php $vs = $view_stats[$a['article_id'] ?? ''] ?? null; if ($vs): ?>
            &nbsp;·&nbsp; 👁 오늘 <?= $vs['today'] ?> / 전체 <?= $vs['total'] ?>
          <?php endif; ?>
        </div>
      </div>
      <div class="btn-group">
        <button class="edit-btn" onclick="openEdit(<?= htmlspecialchars(json_encode([
          'id'    => $a['article_id'] ?? '',
          'cat'   => $cat_file,
          'label' => $cat_label,
          'title' => $a['title'] ?? '',
          'summary' => $a['summary'] ?? '',
          'content' => $a['content'] ?? '',
          'image' => $a['image_url'] ?? '',
          'cur_cat' => $cur_cat,
        ]), ENT_QUOTES) ?>)">수정</button>
        <a href="?delete=<?= urlencode($a['article_id']) ?>&cat=<?= urlencode($cat_file) ?>"
           onclick="return confirm('정말 삭제하시겠습니까?')">
          <button class="del-btn">삭제</button>
        </a>
      </div>
    </div>
  <?php endforeach; ?>
</div>

<!-- 수정 모달 -->
<div class="modal-overlay" id="edit-modal">
  <div class="modal">
    <h3>✏️ 기사 수정</h3>
    <form method="POST" id="edit-form">
      <input type="hidden" name="edit_id" id="ef-id">
      <input type="hidden" name="old_cat" id="ef-old-cat">
      <input type="hidden" name="cur_cat" id="ef-cur-cat">
      <label>제목</label>
      <input type="text" name="new_title" id="ef-title" maxlength="200">
      <label>요약 내용</label>
      <textarea name="new_summary" id="ef-summary" rows="6"></textarea>
      <label>본문 내용 (HTML)</label>
      <textarea name="new_content" id="ef-content" rows="16" style="font-family:monospace; font-size:12px;"></textarea>
      <label>이미지 URL (비워두면 이미지 삭제됨)</label>
      <input type="text" name="new_image_url" id="ef-image" placeholder="https://...">
      <div id="ef-image-preview" style="margin:6px 0;"></div>
      <label>카테고리</label>
      <select name="new_cat" id="ef-cat">
        <?php foreach ($all_cats as $c): ?>
          <option value="<?= htmlspecialchars(str_replace('/', '_', $c)) ?>"><?= htmlspecialchars($c) ?></option>
        <?php endforeach; ?>
      </select>
      <input type="hidden" name="new_cat_label" id="ef-cat-label">
      <div class="modal-actions">
        <button type="button" class="btn-cancel" onclick="closeEdit()">취소</button>
        <button type="submit" class="btn-save">저장</button>
      </div>
    </form>
  </div>
</div>

<script>
const ALL_CATS = <?= json_encode(array_combine(
  array_map(fn($c) => str_replace('/', '_', $c), $all_cats),
  $all_cats
)) ?>;

function openEdit(data) {
  document.getElementById('ef-id').value      = data.id;
  document.getElementById('ef-old-cat').value = data.cat;
  document.getElementById('ef-cur-cat').value = data.cur_cat;
  document.getElementById('ef-title').value   = data.title;
  document.getElementById('ef-summary').value = data.summary;
  document.getElementById('ef-content').value = data.content || '';
  document.getElementById('ef-image').value   = data.image || '';
  document.getElementById('ef-cat').value     = data.cat;
  updateImagePreview();
  document.getElementById('edit-modal').classList.add('open');
}
function updateImagePreview() {
  const url = document.getElementById('ef-image').value.trim();
  const box = document.getElementById('ef-image-preview');
  box.innerHTML = url
    ? `<img src="${url.replace(/"/g, '&quot;')}" style="max-width:100%; max-height:160px; border-radius:6px;" onerror="this.style.display='none'">`
    : '';
}
document.getElementById('ef-image').addEventListener('input', updateImagePreview);
function closeEdit() {
  document.getElementById('edit-modal').classList.remove('open');
}
document.getElementById('edit-modal').addEventListener('click', function(e) {
  if (e.target === this) closeEdit();
});
document.getElementById('edit-form').addEventListener('submit', function() {
  const sel = document.getElementById('ef-cat');
  document.getElementById('ef-cat-label').value = ALL_CATS[sel.value] || sel.value;
});
</script>
<?php endif; ?>

</body>
</html>
