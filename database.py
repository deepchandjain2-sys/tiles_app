import os
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "YOUR_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "YOUR_SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_all_customers():
    try:
        response = supabase.table("customers").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error fetching customers: {e}")
        return []

def save_customer_to_db(customer_data):
    try:
        phone_val = customer_data.get("mobile") or customer_data.get("phone")
        if phone_val:
            existing = supabase.table("customers").select("*").eq("mobile", phone_val).execute()
            if not existing.data:
                existing = supabase.table("customers").select("*").eq("phone", phone_val).execute()
            
            if existing.data and len(existing.data) > 0:
                cust_id = existing.data[0].get("id")
                supabase.table("customers").update(customer_data).eq("id", cust_id).execute()
                return True
                
        supabase.table("customers").insert(customer_data).execute()
        return True
    except Exception as e:
        print(f"Error saving customer: {e}")
        return False

def delete_customer_from_db(customer_id):
    try:
        if str(customer_id).isdigit():
            supabase.table("customers").delete().eq("id", int(customer_id)).execute()
        supabase.table("customers").delete().eq("id", str(customer_id)).execute()
        return True
    except Exception as e:
        print(f"Error deleting customer: {e}")
        return False

def get_all_admin_users():
    try:
        response = supabase.table("admin_users").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        return []
