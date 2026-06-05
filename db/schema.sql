-- newscommu.com Database Schema
-- Run via install.php or manually in phpMyAdmin

SET NAMES utf8mb4;
SET time_zone = '+09:00';

-- ---------------------------------------------------------------------------
-- Comments
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `comments` (
    `id`          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    `article_id`  VARCHAR(64)     NOT NULL,
    `nickname`    VARCHAR(30)     NOT NULL DEFAULT '익명',
    `content`     TEXT            NOT NULL,
    `created_at`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `ip_hash`     VARCHAR(64)     NOT NULL DEFAULT '',
    PRIMARY KEY (`id`),
    KEY `idx_article_id` (`article_id`),
    KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Article cache (optional – used if you want DB-backed article search)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `article_cache` (
    `id`          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    `article_id`  VARCHAR(64)     NOT NULL,
    `title`       VARCHAR(500)    NOT NULL DEFAULT '',
    `summary`     TEXT,
    `url`         VARCHAR(2048)   NOT NULL DEFAULT '',
    `source`      VARCHAR(200)    NOT NULL DEFAULT '',
    `category`    VARCHAR(50)     NOT NULL DEFAULT '',
    `pub_date`    DATETIME,
    `created_at`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_article_id` (`article_id`),
    KEY `idx_category` (`category`),
    KEY `idx_pub_date` (`pub_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
