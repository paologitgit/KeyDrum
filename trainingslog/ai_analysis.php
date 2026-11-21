<?php
// Trainingslog – Trainingsauswertung mit Claude (offizielles Anthropic-PHP-SDK, PHP 8.2+).
// Wird nur von api.php geladen, wenn PHP-Version, SDK (claude/vendor) und API-Schlüssel vorhanden sind.
declare(strict_types=1);

require_once __DIR__ . '/claude/vendor/autoload.php';
require_once __DIR__ . '/ai_prompt.php';

use Anthropic\Client;
use Anthropic\Core\Exceptions\APIConnectionException;
use Anthropic\Core\Exceptions\APIStatusException;
use Anthropic\Core\Exceptions\APITimeoutException;
use Anthropic\Core\Exceptions\AuthenticationException;
use Anthropic\Core\Exceptions\OverloadedException;
use Anthropic\Core\Exceptions\PermissionDeniedException;
use Anthropic\Core\Exceptions\RateLimitException;

const AI_MODEL = 'claude-opus-5-5';


/**
 * Fragt Claude nach einer Auswertung. Rückgabe: ['text' => ...] oder ['error' => ...].
 */
function aiAnalysis(string $apiKey, string $prompt): array
{
    $client = new Client(apiKey: $apiKey, requestOptions: ['timeout' => 150, 'maxRetries' => 1]);
    try {
        $message = $client->beta->messages->create(
            model: AI_MODEL,
            maxTokens: 16000,
            system: AI_SYSTEM,
            messages: [['role' => 'user', 'content' => $prompt]],
            outputConfig: ['effort' => 'medium'],
            // Lehnt das Modell ab, versucht der Server es mit dem vorgesehenen Ersatzmodell
            fallbacks: 'default',
            betas: ['server-side-fallback-2026-07-01'],
        );
    } catch (AuthenticationException $e) {
        return ['error' => 'Der API-Schlüssel wurde abgelehnt. Bitte anthropic_api_key in config.php prüfen.'];
    } catch (PermissionDeniedException $e) {
        return ['error' => 'Der API-Schlüssel hat keine Berechtigung für dieses Modell.'];
    } catch (RateLimitException $e) {
        return ['error' => 'Zu viele Anfragen in kurzer Zeit. Bitte in einer Minute erneut versuchen.'];
    } catch (OverloadedException $e) {
        return ['error' => 'Claude ist gerade stark ausgelastet. Bitte etwas später erneut versuchen.'];
    } catch (APIStatusException $e) {
        if (($e->type?->value ?? '') === 'billing_error') {
            return ['error' => 'Für den API-Schlüssel ist kein Guthaben vorhanden. Bitte in der Claude Console Guthaben aufladen.'];
        }
        return ['error' => 'Die Claude-Schnittstelle meldet einen Fehler: ' . $e->getMessage()];
    } catch (APITimeoutException $e) {
        return ['error' => 'Claude hat nicht rechtzeitig geantwortet. Bitte einen kürzeren Zeitraum wählen oder erneut versuchen.'];
    } catch (APIConnectionException $e) {
        return ['error' => 'Keine Verbindung vom Server zu Claude (api.anthropic.com). Bitte beim Hoster prüfen, ob ausgehende Verbindungen erlaubt sind.'];
    }

    if ($message->stopReason === 'refusal') {
        return ['error' => 'Claude hat diese Auswertung abgelehnt. Bitte die Frage anders formulieren.'];
    }
    $text = '';
    foreach ($message->content as $block) {
        if ($block->type === 'text') {
            $text .= $block->text;
        }
    }
    if (trim($text) === '') {
        return ['error' => 'Claude hat keine Auswertung geliefert. Bitte erneut versuchen.'];
    }
    return [
        'text' => $text,
        'truncated' => $message->stopReason === 'max_tokens',
        'model' => $message->model,
        'usage' => ['input' => $message->usage->inputTokens, 'output' => $message->usage->outputTokens],
    ];
}
