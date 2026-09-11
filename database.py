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

def get_all_customers():
    """Fetches all registered customers/parties from Supabase without any limit."""
    if supabase:
        try:
            # Fetching all records without restrictions
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
    """Saves or updates a customer in Supabase properly."""
    if supabase:
        try:
            # Using upsert matching mobile unique constraint
            supabase.table("customers").upsert(cust_data, on_conflict="mobile").execute()
            return True
        except Exception as e:
            st.error(f"Database Save Error: {e}")
            return False
    else:
        if 'mock_customers' not in st.session_state:
            st.session_state['mock_customers'] = []
        
        # Check if mobile already exists in session, update it; otherwise append new
        existing_idx = next((i for i, c in enumerate(st.session_state['mock_customers']) if c.get('mobile') == cust_data.get('mobile')), None)
        if existing_idx is not None:
            st.session_state['mock_customers'][existing_idx] = cust_data
        else:
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
