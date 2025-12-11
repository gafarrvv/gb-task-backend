import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

DB_NAME = "tasks.db"

app = Flask(__name__)
CORS(app)  # bütün domenlərdən gələn request-lərə icazə (frontend üçün lazımdır)


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # nəticələri dict kimi almaq üçün
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            priority TEXT NOT NULL,
            notes TEXT,
            done INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "service": "gp-task-backend"}), 200


@app.route("/tasks", methods=["GET"])
def list_tasks():
    """
    Bütün taskları qaytarır.
    Gələcəkdə filterlər də əlavə edə bilərik (date, status və s.).
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks ORDER BY date ASC, priority DESC, id DESC;")
    rows = cur.fetchall()
    conn.close()

    tasks = []
    for r in rows:
        tasks.append(
            {
                "id": r["id"],
                "title": r["title"],
                "date": r["date"],
                "priority": r["priority"],
                "notes": r["notes"],
                "done": bool(r["done"]),
                "createdAt": r["created_at"],
            }
        )
    return jsonify(tasks), 200


@app.route("/tasks", methods=["POST"])
def create_task():
    """
    Yeni task əlavə edir.
    Gözlənilən JSON:
    {
      "title": "...",
      "date": "2025-12-12",
      "priority": "low|medium|high",
      "notes": "optional"
    }
    """
    data = request.get_json(silent=True) or {}

    title = (data.get("title") or "").strip()
    date = (data.get("date") or "").strip()
    priority = (data.get("priority") or "medium").strip().lower()
    notes = (data.get("notes") or "").strip()

    if not title or not date:
        return jsonify({"error": "title və date mütləqdir"}), 400

    if priority not in ["low", "medium", "high"]:
        priority = "medium"

    created_at = datetime.utcnow().isoformat()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO tasks (title, date, priority, notes, done, created_at)
        VALUES (?, ?, ?, ?, 0, ?);
        """,
        (title, date, priority, notes, created_at),
    )
    conn.commit()
    task_id = cur.lastrowid
    conn.close()

    return jsonify(
        {
            "id": task_id,
            "title": title,
            "date": date,
            "priority": priority,
            "notes": notes,
            "done": False,
            "createdAt": created_at,
        }
    ), 201


@app.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    """
    Mövcud taskı yeniləyir.
    Gözlənilən JSON: istənilən sahə ola bilər:
    {
      "title": "...",
      "date": "...",
      "priority": "...",
      "notes": "...",
      "done": true/false
    }
    """
    data = request.get_json(silent=True) or {}

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks WHERE id = ?;", (task_id,))
    row = cur.fetchone()

    if row is None:
        conn.close()
        return jsonify({"error": "task tapılmadı"}), 404

    # mövcud dəyərlər
    title = (data.get("title") or row["title"]).strip()
    date = (data.get("date") or row["date"]).strip()
    priority = (data.get("priority") or row["priority"]).strip().lower()
    notes = (data.get("notes") or row["notes"] or "").strip()
    done = data.get("done")
    if done is None:
        done = bool(row["done"])
    else:
        done = bool(done)

    if priority not in ["low", "medium", "high"]:
        priority = "medium"

    cur.execute(
        """
        UPDATE tasks
        SET title = ?, date = ?, priority = ?, notes = ?, done = ?
        WHERE id = ?;
        """,
        (title, date, priority, notes, int(done), task_id),
    )
    conn.commit()
    conn.close()

    return jsonify(
        {
            "id": task_id,
            "title": title,
            "date": date,
            "priority": priority,
            "notes": notes,
            "done": done,
        }
    ), 200


@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    """
    Taskı silir.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM tasks WHERE id = ?;", (task_id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        return jsonify({"error": "task tapılmadı"}), 404

    cur.execute("DELETE FROM tasks WHERE id = ?;", (task_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted"}), 200


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
