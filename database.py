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
            db_data = response.data or []
            if db_data:
                return db_data
        except Exception as e:
            st.error(f"Supabase Fetch Error: {e}")
            
    if 'mock_customers' not in st.session_state:
        st.session_state['mock_customers'] = []
    return st.session_state['mock_customers']

def save_customer_to_db(cust_data):
    if 'mock_customers' not in st.session_state:
        st.session_state['mock_customers'] = []
    
    existing_idx = next((i for i, c in enumerate(st.session_state['mock_customers']) if c.get('mobile') == cust_data.get('mobile')), None)
    if existing_idx is not None:
        st.session_state['mock_customers'][existing_idx] = cust_data
    else:
        st.session_state['mock_customers'].append(cust_data)

    if supabase:
        try:
            # Clean dictionary to match exact Supabase table columns
            clean_data = {
                "mobile": str(cust_data.get("mobile", "")),
                "name": str(cust_data.get("name", "")),
                "address": str(cust_data.get("address", "")),
                "branch": str(cust_data.get("branch", "Hiriyur")),
                "selections": cust_data.get("selections", [])
            }
            res = supabase.table(TABLE_NAME).upsert(clean_data, on_conflict="mobile").execute()
            return True
        except Exception as e:
            st.error(f"⚠️ Supabase Save Failed: {e}")
            return False
    return True

def delete_customer_from_db(mobile):
    if 'mock_customers' in st.session_state:
        st.session_state['mock_customers'] = [c for c in st.session_state['mock_customers'] if c.get('mobile') != mobile]
        
    if supabase:
        try:
            supabase.table(TABLE_NAME).delete().eq("mobile", mobile).execute()
            return True
        except Exception as e:
            st.error(f"Supabase Delete Error: {e}")
            return False
    return True

def get_all_admin_users():
    return [
        {"username": "admin", "password": "password", "role": "ADMIN", "branch": "Hiriyur"}
    ]
