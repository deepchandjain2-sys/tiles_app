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

def get_all_customers():
    if supabase:
        try:
            response = supabase.table(TABLE_NAME).select("*").execute()
            return response.data or []
        except Exception as e:
            st.error(f"Supabase Fetch Error: {e}")
            return []
    else:
        st.warning("⚠️ Running in Local Session Mode (Supabase not connected)")
        if 'mock_customers' not in st.session_state:
            st.session_state['mock_customers'] = []
        return st.session_state['mock_customers']

def save_customer_to_db(cust_data):
    clean_data = {
        "mobile": str(cust_data.get("mobile", "")),
        "name": str(cust_data.get("name", "")),
        "address": str(cust_data.get("address", "")),
        "branch": str(cust_data.get("branch", "Hiriyur")),
        "selections": cust_data.get("selections", [])
    }
    
    if supabase:
        try:
            res = supabase.table(TABLE_NAME).upsert(clean_data, on_conflict="mobile").execute()
            return True
        except Exception as e:
            st.error(f"⚠️ Supabase Save Error: {e}")
            return False
    else:
        if 'mock_customers' not in st.session_state:
            st.session_state['mock_customers'] = []
        existing_idx = next((i for i, c in enumerate(st.session_state['mock_customers']) if c.get('mobile') == clean_data.get('mobile')), None)
        if existing_idx is not None:
            st.session_state['mock_customers'][existing_idx] = clean_data
        else:
            st.session_state['mock_customers'].append(clean_data)
        return True

def delete_customer_from_db(mobile):
    if supabase:
        try:
            supabase.table(TABLE_NAME).delete().eq("mobile", mobile).execute()
            return True
        except Exception as e:
            st.error(f"Supabase Delete Error: {e}")
            return False
    else:
        if 'mock_customers' in st.session_state:
            st.session_state['mock_customers'] = [c for c in st.session_state['mock_customers'] if c.get('mobile') != mobile]
        return True

def get_all_admin_users():
    return [
        {"username": "admin", "password": "password", "role": "ADMIN", "branch": "Hiriyur"}
    ]
