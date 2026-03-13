import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

conn = psycopg.connect(DATABASE_URL)
conn.autocommit = True
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS sleep (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    bed_time TIMESTAMPTZ,
    wake_time TIMESTAMPTZ,
    duration INTEGER,
    score INTEGER,
    status TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    language TEXT DEFAULT 'en',
    streak INTEGER DEFAULT 0,
    timezone TEXT DEFAULT 'UTC',
    last_weekly_report TEXT
)
""")
