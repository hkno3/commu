<?php
function fetch_rss(string $url, string $cache_key, int $ttl = 43200): array {
    $cache_file = DATA_DIR . '/rss_' . $cache_key . '.json';
    if (file_exists($cache_file) && (time() - filemtime($cache_file)) < $ttl) {
        return json_decode(file_get_contents($cache_file), true) ?: [];
    }
    $items = [];
    try {
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT        => 8,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_USERAGENT      => 'Mozilla/5.0',
            CURLOPT_SSL_VERIFYPEER => false,
        ]);
        $raw = curl_exec($ch);
        curl_close($ch);
        if ($raw) {
            libxml_use_internal_errors(true);
            $xml = simplexml_load_string($raw, 'SimpleXMLElement', LIBXML_NOCDATA);
            if ($xml && isset($xml->channel->item)) {
                $i = 0;
                foreach ($xml->channel->item as $item) {
                    if ($i++ >= 5) break;
                    $items[] = [
                        'title' => html_entity_decode((string)$item->title, ENT_QUOTES, 'UTF-8'),
                        'link'  => (string)$item->link ?: '#',
                    ];
                }
            }
        }
    } catch (Exception $e) {}
    if ($items) @file_put_contents($cache_file, json_encode($items));
    return $items;
}
