<?php
// Trainingslog – JSON-API (PHP 7.4+ / 8.x, PDO MySQL)
declare(strict_types=1);
// Körperbereiche für die Auswertung „Balance“
const AREAS = ['pull_v', 'pull_h', 'push_h', 'push_v', 'shoulder_arms', 'hinge', 'legs', 'core', 'relief', 'cardio', 'other'];
// Version der Schnittstelle – index.html prüft, ob der Server aktuell genug ist
const API_VERSION = 8;
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function out($data, int $status = 200): void {
    http_response_code($status);
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}
function fail(string $msg, int $status = 400): void { out(['error' => $msg], $status); }

// Schwere PHP-Fehler trotzdem als JSON melden, damit die App eine Meldung anzeigen kann
ini_set('display_errors', '0');
register_shutdown_function(function () {
    $e = error_get_last();
    if ($e && in_array($e['type'], [E_ERROR, E_PARSE, E_CORE_ERROR, E_COMPILE_ERROR], true)) {
        if (!headers_sent()) { http_response_code(500); header('Content-Type: application/json; charset=utf-8'); }
        echo json_encode(['error' => 'PHP-Fehler: ' . $e['message'] . ' (' . basename($e['file']) . ', Zeile ' . $e['line'] . ')'], JSON_UNESCAPED_UNICODE);
    }
});
// mbstring ist nicht auf jedem Hosting aktiv
function textLength(string $s): int { return function_exists('mb_strlen') ? mb_strlen($s) : (int)preg_match_all('/./us', $s); }

$cfgFile = __DIR__ . '/config.php';
if (!is_file($cfgFile)) fail('config.php fehlt', 500);
try {
    $cfg = require $cfgFile;
} catch (Throwable $e) {
    fail('config.php enthält einen Fehler in Zeile ' . $e->getLine() . ' – bitte check.php öffnen', 500);
}
if (!is_array($cfg)) fail('config.php ist unvollständig – bitte mit config.sample.php vergleichen', 500);
foreach (['db_host', 'db_name', 'db_user', 'db_pass'] as $k) {
    if (!isset($cfg[$k])) fail("In config.php fehlt der Eintrag '$k'", 500);
}

if (trim((string)($cfg['app_token'] ?? '')) !== '') {
    // Code kommt als Header X-Token; manche Hoster filtern eigene Header, daher Ersatz über ?t=
    $expected = trim((string)$cfg['app_token']);
    $token = trim((string)($_SERVER['HTTP_X_TOKEN'] ?? $_GET['t'] ?? ''));
    if ($token === '') out(['error' => 'Kein Zugangscode empfangen', 'reason' => 'missing'], 401);
    if (!hash_equals($expected, $token)) out(['error' => 'Zugangscode falsch', 'reason' => 'wrong'], 401);
}

try {
    $db = new PDO(
        "mysql:host={$cfg['db_host']};dbname={$cfg['db_name']};charset=utf8mb4",
        $cfg['db_user'], $cfg['db_pass'],
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC]
    );
} catch (PDOException $e) {
    fail('Datenbankverbindung fehlgeschlagen' . (!empty($cfg['debug']) ? ': ' . $e->getMessage() : ''), 500);
}

$action = $_GET['action'] ?? '';
$in = json_decode(file_get_contents('php://input') ?: '{}', true) ?: [];
$isPost = $_SERVER['REQUEST_METHOD'] === 'POST';

/**
 * Bestehende Datenbanken automatisch erweitern (Übungen mit Zeit statt Gewicht).
 * Läuft nur, solange die Spalte noch fehlt.
 */
function ensureSchema(PDO $db): void {
    $hasColumn = function (string $table, string $col) use ($db): bool {
        return (bool)$db->query("SHOW COLUMNS FROM `$table` LIKE " . $db->quote($col))->fetch();
    };
    try {
        $hasMode = $hasColumn('exercises', 'mode');
        $hasTimes = $hasColumn('workouts', 'start_time');
        $hasRpe = $hasColumn('workouts', 'rpe');
        $hasPlans = (bool)$db->query("SHOW TABLES LIKE 'plans'")->fetch();
        $hasDistance = $hasColumn('sets', 'distance_km');
        $hasBack = $hasColumn('exercises', 'back');
        $hasArea = $hasColumn('exercises', 'area');
    } catch (PDOException $e) {
        return; // Tabellen fehlen – wird später mit klarer Meldung gemeldet
    }
    try {
        if (!$hasMode) {
            $db->exec("ALTER TABLE exercises ADD COLUMN mode VARCHAR(10) NOT NULL DEFAULT 'weight' AFTER name");
            $db->exec('ALTER TABLE sets MODIFY weight_kg DECIMAL(6,2) NULL, ADD COLUMN duration_s INT UNSIGNED NULL AFTER reps');
        }
        if (!$hasTimes) {
            $db->exec('ALTER TABLE workouts ADD COLUMN start_time TIME NULL AFTER workout_date, ADD COLUMN end_time TIME NULL AFTER start_time');
        }
        if (!$hasRpe) {
            $db->exec('ALTER TABLE workouts ADD COLUMN rpe TINYINT UNSIGNED NULL, ADD COLUMN body_weight DECIMAL(5,2) NULL, ADD COLUMN plan_id INT UNSIGNED NULL');
        }
        if (!$hasDistance) {
            // Ausdauer: Distanz pro Eintrag, dazu die beiden Standard-Übungen
            $db->exec('ALTER TABLE sets ADD COLUMN distance_km DECIMAL(7,2) NULL AFTER duration_s');
            $max = (int)$db->query('SELECT COALESCE(MAX(sort_order), 0) FROM exercises')->fetchColumn();
            $db->prepare("INSERT IGNORE INTO exercises (name, mode, sort_order) VALUES ('Fahrradfahren', 'cardio', ?), ('Joggen', 'cardio', ?)")
               ->execute([$max + 10, $max + 20]);
        }
        if (!$hasArea) {
            // Körperbereich pro Übung (leer = App ordnet nach dem Namen zu) und Rückenbefinden pro Training
            $db->exec('ALTER TABLE exercises ADD COLUMN area VARCHAR(20) NULL AFTER back');
            $db->exec('ALTER TABLE workouts ADD COLUMN back_score TINYINT UNSIGNED NULL');
        }
        if (!$hasBack) {
            // Übungen mit Rücken-Belastung: moderatere Steigerungsvorschläge. Vorbelegung nach Namen.
            $db->exec('ALTER TABLE exercises ADD COLUMN back TINYINT(1) NOT NULL DEFAULT 0 AFTER mode');
            $db->exec("UPDATE exercises SET back = 1 WHERE mode = 'weight' AND (name LIKE '%dead%' OR name LIKE '%kreuzheb%' OR name LIKE '%lat%' OR name LIKE '%rudern%' OR name LIKE '%row%' OR name LIKE '%pull%' OR name LIKE '%klimm%' OR name LIKE 'rücken%' OR name LIKE '% rücken%' OR name LIKE '%butterfly reverse%' OR name LIKE '%reverse fly%' OR name LIKE '%hyperext%')");
        }
        if (!$hasPlans) {
            $db->exec("CREATE TABLE IF NOT EXISTS plans (
                id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
              ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");
            $db->exec("CREATE TABLE IF NOT EXISTS plan_exercises (
                plan_id INT UNSIGNED NOT NULL,
                exercise_id INT UNSIGNED NOT NULL,
                PRIMARY KEY (plan_id, exercise_id),
                CONSTRAINT fk_pe_plan FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
                CONSTRAINT fk_pe_exercise FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE
              ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");
        }
    } catch (PDOException $e) {
        fail('Die Datenbank konnte nicht automatisch erweitert werden. Bitte migrate.sql importieren.', 500);
    }
}

/** Uhrzeit "HH:MM" prüfen; leer = null. */
function timeParam($v): ?string {
    if ($v === null || $v === '') return null;
    if (!preg_match('/^([01]\d|2[0-3]):[0-5]\d$/', (string)$v)) fail('Ungültige Uhrzeit');
    return (string)$v;
}
function hm($t): ?string { return $t === null ? null : substr((string)$t, 0, 5); }

/** Tagesform 1–10 oder null. */
function rpeParam($v): ?int {
    if ($v === null || $v === '') return null;
    if (!is_numeric($v) || $v < 1 || $v > 10) fail('Tagesform muss zwischen 1 und 10 liegen');
    return (int)$v;
}
/** Körpergewicht in kg oder null. */
function bodyWeightParam($v): ?float {
    if ($v === null || $v === '') return null;
    if (!is_numeric($v) || $v <= 0 || $v >= 500) fail('Ungültiges Körpergewicht');
    return (float)$v;
}
function planIdParam($v): ?int { return ($v === null || $v === '' || (int)$v <= 0) ? null : (int)$v; }

/** Übungen eines Plans setzen (ersetzt die bisherige Auswahl). */
function setPlanExercises(PDO $db, int $planId, array $exerciseIds): void {
    $db->prepare('DELETE FROM plan_exercises WHERE plan_id = ?')->execute([$planId]);
    $ins = $db->prepare('INSERT IGNORE INTO plan_exercises (plan_id, exercise_id) VALUES (?, ?)');
    foreach (array_unique(array_map('intval', $exerciseIds)) as $eid) if ($eid > 0) $ins->execute([$planId, $eid]);
}

/**
 * Überblick über die letzten Trainings vor einem Training (oder die letzten überhaupt):
 * welche Übungen darin vorkamen und wann jede Übung zuletzt gemacht wurde.
 */
function recentInfo(PDO $db, ?int $beforeWorkoutId, int $n = 5): array {
    if ($beforeWorkoutId) {
        $st = $db->prepare('SELECT w.id, w.workout_date FROM workouts w JOIN workouts cur ON cur.id = :id
                            WHERE w.workout_date < cur.workout_date OR (w.workout_date = cur.workout_date AND w.id < cur.id)
                            ORDER BY w.workout_date DESC, w.id DESC LIMIT ' . $n);
        $st->execute([':id' => $beforeWorkoutId]);
    } else {
        $st = $db->query('SELECT id, workout_date FROM workouts ORDER BY workout_date DESC, id DESC LIMIT ' . $n);
    }
    $workouts = array_map(fn($r) => ['id' => (int)$r['id'], 'date' => $r['workout_date']], $st->fetchAll());
    $done = [];
    if ($workouts) {
        $ids = implode(',', array_map(fn($w) => $w['id'], $workouts));
        foreach ($db->query("SELECT DISTINCT workout_id, exercise_id FROM sets WHERE workout_id IN ($ids)") as $r) {
            $done[(int)$r['workout_id']][] = (int)$r['exercise_id'];
        }
    }
    // Letztes Datum je Übung (vor dem Training bzw. insgesamt)
    $sql = 'SELECT s.exercise_id, MAX(w.workout_date) AS last_date FROM sets s JOIN workouts w ON w.id = s.workout_id';
    if ($beforeWorkoutId) {
        $sql .= ' JOIN workouts cur ON cur.id = :id WHERE w.workout_date < cur.workout_date OR (w.workout_date = cur.workout_date AND w.id < cur.id)';
    }
    $st = $db->prepare($sql . ' GROUP BY s.exercise_id');
    $st->execute($beforeWorkoutId ? [':id' => $beforeWorkoutId] : []);
    $last = [];
    foreach ($st as $r) $last[(int)$r['exercise_id']] = $r['last_date'];
    foreach ($workouts as &$w) $w['exercises'] = $done[$w['id']] ?? [];
    return ['workouts' => $workouts, 'last' => (object)$last];
}
ensureSchema($db);

/** Einheitliches Format für einen Satz (Gewicht und/oder Zeit). */
function setRow(array $r): array {
    return [
        'weight'   => $r['weight_kg'] === null ? null : (float)$r['weight_kg'],
        'reps'     => $r['reps'] === null ? null : (int)$r['reps'],
        'duration' => $r['duration_s'] === null ? null : (int)$r['duration_s'],
        'distance' => ($r['distance_km'] ?? null) === null ? null : (float)$r['distance_km'],
    ];
}

function modeParam(array $src): string {
    $m = $src['mode'] ?? 'weight';
    return in_array($m, ['time', 'cardio'], true) ? $m : 'weight';
}

function intParam(array $src, string $key): int {
    if (!isset($src[$key]) || !is_numeric($src[$key])) fail("Parameter '$key' fehlt");
    return (int)$src[$key];
}

/** Sätze einer Übung aus dem letzten Training vor dem angegebenen Training. */
function previousSets(PDO $db, int $workoutId): array {
    $w = $db->prepare('SELECT workout_date FROM workouts WHERE id = ?');
    $w->execute([$workoutId]);
    $date = $w->fetchColumn();
    if ($date === false) fail('Training nicht gefunden', 404);

    // Pro Übung: das jüngste frühere Training, in dem sie vorkam.
    $sql = "SELECT s.exercise_id, w.id AS workout_id, w.workout_date, s.set_no, s.weight_kg, s.reps, s.duration_s
            FROM sets s
            JOIN workouts w ON w.id = s.workout_id
            WHERE w.id = (
                SELECT w2.id FROM sets s2 JOIN workouts w2 ON w2.id = s2.workout_id
                WHERE s2.exercise_id = s.exercise_id
                  AND (w2.workout_date < :d OR (w2.workout_date = :d2 AND w2.id < :id))
                ORDER BY w2.workout_date DESC, w2.id DESC LIMIT 1)
            ORDER BY s.exercise_id, s.set_no";
    $st = $db->prepare($sql);
    $st->execute([':d' => $date, ':d2' => $date, ':id' => $workoutId]);
    $res = [];
    foreach ($st as $r) {
        $eid = (int)$r['exercise_id'];
        $res[$eid] ??= ['date' => $r['workout_date'], 'sets' => []];
        $res[$eid]['sets'][] = setRow($r);
    }
    return $res;
}

/** Bisheriges Höchstgewicht und längste Zeit je Übung aus allen Trainings vor dem angegebenen Training. */
function previousBest(PDO $db, int $workoutId): array {
    $st = $db->prepare('SELECT s.exercise_id, MAX(s.weight_kg) AS best_w, MAX(s.duration_s) AS best_d
                        FROM sets s JOIN workouts w ON w.id = s.workout_id
                        JOIN workouts cur ON cur.id = :id
                        WHERE w.workout_date < cur.workout_date
                           OR (w.workout_date = cur.workout_date AND w.id < cur.id)
                        GROUP BY s.exercise_id');
    $st->execute([':id' => $workoutId]);
    $res = [];
    foreach ($st as $r) $res[(int)$r['exercise_id']] = [
        'weight'   => $r['best_w'] === null ? null : (float)$r['best_w'],
        'duration' => $r['best_d'] === null ? null : (int)$r['best_d'],
    ];
    return $res;
}

try {
    switch ($action) {
        case 'ping':
            out(['ok' => true, 'version' => API_VERSION]);

        case 'exercises':
            $where = empty($_GET['all']) ? 'WHERE active = 1' : '';
            $rows = $db->query("SELECT id, name, mode, active FROM exercises $where ORDER BY sort_order, name")->fetchAll();
            out(array_map(fn($r) => ['id' => (int)$r['id'], 'name' => $r['name'], 'mode' => $r['mode'], 'active' => (bool)$r['active']], $rows));

        case 'exercise_update':
            if (!$isPost) fail('POST erforderlich', 405);
            $id = intParam($in, 'id');
            if (array_key_exists('name', $in)) {
                $name = trim((string)$in['name']);
                if ($name === '' || textLength($name) > 100) fail('Ungültiger Name');
                $dup = $db->prepare('SELECT id FROM exercises WHERE name = ? AND id <> ?');
                $dup->execute([$name, $id]);
                if ($dup->fetch()) fail('Diesen Namen gibt es bereits');
                $db->prepare('UPDATE exercises SET name = ? WHERE id = ?')->execute([$name, $id]);
            }
            if (array_key_exists('active', $in)) {
                $db->prepare('UPDATE exercises SET active = ? WHERE id = ?')->execute([$in['active'] ? 1 : 0, $id]);
            }
            if (array_key_exists('mode', $in)) {
                $db->prepare('UPDATE exercises SET mode = ? WHERE id = ?')->execute([modeParam($in), $id]);
            }
            if (array_key_exists('area', $in)) {
                $area = in_array($in['area'], AREAS, true) ? $in['area'] : null;
                $db->prepare('UPDATE exercises SET area = ? WHERE id = ?')->execute([$area, $id]);
            }
            if (array_key_exists('back', $in)) {
                $db->prepare('UPDATE exercises SET back = ? WHERE id = ?')->execute([$in['back'] ? 1 : 0, $id]);
            }
            out(['ok' => true]);

        case 'exercise_reorder':
            if (!$isPost) fail('POST erforderlich', 405);
            $ids = $in['ids'] ?? null;
            if (!is_array($ids)) fail("Parameter 'ids' fehlt");
            $db->beginTransaction();
            $st = $db->prepare('UPDATE exercises SET sort_order = ? WHERE id = ?');
            foreach (array_values($ids) as $i => $eid) $st->execute([($i + 1) * 10, (int)$eid]);
            $db->commit();
            out(['ok' => true]);

        case 'history':
            $eid = intParam($_GET, 'exercise_id');
            $st = $db->prepare('SELECT w.id AS workout_id, w.workout_date, s.weight_kg, s.reps, s.duration_s
                                FROM sets s JOIN workouts w ON w.id = s.workout_id
                                WHERE s.exercise_id = ?
                                ORDER BY w.workout_date, w.id, s.set_no');
            $st->execute([$eid]);
            $res = [];
            foreach ($st as $r) {
                $wid = (int)$r['workout_id'];
                $res[$wid] ??= ['workout_id' => $wid, 'date' => $r['workout_date'], 'sets' => []];
                $res[$wid]['sets'][] = setRow($r);
            }
            out(array_values($res));

        case 'exercise_add':
            if (!$isPost) fail('POST erforderlich', 405);
            $name = trim((string)($in['name'] ?? ''));
            if ($name === '' || textLength($name) > 100) fail('Ungültiger Name');
            $mode = modeParam($in);
            $ex = $db->prepare('SELECT id, mode FROM exercises WHERE name = ?');
            $ex->execute([$name]);
            if ($row = $ex->fetch()) {
                $db->prepare('UPDATE exercises SET active = 1 WHERE id = ?')->execute([$row['id']]);
                out(['id' => (int)$row['id'], 'name' => $name, 'mode' => $row['mode']]);
            }
            $max = (int)$db->query('SELECT COALESCE(MAX(sort_order), 0) FROM exercises')->fetchColumn();
            $db->prepare('INSERT INTO exercises (name, mode, back, sort_order) VALUES (?, ?, ?, ?)')->execute([$name, $mode, empty($in['back']) ? 0 : 1, $max + 10]);
            out(['id' => (int)$db->lastInsertId(), 'name' => $name, 'mode' => $mode]);

        case 'workouts':
            // Unterabfragen statt GROUP BY: funktioniert auch mit sql_mode ONLY_FULL_GROUP_BY (z. B. MariaDB)
            $rows = $db->query(
                'SELECT w.id, w.workout_date, w.note, w.start_time, w.end_time,
                        (SELECT COUNT(*) FROM sets s WHERE s.workout_id = w.id) AS set_count,
                        (SELECT COUNT(DISTINCT s.exercise_id) FROM sets s WHERE s.workout_id = w.id) AS exercise_count
                 FROM workouts w ORDER BY w.workout_date DESC, w.id DESC LIMIT 200'
            )->fetchAll();
            out(array_map(fn($r) => [
                'id' => (int)$r['id'], 'date' => $r['workout_date'], 'note' => $r['note'],
                'start_time' => hm($r['start_time']), 'end_time' => hm($r['end_time']),
                'set_count' => (int)$r['set_count'], 'exercise_count' => (int)$r['exercise_count'],
            ], $rows));

        case 'workout_create':
            if (!$isPost) fail('POST erforderlich', 405);
            $date = (string)($in['date'] ?? '');
            if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $date)) fail('Ungültiges Datum');
            $note = trim((string)($in['note'] ?? '')) ?: null;
            $db->prepare('INSERT INTO workouts (workout_date, start_time, note, plan_id) VALUES (?, ?, ?, ?)')
               ->execute([$date, timeParam($in['start_time'] ?? null), $note, planIdParam($in['plan_id'] ?? null)]);
            out(['id' => (int)$db->lastInsertId()]);

        case 'workout':
            $id = intParam($_GET, 'id');
            $w = $db->prepare('SELECT id, workout_date, start_time, end_time, note FROM workouts WHERE id = ?');
            $w->execute([$id]);
            $wk = $w->fetch();
            if (!$wk) fail('Training nicht gefunden', 404);
            $st = $db->prepare('SELECT id, exercise_id, set_no, weight_kg, reps, duration_s FROM sets WHERE workout_id = ? ORDER BY exercise_id, set_no');
            $st->execute([$id]);
            $sets = array_map(fn($r) => [
                'id' => (int)$r['id'], 'exercise_id' => (int)$r['exercise_id'], 'set_no' => (int)$r['set_no'],
            ] + setRow($r), $st->fetchAll());
            out([
                'id' => (int)$wk['id'], 'date' => $wk['workout_date'], 'note' => $wk['note'],
                'start_time' => hm($wk['start_time']), 'end_time' => hm($wk['end_time']),
                'recent' => recentInfo($db, $id),
                'sets' => $sets, 'previous' => (object)previousSets($db, $id),
                'best' => (object)previousBest($db, $id),
            ]);

        case 'workout_update':
            if (!$isPost) fail('POST erforderlich', 405);
            $id = intParam($in, 'id');
            if (array_key_exists('note', $in)) {
                $note = trim((string)$in['note']);
                if (textLength($note) > 255) fail('Notiz zu lang (max. 255 Zeichen)');
                $db->prepare('UPDATE workouts SET note = ? WHERE id = ?')->execute([$note === '' ? null : $note, $id]);
            }
            foreach (['start_time', 'end_time'] as $k) {
                if (array_key_exists($k, $in)) {
                    $db->prepare("UPDATE workouts SET $k = ? WHERE id = ?")->execute([timeParam($in[$k]), $id]);
                }
            }
            if (array_key_exists('back_score', $in)) {
                $bs = $in['back_score'];
                if ($bs !== null && $bs !== '' && (!is_numeric($bs) || $bs < 0 || $bs > 10)) fail('Rückenbefinden muss zwischen 0 und 10 liegen');
                $db->prepare('UPDATE workouts SET back_score = ? WHERE id = ?')->execute([($bs === null || $bs === '') ? null : (int)$bs, $id]);
            }
            if (array_key_exists('rpe', $in)) $db->prepare('UPDATE workouts SET rpe = ? WHERE id = ?')->execute([rpeParam($in['rpe']), $id]);
            if (array_key_exists('body_weight', $in)) $db->prepare('UPDATE workouts SET body_weight = ? WHERE id = ?')->execute([bodyWeightParam($in['body_weight']), $id]);
            if (array_key_exists('plan_id', $in)) $db->prepare('UPDATE workouts SET plan_id = ? WHERE id = ?')->execute([planIdParam($in['plan_id']), $id]);
            if (array_key_exists('date', $in)) {
                if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', (string)$in['date'])) fail('Ungültiges Datum');
                $db->prepare('UPDATE workouts SET workout_date = ? WHERE id = ?')->execute([$in['date'], $id]);
            }
            out(['ok' => true]);

        case 'snapshot':
            // Alle Daten auf einmal – Grundlage für den Offline-Modus der App
            $ex = $db->query('SELECT id, name, mode, back, area, active FROM exercises ORDER BY sort_order, name')->fetchAll();
            $wk = $db->query('SELECT id, workout_date, start_time, end_time, note, rpe, back_score, body_weight, plan_id FROM workouts')->fetchAll();
            $st = $db->query('SELECT id, workout_id, exercise_id, set_no, weight_kg, reps, duration_s, distance_km FROM sets')->fetchAll();
            $pl = $db->query('SELECT id, name FROM plans ORDER BY name')->fetchAll();
            $pe = [];
            foreach ($db->query('SELECT plan_id, exercise_id FROM plan_exercises') as $r) $pe[(int)$r['plan_id']][] = (int)$r['exercise_id'];
            out([
                'exercises' => array_map(fn($r) => ['id' => (int)$r['id'], 'name' => $r['name'], 'mode' => $r['mode'], 'back' => (bool)$r['back'], 'area' => $r['area'], 'active' => (bool)$r['active']], $ex),
                'workouts' => array_map(fn($r) => [
                    'id' => (int)$r['id'], 'date' => $r['workout_date'], 'start_time' => hm($r['start_time']), 'end_time' => hm($r['end_time']),
                    'note' => $r['note'], 'rpe' => $r['rpe'] === null ? null : (int)$r['rpe'],
                    'back_score' => $r['back_score'] === null ? null : (int)$r['back_score'],
                    'body_weight' => $r['body_weight'] === null ? null : (float)$r['body_weight'],
                    'plan_id' => $r['plan_id'] === null ? null : (int)$r['plan_id'],
                ], $wk),
                'sets' => array_map(fn($r) => [
                    'id' => (int)$r['id'], 'workout_id' => (int)$r['workout_id'], 'exercise_id' => (int)$r['exercise_id'], 'set_no' => (int)$r['set_no'],
                ] + setRow($r), $st),
                'plans' => array_map(fn($r) => ['id' => (int)$r['id'], 'name' => $r['name'], 'exercises' => $pe[(int)$r['id']] ?? []], $pl),
            ]);

        case 'plan_create':
            if (!$isPost) fail('POST erforderlich', 405);
            $name = trim((string)($in['name'] ?? ''));
            if ($name === '' || textLength($name) > 100) fail('Ungültiger Planname');
            $db->beginTransaction();
            $db->prepare('INSERT INTO plans (name) VALUES (?)')->execute([$name]);
            $pid = (int)$db->lastInsertId();
            setPlanExercises($db, $pid, (array)($in['exercises'] ?? []));
            $db->commit();
            out(['id' => $pid]);

        case 'plan_update':
            if (!$isPost) fail('POST erforderlich', 405);
            $pid = intParam($in, 'id');
            $db->beginTransaction();
            if (array_key_exists('name', $in)) {
                $name = trim((string)$in['name']);
                if ($name === '' || textLength($name) > 100) fail('Ungültiger Planname');
                $db->prepare('UPDATE plans SET name = ? WHERE id = ?')->execute([$name, $pid]);
            }
            if (array_key_exists('exercises', $in)) setPlanExercises($db, $pid, (array)$in['exercises']);
            $db->commit();
            out(['ok' => true]);

        case 'plan_delete':
            if (!$isPost) fail('POST erforderlich', 405);
            $pid = intParam($in, 'id');
            $db->prepare('UPDATE workouts SET plan_id = NULL WHERE plan_id = ?')->execute([$pid]);
            $db->prepare('DELETE FROM plans WHERE id = ?')->execute([$pid]);
            out(['ok' => true]);

        case 'overview':
            out(recentInfo($db, null));

        case 'workout_delete':
            if (!$isPost) fail('POST erforderlich', 405);
            $db->prepare('DELETE FROM workouts WHERE id = ?')->execute([intParam($in, 'id')]);
            out(['ok' => true]);

        case 'set_add':
            if (!$isPost) fail('POST erforderlich', 405);
            $wid = intParam($in, 'workout_id');
            $eid = intParam($in, 'exercise_id');
            $has = fn($k) => isset($in[$k]) && $in[$k] !== '' && $in[$k] !== null;
            $weight = $has('weight') ? $in['weight'] : null;
            $duration = $has('duration') ? $in['duration'] : null;
            $distance = $has('distance') ? $in['distance'] : null;
            if ($weight === null && $duration === null && $distance === null) fail('Bitte Gewicht, Zeit oder Distanz angeben');
            if ($distance !== null && (!is_numeric($distance) || $distance < 0 || $distance > 99999)) fail('Ungültige Distanz');
            if ($weight !== null && (!is_numeric($weight) || $weight < 0 || $weight > 9999)) fail('Ungültiges Gewicht');
            if ($duration !== null && (!is_numeric($duration) || $duration <= 0 || $duration > 86400)) fail('Ungültige Zeit');
            $reps = $has('reps') ? (int)$in['reps'] : null;
            if ($reps !== null && ($reps < 0 || $reps > 1000)) fail('Ungültige Wiederholungen');
            $db->beginTransaction();
            $n = $db->prepare('SELECT COALESCE(MAX(set_no), 0) + 1 FROM sets WHERE workout_id = ? AND exercise_id = ? FOR UPDATE');
            $n->execute([$wid, $eid]);
            $setNo = (int)$n->fetchColumn();
            $db->prepare('INSERT INTO sets (workout_id, exercise_id, set_no, weight_kg, reps, duration_s, distance_km) VALUES (?, ?, ?, ?, ?, ?, ?)')
               ->execute([$wid, $eid, $setNo, $weight === null ? null : (float)$weight, $reps,
                          $duration === null ? null : (int)$duration, $distance === null ? null : (float)$distance]);
            $id = (int)$db->lastInsertId();
            $db->commit();
            out(['id' => $id, 'set_no' => $setNo]);

        case 'set_delete':
            if (!$isPost) fail('POST erforderlich', 405);
            $db->prepare('DELETE FROM sets WHERE id = ?')->execute([intParam($in, 'id')]);
            out(['ok' => true]);

        default:
            fail('Unbekannte Aktion');
    }
} catch (Throwable $e) {
    if ($db->inTransaction()) $db->rollBack();
    if (!$e instanceof PDOException) fail('Serverfehler: ' . $e->getMessage(), 500);
    $msg = $e->getMessage();
    if (stripos($msg, "doesn't exist") !== false) fail('Datenbanktabellen fehlen – bitte schema.sql importieren', 500);
    fail(!empty($cfg['debug']) ? "Datenbankfehler: $msg" : 'Datenbankfehler', 500);
}
