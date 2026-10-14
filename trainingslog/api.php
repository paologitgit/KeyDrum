<?php
// Trainingslog – JSON-API (PHP 7.4+ / 8.x, PDO MySQL)
declare(strict_types=1);
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function out($data, int $status = 200): void {
    http_response_code($status);
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}
function fail(string $msg, int $status = 400): void { out(['error' => $msg], $status); }

$cfgFile = __DIR__ . '/config.php';
if (!is_file($cfgFile)) fail('config.php fehlt', 500);
$cfg = require $cfgFile;

if (!empty($cfg['app_token'])) {
    $token = $_SERVER['HTTP_X_TOKEN'] ?? '';
    if (!hash_equals((string)$cfg['app_token'], $token)) fail('Nicht autorisiert', 401);
}

try {
    $db = new PDO(
        "mysql:host={$cfg['db_host']};dbname={$cfg['db_name']};charset=utf8mb4",
        $cfg['db_user'], $cfg['db_pass'],
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC]
    );
} catch (PDOException $e) {
    fail('Datenbankverbindung fehlgeschlagen', 500);
}

$action = $_GET['action'] ?? '';
$in = json_decode(file_get_contents('php://input') ?: '{}', true) ?: [];
$isPost = $_SERVER['REQUEST_METHOD'] === 'POST';

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
    $sql = "SELECT s.exercise_id, w.id AS workout_id, w.workout_date, s.set_no, s.weight_kg, s.reps
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
        $res[$eid]['sets'][] = ['weight' => (float)$r['weight_kg'], 'reps' => $r['reps'] === null ? null : (int)$r['reps']];
    }
    return $res;
}

/** Bisheriges Höchstgewicht je Übung aus allen Trainings vor dem angegebenen Training. */
function previousBest(PDO $db, int $workoutId): array {
    $st = $db->prepare('SELECT s.exercise_id, MAX(s.weight_kg) AS best
                        FROM sets s JOIN workouts w ON w.id = s.workout_id
                        JOIN workouts cur ON cur.id = :id
                        WHERE w.workout_date < cur.workout_date
                           OR (w.workout_date = cur.workout_date AND w.id < cur.id)
                        GROUP BY s.exercise_id');
    $st->execute([':id' => $workoutId]);
    $res = [];
    foreach ($st as $r) $res[(int)$r['exercise_id']] = (float)$r['best'];
    return $res;
}

try {
    switch ($action) {
        case 'ping':
            out(['ok' => true]);

        case 'exercises':
            $where = empty($_GET['all']) ? 'WHERE active = 1' : '';
            $rows = $db->query("SELECT id, name, active FROM exercises $where ORDER BY sort_order, name")->fetchAll();
            out(array_map(fn($r) => ['id' => (int)$r['id'], 'name' => $r['name'], 'active' => (bool)$r['active']], $rows));

        case 'exercise_update':
            if (!$isPost) fail('POST erforderlich', 405);
            $id = intParam($in, 'id');
            if (array_key_exists('name', $in)) {
                $name = trim((string)$in['name']);
                if ($name === '' || mb_strlen($name) > 100) fail('Ungültiger Name');
                $dup = $db->prepare('SELECT id FROM exercises WHERE name = ? AND id <> ?');
                $dup->execute([$name, $id]);
                if ($dup->fetch()) fail('Diesen Namen gibt es bereits');
                $db->prepare('UPDATE exercises SET name = ? WHERE id = ?')->execute([$name, $id]);
            }
            if (array_key_exists('active', $in)) {
                $db->prepare('UPDATE exercises SET active = ? WHERE id = ?')->execute([$in['active'] ? 1 : 0, $id]);
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
            $st = $db->prepare('SELECT w.id AS workout_id, w.workout_date, s.weight_kg, s.reps
                                FROM sets s JOIN workouts w ON w.id = s.workout_id
                                WHERE s.exercise_id = ?
                                ORDER BY w.workout_date, w.id, s.set_no');
            $st->execute([$eid]);
            $res = [];
            foreach ($st as $r) {
                $wid = (int)$r['workout_id'];
                $res[$wid] ??= ['workout_id' => $wid, 'date' => $r['workout_date'], 'sets' => []];
                $res[$wid]['sets'][] = ['weight' => (float)$r['weight_kg'], 'reps' => $r['reps'] === null ? null : (int)$r['reps']];
            }
            out(array_values($res));

        case 'exercise_add':
            if (!$isPost) fail('POST erforderlich', 405);
            $name = trim((string)($in['name'] ?? ''));
            if ($name === '' || mb_strlen($name) > 100) fail('Ungültiger Name');
            $ex = $db->prepare('SELECT id, active FROM exercises WHERE name = ?');
            $ex->execute([$name]);
            if ($row = $ex->fetch()) {
                $db->prepare('UPDATE exercises SET active = 1 WHERE id = ?')->execute([$row['id']]);
                out(['id' => (int)$row['id'], 'name' => $name]);
            }
            $max = (int)$db->query('SELECT COALESCE(MAX(sort_order), 0) FROM exercises')->fetchColumn();
            $db->prepare('INSERT INTO exercises (name, sort_order) VALUES (?, ?)')->execute([$name, $max + 10]);
            out(['id' => (int)$db->lastInsertId(), 'name' => $name]);

        case 'workouts':
            $rows = $db->query(
                'SELECT w.id, w.workout_date, w.note, COUNT(s.id) AS set_count,
                        COUNT(DISTINCT s.exercise_id) AS exercise_count
                 FROM workouts w LEFT JOIN sets s ON s.workout_id = w.id
                 GROUP BY w.id ORDER BY w.workout_date DESC, w.id DESC LIMIT 200'
            )->fetchAll();
            out(array_map(fn($r) => [
                'id' => (int)$r['id'], 'date' => $r['workout_date'], 'note' => $r['note'],
                'set_count' => (int)$r['set_count'], 'exercise_count' => (int)$r['exercise_count'],
            ], $rows));

        case 'workout_create':
            if (!$isPost) fail('POST erforderlich', 405);
            $date = (string)($in['date'] ?? '');
            if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $date)) fail('Ungültiges Datum');
            $note = trim((string)($in['note'] ?? '')) ?: null;
            $db->prepare('INSERT INTO workouts (workout_date, note) VALUES (?, ?)')->execute([$date, $note]);
            out(['id' => (int)$db->lastInsertId()]);

        case 'workout':
            $id = intParam($_GET, 'id');
            $w = $db->prepare('SELECT id, workout_date, note FROM workouts WHERE id = ?');
            $w->execute([$id]);
            $wk = $w->fetch();
            if (!$wk) fail('Training nicht gefunden', 404);
            $st = $db->prepare('SELECT id, exercise_id, set_no, weight_kg, reps FROM sets WHERE workout_id = ? ORDER BY exercise_id, set_no');
            $st->execute([$id]);
            $sets = array_map(fn($r) => [
                'id' => (int)$r['id'], 'exercise_id' => (int)$r['exercise_id'], 'set_no' => (int)$r['set_no'],
                'weight' => (float)$r['weight_kg'], 'reps' => $r['reps'] === null ? null : (int)$r['reps'],
            ], $st->fetchAll());
            out([
                'id' => (int)$wk['id'], 'date' => $wk['workout_date'], 'note' => $wk['note'],
                'sets' => $sets, 'previous' => (object)previousSets($db, $id),
                'best' => (object)previousBest($db, $id),
            ]);

        case 'workout_update':
            if (!$isPost) fail('POST erforderlich', 405);
            $id = intParam($in, 'id');
            if (array_key_exists('note', $in)) {
                $note = trim((string)$in['note']);
                if (mb_strlen($note) > 255) fail('Notiz zu lang (max. 255 Zeichen)');
                $db->prepare('UPDATE workouts SET note = ? WHERE id = ?')->execute([$note === '' ? null : $note, $id]);
            }
            if (array_key_exists('date', $in)) {
                if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', (string)$in['date'])) fail('Ungültiges Datum');
                $db->prepare('UPDATE workouts SET workout_date = ? WHERE id = ?')->execute([$in['date'], $id]);
            }
            out(['ok' => true]);

        case 'workout_delete':
            if (!$isPost) fail('POST erforderlich', 405);
            $db->prepare('DELETE FROM workouts WHERE id = ?')->execute([intParam($in, 'id')]);
            out(['ok' => true]);

        case 'set_add':
            if (!$isPost) fail('POST erforderlich', 405);
            $wid = intParam($in, 'workout_id');
            $eid = intParam($in, 'exercise_id');
            if (!isset($in['weight']) || !is_numeric($in['weight']) || $in['weight'] < 0 || $in['weight'] > 9999) fail('Ungültiges Gewicht');
            $reps = (isset($in['reps']) && $in['reps'] !== '' && $in['reps'] !== null) ? (int)$in['reps'] : null;
            $db->beginTransaction();
            $n = $db->prepare('SELECT COALESCE(MAX(set_no), 0) + 1 FROM sets WHERE workout_id = ? AND exercise_id = ? FOR UPDATE');
            $n->execute([$wid, $eid]);
            $setNo = (int)$n->fetchColumn();
            $db->prepare('INSERT INTO sets (workout_id, exercise_id, set_no, weight_kg, reps) VALUES (?, ?, ?, ?, ?)')
               ->execute([$wid, $eid, $setNo, (float)$in['weight'], $reps]);
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
} catch (PDOException $e) {
    if ($db->inTransaction()) $db->rollBack();
    fail('Datenbankfehler', 500);
}
