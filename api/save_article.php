<?php
/**
 * Internal article save API
 * Called by GitHub Actions after FTP deploy to persist articles to DB
 */

// Simple secret key auth
$secret = $_SERVER['HTTP_X_SAVE_SECRET'] ?? '';
if ($secret !== (defined('SAVE_SECRET') ? SAVE_SECRET : '')) {
    http_response_code(403);
    echo json_encode(['error' => 'forbidden']);
    exit;
}

require_once __DIR__ . '/../config.php';
require_once __DIR__ . '/../db/init.php';

header('Content-Type: application/json; charset=utf-8');

$body = file_get_contents('php://input');
$article = json_decode($body, true);

if (!$article || empty($article['article_id'])) {
    http_response_code(400);
    echo json_encode(['error' => 'invalid payload']);
    exit;
}

try {
    $pdo = db_connect();

    $pub = $article['pubDate'] ?? $article['pub_date'] ?? null;
    $pub_dt = null;
    if ($pub) {
        try {
            $pub_dt = (new DateTime($pub))->format('Y-m-d H:i:s');
        } catch (Exception $e) {}
    }

    $stmt = $pdo->prepare("
        INSERT INTO article_cache
            (article_id, title, summary, content, image_url, original_url,
             source, category, category_label, article_type, pub_date)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
        ON DUPLICATE KEY UPDATE
            title=VALUES(title), summary=VALUES(summary),
            content=VALUES(content), image_url=VALUES(image_url),
            category=VALUES(category), category_label=VALUES(category_label),
            pub_date=VALUES(pub_date)
    ");

    $stmt->execute([
        $article['article_id'],
        mb_substr($article['title'] ?? '', 0, 500),
        $article['summary'] ?? '',
        $article['content'] ?? '',
        mb_substr($article['image_url'] ?? '', 0, 2048),
        mb_substr($article['original_url'] ?? $article['url'] ?? '', 0, 2048),
        $article['source'] ?? '',
        $article['category'] ?? '',
        $article['category_label'] ?? '',
        $article['article_type'] ?? 'news',
        $pub_dt,
    ]);

    echo json_encode(['ok' => true, 'article_id' => $article['article_id']]);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['error' => $e->getMessage()]);
}
