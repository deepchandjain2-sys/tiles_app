import os
import streamlit as st
from supabase import create_client, Client

SUPABASE_URL = "https://gedrazirswxsakanppchc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdlZHJhemlyc3d4c2FrYW5wcGNoYyIsInJvbGUiOiJhbm9uIiwiaWF0IjoxNzM1MTQzMjUzLCJleHAiOjIwNTA3MTkyNTN9.yIp3MUiOjicDHwfzS25Isin1ZlI1lInRSCl6IKpxVC39.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdlZHJhemlyc3d4c2FrYW5wcGNoYyIsInJvbGUiOiJhbm9uIiwiaWF0IjoxNzM1MTQzMjUzLCJleHAiOjIwNTA3MTkyNTN9.WlZHSn1Z1lInRSCl6IKpxVC39"

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
        if 'mock_customers' not in st.session_state:
            st.session_state['mock_customers'] = []
        return st.session_state['mock_customers']

def save_customer_to_db(cust_data):
    # Support both phone and mobile keys safely
    phone_val = str(cust_data.get("mobile", "") or cust_data.get("phone", ""))
    
    clean_data = {
        "mobile": phone_val,
        "name": str(cust_data.get("name", "")),
        "address": str(cust_data.get("address", "")),
        "branch": str(cust_data.get("branch", "Hiriyur")),
        "selections": cust_data.get("selections", [])
    }
    
    if supabase:
        try:
            # Use insert instead of upsert so it creates a new row every time without overwriting
            res = supabase.table(TABLE_NAME).insert(clean_data).execute()
            return True
        except Exception as e:
            st.error(f"Supabase Save Error: {e}")
            return False
    else:
        if 'mock_customers' not in st.session_state:
            st.session_state['mock_customers'] = []
        st.session_state['mock_customers'].append(clean_data)
        return True

def delete_customer_from_db(identifier):
    if supabase:
        try:
            # Delete by mobile or id if available
            supabase.table(TABLE_NAME).delete().eq("mobile", identifier).execute()
            return True
        except Exception as e:
            st.error(f"Supabase Delete Error: {e}")
            return False
    return False
