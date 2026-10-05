<?php

$method = $_SERVER['REQUEST_METHOD'] ?? '';
if ($method === 'GET') {
    header('Content-Type: text/html; charset=utf-8');
    readfile(__DIR__ . '/frontend.html');
    exit;
}
header('Content-Type: text/plain; charset=utf-8');
if ($method !== 'POST') {
    header('Allow: GET, POST');
    http_response_code(405);
    echo 'Method not allowed';
    exit;
}
$values = [];
foreach (['nome' => 50, 'email' => 50, 'comentario' => 100] as $field => $limit) {
    $value = $_POST[$field] ?? null;
    if (!is_string($value)) {
        http_response_code(422);
        echo 'Name, email and comment are required';
        exit;
    }
    $value = trim($value);
    if ($value === '' || preg_match('//u', $value) !== 1
        || preg_match_all('/./us', $value) > $limit) {
        http_response_code(422);
        echo 'Invalid field value or length';
        exit;
    }
    $values[$field] = $value;
}
if (filter_var($values['email'], FILTER_VALIDATE_EMAIL) === false) {
    http_response_code(422);
    echo 'Invalid email address';
    exit;
}
try {
    require __DIR__ . '/conexao.php';
    $id = random_int(1, 999);
    $statement = $link->prepare(
        'INSERT INTO mensagens (id, nome, email, comentario) VALUES (?, ?, ?, ?)'
    );
    $statement->bind_param('isss', $id, $values['nome'], $values['email'], $values['comentario']);
    $statement->execute();
    $statement->close();
    $link->close();
    echo 'New record created successfully';
} catch (Throwable $error) {
    error_log('Message persistence failed (' . get_class($error) . ')');
    http_response_code(503);
    echo 'Unable to save the message. Please try again later.';
}
