<?php
// Trainingslog – Prüfseite für die Einrichtung.
// Zeigt keine Passwörter oder Codes an. Nach erfolgreicher Prüfung darf die Datei gelöscht werden.
// Bewusst in einfacher PHP-Syntax geschrieben, damit sie auch auf alten PHP-Versionen läuft.

// Fehler direkt anzeigen statt einer leeren Seite
error_reporting(E_ALL);
ini_set('display_errors', '1');

if (isset($_GET['header'])) {
    // Test: kommt der Header X-Token beim Server an?
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(array('received' => isset($_SERVER['HTTP_X_TOKEN']) && $_SERVER['HTTP_X_TOKEN'] === 'test123'));
    exit;
}

$checks = array();
function check($label, $ok, $detail) {
    global $checks;
    $checks[] = array($label, $ok, $detail);
}

check('PHP-Version', version_compare(PHP_VERSION, '7.4.0', '>='),
      PHP_VERSION . (version_compare(PHP_VERSION, '7.4.0', '>=') ? '' : ' – mindestens 7.4 nötig (in der Hosting-Verwaltung umstellen)'));
// Version von api.php (muss zur index.html passen)
$apiSrc = @file_get_contents(dirname(__FILE__) . '/api.php');
$apiVer = ($apiSrc && preg_match('/const API_VERSION = (\d+);/', $apiSrc, $mm)) ? (int)$mm[1] : 0;
$htmlSrc = @file_get_contents(dirname(__FILE__) . '/index.html');
$needVer = ($htmlSrc && preg_match('/const API_VERSION_NEEDED = (\d+);/', $htmlSrc, $mm)) ? (int)$mm[1] : 0;
check('api.php', $apiVer >= $needVer && $apiVer > 0, $apiVer
    ? "Version $apiVer" . ($apiVer < $needVer ? " – index.html braucht Version $needVer: bitte die neue api.php hochladen" : '')
    : 'veraltet oder nicht gefunden – bitte die neue api.php hochladen');
check('PDO MySQL', extension_loaded('pdo_mysql'), extension_loaded('pdo_mysql') ? 'vorhanden' : 'fehlt – beim Hoster aktivieren');

$cfgFile = dirname(__FILE__) . '/config.php';
$cfg = null;
if (!is_file($cfgFile)) {
    check('config.php', false, 'nicht gefunden – config.sample.php als config.php speichern');
} else {
    $cfgError = '';
    try {
        $cfg = include $cfgFile;
    } catch (Exception $e) {
        $cfgError = 'Zeile ' . $e->getLine() . ': ' . $e->getMessage();
    } catch (Throwable $e) {   // PHP 7+: Syntaxfehler in config.php
        $cfgError = 'Zeile ' . $e->getLine() . ': ' . $e->getMessage();
    }
    if ($cfgError !== '') {
        check('config.php', false, 'enthält einen Fehler (' . htmlspecialchars($cfgError) . '). Häufige Ursachen: fehlendes Komma am Zeilenende, typografische Anführungszeichen „ “ ‘ ’ statt gerader \', fehlendes Semikolon nach ];');
        $cfg = null;
    } elseif (!is_array($cfg)) {
        check('config.php', false, 'kann nicht gelesen werden – Schreibweise prüfen (gerade Anführungszeichen \' verwenden, keine „typografischen“)');
        $cfg = null;
    } else {
        $missing = array();
        foreach (array('db_host', 'db_name', 'db_user', 'db_pass') as $k) if (!isset($cfg[$k])) $missing[] = $k;
        if ($missing) { check('config.php', false, 'es fehlen Einträge: ' . implode(', ', $missing)); $cfg = null; }
        else check('config.php', true, 'gefunden und lesbar');
    }
}

if ($cfg) {
    $tok = isset($cfg['app_token']) ? (string)$cfg['app_token'] : '';
    if (trim($tok) === '') {
        check('Zugangscode (app_token)', true, 'leer – die App fragt keinen Code ab');
    } elseif (trim($tok) === 'BITTE_AENDERN') {
        check('Zugangscode (app_token)', false, 'noch der Platzhalter BITTE_AENDERN – eigenen Code eintragen');
    } else {
        $d = 'gesetzt, ' . strlen(trim($tok)) . ' Zeichen';
        if ($tok !== trim($tok)) $d .= ' (Leerzeichen am Anfang/Ende werden ignoriert)';
        if (preg_match('/[^\x20-\x7E]/', $tok)) $d .= ' – enthält Umlaute oder Sonderzeichen; im Zweifel nur Buchstaben und Ziffern verwenden';
        check('Zugangscode (app_token)', true, $d);
    }

    if (!extension_loaded('pdo_mysql')) {
        check('Datenbankverbindung', false, 'nicht prüfbar, da PDO MySQL fehlt');
    } else try {
        $db = new PDO('mysql:host=' . $cfg['db_host'] . ';dbname=' . $cfg['db_name'] . ';charset=utf8mb4',
                      $cfg['db_user'], $cfg['db_pass'], array(PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION));
        check('Datenbankverbindung', true, 'Verbindung zu „' . htmlspecialchars($cfg['db_name']) . '“ ok');
        foreach (array('exercises', 'workouts', 'sets') as $t) {
            try {
                $n = $db->query("SELECT COUNT(*) FROM `$t`")->fetchColumn();
                check("Tabelle $t", true, "$n Einträge");
            } catch (PDOException $e) {
                check("Tabelle $t", false, 'fehlt – schema.sql importieren');
            }
        }
        // Stand der Datenbank (wird von api.php beim ersten Aufruf automatisch erweitert)
        $col = function ($t, $c) use ($db) { try { return (bool)$db->query("SHOW COLUMNS FROM `$t` LIKE " . $db->quote($c))->fetch(); } catch (Exception $e) { return false; } };
        $features = array(
            'Zeit-Übungen' => $col('exercises', 'mode'),
            'Trainingsdauer' => $col('workouts', 'start_time'),
            'Tagesform, Körpergewicht, Pläne' => $col('workouts', 'rpe'),
            'Ausdauer (Distanz)' => $col('sets', 'distance_km'),
        );
        $missing = array_keys(array_filter($features, function ($v) { return !$v; }));
        check('Datenbank-Stand', !$missing, $missing
            ? 'es fehlt: ' . implode(', ', $missing) . ' – die App einmal öffnen (api.php ergänzt das selbst) oder migrate.sql importieren'
            : 'aktuell');
        if ($features['Ausdauer (Distanz)']) {
            $cardio = $db->query("SELECT name, active FROM exercises WHERE mode = 'cardio' ORDER BY sort_order")->fetchAll(PDO::FETCH_ASSOC);
            $names = array_map(function ($r) { return htmlspecialchars($r['name']) . ($r['active'] ? '' : ' (ausgeblendet)'); }, $cardio);
            check('Ausdauer-Übungen', (bool)$cardio, $cardio ? implode(', ', $names) : 'keine – in der App unter „Übungen“ mit Art „Ausdauer“ anlegen');
        }
    } catch (PDOException $e) {
        check('Datenbankverbindung', false, 'fehlgeschlagen: ' . htmlspecialchars($e->getMessage()));
    }
}
?><!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Trainingslog – Prüfung</title>
<style>
  body { font: 15px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 16px; background: #f4f5f7; color: #16191d; }
  h1 { font-size: 19px; margin: 0 0 12px; }
  .item { background: #fff; border: 1px solid #e3e5e8; border-radius: 12px; padding: 10px 12px; margin-bottom: 8px; }
  .ok::before { content: "✔ "; color: #1b7f3b; font-weight: 700; }
  .bad::before { content: "✘ "; color: #c62828; font-weight: 700; }
  .d { color: #555; font-size: 14px; margin-top: 2px; word-break: break-word; }
  p { color: #555; font-size: 14px; }
</style>
</head>
<body>
<h1>Trainingslog – Prüfung</h1>
<?php foreach ($checks as $c): ?>
  <div class="item"><strong class="<?php echo $c[1] ? 'ok' : 'bad'; ?>"><?php echo $c[0]; ?></strong>
    <div class="d"><?php echo $c[2]; ?></div></div>
<?php endforeach; ?>
<div class="item"><strong id="h">Weitergabe des Zugangscodes</strong><div class="d" id="hd">wird geprüft …</div></div>
<p>Diese Seite zeigt keine Passwörter an. Nach der Prüfung können Sie check.php vom Server löschen.</p>
<script>
fetch('check.php?header=1', { headers: { 'X-Token': 'test123' } })
  .then(function (r) { return r.json(); })
  .then(function (d) {
    document.getElementById('h').className = 'ok';
    document.getElementById('hd').textContent = d.received
      ? 'ok – der Server empfängt den Code'
      : 'der Server filtert den Code heraus – die App weicht automatisch auf einen Ersatzweg aus';
  })
  .catch(function () { document.getElementById('h').className = 'bad'; document.getElementById('hd').textContent = 'Test fehlgeschlagen'; });
</script>
</body>
</html>
