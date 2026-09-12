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
    return []

def save_customer_to_db(cust_data):
    m_val = str(cust_data.get("mobile", "") or cust_data.get("phone", ""))
    n_val = str(cust_data.get("name", ""))
    e_name = str(cust_data.get("engineer_name", ""))
    e_mob = str(cust_data.get("engineer_mobile", ""))
    addr = str(cust_data.get("address", ""))
    branch = str(cust_data.get("branch", "Hiriyur"))
    
    clean_data = {
        "mobile": m_val,
        "name": n_val,
        "engineer": e_name,
        "engineer_mobile": e_mob,
        "address": addr,
        "branch": branch
    }
    
    if supabase:
        try:
            supabase.table(TABLE_NAME).insert(clean_data).execute()
            return True
        except Exception as e:
            st.error(f"Supabase Save Error: {e}")
            return False
    return False
def delete_customer_from_db(customer_id):
    try:
        # Try deleting by integer ID
        if str(customer_id).isdigit():
            supabase.table("customers").delete().eq("id", int(customer_id)).execute()
        
        # Try deleting by string/UUID ID
        supabase.table("customers").delete().eq("id", str(customer_id)).execute()
        return True
    except Exception as e:
        print(f"Error deleting customer: {e}")
        return Falsedef get_all_admin_users():
    return []
