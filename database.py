import sqlite3

DB_NAME = "tasks.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            priority INTEGER NOT NULL CHECK (priority IN (1, 2, 3)),
            status TEXT NOT NULL DEFAULT 'Не выполнено',
            created_at TEXT NOT NULL DEFAULT (date('now')),
            description TEXT NOT NULL DEFAULT '',
            deadline TEXT
        )
        """
    )
    columns = [row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()]
    if "created_at" not in columns:
        conn.execute(
            "ALTER TABLE tasks ADD COLUMN created_at TEXT NOT NULL DEFAULT '1970-01-01'"
        )
        conn.execute("UPDATE tasks SET created_at = date('now')")
    if "description" not in columns:
        conn.execute(
            "ALTER TABLE tasks ADD COLUMN description TEXT NOT NULL DEFAULT ''"
        )
    if "deadline" not in columns:
        conn.execute("ALTER TABLE tasks ADD COLUMN deadline TEXT")
    conn.commit()
    conn.close()


def add_task(title, priority, created_at=None, description=None, deadline=None):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO tasks (title, priority, status, created_at, description, deadline) "
        "VALUES (?, ?, ?, COALESCE(?, date('now')), ?, ?)",
        (title, priority, "Не выполнено", created_at, description or "", deadline or None),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def get_tasks():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, title, priority, status, created_at, description, deadline "
        "FROM tasks ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_task(task_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, title, priority, status, created_at, description, deadline "
        "FROM tasks WHERE id = ?",
        (task_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_task(task_id, title, priority, created_at=None, description=None, deadline=None):
    conn = get_connection()
    cursor = conn.execute(
        "UPDATE tasks SET title = ?, priority = ?, created_at = ?, "
        "description = ?, deadline = ? WHERE id = ?",
        (title, priority, created_at, description or "", deadline or None, task_id),
    )
    conn.commit()
    changed = cursor.rowcount > 0
    conn.close()
    return changed


def mark_complete(task_id):
    conn = get_connection()
    cursor = conn.execute(
        "UPDATE tasks SET status = 'Выполнено' WHERE id = ? AND status != 'Выполнено'",
        (task_id,),
    )
    conn.commit()
    changed = cursor.rowcount > 0
    conn.close()
    return changed


def mark_todo(task_id):
    conn = get_connection()
    cursor = conn.execute(
        "UPDATE tasks SET status = 'Не выполнено' WHERE id = ? AND status != 'Не выполнено'",
        (task_id,),
    )
    conn.commit()
    changed = cursor.rowcount > 0
    conn.close()
    return changed


def get_progress_data():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, title, status FROM tasks ORDER BY id"
    ).fetchall()
    conn.close()
    data = []
    cumulative = 0
    for row in rows:
        if row["status"] == "Выполнено":
            cumulative += 1
        data.append(
            {"step": row["id"], "done": cumulative, "title": row["title"]}
        )
    return data


def get_stats():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    done = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE status = 'Выполнено'"
    ).fetchone()[0]
    remaining = total - done
    by_priority = {
        priority: conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE priority = ?", (priority,)
        ).fetchone()[0]
        for priority in (1, 2, 3)
    }
    conn.close()
    return {
        "total": total,
        "done": done,
        "remaining": remaining,
        "by_priority": by_priority,
    }