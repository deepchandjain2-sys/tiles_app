import streamlit as st
from supabase import create_client, Client

SUPABASE_URL = "https://gedzazriwvaxabnppchc.supabase.co"
SUPABASE_KEY = "sb_publishable_oI8gTy66M8ICtq-DasQHA_M1Wq_s"

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
