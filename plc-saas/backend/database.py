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
    admin_pass = os.environ.get("ADMIN_PASSWORD")
    generated = False
    if not admin_pass:
        import secrets
        admin_pass = secrets.token_urlsafe(16)
        generated = True
    c.execute("SELECT id FROM users WHERE email=?", (admin_email,))
    existing_admin = c.fetchone()
    if existing_admin and not generated:
        # ADMIN_PASSWORD set in the environment → always sync it, so the old default
        # password ("admin123") stops working as soon as the variable is configured.
        c.execute("UPDATE users SET password_hash=? WHERE email=?", (hash_password(admin_pass), admin_email))
        print(f"✅ Admin password synced from ADMIN_PASSWORD for {admin_email}")
    if not existing_admin:
        c.execute("""
            INSERT INTO users (email, password_hash, full_name, plan, is_admin)
            VALUES (?, ?, ?, 'enterprise', 1)
        """, (admin_email, hash_password(admin_pass), "Administrator"))
        user_id = c.lastrowid
        c.execute("""
            INSERT INTO subscriptions (user_id, plan, monthly_limit)
            VALUES (?, 'enterprise', 999999)
        """, (user_id,))
        if generated:
            print(f"⚠ ADMIN_PASSWORD not set — generated one-time admin password for {admin_email}: {admin_pass}")
        else:
            print(f"✅ Admin created: {admin_email}")

    conn.commit()
    conn.close()
    print("✅ Database initialized")
