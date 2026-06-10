import sqlite3
import bcrypt
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "users.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def register_user(full_name, email, password):
    try:
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (full_name, email, password) VALUES (?, ?, ?)",
            (full_name, email, hashed)
        )
        conn.commit()
        conn.close()
        return True, "Registration successful!"
    except sqlite3.IntegrityError:
        return False, "Email already registered!"
    except Exception as e:
        return False, f"Error: {e}"

def login_user(email, password):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT full_name, password FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()
        if not user:
            return False, None, "Email not found!"
        if bcrypt.checkpw(password.encode(), user[1].encode()):
            return True, user[0], "Login successful!"
        return False, None, "Wrong password!"
    except Exception as e:
        return False, None, f"Error: {e}"

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, full_name, email, created_at FROM users")
    users = c.fetchall()
    conn.close()
    return users
