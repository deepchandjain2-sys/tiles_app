import sqlite3
import os
import base64
import requests
import streamlit as st

GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
REPO_NAME = st.secrets.get("REPO_NAME", "deepchandjain2-sys/tiles_app")
DB_FILE = "jay_granite_master.db"

def fetch_db_from_github():
    if not GITHUB_TOKEN:
        return
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{DB_FILE}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            content_encoded = response.json().get("content", "")
            decoded_bytes = base64.b64decode(content_encoded)
            with open(DB_FILE, "wb") as f:
                f.write(decoded_bytes)
    except:
        pass

def save_db_to_github():
    if not GITHUB_TOKEN:
        return
    if not os.path.exists(DB_FILE):
        return
    
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{DB_FILE}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    
    sha = None
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            sha = res.json().get("sha")
    except:
        pass
        
    with open(DB_FILE, "rb") as f:
        db_bytes = f.read()
    encoded_content = base64.b64encode(db_bytes).decode('utf-8')
    
    payload = {
        "message": f"Auto-update SQLite database {DB_FILE} from Streamlit App",
        "content": encoded_content,
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha
        
    try:
        requests.put(url, headers=headers, json=payload, timeout=10)
    except:
        pass

# App shuru hote hi GitHub se latest DB fetch karein
fetch_db_from_github()

def get_db():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_database():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers_master (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        mobile TEXT,
        address TEXT,
        engineer TEXT,
        salesman TEXT,
        branch TEXT DEFAULT 'Hiriyur',
        status TEXT DEFAULT 'SELECTION ONLY',
        selections_json TEXT DEFAULT '[]',
        total_sqft REAL DEFAULT 0.0,
        total_boxes REAL DEFAULT 0.0,
        created_at TEXT
    )
    """)
    conn.commit()
    conn.close()
    # Database initialize hone ke baad GitHub par sync karein
    save_db_to_github()
