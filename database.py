import sqlite3
import hashlib

DB_FILE = "tiles_app.db"

def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def hash_pass(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_tables():
    conn = get_connection()
    c = conn.cursor()
    
    # Users Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            role TEXT,
            security_pin TEXT
        )
    """)
    
   # Auto-insert default Admins
    admins_list = [
        ("DEEPCHAND JAIN", "deep123", "1234"),
        ("GOURAV", "GOURAV", "1234"),
        ("JAY", "JAY", "1234")
    ]
    
    for u_name, u_pass, u_pin in admins_list:
        c.execute("SELECT * FROM users WHERE username = ?", (u_name,))
        if not c.fetchone():
            c.execute("""
                INSERT INTO users (username, password_hash, role, security_pin)
                VALUES (?, ?, 'admin', ?)
            """, (u_name, hash_pass(u_pass), u_pin))
    # Customers Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salesman TEXT,
            customer_name TEXT,
            mobile TEXT,
            address TEXT,
            engineer_name TEXT,
            engineer_mobile TEXT,
            status TEXT,
            created_at TEXT
        )
    """)
    
    # Selections Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS customer_selections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            customer_name TEXT,
            mobile TEXT,
            salesman TEXT,
            floor TEXT,
            area_type TEXT,
            area_name TEXT,
            tile_name TEXT,
            dimensions TEXT,
            sqft_covered REAL,
            boxes_required REAL,
            status TEXT,
            timestamp TEXT
        )
    """)
    
    # Login History Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS login_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            timestamp TEXT
        )
    """)
    
    conn.commit()
    conn.close()
