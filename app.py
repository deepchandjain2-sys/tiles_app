import streamlit as st
import pandas as pd
import math
import urllib.parse
from database import get_all_customers, save_customer_to_db, delete_customer_from_db, get_staff_users_db, insert_staff_user_db, delete_staff_user_db

st.set_page_config(page_title="Tiles & BOQ Management App", layout="wide")

# Session state defaults
for key, default in [
    ('auth', False),
    ('username', ""),
    ('role', ""),
    ('branch', 'Hiriyur'),
    ('selected_customer', None),
    ('selections', []),
    ('clear_form_flag', False)
]:
    if key not in st.session_state:
        st.session_state[key] = default

# --- 1. LOGIN SCREEN (Jab tak login nahi hoga, yehi chalega) ---
if not st.session_state.auth:
    st.title("🏛️ Jay Granite & Tiles Portal")
    st.caption("Enterprise Tile Selection & Quotation Engine")
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.subheader("🔐 Staff Sign In")
        with st.form("login_form"):
            role_type = st.radio("Account Role", ["Salesman", "Admin"], horizontal=True)
            if role_type == "Salesman":
                branch_choice = st.selectbox("Select Branch / Showroom", ["Hiriyur", "Davangere"])
            else:
                branch_choice = st.selectbox("Select View / Showroom", ["All Showrooms", "Hiriyur", "Davangere"])
                
            u = st.text_input("Username").strip()
            p = st.text_input("Password", type="password").strip()
            submit = st.form_submit_button("🚀 Sign In", type="primary", use_container_width=True)
            
            if submit:
                # Master Admin Bypass
                if (u.upper() in ["DEEPCHAND JAIN", "ADMIN", "GOURAV"] and p in ["deep123", "pass123", "admin123", "GOURAV", "deep1965", "1234"]) or (role_type == "Admin" and p in ["deep123", "admin123", "1234"]):
                    st.session_state.auth = True
                    st.session_state.username = u if u else "DEEPCHAND JAIN"
                    st.session_state.role = "Admin"
                    st.session_state.branch = branch_choice
                    st.rerun()
                else:
                    staff_list = get_staff_users_db()
                    matched_staff = None
                    for staff in staff_list:
                        if staff.get('username') == u and staff.get('password') == p:
                            matched_staff = staff
                            break
                    if matched_staff:
                        st.session_state.auth = True
                        st.session_state.username = u
                        st.session_state.role = matched_staff.get('role', 'Salesman')
                        st.session_state.branch = matched_staff.get('branch', branch_choice)
                        st.rerun()
                    else:
                        st.error("Invalid Username or Password.")
        st.stop() # Yahin rok dega taaki login ke baad hi aage ka page khule

# --- 2. MAIN APPLICATION (Login ke baad ka hissa) ---
st.sidebar.title(f"👤 {st.session_state.username.upper()}")
st.sidebar.markdown(f"**Role:** `{st.session_state.role.upper()}`")
st.sidebar.markdown(f"**Branch:** `{st.session_state.branch}`")

if st.sidebar.button("🚪 Sign Out", use_container_width=True):
    st.session_state.auth = False
    st.session_state.selected_customer = None
    st.session_state.selections = []
    st.rerun()

page = st.sidebar.selectbox("Navigation Flow", ["1. Customer Registration", "2. Area & Tile Selection", "3. BOQ Calculation & Finalize"])

if page == "1. Customer Registration":
    st.title("📋 Customer Registration & Management")
    
    c_name = st.text_input("Customer Name")
    c_phone = st.text_input("Phone Number")
    engineer_name = st.text_input("Engineer Name")
    engineer_mobile = st.text_input("Engineer Mobile")
    cust_address = st.text_area("Address")
    
    if st.button("Save Customer"):
        if c_name and c_phone:
            cust_data = {
                "name": c_name, "mobile": c_phone, "phone": c_phone,
                "engineer": engineer_name, "engineer_mobile": engineer_mobile,
                "address": cust_address, "branch": st.session_state.branch,
                "salesman": st.session_state.username
            }
            if save_customer_to_db(cust_data):
                st.success(f"Customer {c_name} saved successfully!")
                st.rerun()
            else:
                st.error("Failed to save customer.")
        else:
            st.error("Please enter Customer Name and Phone number.")
            
    st.markdown("### Registered Customers")
    customers = get_all_customers()
    if customers:
        for idx, c in enumerate(customers):
            c_id = c.get('id', str(idx))
            c_phone = c.get('mobile', '') or c.get('phone', 'no_phone')
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{c.get('name')}** | Mobile: {c_phone}")
            with col2:
                if st.button("Select for Tiles", key=f"select_cust_{c_id}_{idx}"):
                    st.session_state.selected_customer = c
                    st.success(f"Selected customer: {c.get('name')}")
    else:
        st.info("No customers found.")
