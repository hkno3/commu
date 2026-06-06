<?php
/**
 * newscommu.com - Site Configuration
 * Fill in your actual credentials before deploying.
 */

// ---------------------------------------------------------------------------
// Database
// ---------------------------------------------------------------------------
define('DB_HOST', 'localhost');
define('DB_NAME', 'bizachie_newscommu');
define('DB_USER', 'bizachie_nc');
define('DB_PASS', 'VYrudejr!@11');
define('DB_CHARSET', 'utf8mb4');

// ---------------------------------------------------------------------------
// Site
// ---------------------------------------------------------------------------
define('SITE_NAME', 'newscommu.com');
define('SITE_DESC', '한국 주요 뉴스를 한눈에 — 실시간 뉴스 커뮤니티');
define('SITE_URL', 'https://newscommu.com');
define('DATA_DIR', __DIR__ . '/data');

// ---------------------------------------------------------------------------
// AdSense
// ---------------------------------------------------------------------------
define('ADSENSE_PUBLISHER_ID', 'ca-pub-XXXXXXXXXXXXXXXXX'); // Replace with your ID

// ---------------------------------------------------------------------------
// Comment settings
// ---------------------------------------------------------------------------
define('MAX_COMMENT_LENGTH', 500);
define('DEFAULT_NICKNAME', '익명');

// ---------------------------------------------------------------------------
// Timezone
// ---------------------------------------------------------------------------
date_default_timezone_set('Asia/Seoul');

// 카테고리 → ASCII 파일명 (FTP 한글 파일명 문제 해결)
function cat_to_filename(string $cat): string {
    static $map = [
        '정치'=>'politics','경제'=>'economy','사회'=>'society',
        '생활/문화'=>'lifestyle','생활_문화'=>'lifestyle',
        '세계'=>'world',
        'IT/과학'=>'tech','IT_과학'=>'tech',
        '부동산'=>'realestate',
        '헬스/건강'=>'health','헬스_건강'=>'health',
        '스포츠'=>'sports','연예'=>'entertainment','자동차'=>'auto','날씨'=>'weather',
        '가상화폐'=>'crypto','주식'=>'stock','육아'=>'parenting',
        '여행'=>'travel','게임'=>'game',
        '패션/뷰티'=>'fashion','패션_뷰티'=>'fashion',
        '음식/맛집'=>'food','음식_맛집'=>'food',
        '교육'=>'education','환경'=>'environment','법률'=>'law',
        '취업/직장'=>'jobs','취업_직장'=>'jobs',
        '반려동물'=>'pets','영화'=>'movies',
    ];
    return $map[$cat] ?? str_replace('/', '_', $cat);
}
