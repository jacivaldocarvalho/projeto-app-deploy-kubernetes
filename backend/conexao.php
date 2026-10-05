<?php

mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);
$configuration = [];
foreach (['DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME'] as $variable) {
    $value = getenv($variable);
    if ($value === false || $value === '') {
        throw new RuntimeException('Missing database configuration');
    }
    $configuration[$variable] = $value;
}
// Criar conexão
$link = mysqli_init();
$link->options(MYSQLI_OPT_CONNECT_TIMEOUT, 3);
$link->options(MYSQLI_OPT_READ_TIMEOUT, 3);
$link->real_connect(
    $configuration['DB_HOST'],
    $configuration['DB_USER'],
    $configuration['DB_PASSWORD'],
    $configuration['DB_NAME']
);
$link->set_charset('utf8mb4');
