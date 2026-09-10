import streamlit as st
from supabase import create_client, Client
SUPABASE_URL = "gedzazirwxaxabnppchc"
SUPABASE_KEY = "sb_publishable_oi8gTy66MV8CTq-DasQHAA_M1Wvgg-g"

@st.cache_resource
def init_supabase():
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return client
    except Exception as e:
        st.error(f"Supabase Init Error: {e}")
        return None
supabase = init_supabase()

def save_customer_to_db(cust_data):
    try:
        if supabase:
            data = supabase.table("customers").upsert({
                "mobile": str(cust_data['mobile']),
                "name": str(cust_data['name']),
                "address": str(cust_data.get('address', '')),
                "engineer": str(cust_data.get('engineer', '')),
                "engineer_mobile": str(cust_data.get('engineer_mobile', '')),
                "salesman": str(cust_data.get('salesman', '')),
                "branch": str(cust_data.get('branch', '')),
                "status": str(cust_data.get('status', 'ACTIVE')),
                "selections": cust_data.get('selections', []),
                "total_sqft": float(cust_data.get('total_sqft', 0.0)),
                "total_boxes": float(cust_data.get('total_boxes', 0.0))
            }, on_conflict="mobile").execute()
            return True
    except Exception as e:
        st.error(f"Supabase Error: {e}")
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
