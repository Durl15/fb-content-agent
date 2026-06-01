import sqlite3

DB_PATH = "content.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            format TEXT,
            content_json TEXT,
            status TEXT DEFAULT 'draft',
            scheduled_time TEXT,
            posted_at TEXT,
            fb_post_id TEXT,
            reach INTEGER DEFAULT 0,
            views INTEGER DEFAULT 0,
            engagement INTEGER DEFAULT 0,
            score INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS performance_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER,
            checked_at TEXT,
            reach INTEGER,
            views INTEGER,
            likes INTEGER,
            comments INTEGER,
            shares INTEGER
        )
    """)

    conn.commit()
    conn.close()
    print(f"Database initialized: {DB_PATH}")


if __name__ == "__main__":
    init_db()
