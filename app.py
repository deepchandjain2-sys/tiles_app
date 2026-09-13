import streamlit as st
import pandas as pd
import math
from database import (
    get_all_customers, 
    save_customer_to_db, 
    delete_customer_from_db, 
    get_staff_users_db, 
    insert_staff_user_db, 
    delete_staff_user_db
)

st.set_page_config(page_title="Tiles & BOQ Management App", layout="wide")

# Session State Initialization
for key, default in [
    ('auth', False),
    ('username', ""),
    ('role', ""),
    ('branch', 'Hiriyur'),
    ('customer', None),
    ('selections', [])
]:
    if key not in st.session_state:
        st.session_state[key] = default

# --- LOGIN SCREEN ---
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
                    st.session_state.role = "admin"
                    st.session_state.branch = branch_choice
                    st.rerun()
                elif u and p:
                    staff_list = get_staff_users_db()
                    matched_role = "salesman"
                    matched_branch = branch_choice
                    login_valid = False
                    
                    for staff in staff_list:
                        if staff.get('username', '').strip().lower() == u.lower() and str(staff.get('password')) == str(p):
                            login_valid = True
                            matched_role = staff.get('role', 'salesman')
                            matched_branch = staff.get('branch', branch_choice)
                            break
                            
                    if login_valid:
                        st.session_state.auth = True
                        st.session_state.username = u
                        st.session_state.role = "admin" if str(matched_role).strip().lower() in ["admin", "executive"] else "salesman"
                        st.session_state.branch = matched_branch
                        st.rerun()
                    else:
                        st.error("Invalid Username or Password.")
                else:
                    st.error("Credentials enter karein.")
    st.stop()

# --- SIDEBAR NAVIGATION ---
st.sidebar.title(f"👤 {st.session_state.username.upper()}")
st.sidebar.markdown(f"**Role:** `{st.session_state.role.upper()}`")
st.sidebar.markdown(f"**Branch:** `{st.session_state.branch}`")

if st.sidebar.button("🚪 Sign Out", use_container_width=True):
    st.session_state.auth = False
    st.session_state.customer = None
    st.rerun()

nav_list = [
    "1. Customer Registration & History", 
    "2. Area & Tile Selection", 
    "3. Sq.Ft Entry & Final Estimate"
]

if st.session_state.role == "admin":
    nav_list.extend(["📊 Executive Dashboard", "⚙️ Staff & Stock Management"])

nav = st.sidebar.selectbox("Navigation Flow", nav_list)

# --- MAIN PAGES ---
if nav == "1. Customer Registration & History":
    st.title("📋 Customer Registration & Management")
    c_name = st.text_input("Customer Name")
    c_mobile = st.text_input("Mobile Number")
    c_address = st.text_area("Address")
    
    if st.button("Save Customer"):
        if c_name and c_mobile:
            cust_data = {
                "name": c_name,
                "mobile": c_mobile,
                "address": c_address,
                "branch": st.session_state.branch,
                "salesman": st.session_state.username,
                "selections": []
            }
            save_customer_to_db(cust_data)
            st.session_state.customer = cust_data
            st.success("Customer saved successfully!")
            st.rerun()
        else:
            st.error("Please enter Name and Mobile number.")

elif nav == "2. Area & Tile Selection":
    st.title("🏗️ Area & Tile Selection")
    if not st.session_state.get('customer'):
        st.warning("Please select a customer first on page 1.")
    else:
        cust = st.session_state['customer']
        st.info(f"Active Customer: {cust.get('name')} ({cust.get('mobile')})")
        floor = st.selectbox("Floor Level", ["Ground Floor", "1st Floor", "2nd Floor", "Other"])
        area_type = st.selectbox("Category", ["Floor", "Wall"])
        room = st.text_input("Area / Room Name", "Hall")
        
        tile_name = st.text_input("Tile Name / Code")
        sqft = st.number_input("Total Sq.Ft", min_value=0.0, value=100.0)
        
        if st.button("Add to Queue"):
            item = {"floor": floor, "category": area_type, "area": room, "tile_name": tile_name, "sqft": sqft, "boxes": math.ceil(sqft / 15.0), "total": sqft * 10}
            cust.setdefault('selections', []).append(item)
            save_customer_to_db(cust)
            st.success("Item added to queue!")

elif nav == "3. Sq.Ft Entry & Final Estimate":
    st.title("📋 BOQ Calculation & Finalize")
    if not st.session_state.get('customer'):
        st.warning("Please select a customer first.")
    else:
        cust = st.session_state['customer']
        selections = cust.get('selections', [])
        if not selections:
            st.info("Queue is empty.")
        else:
            for idx, s in enumerate(selections):
                st.write(f"{idx+1}. {s.get('area')} - {s.get('tile_name')} | {s.get('sqft')} sqft | Boxes: {s.get('boxes')}")
            if st.button("Finalize Order"):
                st.success("Order finalized!")

elif nav == "⚙️ Staff & Stock Management" and st.session_state.role == "admin":
    st.title("👥 Staff Management (Add/Remove Salesmen)")
    with st.form("add_staff_form"):
        new_u = st.text_input("New Salesman Username")
        new_p = st.text_input("Password", type="password")
        new_b = st.selectbox("Branch", ["Hiriyur", "Davangere"])
        if st.form_submit_button("Create Salesman"):
            if new_u and new_p:
                insert_staff_user_db(new_u, new_p, new_b, "salesman")
                st.success(f"Salesman {new_u} created successfully!")
                st.rerun()
            else:
                st.warning("Enter username and password.")
