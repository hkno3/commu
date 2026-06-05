<?php
/**
 * newscommu.com - One-time installation script
 * Visit this page once after uploading, then DELETE it.
 */

// Primitive protection: require a token query param to prevent accidental runs
$token = $_GET['token'] ?? '';
$expected = 'install_' . substr(md5(__FILE__ . filemtime(__FILE__)), 0, 8);

if ($token !== $expected) {
    http_response_code(403);
    echo "<h2>Access denied.</h2><p>Add <code>?token={$expected}</code> to the URL.</p>";
    exit;
}

require_once __DIR__ . '/db/init.php';

$errors = [];
$success = false;

try {
    db_init_schema();
    $success = true;
} catch (Exception $e) {
    $errors[] = htmlspecialchars($e->getMessage());
}

?><!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>newscommu.com 설치</title>
<style>
  body { font-family: sans-serif; max-width: 600px; margin: 60px auto; padding: 0 20px; }
  .ok  { color: green; } .err { color: red; }
</style>
</head>
<body>
<h1>newscommu.com 설치</h1>
<?php if ($success): ?>
  <p class="ok">&#10003; 데이터베이스 테이블이 성공적으로 생성되었습니다.</p>
  <p><strong>보안을 위해 지금 바로 <code>install.php</code> 파일을 삭제하세요.</strong></p>
  <p><a href="/">메인 페이지로 이동</a></p>
<?php else: ?>
  <p class="err">&#10007; 설치 중 오류가 발생했습니다:</p>
  <ul><?php foreach ($errors as $e) echo "<li>{$e}</li>"; ?></ul>
  <p>config.php의 DB 설정을 확인하세요.</p>
<?php endif; ?>
</body>
</html>
