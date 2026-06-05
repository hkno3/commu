<?php
/**
 * newscommu.com - Site Configuration
 * Fill in your actual credentials before deploying.
 */

// ---------------------------------------------------------------------------
// Database
// ---------------------------------------------------------------------------
define('DB_HOST', getenv('DB_HOST') ?: 'localhost');
define('DB_NAME', getenv('DB_NAME') ?: 'newscommu');
define('DB_USER', getenv('DB_USER') ?: 'db_user');
define('DB_PASS', getenv('DB_PASS') ?: 'db_password');
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
