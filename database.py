import sqlite3
import json
from datetime import datetime

DB_NAME = "tiles_business.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # 1. Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            role TEXT,
            full_name TEXT
        )
    ''')
    
    # 2. Customers table
    c.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            mobile TEXT,
            address TEXT,
            engineer_name TEXT,
            engineer_mobile TEXT,
            salesman TEXT,
            created_at TEXT,
            status TEXT DEFAULT 'Shown', -- Shown, Selected, Finalized
            stage TEXT DEFAULT 'Selection' -- Selection, Measurement, Closed
        )
    ''')
    
    # 3. Selections / Measurements table
    c.execute('''
        CREATE TABLE IF NOT EXISTS customer_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            floor TEXT,
            section_type TEXT, -- Floor or Wall
            area_name TEXT,
            item_id TEXT,
            item_name TEXT,
            box_sqft REAL,
            calc_mode TEXT, -- Direct or LxW
            length REAL,
            width REAL,
            wastage REAL,
            sqft REAL,
            boxes INTEGER,
            exact_boxes REAL,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    ''')
    
    # Add default admin and salesman if not present
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', 'admin123', 'admin', 'Deepchand Jain')")
    c.execute("INSERT OR IGNORE INTO users VALUES ('sales1', '1234', 'salesman', 'Sales Executive 1')")
    c.execute("INSERT OR IGNORE INTO users VALUES ('sales2', '1234', 'salesman', 'Sales Executive 2')")
    
    conn.commit()
    conn.close()

init_db()
