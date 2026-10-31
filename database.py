"""Customer database for the Tiles & BOQ app.

Uses Supabase when SUPABASE_URL and SUPABASE_KEY are set in Streamlit secrets
(or environment variables). Otherwise falls back to a local SQLite file, and
creates the table automatically, so the app always starts.
"""
import os
import json
import sqlite3
import streamlit as st

TABLE_NAME = "customers"
DB_FILE = "jay_granite_master.db"


def _secret(name):
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.environ.get(name)


# ---------------- Supabase (optional) ----------------
supabase = None
_url, _key = _secret("SUPABASE_URL"), _secret("SUPABASE_KEY")
if _url and _key:
    try:
        from supabase import create_client
        supabase = create_client(_url, _key)
    except Exception as e:  # bad URL/key -> use SQLite instead of crashing
        print(f"Supabase init failed, using SQLite: {e}")
        supabase = None


# ---------------- SQLite fallback ----------------
def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(
        f"""CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            mobile TEXT UNIQUE,
            engineer_name TEXT,
            engineer_mobile TEXT,
            address TEXT,
            branch TEXT,
            selections TEXT DEFAULT '[]',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    return conn


def _clean(cust_data):
    sel = cust_data.get("selections", [])
    if not isinstance(sel, str):
        sel = json.dumps(sel or [], ensure_ascii=False)
    return {
        "name": str(cust_data.get("name", "") or ""),
        "mobile": str(cust_data.get("mobile", "") or cust_data.get("phone", "") or ""),
        "engineer_name": str(cust_data.get("engineer_name", "") or cust_data.get("engineer", "") or ""),
        "engineer_mobile": str(cust_data.get("engineer_mobile", "") or ""),
        "address": str(cust_data.get("address", "") or ""),
        "branch": str(cust_data.get("branch", "Hiriyur") or "Hiriyur"),
        "selections": sel,
    }


def get_all_customers():
    if supabase:
        try:
            return supabase.table(TABLE_NAME).select("*").order("id", desc=True).execute().data or []
        except Exception as e:
            st.error(f"Supabase Fetch Error: {e}")
            return []
    conn = get_db()
    rows = conn.execute(f"SELECT * FROM {TABLE_NAME} ORDER BY id DESC").fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        d["phone"] = d.get("mobile")
        d["engineer"] = d.get("engineer_name")
        out.append(d)
    return out


# Old name kept so older code keeps working
get_all_customers_db = get_all_customers


def save_customer_to_db(cust_data):
    """Insert a new customer, or update the existing one with the same mobile."""
    data = _clean(cust_data)
    if not data["mobile"]:
        return False
    if supabase:
        try:
            supabase.table(TABLE_NAME).upsert(data, on_conflict="mobile").execute()
            return True
        except Exception as e:
            st.error(f"Supabase Save Error: {e}")
            return False
    try:
        conn = get_db()
        conn.execute(
            f"""INSERT INTO {TABLE_NAME} (name, mobile, engineer_name, engineer_mobile, address, branch, selections)
                VALUES (:name, :mobile, :engineer_name, :engineer_mobile, :address, :branch, :selections)
                ON CONFLICT(mobile) DO UPDATE SET
                    name=excluded.name, engineer_name=excluded.engineer_name,
                    engineer_mobile=excluded.engineer_mobile, address=excluded.address,
                    branch=excluded.branch, selections=excluded.selections""",
            data,
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Database Save Error: {e}")
        return False


def update_customer_in_db(cust_id, updates):
    """Update some fields (e.g. {'selections': '[...]'}) of one customer by id."""
    if cust_id is None or not updates:
        return False
    updates = dict(updates)
    if "selections" in updates and not isinstance(updates["selections"], str):
        updates["selections"] = json.dumps(updates["selections"], ensure_ascii=False)
    if supabase:
        supabase.table(TABLE_NAME).update(updates).eq("id", cust_id).execute()
        return True
    allowed = {"name", "mobile", "engineer_name", "engineer_mobile", "address", "branch", "selections"}
    updates = {k: v for k, v in updates.items() if k in allowed}
    if not updates:
        return False
    sets = ", ".join(f"{k} = ?" for k in updates)
    conn = get_db()
    conn.execute(f"UPDATE {TABLE_NAME} SET {sets} WHERE id = ?", (*updates.values(), cust_id))
    conn.commit()
    conn.close()
    return True


def delete_customer_from_db(cust_id_or_mobile):
    """Delete by id (number) or by mobile number."""
    key = str(cust_id_or_mobile)
    if supabase:
        try:
            col = "id" if key.isdigit() and len(key) < 10 else "mobile"
            supabase.table(TABLE_NAME).delete().eq(col, key).execute()
            return True
        except Exception as e:
            st.error(f"Supabase Delete Error: {e}")
            return False
    conn = get_db()
    conn.execute(f"DELETE FROM {TABLE_NAME} WHERE CAST(id AS TEXT) = ? OR mobile = ?", (key, key))
    conn.commit()
    conn.close()
    return True


delete_customer_db = delete_customer_from_db


def get_all_admin_users():
    """Extra logins can be added in Streamlit secrets as ADMIN_USERS (JSON list)."""
    raw = _secret("ADMIN_USERS")
    if raw:
        try:
            return json.loads(raw) if isinstance(raw, str) else list(raw)
        except Exception:
            pass
    return [{"username": "admin", "password": "password", "role": "ADMIN", "branch": "Hiriyur"}]
