<?php
// Trainingslog – Trainingsauswertung über OpenRouter (openrouter.ai).
// OpenRouter bietet viele KI-Modelle (Claude, GPT, Gemini u. a.) über eine gemeinsame Schnittstelle an.
// Kein SDK nötig: ein einfacher HTTPS-Aufruf mit cURL oder – falls cURL fehlt – mit file_get_contents.
declare(strict_types=1);

require_once __DIR__ . '/ai_prompt.php';

const OPENROUTER_DEFAULT_MODEL = 'anthropic/claude-opus-5.5';
const OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions';

/** Kann der Server ausgehende HTTPS-Anfragen stellen? */
function openRouterHttpAvailable(): bool
{
    return function_exists('curl_init') || filter_var(ini_get('allow_url_fopen'), FILTER_VALIDATE_BOOLEAN);
}

/**
 * Sendet einen POST mit JSON. Rückgabe: [HTTP-Status, Antworttext] oder [0, Fehlermeldung] bei Verbindungsfehlern.
 */
function openRouterPost(string $url, array $headers, string $body, int $timeout): array
{
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => $body,
            CURLOPT_HTTPHEADER => $headers,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_CONNECTTIMEOUT => 15,
            CURLOPT_TIMEOUT => $timeout,
        ]);
        $res = curl_exec($ch);
        if ($res === false) {
            $err = curl_errno($ch) === CURLE_OPERATION_TIMEDOUT ? 'timeout' : curl_error($ch);
            curl_close($ch);
            return [0, $err];
        }
        $status = (int)curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        curl_close($ch);
        return [$status, (string)$res];
    }
    $ctx = stream_context_create(['http' => [
        'method' => 'POST',
        'header' => implode("\r\n", $headers),
        'content' => $body,
        'timeout' => $timeout,
        'ignore_errors' => true,   // auch bei 4xx/5xx den Text der Antwort lesen
    ]]);
    $res = @file_get_contents($url, false, $ctx);
    if ($res === false) {
        $e = error_get_last();
        return [0, is_array($e) ? (string)$e['message'] : 'Verbindung fehlgeschlagen'];
    }
    $status = 0;
    foreach ($http_response_header ?? [] as $h) {
        if (preg_match('#^HTTP/\S+\s+(\d{3})#', $h, $m)) $status = (int)$m[1];
    }
    return [$status, (string)$res];
}

/**
 * Fragt das gewählte Modell über OpenRouter nach einer Auswertung.
 * Rückgabe: ['text' => ...] oder ['error' => ...].
 */
function aiAnalysisOpenRouter(string $apiKey, string $model, string $prompt, string $url = OPENROUTER_URL): array
{
    $model = trim($model) !== '' ? trim($model) : OPENROUTER_DEFAULT_MODEL;
    $body = json_encode([
        'model' => $model,
        'max_tokens' => 16000,
        'messages' => [
            ['role' => 'system', 'content' => AI_SYSTEM],
            ['role' => 'user', 'content' => $prompt],
        ],
        // Gründliches, aber nicht übermässig langes Nachdenken (Modelle ohne diese Option ignorieren es)
        'reasoning' => ['effort' => 'medium', 'exclude' => true],
    ], JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE);

    [$status, $raw] = openRouterPost($url, [
        'Content-Type: application/json',
        'Authorization: Bearer ' . $apiKey,
        'X-Title: Trainingslog',
    ], (string)$body, 150);

    if ($status === 0) {
        return ['error' => $raw === 'timeout' || stripos($raw, 'timed out') !== false
            ? 'Das Modell hat nicht rechtzeitig geantwortet. Bitte einen kürzeren Zeitraum wählen oder erneut versuchen.'
            : 'Keine Verbindung vom Server zu OpenRouter (openrouter.ai). Bitte beim Hoster prüfen, ob ausgehende Verbindungen erlaubt sind.'];
    }

    $data = json_decode($raw, true);
    $apiMsg = is_array($data) && isset($data['error']['message']) ? (string)$data['error']['message'] : '';
    $code = is_array($data) && isset($data['error']['code']) ? (int)$data['error']['code'] : $status;
    if ($status >= 400 || $apiMsg !== '') {
        switch ($code ?: $status) {
            case 401: return ['error' => 'Der OpenRouter-Schlüssel wurde abgelehnt. Bitte openrouter_api_key in config.php prüfen.'];
            case 402: return ['error' => 'Auf Ihrem OpenRouter-Konto ist zu wenig Guthaben. Bitte unter openrouter.ai bei „Credits“ aufladen.'];
            case 403: return ['error' => 'OpenRouter hat die Anfrage abgelehnt' . ($apiMsg !== '' ? ': ' . $apiMsg : '.')];
            case 404: return ['error' => "Das Modell „{$model}“ ist bei OpenRouter nicht verfügbar. Bitte openrouter_model in config.php prüfen (Liste: openrouter.ai/models)."];
            case 408: return ['error' => 'Das Modell hat nicht rechtzeitig geantwortet. Bitte einen kürzeren Zeitraum wählen oder erneut versuchen.'];
            case 429: return ['error' => 'Zu viele Anfragen in kurzer Zeit. Bitte in einer Minute erneut versuchen.'];
            case 502:
            case 503: return ['error' => 'Das Modell ist gerade nicht erreichbar oder ausgelastet. Bitte etwas später erneut versuchen.'];
        }
        if ($apiMsg !== '' && stripos($apiMsg, 'model') !== false && stripos($apiMsg, 'valid') !== false) {
            return ['error' => "Das Modell „{$model}“ kennt OpenRouter nicht. Bitte openrouter_model in config.php prüfen (Liste: openrouter.ai/models)."];
        }
        return ['error' => 'OpenRouter meldet einen Fehler' . ($apiMsg !== '' ? ': ' . $apiMsg : " (HTTP $status).")];
    }
    if (!is_array($data) || !isset($data['choices'][0])) {
        return ['error' => 'OpenRouter hat eine unerwartete Antwort geliefert. Bitte erneut versuchen.'];
    }

    $choice = $data['choices'][0];
    $content = $choice['message']['content'] ?? '';
    if (is_array($content)) {   // manche Modelle liefern Textteile als Liste
        $content = implode('', array_map(fn($p) => is_array($p) ? (string)($p['text'] ?? '') : (string)$p, $content));
    }
    $text = (string)$content;
    $finish = (string)($choice['finish_reason'] ?? '');
    if (trim($text) === '') {
        return ['error' => $finish === 'content_filter'
            ? 'Das Modell hat diese Auswertung abgelehnt. Bitte die Frage anders formulieren.'
            : 'Das Modell hat keine Auswertung geliefert. Bitte erneut versuchen.'];
    }
    return [
        'text' => $text,
        'truncated' => $finish === 'length',
        'model' => (string)($data['model'] ?? $model),
        'usage' => [
            'input' => (int)($data['usage']['prompt_tokens'] ?? 0),
            'output' => (int)($data['usage']['completion_tokens'] ?? 0),
        ],
    ];
}
