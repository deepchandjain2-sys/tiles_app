import streamlit as st
import requests
import json

SUPABASE_URL = "https://gedzazriwvaxabnppchc.supabase.co"
SUPABASE_KEY = "sb_publishable_o18gTy66MVBCtq-DasQHAA_MlWvg_g"

def get_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

def save_customer_to_db(cust_data):
    try:
        url = f"{SUPABASE_URL}/rest/v1/customers"
        payload = {
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
        }
        response = requests.post(url, headers=get_headers(), data=json.dumps(payload))
        if response.status_code in [200, 201, 204]:
            return True
        else:
            st.error(f"API Error ({response.status_code}): {response.text}")
            return False
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return False

def get_all_customers_from_db():
    try:
        url = f"{SUPABASE_URL}/rest/v1/customers?select=*"
        response = requests.get(url, headers=get_headers())
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        pass
    return []

def delete_customer_from_db(mobile):
    try:
        url = f"{SUPABASE_URL}/rest/v1/customers?mobile=eq.{mobile}"
        response = requests.delete(url, headers=get_headers())
        if response.status_code in [200, 204]:
            return True
    except Exception as e:
        pass
    return False
