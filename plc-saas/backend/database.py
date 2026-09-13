import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "plc_saas.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            plan TEXT DEFAULT 'free',
            is_active INTEGER DEFAULT 1,
            is_admin INTEGER DEFAULT 0,
            usage_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # PLC History table
    c.execute("""
        CREATE TABLE IF NOT EXISTS plc_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT,
            description TEXT,
            prog_type TEXT,
            cpu_model TEXT,
            block_type TEXT,
            scl_code TEXT,
            ladder_json TEXT,
            io_list TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Subscriptions table
    c.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            plan TEXT DEFAULT 'free',
            monthly_limit INTEGER DEFAULT 10,
            usage_this_month INTEGER DEFAULT 0,
            reset_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Create default admin if not exists
    from auth_utils import hash_password
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@plcai.com")
    admin_pass = os.environ.get("ADMIN_PASSWORD", "admin123")
    c.execute("SELECT id FROM users WHERE email=?", (admin_email,))
    if not c.fetchone():
        c.execute("""
            INSERT INTO users (email, password_hash, full_name, plan, is_admin)
            VALUES (?, ?, ?, 'enterprise', 1)
        """, (admin_email, hash_password(admin_pass), "Administrator"))
        user_id = c.lastrowid
        c.execute("""
            INSERT INTO subscriptions (user_id, plan, monthly_limit)
            VALUES (?, 'enterprise', 999999)
        """, (user_id,))
        print(f"✅ Admin created: {admin_email} / {admin_pass}")

    conn.commit()
    conn.close()
    print("✅ Database initialized")
