import os
import json
import requests
import pandas as pd
import streamlit as st

SUPABASE_URL = "https://gedzazirwxaxabnppchc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdlZHphemlyd3hheGFibnBwY2hjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg2ODAyOTgsImV4cCI6MjEwNDI1NjI5OH0.CSCbuwInWJtGpL7w_nMFU6ElGWnXxr67bKeMWuTpMMM"

def get_supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
def get_all_customers_db():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    url = f"{SUPABASE_URL}/rest/v1/customers_master?select=*"
    try:
        response = requests.get(url, headers=get_supabase_headers(), timeout=10)
        if response.status_code == 200:
            rows = response.json()
            clients = []
            for r in rows:
                try:
                    sels = json.loads(r.get("selections_json", "[]"))
                except Exception:
                    sels = []
                clients.append({
                    "id": r.get("id"),
                    "name": r.get("name"),
                    "mobile": r.get("mobile"),
                    "address": r.get("address"),
                    "engineer": r.get("engineer"),
                    "salesman": r.get("salesman"),
                    "status": r.get("status", "SELECTION ONLY"),
                    "selections": sels,
                    "total_sqft": float(r.get("total_sqft", 0.0) or 0.0),
                    "total_boxes": float(r.get("total_boxes", 0.0) or 0.0),
                    "created_at": r.get("created_at"),
                    "branch": r.get("branch", "Hiriyur")
                })
            # Sort by ID descending so newest are on top
            clients.sort(key=lambda x: x["id"], reverse=True)
            return clients
    except Exception:
        pass
    return []

def insert_new_customer(name, mobile, address, engineer, salesman, branch, status="SELECTION ONLY", selections_json="[]", total_sqft=0.0, total_boxes=0.0):
    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "name": name,
        "mobile": mobile,
        "address": address,
        "engineer": engineer,
        "salesman": salesman,
        "branch": branch,
        "status": status,
        "selections_json": selections_json,
        "total_sqft": total_sqft,
        "total_boxes": total_boxes,
        "created_at": now_str
    }
    def update_customer_db(customer):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    cust_id = customer.get("id")
    url = f"{SUPABASE_URL}/rest/v1/customer_master?id=eq.{cust_id}"
    try:
        response = requests.patch(url, headers=get_supabase_headers(), json=customer, timeout=10)
        return response.status_code in [200, 204]
    except Exception as e:
        print(f"Error updating customer: {e}")
    return False
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {"id": int(datetime.now().timestamp()), **payload, "selections": []}
        
   url = f"{SUPABASE_URL}/rest/v1/customer_master"
    try:
        response = requests.post(url, headers=get_supabase_headers(), json=payload, timeout=10)
        print("Supabase Response:", response.status_code, response.text) # Yeh error print karega
        if response.status_code in [200, 201]:
            return response.json()
        else:
            st.error(f"DB Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Error inserting customer: {e}")
        st.error(f"Connection Exception: {e}")
    return None   if data and len(data) > 0:
                inserted = data[0]
                return {
                    "id": inserted.get("id"),
                    "name": inserted.get("name"),
                    "mobile": inserted.get("mobile"),
                    "address": inserted.get("address"),
                    "engineer": inserted.get("engineer"),
                    "salesman": inserted.get("salesman"),
                    "branch": inserted.get("branch", "Hiriyur"),
                    "status": inserted.get("status", "SELECTION ONLY"),
                    "selections": [],
                    "total_sqft": 0.0,
                    "total_boxes": 0.0,
                    "created_at": inserted.get("created_at")
                }
    except Exception:
        pass
    return {"id": int(datetime.now().timestamp()), **payload, "selections": []}

def update_customer_db(cust_dict):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
        
    cust_id = cust_dict.get("id")
    payload = {
        "name": cust_dict.get("name"),
        "mobile": cust_dict.get("mobile"),
        "address": cust_dict.get("address"),
        "engineer": cust_dict.get("engineer"),
        "salesman": cust_dict.get("salesman"),
        "branch": cust_dict.get("branch", "Hiriyur"),
        "status": cust_dict.get("status", "SELECTION ONLY"),
        "selections_json": json.dumps(cust_dict.get("selections", []), ensure_ascii=False),
        "total_sqft": float(cust_dict.get("total_sqft", 0.0)),
        "total_boxes": float(cust_dict.get("total_boxes", 0.0))
    }
    
    # Agar ID nahi hai ya update fail ho, toh insert kar do
    if cust_id:
        url = f"{SUPABASE_URL}/rest/v1/customer_master?id=eq.{cust_id}"
        try:
            response = requests.patch(url, headers=get_supabase_headers(), json=payload, timeout=10)
            if response.status_code in [200, 204]:
                return True
        except Exception as e:
            print(f"Update error: {e}")
            
    # Fallback: Agar ID na ho ya patch kaam na kare toh naya row insert kar do
    insert_url = f"{SUPABASE_URL}/rest/v1/customer_master"
    try:
        response = requests.post(insert_url, headers=get_supabase_headers(), json=payload, timeout=10)
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"Insert fallback error: {e}")
    return Falsedef delete_customer_db(cust_id):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    url = f"{SUPABASE_URL}/rest/v1/customers_master?id=eq.{cust_id}"
    try:
        requests.delete(url, headers=get_supabase_headers(), timeout=10)
    except Exception:
        pass

@st.cache_data(ttl=5)
def get_master_df():
    try:
        raw_df = pd.read_csv(GOOGLE_SHEET_CSV_URL, header=None, dtype=str)
        h_idx = 0
        for i in range(min(15, len(raw_df))):
            row_vals = [str(x).upper().strip() for x in raw_df.iloc[i].values if pd.notna(x)]
            if "ITEM NAME" in row_vals:
                h_idx = i
                break
                
        headers = [str(x).strip().upper() for x in raw_df.iloc[h_idx].values]
        data_rows = raw_df.iloc[h_idx + 1:].copy()
        
        item_col = 0
        cf_col = None
        pu_col = None
        
        for idx, h in enumerate(headers):
            if h == "ITEM NAME":
                item_col = idx
            elif h == "CON FACTOR":
                cf_col = idx
            elif "PACKING" in h:
                pu_col = idx

        if cf_col is None: cf_col = 7
        if pu_col is None: pu_col = 8

        parsed_stock = []
        for _, r in data_rows.iterrows():
            if item_col >= len(r) or not pd.notna(r.iloc[item_col]): 
                continue
            item_name = str(r.iloc[item_col]).strip()
            if not item_name or item_name.upper() in ["NAN", "ITEM NAME", "TOTAL", "NONE", "NULL", "UNNAMED", ""]:
                continue
            
            cf_val = 1.0
            if cf_col < len(r) and pd.notna(r.iloc[cf_col]):
                try:
                    cf_val = float(str(r.iloc[cf_col]).replace(',', '').strip())
                except Exception:
                    cf_val = 1.0
            if cf_val <= 0: cf_val = 1.0

            pu_val = 1.0
            if pu_col < len(r) and pd.notna(r.iloc[pu_col]):
                try:
                    pu_val = float(str(r.iloc[pu_col]).replace(',', '').strip())
                except Exception:
                    pu_val = 1.0
            if pu_val <= 0: pu_val = 1.0
                
            box_cov = round(cf_val * pu_val, 2)
            parsed_stock.append({
                "item_name": item_name,
                "con_factor": cf_val,
                "packing_unit": pu_val,
                "sqft_per_box": box_cov if box_cov > 0 else 1.0
            })
            
        df = pd.DataFrame(parsed_stock).drop_duplicates(subset=["item_name"])
        if not df.empty:
            return df
    except Exception as ex:
        st.error(f"Google Sheet Sync Error: {str(ex)}")
    return pd.DataFrame()
    def get_staff_users_db():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    url = f"{SUPABASE_URL}/rest/v1/staff_users?select=*"
    try:
        response = requests.get(url, headers=get_supabase_headers(), timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return []

def insert_staff_user_db(username, password, branch, role):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    url = f"{SUPABASE_URL}/rest/v1/staff_users"
    payload = {
        "username": username,
        "password": password,
        "branch": branch,
        "role": role
    }
    try:
        response = requests.post(url, headers=get_supabase_headers(), json=payload, timeout=10)
        return response.status_code in [200, 201]
    except Exception:
        return False

def delete_staff_user_db(user_id):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    url = f"{SUPABASE_URL}/rest/v1/staff_users?id=eq.{user_id}"
    try:
        response = requests.delete(url, headers=get_supabase_headers(), timeout=10)
        return response.status_code in [200, 204]
    except Exception:
        return False

def calculate_box_sqft(cf, pu):
    try:
        cov = float(cf) * float(pu)
        return round(cov, 2) if cov > 0 else 1.0
    except Exception:
        return 1.0

def calculate_boxes(sqft, cf, PU):
    try:
        cov = float(cf) * float(PU)
        if cov <= 0:
            cov = 1.0
        import math
        return math.ceil(float(sqft) / cov)
    except Exception:
        return 0
