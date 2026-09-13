import os
import streamlit as st
from supabase import create_client, Client

SUPABASE_URL = "https://gedrazirswxsakanppchc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdlZHJhemlyc3d4c2FrYW5wcGNoYyIsInJvbGUiOiJhbm9uIiwiaWF0IjoxNzM1MTQzMjUzLCJleHAiOjIwNTA3MTkyNTN9.yIp3MUiOjicDHwfzS25Isin1ZlI1lInRSCl6IKpxVC39"

supabase: Client = None
try:
    if SUPABASE_URL and SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Supabase Connection Init Error: {e}")

TABLE_NAME = "customers"

def get_all_customers_db():
    """Supabase cloud se saare customers fetch karta hai"""
    if supabase:
        try:
            response = supabase.table(TABLE_NAME).select("*").execute()
            return response.data or []
        except Exception as e:
            st.error(f"Supabase Fetch Error: {e}")
            return []
    return []

# Alias taaki dono naam se function kaam kare
def get_all_customers():
    return get_all_customers_db()

def save_customer_to_db(cust_data):
    """Customer aur uski selections ko Supabase mein upsert karta hai"""
    m_val = str(cust_data.get("mobile", "") or cust_data.get("phone", ""))
    n_val = str(cust_data.get("name", ""))
    e_name = str(cust_data.get("engineer_name", "") or cust_data.get("engineer", ""))
    e_mob = str(cust_data.get("engineer_mobile", ""))
    addr = str(cust_data.get("address", ""))
    branch = str(cust_data.get("branch", "Hiriyur"))
    selections = cust_data.get("selections", [])
    
    clean_data = {
        "mobile": m_val,
        "name": n_val,
        "engineer": e_name,
        "engineer_mobile": e_mob,
        "address": addr,
        "branch": branch,
        "selections": selections
    }
    
    if supabase:
        try:
            supabase.table(TABLE_NAME).upsert(clean_data, on_conflict="mobile").execute()
            return True
        except Exception as e:
            st.error(f"Supabase Save Error: {e}")
            return False
    return False

def delete_customer_from_db(mobile):
    """Supabase table se customer ko delete karta hai"""
    if supabase:
        try:
            supabase.table(TABLE_NAME).delete().eq("mobile", str(mobile)).execute()
            return True
        except Exception as e:
            st.error(f"Supabase Delete Error: {e}")
            return False
    return False
