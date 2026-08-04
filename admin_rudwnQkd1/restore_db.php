<?php
/**
 * DB → JSON 복원 스크립트
 * article_cache 테이블의 글을 각 카테고리 JSON 파일로 복원
 * 실행 후 삭제 권장
 */
require_once __DIR__ . '/../config.php';

// 카테고리 → JSON 파일명 매핑
const CAT_FILE_MAP = [
    '정치'      => 'politics',
    '경제'      => 'economy',
    '사회'      => 'society',
    '생활/문화' => 'lifestyle',
    '생활_문화' => 'lifestyle',
    'IT/과학'   => 'tech',
    'IT_과학'   => 'tech',
    '천천히 늙자' => 'animal',
    '천천히_늙자' => 'animal',
    '여행지'    => 'travelguide',
];

$dry_run = isset($_GET['dry']) && $_GET['dry'] === '1';

echo "<pre>\n";
echo "=== DB → JSON 복원 스크립트 ===\n";
echo ($dry_run ? "[DRY RUN - 실제 저장 안 함]\n" : "[실제 저장 모드]\n");
echo "\n";

try {
    require_once __DIR__ . '/../db/init.php';
    $pdo = db_connect();

    // 전체 article_cache 조회 (최신순)
    $stmt = $pdo->query(
        "SELECT article_id, title, summary, content, image_url,
                IFNULL(image_credit,'') AS image_credit,
                IFNULL(image_source,'') AS image_source,
                IFNULL(category_label,'') AS category_label,
                IFNULL(article_type,'news') AS article_type,
                original_url, source, category,
                DATE_FORMAT(pub_date, '%Y-%m-%dT%H:%i:%s+09:00') AS pub_date
         FROM article_cache
         ORDER BY pub_date DESC"
    );
    $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
    echo "DB 전체 글 수: " . count($rows) . "개\n\n";

    // 카테고리별 분류
    $grouped = [];
    $skipped = [];
    foreach ($rows as $row) {
        $cat   = $row['category_label'] ?: $row['category'];
        $fname = CAT_FILE_MAP[$cat] ?? null;
        if (!$fname) {
            // cat_to_filename 시도
            $fname = cat_to_filename($cat);
            if ($fname === $cat) { // 변환 안 됨
                $skipped[] = "[{$cat}] {$row['article_id']} - {$row['title']}";
                continue;
            }
        }
        $grouped[$fname][] = [
            'article_id'    => $row['article_id'],
            'slug'          => $row['article_id'], // fallback slug
            'title'         => $row['title'],
            'summary'       => $row['summary'] ?? '',
            'content'       => $row['content'] ?? '',
            'image_url'     => $row['image_url'],
            'image_credit'  => $row['image_credit'],
            'image_source'  => $row['image_source'],
            'category'      => $row['category'],
            'category_label'=> $row['category_label'] ?: $row['category'],
            'article_type'  => $row['article_type'],
            'original_url'  => $row['original_url'],
            'source'        => $row['source'],
            'pub_date'      => $row['pub_date'],
            'pubDate'       => $row['pub_date'],
        ];
    }

    // JSON 파일별 저장
    foreach ($grouped as $fname => $articles) {
        $path = DATA_DIR . "/{$fname}.json";

        // 기존 파일 로드
        $existing = [];
        if (file_exists($path)) {
            $existing = json_decode(file_get_contents($path), true) ?: [];
        }

        // 기존 article_id 인덱스
        $existing_ids = array_column($existing, null, 'article_id');

        // DB 글을 앞에, 기존 글 중 DB에 없는 것은 뒤에 병합
        $db_ids = array_column($articles, null, 'article_id');
        $merged = $articles;
        foreach ($existing as $a) {
            if (!isset($db_ids[$a['article_id']])) {
                $merged[] = $a;
            }
        }

        // pub_date 기준 최신순 정렬
        usort($merged, fn($a, $b) =>
            strcmp($b['pubDate'] ?? $b['pub_date'] ?? '', $a['pubDate'] ?? $a['pub_date'] ?? '')
        );

        $count_db = count($articles);
        echo "  └ {$fname}.json: DB {$count_db}개 + 기존 " . count($existing) . "개 → 병합 " . count($merged) . "개\n";

        if (!$dry_run) {
            file_put_contents($path, json_encode($merged, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES));
            echo "  └ 저장 완료: {$path}\n";
        }
    }

    if (!empty($skipped)) {
        echo "\n[카테고리 미인식 - 스킵됨]\n";
        foreach ($skipped as $s) echo "  {$s}\n";
    }

    echo "\n완료!\n";
    if ($dry_run) {
        echo "\n실제 저장하려면 ?dry=0 으로 접근하세요.\n";
    }

} catch (Exception $e) {
    echo "오류: " . $e->getMessage() . "\n";
}

echo "</pre>\n";
