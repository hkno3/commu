<?php
/**
 * Articles API
 * GET /api/articles.php?category=정치&page=1&limit=10
 */

require_once __DIR__ . '/../config.php';

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: ' . SITE_URL);

$category = trim($_GET['category'] ?? '');
$page     = max(1, (int)($_GET['page'] ?? 1));
$limit    = min(50, max(1, (int)($_GET['limit'] ?? 10)));
$offset   = ($page - 1) * $limit;

// 카테고리별 JSON 파일 목록 (독립 구조)
const CATEGORY_FILES = [
    'politics', 'economy', 'society', 'lifestyle', 'tech',
    'animal', 'travelguide',
];

// 레거시 카테고리 병합 (구 파일명 → 현재 카테고리)
const MERGE_MAP = [
    '경제'      => ['realestate', 'crypto', 'stock'],
    'IT_과학'   => ['auto'],
    '생활_문화' => ['health', 'sports', 'entertainment'],
];

$articles = [];

if ($category !== '' && $category !== 'all') {
    $filename = cat_to_filename($category);
    $paths = [DATA_DIR . '/' . $filename . '.json'];
    foreach (MERGE_MAP[$category] ?? [] as $legacy) {
        $paths[] = DATA_DIR . '/' . $legacy . '.json';
    }
    foreach ($paths as $path) {
        if (file_exists($path)) {
            $articles = array_merge($articles, json_decode(file_get_contents($path), true) ?: []);
        }
    }
    usort($articles, fn($a, $b) => strcmp($b['pubDate'] ?? $b['pub_date'] ?? '', $a['pubDate'] ?? $a['pub_date'] ?? ''));
} else {
    // 전체: 각 카테고리 JSON 직접 병합 (latest.json 불필요)
    foreach (CATEGORY_FILES as $fname) {
        $path = DATA_DIR . '/' . $fname . '.json';
        if (file_exists($path)) {
            $articles = array_merge($articles, json_decode(file_get_contents($path), true) ?: []);
        }
    }
    usort($articles, fn($a, $b) => strcmp($b['pubDate'] ?? $b['pub_date'] ?? '', $a['pubDate'] ?? $a['pub_date'] ?? ''));
}

$total = count($articles);
$slice = array_slice($articles, $offset, $limit);

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
