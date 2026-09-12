import os
import streamlit as st
from supabase import create_client, Client

SUPABASE_URL = "https://gedzazirwxaxabnppchc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdlZHphemlyd3hheGFibnBwY2hjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg2ODAyOTgsImV4cCI6MjEwNDI1NjI5OH0.CSCbuwInWJtGpL7w_nMFU6ElGWnXxr67bKeMWuTpMMM"

supabase: Client = None
try:
    if SUPABASE_URL and SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Supabase Connection Init Error: {e}")

TABLE_NAME = "customers"

def get_all_customers_db():
    if supabase:
        try:
            response = supabase.table(TABLE_NAME).select("*").execute()
            rows = response.data or []
            formatted_clients = []
            for r in rows:
                formatted_clients.append({
                    "id": r.get("id", 1),
                    "name": r.get("name", ""),
                    "mobile": r.get("mobile", ""),
                    "address": r.get("address", ""),
                    "engineer": r.get("engineer", ""),
                    "salesman": r.get("salesman", ""),
                    "branch": r.get("branch", "Hiriyur"),
                    "status": r.get("status", "SELECTION ONLY"),
                    "selections": r.get("selections", []) if isinstance(r.get("selections"), list) else [],
                    "total_sqft": float(r.get("total_sqft") or 0.0),
                    "total_boxes": float(r.get("total_boxes") or 0.0),
                    "created_at": r.get("created_at", "")
                })
            return formatted_clients
        except Exception as e:
            st.error(f"Supabase Fetch Error: {e}")
            return []
    return []

def insert_new_customer(name, mobile, address, engineer, salesman, branch):
    cust_data = {
        "mobile": str(mobile),
        "name": str(name),
        "address": str(address or ""),
        "engineer": str(engineer or ""),
        "salesman": str(salesman or ""),
        "branch": str(branch or "Hiriyur"),
        "status": "SELECTION ONLY",
        "selections": [],
        "total_sqft": 0.0,
        "total_boxes": 0.0
    }
    if supabase:
        try:
            supabase.table(TABLE_NAME).upsert(cust_data, on_conflict="mobile").execute()
        except Exception as e:
            st.error(f"Insert Error: {e}")
    return cust_data

def update_customer_db(cust_dict):
    clean_data = {
        "mobile": str(cust_dict.get("mobile", "")),
        "name": str(cust_dict.get("name", "")),
        "address": str(cust_dict.get("address", "")),
        "engineer": str(cust_dict.get("engineer", "")),
        "salesman": str(cust_dict.get("salesman", "")),
        "branch": str(cust_dict.get("branch", "Hiriyur")),
        "status": str(cust_dict.get("status", "SELECTION ONLY")),
        "selections": cust_dict.get("selections", []),
        "total_sqft": float(cust_dict.get("total_sqft", 0.0)),
        "total_boxes": float(cust_dict.get("total_boxes", 0.0))
    }
    
    if supabase:
        try:
            supabase.table(TABLE_NAME).upsert(clean_data, on_conflict="mobile").execute()
            return True
        except Exception as e:
            st.error(f"⚠️ Supabase Save Error: {e}")
            return False
    return False

def delete_customer_db(cust_id_or_mobile):
    if supabase:
        try:
            val = str(cust_id_or_mobile)
            if val.isdigit() and len(val) < 8:
                supabase.table(TABLE_NAME).delete().eq("id", int(val)).execute()
            else:
                supabase.table(TABLE_NAME).delete().eq("mobile", val).execute()
            return True
        except Exception as e:
            st.error(f"Supabase Delete Error: {e}")
            return False
    return False

def get_all_admin_users():
    return [
        {"username": "admin", "password": "password", "role": "ADMIN", "branch": "Hiriyur"}
    ]
