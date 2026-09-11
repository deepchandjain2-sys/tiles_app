import os
import streamlit as st
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        supabase = None
else:
    supabase = None

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
        if 'mock_customers' not in st.session_state:
            st.session_state['mock_customers'] = []
        return st.session_state['mock_customers']

def save_customer_to_db(cust_data):
    if supabase:
        try:
            res = supabase.table(TABLE_NAME).upsert(cust_data, on_conflict="mobile").execute()
            return True
        except Exception as e:
            st.error(f"Supabase Save Error: {e}")
            return False
    else:
        if 'mock_customers' not in st.session_state:
            st.session_state['mock_customers'] = []
        existing_idx = next((i for i, c in enumerate(st.session_state['mock_customers']) if c.get('mobile') == cust_data.get('mobile')), None)
        if existing_idx is not None:
            st.session_state['mock_customers'][existing_idx] = cust_data
        else:
            st.session_state['mock_customers'].append(cust_data)
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
