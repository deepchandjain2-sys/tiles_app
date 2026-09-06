import sqlite3
import os
import base64
import requests
import pandas as pd
import streamlit as st

GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
REPO_NAME = st.secrets.get("REPO_NAME", "deepchandjain2-sys/tiles_app")
DB_FILE = "jay_granite_master.db"
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR4mWSP3s6r7UIwn-kcX8Ogev4yXWTMpMLvL87PGTR_UwxKjkcbU9NNxy__mbkyYplhDHxvsD2nKFvW/pub?gid=1816720040&single=true&output=csv"

def get_db():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_database():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
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
    try:
        c.execute("ALTER TABLE customers_master ADD COLUMN branch TEXT DEFAULT 'Hiriyur'")
        conn.commit()
    except Exception:
        pass
    conn.close()

init_database()

def fetch_db_from_github():
    if not GITHUB_TOKEN or not REPO_NAME:
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
    except Exception:
        pass

def push_db_to_github():
    if not GITHUB_TOKEN or not REPO_NAME:
        return
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{DB_FILE}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        sha = r.json().get("sha") if r.status_code == 200 else None

        if os.path.exists(DB_FILE):
            with open(DB_FILE, "rb") as f:
                content_bytes = f.read()
            content_encoded = base64.b64encode(content_bytes).decode("utf-8")

            payload = {
                "message": "Auto-sync SQLite database [skip ci]",
                "content": content_encoded,
                "branch": "main"
            }
            if sha:
                payload["sha"] = sha

            requests.put(url, headers=headers, json=payload, timeout=10)
    except Exception:
        pass

if not os.path.exists(DB_FILE):
    fetch_db_from_github()

def get_all_customers_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, mobile, address, engineer, salesman, status, selections_json, total_sqft, total_boxes, created_at, branch FROM customers_master ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    
    import json
    clients = []
    for r in rows:
        try:
            sels = json.loads(r[7])
        except Exception:
            sels = []
        clients.append({
            "id": r[0],
            "name": r[1],
            "mobile": r[2],
            "address": r[3],
            "engineer": r[4],
            "salesman": r[5],
            "status": r[6],
            "selections": sels,
            "total_sqft": r[8],
            "total_boxes": r[9],
            "created_at": r[10],
            "branch": r[11] if len(r) > 11 and r[11] else "Hiriyur"
        })
    return clients

def insert_new_customer(name, mobile, address, engineer, salesman, branch):
    conn = get_db()
    c = conn.cursor()
    from datetime import datetime
    now_str = datetime.now().strftime("%d-%m-%Y %H:%M")
    c.execute("""
        INSERT INTO customers_master (name, mobile, address, engineer, salesman, branch, status, selections_json, total_sqft, total_boxes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'SELECTION ONLY', '[]', 0.0, 0.0, ?)
    """, (name, mobile, address, engineer, salesman, branch, now_str))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    push_db_to_github()
    return {
        "id": new_id,
        "name": name,
        "mobile": mobile,
        "address": address,
        "engineer": engineer,
        "salesman": salesman,
        "branch": branch,
        "status": "SELECTION ONLY",
        "selections": [],
        "total_sqft": 0.0,
        "total_boxes": 0.0,
        "created_at": now_str
    }

def update_customer_db(cust_dict):
    conn = get_db()
    c = conn.cursor()
    import json
    sels_json = json.dumps(cust_dict.get("selections", []), ensure_ascii=False)
    c.execute("""
        UPDATE customers_master 
        SET name = ?, mobile = ?, address = ?, engineer = ?, salesman = ?, branch = ?, status = ?, selections_json = ?, total_sqft = ?, total_boxes = ?
        WHERE id = ?
    """, (
        cust_dict.get("name"),
        cust_dict.get("mobile"),
        cust_dict.get("address"),
        cust_dict.get("engineer"),
        cust_dict.get("salesman"),
        cust_dict.get("branch", "Hiriyur"),
        cust_dict.get("status", "SELECTION ONLY"),
        sels_json,
        float(cust_dict.get("total_sqft", 0.0)),
        float(cust_dict.get("total_boxes", 0.0)),
        cust_dict.get("id")
    ))
    conn.commit()
    conn.close()
    push_db_to_github()

def delete_customer_db(cust_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM customers_master WHERE id = ?", (cust_id,))
    conn.commit()
    conn.close()
    push_db_to_github()

@st.cache_data(ttl=5)
def get_master_df():
    try:
        raw_df = pd.read_csv(GOOGLE_SHEET_CSV_URL, header=None, dtype=str)
        h_idx = 0
        for i in range(min(15, len(raw_df))):
            row_vals = [str(x).upper().strip() for x in raw_df.iloc[i].values if pd.notna(x)]
            if "ITEM NAME" in row_vals:
                h_idx = i
                break
                
        headers = [str(x).strip().upper() for x in raw_df.iloc[h_idx].values]
        data_rows = raw_df.iloc[h_idx + 1:].copy()
        
        item_col = 0
        cf_col = None
        pu_col = None
        
        for idx, h in enumerate(headers):
            if h == "ITEM NAME":
                item_col = idx
            elif h == "CON FACTOR":
                cf_col = idx
            elif "PACKING" in h:
                pu_col = idx

        if cf_col is None: cf_col = 7
        if pu_col is None: pu_col = 8

        parsed_stock = []
        for _, r in data_rows.iterrows():
            if item_col >= len(r) or not pd.notna(r.iloc[item_col]): 
                continue
            item_name = str(r.iloc[item_col]).strip()
            if not item_name or item_name.upper() in ["NAN", "ITEM NAME", "TOTAL", "NONE", "NULL", "UNNAMED", ""]:
                continue
            
            cf_val = 1.0
            if cf_col < len(r) and pd.notna(r.iloc[cf_col]):
                try:
                    cf_val = float(str(r.iloc[cf_col]).replace(',', '').strip())
                except Exception:
                    cf_val = 1.0
            if cf_val <= 0: cf_val = 1.0

            pu_val = 1.0
            if pu_col < len(r) and pd.notna(r.iloc[pu_col]):
                try:
                    pu_val = float(str(r.iloc[pu_col]).replace(',', '').strip())
                except Exception:
                    pu_val = 1.0
            if pu_val <= 0: pu_val = 1.0
                
            box_cov = round(cf_val * pu_val, 2)
            parsed_stock.append({
                "item_name": item_name,
                "con_factor": cf_val,
                "packing_unit": pu_val,
                "sqft_per_box": box_cov if box_cov > 0 else 1.0
            })
            
        df = pd.DataFrame(parsed_stock).drop_duplicates(subset=["item_name"])
        if not df.empty:
            return df
    except Exception as ex:
        st.error(f"Google Sheet Sync Error: {str(ex)}")
    return pd.DataFrame()

def calculate_box_sqft(cf, pu):
    try:
        cov = float(cf) * float(pu)
        return round(cov, 2) if cov > 0 else 1.0
    except Exception:
        return 1.0

def calculate_boxes(sqft, cf, PU):
    try:
        cov = float(cf) * float(PU)
        if cov <= 0:
            cov = 1.0
        import math
        return math.ceil(float(sqft) / cov)
    except Exception:
        return 0
