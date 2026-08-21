import sqlite3
import hashlib
from datetime import datetime

def get_connection():
    return sqlite3.connect("tiles_app.db")

def create_tables():
    conn = get_connection()
    c = conn.cursor()
    
    # Users Table
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT,
        role TEXT,
        security_pin TEXT
    )""")
    
    # Login History
    c.execute("""CREATE TABLE IF NOT EXISTS login_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        timestamp TEXT
    )""")
    
    # Customer Master
    c.execute("""CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        salesman TEXT,
        customer_name TEXT,
        mobile TEXT UNIQUE,
        address TEXT,
        engineer_name TEXT,
        engineer_mobile TEXT,
        status TEXT,
        created_at TEXT
    )""")
    
    # Tile Selections Line Items
    c.execute("""CREATE TABLE IF NOT EXISTS customer_selections (
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
        boxes_required INTEGER,
        status TEXT,
        timestamp TEXT,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )""")
    conn.commit()
    conn.close()

def hash_pass(password):
    return hashlib.sha256(password.encode()).hexdigest()