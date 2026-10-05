<?php

header('Content-Type: text/plain; charset=utf-8');
header('Cache-Control: no-store');

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'GET') {
    header('Allow: GET');
    http_response_code(405);
    echo 'Method not allowed';
    exit;
}

try {
    require __DIR__ . '/conexao.php';
    $link->query('SELECT 1 FROM mensagens LIMIT 1');
    $link->close();
    echo 'Ready';
} catch (Throwable $error) {
    http_response_code(503);
    echo 'Not ready';
}
