<?php
// Приём сообщений «Сообщить о неточности».
// Каждое сообщение дописывается в файл ~/atlas-feedback.log (вне папки сайта, посетителям не виден).
// Если в файле ~/atlas-feedback.ini есть строка email = адрес, копия уходит на эту почту.
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
function reply($code, $msg) { http_response_code($code); echo json_encode(['ok' => $code === 200, 'message' => $msg], JSON_UNESCAPED_UNICODE); exit; }

if ($_SERVER['REQUEST_METHOD'] !== 'POST') reply(405, 'Нужен POST-запрос');
$raw = file_get_contents('php://input', false, null, 0, 20000);
$in = json_decode($raw, true);
if (!is_array($in)) reply(400, 'Неверный формат');
if (!empty($in['website'])) reply(200, 'ok'); // ловушка для ботов: поле скрыто от людей

$clip = function ($v, $n) { $v = is_string($v) ? trim(preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', $v)) : ''; return mb_substr($v, 0, $n); };
$msg = $clip($in['message'] ?? '', 2000);
if (mb_strlen($msg) < 3) reply(400, 'Опишите, что не так');
$item = [
  'at' => date('c'),
  'message' => $msg,
  'source' => $clip($in['source'] ?? '', 300),
  'contact' => $clip($in['contact'] ?? '', 120),
  'context' => $clip($in['context'] ?? '', 300),
  'page' => $clip($in['page'] ?? '', 300),
];

$home = dirname(__DIR__, 2);
// не больше 5 сообщений в час с одного адреса
$tmp = sys_get_temp_dir() . '/atlas-fb-' . md5(($_SERVER['REMOTE_ADDR'] ?? '') . 'atlas');
$hits = array_filter(explode("\n", (string) @file_get_contents($tmp)), function ($t) { return $t && $t > time() - 3600; });
if (count($hits) >= 5) reply(429, 'Слишком много сообщений, попробуйте через час');
$hits[] = time();
@file_put_contents($tmp, implode("\n", $hits));

$ok = @file_put_contents($home . '/atlas-feedback.log', json_encode($item, JSON_UNESCAPED_UNICODE) . "\n", FILE_APPEND | LOCK_EX);
if ($ok === false) reply(500, 'Не удалось сохранить сообщение');

$cfg = @parse_ini_file($home . '/atlas-feedback.ini');
$to = is_array($cfg) ? trim($cfg['email'] ?? '') : '';
if ($to && filter_var($to, FILTER_VALIDATE_EMAIL)) {
  $host = preg_replace('/[^a-z0-9.\-]/i', '', $_SERVER['HTTP_HOST'] ?? 'earthatlas.ru');
  $text = "Сообщение о неточности на карте\n\n{$item['message']}\n\nИсточник: {$item['source']}\nКонтакт: {$item['contact']}\nГде на карте: {$item['context']}\nСтраница: {$item['page']}\nВремя: {$item['at']}\n";
  $headers = "From: Атлас мира <noreply@{$host}>\r\nContent-Type: text/plain; charset=utf-8\r\n";
  if (filter_var($item['contact'], FILTER_VALIDATE_EMAIL)) $headers .= "Reply-To: {$item['contact']}\r\n";
  @mail($to, '=?UTF-8?B?' . base64_encode('Атлас мира: сообщение о неточности') . '?=', $text, $headers);
}
reply(200, 'ok');
