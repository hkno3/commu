<?php
$_body_codes_file = defined('DATA_DIR') ? DATA_DIR . '/body_codes.txt' : __DIR__ . '/../data/body_codes.txt';
if (file_exists($_body_codes_file)) {
    echo file_get_contents($_body_codes_file);
}
