<?php
/**
 * Comment API
 * GET  /api/comment.php?article_id=xxx&page=1
 * POST /api/comment.php  { article_id, nickname, content }
 */

require_once __DIR__ . '/../config.php';
require_once __DIR__ . '/../db/init.php';

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: ' . SITE_URL);
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

// ---------------------------------------------------------------------------
// Profanity filter
// ---------------------------------------------------------------------------
const BANNED_PATTERNS = [
    // Base bad words + common leet/spacing variations
    '/씨\s*[발팔]/u',
    '/시\s*[발팔]/u',
    '/개\s*새\s*끼/u',
    '/병\s*신/u',
    '/미\s*친/u',
    '/죽\s*어/u',
    '/닥\s*쳐/u',
    '/꺼\s*져/u',
    '/바\s*보/u',
    '/멍\s*청/u',
    '/찐\s*따/u',
    '/보\s*지/u',
    '/자\s*지/u',
    '/섹\s*[스쑤]/u',
    '/ㅅㅂ/u',
    '/ㅂㅅ/u',
    '/ㅁㅊ/u',
];

function contains_profanity(string $text): bool {
    foreach (BANNED_PATTERNS as $pattern) {
        if (preg_match($pattern, $text)) {
            return true;
        }
    }
    return false;
}

function ip_hash(): string {
    $ip = $_SERVER['HTTP_X_FORWARDED_FOR']
        ?? $_SERVER['HTTP_CF_CONNECTING_IP']
        ?? $_SERVER['REMOTE_ADDR']
        ?? '';
    return hash('sha256', $ip . 'newscommu_salt_2024');
}

// ---------------------------------------------------------------------------
// GET: fetch comments
// ---------------------------------------------------------------------------
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    $article_id = trim($_GET['article_id'] ?? '');
    $page       = max(1, (int)($_GET['page'] ?? 1));
    $limit      = 20;
    $offset     = ($page - 1) * $limit;

    if ($article_id === '') {
        http_response_code(400);
        echo json_encode(['error' => 'article_id required']);
        exit;
    }

    $article_id = substr($article_id, 0, 64);
    $count_only = isset($_GET['count']);

    $pdo = db_connect();

    $countStmt = $pdo->prepare("SELECT COUNT(*) FROM comments WHERE article_id = ?");
    $countStmt->execute([$article_id]);
    $total = (int)$countStmt->fetchColumn();

    if ($count_only) {
        echo json_encode(['count' => $total], JSON_UNESCAPED_UNICODE);
        exit;
    }

    $stmt = $pdo->prepare(
        "SELECT id, nickname, content, created_at
         FROM comments
         WHERE article_id = ?
         ORDER BY created_at ASC
         LIMIT ? OFFSET ?"
    );
    $stmt->execute([$article_id, $limit, $offset]);
    $comments = $stmt->fetchAll();

    echo json_encode([
        'total'    => $total,
        'page'     => $page,
        'has_more' => ($offset + $limit) < $total,
        'comments' => $comments,
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

// ---------------------------------------------------------------------------
// POST: add comment
// ---------------------------------------------------------------------------
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Accept JSON body or form data
    $body = [];
    $raw  = file_get_contents('php://input');
    if ($raw) {
        $body = json_decode($raw, true) ?: [];
    }
    if (empty($body)) {
        $body = $_POST;
    }

    $article_id = trim($body['article_id'] ?? '');
    $nickname   = trim($body['nickname']   ?? '') ?: DEFAULT_NICKNAME;
    $content    = trim($body['content']    ?? '');

    // Validation
    if ($article_id === '') {
        http_response_code(400);
        echo json_encode(['error' => 'article_id required']);
        exit;
    }
    if ($content === '') {
        http_response_code(400);
        echo json_encode(['error' => '댓글 내용을 입력하세요.']);
        exit;
    }
    if (mb_strlen($content) > MAX_COMMENT_LENGTH) {
        http_response_code(400);
        echo json_encode(['error' => '댓글은 ' . MAX_COMMENT_LENGTH . '자 이내로 작성하세요.']);
        exit;
    }
    if (mb_strlen($nickname) > 30) {
        $nickname = mb_substr($nickname, 0, 30);
    }

    // Profanity check
    if (contains_profanity($content) || contains_profanity($nickname)) {
        http_response_code(422);
        echo json_encode(['error' => '부적절한 표현이 포함되어 있습니다.']);
        exit;
    }

    // Rate limiting: 5 comments per minute per IP
    $pdo     = db_connect();
    $ipHash  = ip_hash();
    $rateStmt = $pdo->prepare(
        "SELECT COUNT(*) FROM comments
         WHERE ip_hash = ? AND created_at > DATE_SUB(NOW(), INTERVAL 1 MINUTE)"
    );
    $rateStmt->execute([$ipHash]);
    if ((int)$rateStmt->fetchColumn() >= 5) {
        http_response_code(429);
        echo json_encode(['error' => '너무 많은 댓글을 작성했습니다. 잠시 후 다시 시도하세요.']);
        exit;
    }

    $insert = $pdo->prepare(
        "INSERT INTO comments (article_id, nickname, content, ip_hash)
         VALUES (?, ?, ?, ?)"
    );
    $insert->execute([
        substr($article_id, 0, 64),
        htmlspecialchars($nickname, ENT_QUOTES, 'UTF-8'),
        htmlspecialchars($content,  ENT_QUOTES, 'UTF-8'),
        $ipHash,
    ]);

    $newId = $pdo->lastInsertId();

    http_response_code(201);
    echo json_encode([
        'success' => true,
        'comment' => [
            'id'         => $newId,
            'nickname'   => htmlspecialchars($nickname, ENT_QUOTES, 'UTF-8'),
            'content'    => htmlspecialchars($content,  ENT_QUOTES, 'UTF-8'),
            'created_at' => date('Y-m-d H:i:s'),
        ],
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

http_response_code(405);
echo json_encode(['error' => 'Method not allowed']);
