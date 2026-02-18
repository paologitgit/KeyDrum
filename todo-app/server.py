#!/usr/bin/env python3
"""Flask backend for the Todo App with MySQL database."""

import os
import pymysql
import pymysql.cursors
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# ===================== DATABASE CONFIG =====================
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'todoapp'),
    'password': os.environ.get('DB_PASSWORD', 'todoapp123'),
    'database': os.environ.get('DB_NAME', 'todo_app'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}


def get_db():
    """Create a new database connection."""
    return pymysql.connect(**DB_CONFIG)


# ===================== SERVE FRONTEND =====================
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')


# ===================== GROUPS API =====================
@app.route('/api/groups', methods=['GET'])
def get_groups():
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute('SELECT * FROM `groups` ORDER BY sort_order, created_at')
            groups = cursor.fetchall()
            # Convert datetime objects to strings
            for g in groups:
                if g.get('created_at'):
                    g['created_at'] = g['created_at'].isoformat()
        return jsonify(groups)
    finally:
        db.close()


@app.route('/api/groups', methods=['POST'])
def create_group():
    data = request.get_json()
    if not data or not data.get('id') or not data.get('name'):
        return jsonify({'error': 'id and name are required'}), 400

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                'SELECT COALESCE(MAX(sort_order), -1) + 1 AS next_order FROM `groups`'
            )
            next_order = cursor.fetchone()['next_order']
            cursor.execute(
                'INSERT INTO `groups` (id, name, color, sort_order) VALUES (%s, %s, %s, %s)',
                (data['id'], data['name'], data.get('color', '#6B8F71'), next_order)
            )
        db.commit()
        return jsonify({'success': True, 'id': data['id']}), 201
    finally:
        db.close()


@app.route('/api/groups/<group_id>', methods=['PUT'])
def update_group(group_id):
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    db = get_db()
    try:
        with db.cursor() as cursor:
            fields = []
            values = []
            if 'name' in data:
                fields.append('name = %s')
                values.append(data['name'])
            if 'color' in data:
                fields.append('color = %s')
                values.append(data['color'])
            if not fields:
                return jsonify({'error': 'Nothing to update'}), 400
            values.append(group_id)
            cursor.execute(
                f'UPDATE `groups` SET {", ".join(fields)} WHERE id = %s',
                values
            )
        db.commit()
        return jsonify({'success': True})
    finally:
        db.close()


@app.route('/api/groups/<group_id>', methods=['DELETE'])
def delete_group(group_id):
    db = get_db()
    try:
        with db.cursor() as cursor:
            # Set tasks in this group to have no group
            cursor.execute('UPDATE tasks SET group_id = NULL WHERE group_id = %s', (group_id,))
            cursor.execute('DELETE FROM `groups` WHERE id = %s', (group_id,))
        db.commit()
        return jsonify({'success': True})
    finally:
        db.close()


# ===================== TASKS API =====================
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute('SELECT * FROM tasks ORDER BY sort_order, created_at DESC')
            tasks = cursor.fetchall()

            # Fetch subtasks for each task
            for task in tasks:
                cursor.execute(
                    'SELECT * FROM subtasks WHERE task_id = %s ORDER BY sort_order, id',
                    (task['id'],)
                )
                task['subtasks'] = cursor.fetchall()
                # Convert date/datetime to string
                if task.get('due_date'):
                    task['due_date'] = task['due_date'].isoformat()
                else:
                    task['due_date'] = ''
                if task.get('reminder'):
                    task['reminder'] = task['reminder'].isoformat()
                else:
                    task['reminder'] = ''
                if task.get('created_at'):
                    task['created_at'] = task['created_at'].isoformat()
                # Convert boolean
                task['completed'] = bool(task['completed'])
                for st in task['subtasks']:
                    st['completed'] = bool(st['completed'])
                # Map DB field names to frontend field names
                task['groupId'] = task.pop('group_id')
                task['dueDate'] = task.pop('due_date')
                task['createdAt'] = task.pop('created_at')
        return jsonify(tasks)
    finally:
        db.close()


@app.route('/api/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    if not data or not data.get('id') or not data.get('title'):
        return jsonify({'error': 'id and title are required'}), 400

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                'SELECT COALESCE(MIN(sort_order), 1) - 1 AS next_order FROM tasks'
            )
            next_order = cursor.fetchone()['next_order']
            cursor.execute(
                '''INSERT INTO tasks (id, title, description, group_id, due_date, reminder, completed, sort_order)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
                (
                    data['id'],
                    data['title'],
                    data.get('description', ''),
                    data.get('groupId') or None,
                    data.get('dueDate') or None,
                    data.get('reminder') or None,
                    data.get('completed', False),
                    next_order,
                )
            )
            # Insert subtasks if provided
            for i, st in enumerate(data.get('subtasks', [])):
                cursor.execute(
                    'INSERT INTO subtasks (task_id, title, completed, sort_order) VALUES (%s, %s, %s, %s)',
                    (data['id'], st['title'], st.get('completed', False), i)
                )
        db.commit()
        return jsonify({'success': True, 'id': data['id']}), 201
    finally:
        db.close()


@app.route('/api/tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    db = get_db()
    try:
        with db.cursor() as cursor:
            fields = []
            values = []
            field_map = {
                'title': 'title',
                'description': 'description',
                'groupId': 'group_id',
                'dueDate': 'due_date',
                'reminder': 'reminder',
                'completed': 'completed',
            }
            for js_key, db_key in field_map.items():
                if js_key in data:
                    val = data[js_key]
                    if js_key in ('dueDate', 'reminder') and val == '':
                        val = None
                    if js_key == 'groupId' and val == '':
                        val = None
                    fields.append(f'{db_key} = %s')
                    values.append(val)

            if fields:
                values.append(task_id)
                cursor.execute(
                    f'UPDATE tasks SET {", ".join(fields)} WHERE id = %s',
                    values
                )

            # Update subtasks if provided
            if 'subtasks' in data:
                cursor.execute('DELETE FROM subtasks WHERE task_id = %s', (task_id,))
                for i, st in enumerate(data['subtasks']):
                    cursor.execute(
                        'INSERT INTO subtasks (task_id, title, completed, sort_order) VALUES (%s, %s, %s, %s)',
                        (task_id, st['title'], st.get('completed', False), i)
                    )
        db.commit()
        return jsonify({'success': True})
    finally:
        db.close()


@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    db = get_db()
    try:
        with db.cursor() as cursor:
            # subtasks cascade-deleted via FK
            cursor.execute('DELETE FROM tasks WHERE id = %s', (task_id,))
        db.commit()
        return jsonify({'success': True})
    finally:
        db.close()


@app.route('/api/tasks/reorder', methods=['POST'])
def reorder_tasks():
    """Update task order and optionally move a task to a different group."""
    data = request.get_json()
    if not data or 'taskIds' not in data:
        return jsonify({'error': 'taskIds array required'}), 400

    db = get_db()
    try:
        with db.cursor() as cursor:
            for i, task_id in enumerate(data['taskIds']):
                cursor.execute(
                    'UPDATE tasks SET sort_order = %s WHERE id = %s',
                    (i, task_id)
                )
            # Optionally move a task to a new group
            if data.get('movedTaskId') and data.get('newGroupId'):
                cursor.execute(
                    'UPDATE tasks SET group_id = %s WHERE id = %s',
                    (data['newGroupId'], data['movedTaskId'])
                )
        db.commit()
        return jsonify({'success': True})
    finally:
        db.close()


# ===================== MAIN =====================
if __name__ == '__main__':
    print('Starting Todo App Server...')
    print('Open http://localhost:5000 in your browser')
    app.run(host='0.0.0.0', port=5000, debug=True)
