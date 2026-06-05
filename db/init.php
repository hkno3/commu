<?php
/**
 * Database connection and bootstrap helper.
 */

require_once __DIR__ . '/../config.php';

function db_connect(): PDO {
    static $pdo = null;
    if ($pdo !== null) {
        return $pdo;
    }

    $dsn = sprintf(
        'mysql:host=%s;dbname=%s;charset=%s',
        DB_HOST, DB_NAME, DB_CHARSET
    );

    $options = [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES   => false,
    ];

    try {
        $pdo = new PDO($dsn, DB_USER, DB_PASS, $options);
    } catch (PDOException $e) {
        // Do not expose credentials in production
        http_response_code(500);
        die(json_encode(['error' => 'Database connection failed.']));
    }

    return $pdo;
}

/**
 * Run the schema SQL to create tables if they don't exist yet.
 */
function db_init_schema(): void {
    $pdo = db_connect();
    $sql = file_get_contents(__DIR__ . '/schema.sql');

    // Split on semicolons, ignoring blank statements
    $statements = array_filter(
        array_map('trim', explode(';', $sql)),
        fn($s) => $s !== ''
    );

    foreach ($statements as $stmt) {
        $pdo->exec($stmt);
    }
}
