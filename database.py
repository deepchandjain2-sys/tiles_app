import os
import streamlit as st
from supabase import create_client, Client

# Directly read from Environment Variables to completely avoid st.secrets error
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        supabase = None
else:
    supabase = None

def get_all_customers():
    if supabase:
        try:
            response = supabase.table("customers").select("*").execute()
            return response.data or []
        except Exception as e:
            st.error(f"Database Fetch Error: {e}")
            return []
    else:
        if 'mock_customers' not in st.session_state:
            st.session_state['mock_customers'] = []
        return st.session_state['mock_customers']

def save_customer_to_db(cust_data):
    if supabase:
        try:
            supabase.table("customers").upsert(cust_data, on_conflict="mobile").execute()
            return True
        except Exception as e:
            st.error(f"Database Save Error: {e}")
            return False
    else:
        if 'mock_customers' not in st.session_state:
            st.session_state['mock_customers'] = []
        existing = [c for c in st.session_state['mock_customers'] if c.get('mobile') == cust_data.get('mobile')]
        if existing:
            st.session_state['mock_customers'].remove(existing[0])
        st.session_state['mock_customers'].append(cust_data)
        return True

def delete_customer_from_db(mobile):
    if supabase:
        try:
            supabase.table("customers").delete().eq("mobile", mobile).execute()
            return True
        except Exception as e:
            st.error(f"Database Delete Error: {e}")
            return False
    else:
        if 'mock_customers' in st.session_state:
            st.session_state['mock_customers'] = [c for c in st.session_state['mock_customers'] if c.get('mobile') != mobile]
        return True

def get_all_admin_users():
    return [
        {"username": "admin", "password": "password", "role": "ADMIN", "branch": "Hiriyur"}
    ]
