<?php
$_head_codes_file = defined('DATA_DIR') ? DATA_DIR . '/head_codes.txt' : __DIR__ . '/../data/head_codes.txt';
if (file_exists($_head_codes_file)) {
    echo file_get_contents($_head_codes_file);
}
