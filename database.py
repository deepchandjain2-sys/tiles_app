import json
import requests

SUPABASE_URL = "https://gedzazirwxaxabnppchc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdlZHppemlyd3hheGFibnBjaGNjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDEyMzg2ODMsImV4cCI6MjA1NjgxNDY4M30.YOUR_ANON_KEY_HERE"

def get_supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

def save_customer_to_db(cust_dict):
    try:
        headers = get_supabase_headers()
        payload = {
            "name": cust_dict.get("name"),
            "mobile": cust_dict.get("mobile"),
            "address": cust_dict.get("address"),
            "engineer": cust_dict.get("engineer"),
            "salesman": cust_dict.get("salesman"),
            "branch": cust_dict.get("branch", "Hiriyur"),
            "status": cust_dict.get("status", "ACTIVE"),
            "selections_json": json.dumps(cust_dict.get("selections", []), ensure_ascii=False),
            "total_sqft": float(cust_dict.get("total_sqft", 0.0)),
            "total_boxes": float(cust_dict.get("total_boxes", 0.0))
        }
        url = f"{SUPABASE_URL}/rest/v1/customer_master"
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        return res.status_code in [200, 201]
    except Exception as e:
        return False
