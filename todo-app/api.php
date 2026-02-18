<?php
/**
 * Todo App - PHP Backend API
 * Connects the frontend to a MySQL database.
 *
 * Upload this file to your webserver in the same folder as index.html.
 */

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// Handle preflight requests
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

// ===================== DATABASE CONFIG =====================
// HIER DEINE METANET-DATEN EINTRAGEN:
$DB_HOST = 'localhost';          // Meist 'localhost' - steht in deinem metanet Control Panel
$DB_NAME = 'todo_app';          // Name deiner Datenbank (z.B. 'usr_todo' oder wie du sie nennst)
$DB_USER = 'dein_benutzer';     // Dein Datenbank-Benutzername (steht im Control Panel)
$DB_PASS = 'dein_passwort';     // Dein Datenbank-Passwort (steht im Control Panel)

// ===================== DATABASE CONNECTION =====================
try {
    $pdo = new PDO(
        "mysql:host=$DB_HOST;dbname=$DB_NAME;charset=utf8mb4",
        $DB_USER,
        $DB_PASS,
        [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false,
        ]
    );
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Datenbankverbindung fehlgeschlagen: ' . $e->getMessage()]);
    exit;
}

// ===================== ROUTING =====================
$method = $_SERVER['REQUEST_METHOD'];
$path = isset($_GET['action']) ? $_GET['action'] : '';
$input = json_decode(file_get_contents('php://input'), true);

// Routes:
// GET    ?action=groups          -> list groups
// POST   ?action=groups          -> create group
// PUT    ?action=group&id=X      -> update group
// DELETE ?action=group&id=X      -> delete group
// GET    ?action=tasks           -> list tasks with subtasks
// POST   ?action=tasks           -> create task
// PUT    ?action=task&id=X       -> update task
// DELETE ?action=task&id=X       -> delete task
// POST   ?action=reorder         -> reorder tasks

switch ($path) {

    // ===================== GROUPS =====================
    case 'groups':
        if ($method === 'GET') {
            $stmt = $pdo->query('SELECT * FROM `groups` ORDER BY sort_order, created_at');
            $groups = $stmt->fetchAll();
            echo json_encode($groups);
        } elseif ($method === 'POST') {
            if (empty($input['id']) || empty($input['name'])) {
                http_response_code(400);
                echo json_encode(['error' => 'id and name required']);
                exit;
            }
            $stmt = $pdo->query('SELECT COALESCE(MAX(sort_order), -1) + 1 AS next_order FROM `groups`');
            $nextOrder = $stmt->fetch()['next_order'];
            $stmt = $pdo->prepare('INSERT INTO `groups` (id, name, color, sort_order) VALUES (?, ?, ?, ?)');
            $stmt->execute([$input['id'], $input['name'], $input['color'] ?? '#6B8F71', $nextOrder]);
            echo json_encode(['success' => true, 'id' => $input['id']]);
        }
        break;

    case 'group':
        $id = $_GET['id'] ?? '';
        if (!$id) {
            http_response_code(400);
            echo json_encode(['error' => 'id required']);
            exit;
        }
        if ($method === 'PUT') {
            $fields = [];
            $values = [];
            if (isset($input['name'])) { $fields[] = 'name = ?'; $values[] = $input['name']; }
            if (isset($input['color'])) { $fields[] = 'color = ?'; $values[] = $input['color']; }
            if (empty($fields)) {
                echo json_encode(['error' => 'Nothing to update']);
                exit;
            }
            $values[] = $id;
            $stmt = $pdo->prepare('UPDATE `groups` SET ' . implode(', ', $fields) . ' WHERE id = ?');
            $stmt->execute($values);
            echo json_encode(['success' => true]);
        } elseif ($method === 'DELETE') {
            $pdo->prepare('UPDATE tasks SET group_id = NULL WHERE group_id = ?')->execute([$id]);
            $pdo->prepare('DELETE FROM `groups` WHERE id = ?')->execute([$id]);
            echo json_encode(['success' => true]);
        }
        break;

    // ===================== TASKS =====================
    case 'tasks':
        if ($method === 'GET') {
            $stmt = $pdo->query('SELECT * FROM tasks ORDER BY sort_order, created_at DESC');
            $tasks = $stmt->fetchAll();

            foreach ($tasks as &$task) {
                $stSub = $pdo->prepare('SELECT * FROM subtasks WHERE task_id = ? ORDER BY sort_order, id');
                $stSub->execute([$task['id']]);
                $task['subtasks'] = $stSub->fetchAll();

                // Convert for frontend
                $task['groupId'] = $task['group_id'];
                unset($task['group_id']);
                $task['dueDate'] = $task['due_date'] ?? '';
                unset($task['due_date']);
                $task['createdAt'] = $task['created_at'] ?? '';
                unset($task['created_at']);
                $task['completed'] = (bool)$task['completed'];
                $task['reminder'] = $task['reminder'] ?? '';

                foreach ($task['subtasks'] as &$st) {
                    $st['completed'] = (bool)$st['completed'];
                }
            }
            echo json_encode($tasks);
        } elseif ($method === 'POST') {
            if (empty($input['id']) || empty($input['title'])) {
                http_response_code(400);
                echo json_encode(['error' => 'id and title required']);
                exit;
            }
            $stmt = $pdo->query('SELECT COALESCE(MIN(sort_order), 1) - 1 AS next_order FROM tasks');
            $nextOrder = $stmt->fetch()['next_order'];

            $stmt = $pdo->prepare(
                'INSERT INTO tasks (id, title, description, group_id, due_date, reminder, completed, sort_order)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
            );
            $stmt->execute([
                $input['id'],
                $input['title'],
                $input['description'] ?? '',
                !empty($input['groupId']) ? $input['groupId'] : null,
                !empty($input['dueDate']) ? $input['dueDate'] : null,
                !empty($input['reminder']) ? $input['reminder'] : null,
                !empty($input['completed']) ? 1 : 0,
                $nextOrder,
            ]);

            // Insert subtasks
            if (!empty($input['subtasks'])) {
                $stSub = $pdo->prepare('INSERT INTO subtasks (task_id, title, completed, sort_order) VALUES (?, ?, ?, ?)');
                foreach ($input['subtasks'] as $i => $st) {
                    $stSub->execute([$input['id'], $st['title'], !empty($st['completed']) ? 1 : 0, $i]);
                }
            }
            echo json_encode(['success' => true, 'id' => $input['id']]);
        }
        break;

    case 'task':
        $id = $_GET['id'] ?? '';
        if (!$id) {
            http_response_code(400);
            echo json_encode(['error' => 'id required']);
            exit;
        }
        if ($method === 'PUT') {
            $fieldMap = [
                'title' => 'title',
                'description' => 'description',
                'groupId' => 'group_id',
                'dueDate' => 'due_date',
                'reminder' => 'reminder',
                'completed' => 'completed',
            ];
            $fields = [];
            $values = [];
            foreach ($fieldMap as $jsKey => $dbKey) {
                if (array_key_exists($jsKey, $input)) {
                    $val = $input[$jsKey];
                    if (in_array($jsKey, ['dueDate', 'reminder', 'groupId']) && $val === '') {
                        $val = null;
                    }
                    if ($jsKey === 'completed') {
                        $val = $val ? 1 : 0;
                    }
                    $fields[] = "$dbKey = ?";
                    $values[] = $val;
                }
            }
            if (!empty($fields)) {
                $values[] = $id;
                $stmt = $pdo->prepare('UPDATE tasks SET ' . implode(', ', $fields) . ' WHERE id = ?');
                $stmt->execute($values);
            }

            // Update subtasks if provided
            if (array_key_exists('subtasks', $input)) {
                $pdo->prepare('DELETE FROM subtasks WHERE task_id = ?')->execute([$id]);
                $stSub = $pdo->prepare('INSERT INTO subtasks (task_id, title, completed, sort_order) VALUES (?, ?, ?, ?)');
                foreach ($input['subtasks'] as $i => $st) {
                    $stSub->execute([$id, $st['title'], !empty($st['completed']) ? 1 : 0, $i]);
                }
            }
            echo json_encode(['success' => true]);
        } elseif ($method === 'DELETE') {
            // subtasks are cascade-deleted via FK
            $pdo->prepare('DELETE FROM tasks WHERE id = ?')->execute([$id]);
            echo json_encode(['success' => true]);
        }
        break;

    // ===================== REORDER =====================
    case 'reorder':
        if ($method === 'POST' && !empty($input['taskIds'])) {
            $stmt = $pdo->prepare('UPDATE tasks SET sort_order = ? WHERE id = ?');
            foreach ($input['taskIds'] as $i => $taskId) {
                $stmt->execute([$i, $taskId]);
            }
            if (!empty($input['movedTaskId']) && !empty($input['newGroupId'])) {
                $pdo->prepare('UPDATE tasks SET group_id = ? WHERE id = ?')
                    ->execute([$input['newGroupId'], $input['movedTaskId']]);
            }
            echo json_encode(['success' => true]);
        }
        break;

    default:
        http_response_code(404);
        echo json_encode(['error' => 'Unknown action']);
        break;
}
