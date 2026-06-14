-- Migration: add missing columns to article_cache
-- Run once in phpMyAdmin

ALTER TABLE `article_cache`
    ADD COLUMN IF NOT EXISTS `content`        MEDIUMTEXT        AFTER `summary`,
    ADD COLUMN IF NOT EXISTS `image_url`      VARCHAR(2048)     NOT NULL DEFAULT '' AFTER `content`,
    ADD COLUMN IF NOT EXISTS `original_url`   VARCHAR(2048)     NOT NULL DEFAULT '' AFTER `image_url`,
    ADD COLUMN IF NOT EXISTS `category_label` VARCHAR(50)       NOT NULL DEFAULT '' AFTER `category`,
    ADD COLUMN IF NOT EXISTS `article_type`   VARCHAR(30)       NOT NULL DEFAULT 'news' AFTER `category_label`;
