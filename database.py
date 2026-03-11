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

conn.commit()
