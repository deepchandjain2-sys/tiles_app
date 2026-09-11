import streamlit as st
from supabase import create_client, Client

SUPABASE_URL = https://gedzazirwxaxabnppchc.supabase.co
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdlZHphemlyd3hheGFibnBwY2hjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg2ODAyOTgsImV4cCI6MjEwNDI1NjI5OH0.CSCbuwInWJtGpL7w_nMFU6ElGWnXxr67bKeMWuTpMMM"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def save_customer_to_db(cust_data):
    
    try:
        data = {
            "mobile": str(cust_data.get('mobile')),
            "name": str(cust_data.get('name')),
            "address": str(cust_data.get('address')),
            "engineer": str(cust_data.get('engineer')),
            "engineer_mobile": str(cust_data.get('engineer_mobile'))
        }
        response = supabase.table("customers").upsert(data).execute()
        return True
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return False

def get_all_customers_from_db():
    try:
        response = supabase.table("customers").select("*").execute()
        return response.data
    except Exception as e:
        return []

def delete_customer_from_db(mobile):
    try:
        supabase.table("customers").delete().eq("mobile", mobile).execute()
        return True
    except Exception as e:
        return False
