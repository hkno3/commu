<?php
/**
 * Articles API
 * GET /api/articles.php?category=정치&page=1&limit=10
 */

require_once __DIR__ . '/../config.php';

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: ' . SITE_URL);

// ---------------------------------------------------------------------------
// Input
// ---------------------------------------------------------------------------
$category = trim($_GET['category'] ?? '');
$page     = max(1, (int)($_GET['page'] ?? 1));
$limit    = min(50, max(1, (int)($_GET['limit'] ?? 10)));
$offset   = ($page - 1) * $limit;

// ---------------------------------------------------------------------------
// Load JSON data files
// ---------------------------------------------------------------------------
$articles = [];

if ($category !== '' && $category !== 'all') {
    // Single category — also load merged legacy categories
    $merge_map = [
        '경제'    => ['realestate', 'crypto', 'stock'],   // 부동산·가상화폐·주식 → 경제
        'IT_과학' => ['auto'],                             // 자동차 → IT/과학
        '생활_문화' => ['health', 'sports', 'entertainment'], // 헬스·스포츠·연예 → 생활/문화
    ];
    $filename = cat_to_filename($category);
    $paths = [DATA_DIR . '/' . $filename . '.json'];
    foreach ($merge_map[$category] ?? [] as $legacy) {
        $paths[] = DATA_DIR . '/' . $legacy . '.json';
    }
    foreach ($paths as $path) {
        if (file_exists($path)) {
            $items = json_decode(file_get_contents($path), true) ?: [];
            $articles = array_merge($articles, $items);
        }
    }
    usort($articles, fn($a, $b) => strcmp($b['pubDate'] ?? $b['pub_date'] ?? '', $a['pubDate'] ?? $a['pub_date'] ?? ''));
} else {
    // All categories — use latest.json if it exists, else merge
    $latestPath = DATA_DIR . '/latest.json';
    if (file_exists($latestPath)) {
        $articles = json_decode(file_get_contents($latestPath), true) ?: [];
    } else {
        $files = glob(DATA_DIR . '/*.json');
        foreach ($files as $file) {
            $items = json_decode(file_get_contents($file), true) ?: [];
            $articles = array_merge($articles, $items);
        }
        usort($articles, fn($a, $b) => strcmp($b['pubDate'] ?? '', $a['pubDate'] ?? ''));
    }
}

$total   = count($articles);
$slice   = array_slice($articles, $offset, $limit);

// Attach comment counts lazily (skip DB call if not needed)
$withCounts = [];
if (!empty($slice)) {
    try {
        require_once __DIR__ . '/../db/init.php';
        $pdo = db_connect();
        $ids = array_column($slice, 'article_id');
        $placeholders = implode(',', array_fill(0, count($ids), '?'));
        $stmt = $pdo->prepare(
            "SELECT article_id, COUNT(*) AS cnt FROM comments
             WHERE article_id IN ($placeholders) GROUP BY article_id"
        );
        $stmt->execute($ids);
        $counts = array_column($stmt->fetchAll(), 'cnt', 'article_id');
        foreach ($slice as $a) {
            $a['url']           = $a['original_url'] ?? $a['url'] ?? '';
            $a['pub_date']      = $a['pubDate'] ?? $a['pub_date'] ?? '';
            $a['comment_count'] = (int)($counts[$a['article_id']] ?? 0);
            $withCounts[] = $a;
        }
    } catch (Exception $e) {
        foreach ($slice as $a) {
            $a['url']           = $a['original_url'] ?? $a['url'] ?? '';
            $a['pub_date']      = $a['pubDate'] ?? $a['pub_date'] ?? '';
            $a['comment_count'] = 0;
            $withCounts[] = $a;
        }
    }
}

echo json_encode([
    'page'     => $page,
    'limit'    => $limit,
    'total'    => $total,
    'has_more' => ($offset + $limit) < $total,
    'articles' => $withCounts,
], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
