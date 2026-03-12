import sqlite3

conn = sqlite3.connect("sleep.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS sleep (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    bed_time TEXT,
    wake_time TEXT,
    duration INTEGER,
    score INTEGER,
    status TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    language TEXT DEFAULT 'en',
    streak INTEGER DEFAULT 0,
    timezone TEXT DEFAULT 'UTC',
    last_weekly_report TEXT
)
""")

def add_column_if_missing(table_name: str, column_name: str, column_def: str):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    if column_name not in columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")

add_column_if_missing("users", "language", "TEXT DEFAULT 'en'")
add_column_if_missing("users", "streak", "INTEGER DEFAULT 0")
add_column_if_missing("users", "timezone", "TEXT DEFAULT 'UTC'")
add_column_if_missing("users", "last_weekly_report", "TEXT")

conn.commit()

