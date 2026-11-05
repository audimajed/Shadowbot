import sqlite3
from datetime import datetime

DB_PATH = "shadowbot.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        role TEXT DEFAULT 'user',
        banned INTEGER DEFAULT 0,
        joined_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        details TEXT,
        created_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        file_name TEXT,
        file_id TEXT,
        uploaded_at TEXT
    )""")
    conn.commit()
    conn.close()

def add_user(user_id, username, first_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT OR IGNORE INTO users
        (user_id, username, first_name, joined_at)
        VALUES (?, ?, ?, ?)""",
        (user_id, username or "", first_name or "", datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def set_role(user_id, role):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET role=? WHERE user_id=?", (role, user_id))
    conn.commit()
    conn.close()

def set_banned(user_id, banned):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET banned=? WHERE user_id=?", (1 if banned else 0, user_id))
    conn.commit()
    conn.close()

def is_banned(user_id):
    row = get_user(user_id)
    return bool(row and row[4])

def log_action(user_id, action, details=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT INTO audit_log (user_id, action, details, created_at)
        VALUES (?, ?, ?, ?)""",
        (user_id, action, details, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def count_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    n = c.fetchone()[0]
    conn.close()
    return n

def all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE banned=0")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def save_file(user_id, file_name, file_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT INTO files (user_id, file_name, file_id, uploaded_at)
        VALUES (?, ?, ?, ?)""",
        (user_id, file_name, file_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()
