<?php
// Trainingslog – Trainingsauswertung mit Claude (offizielles Anthropic-PHP-SDK, PHP 8.2+).
// Wird nur von api.php geladen, wenn PHP-Version, SDK (claude/vendor) und API-Schlüssel vorhanden sind.
declare(strict_types=1);

require_once __DIR__ . '/claude/vendor/autoload.php';

use Anthropic\Client;
use Anthropic\Core\Exceptions\APIConnectionException;
use Anthropic\Core\Exceptions\APIStatusException;
use Anthropic\Core\Exceptions\APITimeoutException;
use Anthropic\Core\Exceptions\AuthenticationException;
use Anthropic\Core\Exceptions\OverloadedException;
use Anthropic\Core\Exceptions\PermissionDeniedException;
use Anthropic\Core\Exceptions\RateLimitException;

const AI_MODEL = 'claude-opus-5-5';

const AI_SYSTEM = <<<'TXT'
Sie werten das persönliche Trainingstagebuch einer erwachsenen Person aus. Sie trainiert Kraft und Ausdauer und achtet besonders auf einen gesunden Rücken: Übungen, die den Rücken belasten, sind markiert, und pro Training kann ein Rückenbefinden von 0 (starke Beschwerden) bis 10 (beschwerdefrei) erfasst sein.

So schreiben Sie:
- Auf Deutsch, in der Höflichkeitsform (Sie), sachlich und freundlich – wie eine erfahrene Trainerin im Gespräch unter Erwachsenen, nicht belehrend.
- Stützen Sie jede Aussage auf die mitgelieferten Daten und nennen Sie dabei konkrete Zahlen (Sätze, Gewichte, Daten, Anteile). Wo die Daten für eine Aussage nicht reichen, sagen Sie das kurz, statt zu raten.
- Keine medizinischen Diagnosen. Deuten die Daten auf zunehmende oder anhaltende Beschwerden hin, empfehlen Sie in einem Satz eine Abklärung durch eine Fachperson; sonst nicht.
- Vorschläge sind konkret und umsetzbar (Übung, Satz- oder Wiederholungszahl, Häufigkeit) und passen zur Rückensituation.
- Umfang etwa 350 bis 600 Wörter.

Gliedern Sie mit diesen Markdown-Überschriften (## …) und verwenden Sie darunter Absätze oder Listen mit „- “; Hervorhebungen mit **…**; keine Tabellen:
## Kurzfazit
## Was gut läuft
## Balance und Bewegungsmuster
## Rücken
## Belastung und Erholung
## Vorschläge für die nächsten Wochen
Die letzte Überschrift enthält höchstens fünf Punkte. Beantworten Sie eine allfällige Frage der Person in dem Abschnitt, zu dem sie passt.
TXT;

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
