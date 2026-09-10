import streamlit as st
from supabase import create_client, Client
SUPABASE_URL = "https://apka-project-url.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdlZHphemlyd3hheGFibnBwY2hjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg2ODAyOTgsImV4cCI6MjEwNDI1NjI5OH0.CSCbuwInWJtGpL7w_nMFU6ElGWnXxr67bKeMWuTpMMM"

@st.cache_resource
def init_supabase():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except:
        return None

supabase = init_supabase()

def save_customer_to_db(cust_data):
    try:
        if supabase:
            data = supabase.table("customers").upsert({
                "mobile": cust_data['mobile'],
                "name": cust_data['name'],
                "address": cust_data['address'],
                "engineer": cust_data['engineer'],
                "engineer_mobile": cust_data['engineer_mobile'],
                "salesman": cust_data['salesman'],
                "branch": cust_data['branch'],
                "status": cust_data['status'],
                "selections": cust_data['selections'],
                "total_sqft": cust_data['total_sqft'],
                "total_boxes": cust_data['total_boxes']
            }, on_conflict="mobile").execute()
            return True
    except Exception as e:
        print(e)
    return False

def get_all_customers_from_db():
    try:
        if supabase:
            response = supabase.table("customers").select("*").execute()
            return response.data if response.data else []
    except Exception as e:
        print(e)
    return []

def delete_customer_from_db(mobile):
    try:
        if supabase:
            supabase.table("customers").delete().eq("mobile", mobile).execute()
            return True
    except Exception as e:
        print(e)
    return False
