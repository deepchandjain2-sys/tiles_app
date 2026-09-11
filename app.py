import streamlit as st
import math
from database import (
    get_all_customers, 
    save_customer_to_db, 
    delete_customer_from_db, 
    get_all_admin_users, 
    add_admin_user, 
    delete_admin_user
)

# Page Configuration
st.set_page_config(page_title="Tiles & BOQ Management App", layout="wide")

# Session State Initialization
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'user' not in st.session_state:
    st.session_state['user'] = None
if 'role' not in st.session_state:
    st.session_state['role'] = None
if 'branch' not in st.session_state:
    st.session_state['branch'] = None

# Authentication Check
if not st.session_state['authenticated']:
    st.title("🔐 Admin & Salesman Login")
    login_username = st.text_input("Username", key="login_user_input")
    login_password = st.text_input("Password", type="password", key="login_pass_input")
    
    if st.button("Login", key="login_btn"):
        admins = get_all_admin_users()
        user_found = False
        for adm in admins:
            if adm.get('username') == login_username and adm.get('password') == login_password:
                st.session_state['authenticated'] = True
                st.session_state['user'] = login_username
                st.session_state['role'] = adm.get('role', 'SALESMAN')
                st.session_state['branch'] = adm.get('branch', 'Hiriyur')
                user_found = True
                st.success("Login Successful!")
                st.rerun()
        if not user_found:
            st.error("Invalid Username or Password")
    st.stop()

# Sidebar Navigation & User Info
st.sidebar.markdown(f"**User:** {st.session_state.get('user')}")
st.sidebar.markdown(f"**Role:** {st.session_state.get('role')}")
st.sidebar.markdown(f"**Showroom Branch:**")
branch = st.sidebar.selectbox("Branch", ["Hiriyur", "Other Branch"], index=0, key="sidebar_branch_select")
st.session_state['branch'] = branch

st.sidebar.markdown("---")
st.sidebar.markdown("### Navigation Flow")
menu = st.sidebar.selectbox("Select Page", [
    "1. Customer Registration", 
    "2. Tile Selection & BOQ", 
    "3. Calculation & Final Estimate", 
    "Dashboard & Salesman Summary", 
    "Admin User Management"
], key="main_navigation_selectbox")

if st.sidebar.button("Sign Out", key="signout_btn"):
    st.session_state['authenticated'] = False
    st.session_state['user'] = None
    st.session_state['role'] = None
    st.rerun()

#-- PAGE 1: CUSTOMER REGISTRATION --
if menu == "1. Customer Registration":
    st.title("Step 1: Customer Registration / Party Selection")
    
    st.markdown("### 📝 Register New Customer / Party")
    with st.form("customer_reg_form"):
        cust_name = st.text_input("Customer / Party Name")
        cust_mobile = st.text_input("Mobile Number (Unique ID)")
        cust_address = st.text_area("Site Address")
        
        submitted = st.form_submit_button("Register & Proceed")
        if submitted:
            if cust_name and cust_mobile:
                cust_data = {
                    "name": cust_name,
                    "mobile": cust_mobile,
                    "address": cust_address,
                    "branch": st.session_state['branch'],
                    "selections": []
                }
                if save_customer_to_db(cust_data):
                    st.session_state['customer'] = cust_data
                    st.success(f"Customer '{cust_name}' registered successfully!")
                else:
                    st.error("Failed to save customer to database.")
            else:
                st.error("Please fill in both Customer Name and Mobile Number.")

    st.markdown("---")
    st.markdown("### 📂 Permanent Existing Customers / Parties List")
    customers = get_all_customers()
    
    if customers:
        cust_options = {f"{c.get('name')} ({c.get('mobile', 'No Mobile')})": c for c in customers}
        selected_cust_key = st.selectbox("Select Party / Customer to Modify", list(cust_options.keys()), key="existing_cust_selectbox")
        
        if selected_cust_key:
            active_c = cust_options[selected_cust_key]
            st.session_state['customer'] = active_c
            
            st.write(f"**Active Party Selected:** {active_c.get('name')} | **Mobile:** {active_c.get('mobile')}")
            
            safe_selections = active_c.get('selections', []) or []
            st.write(f"**Current Selections Count:** {len(safe_selections)} items")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("Load this Customer for Tile Modification", key="load_cust_btn"):
                    st.success(f"Customer '{active_c.get('name')}' loaded! Now go to '2. Tile Selection & BOQ'.")
            with col_btn2:
                if st.button("Delete Customer Permanently", key="del_cust_btn"):
                    if delete_customer_from_db(active_c.get('mobile')):
                        st.success("Customer deleted successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to delete customer.")
    else:
        st.info("No existing customers found in the database.")

#-- PAGE 2: TILE SELECTION & BOQ --
elif menu == "2. Tile Selection & BOQ":
    st.title("Step 2: Area-wise Tile Selection")

    if not st.session_state.get('customer'):
        st.warning("Please register a customer first from '1. Customer Registration'.")
    else:
        cust = st.session_state['customer']
        st.info(f"**Active Customer:** {cust.get('name')} | **Mobile:** {cust.get('mobile')} | **Branch:** {cust.get('branch')}")
        
        st.markdown("### 🏗️ Building & Floor Selection")
        
        floor_level = st.selectbox("Select Floor Level", [
            "-- Select Floor Level --",
            "Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "Other / Independent Area"
        ], key="floor_level_selectbox")
        
        area_type = st.selectbox("Select Building Area / Room", [
            "-- Select Area Type --",
            "Hall Floor", "Kitchen Floor", "Master Bedroom Floor", "Common Bedroom Floor",
            "3rd Bedroom Floor", "4th Bedroom Floor", "Associated Bathroom Floor", "Custom Area"
        ], key="area_type_selectbox")
        
        if area_type == "Custom Area":
            custom_area_name = st.text_input("Enter Custom Area Name", key="custom_area_input")
        else:
            custom_area_name = area_type

        if floor_level != "-- Select Floor Level --" and area_type != "-- Select Area Type --":
            st.markdown("---")
            st.markdown(f"### 📐 Dimensions & Box Calculation for: {floor_level} -> {custom_area_name}")
            
            col1, col2 = st.columns(2)
            with col1:
                area_sqft = st.number_input("Total Area (Sq. Ft.)", min_value=0.0, value=100.0, step=1.0, key="area_sqft_input")
            with col2:
                box_coverage = st.number_input("Box Coverage (Sq. Ft. per Box)", min_value=0.1, value=15.0, step=0.5, key="box_cov_input")
                tile_price = st.number_input("Price per Box (₹)", min_value=0.0, value=600.0, step=50.0, key="tile_price_input")

            # Calculation without wastage
            exact_boxes = area_sqft / box_coverage if box_coverage > 0 else 0
            rounded_boxes = math.ceil(exact_boxes)
            total_est_cost = rounded_boxes * tile_price

            st.markdown("#### 📦 Calculation Summary")
            m1, m2, m3 = st.columns(3)
            m1.metric("Net Area", f"{area_sqft} sq.ft")
            m2.metric("Required Boxes (Rounded)", f"{rounded_boxes} Boxes")
            m3.metric("Estimated Cost", f"₹ {total_est_cost}")

            if st.button("Add This Area to Customer Order", key="add_area_btn"):
                selection_entry = {
                    "floor": floor_level,
                    "area": custom_area_name,
                    "sqft": area_sqft,
                    "boxes": rounded_boxes,
                    "price_per_box": tile_price,
                    "total_cost": total_est_cost
                }
                if 'selections' not in cust:
                    cust['selections'] = []
                cust['selections'].append(selection_entry)
                save_customer_to_db(cust)
                st.success(f"Added {custom_area_name} successfully! Go to Step 3 to view final BOQ.")

#-- PAGE 3: CALCULATION & FINAL ESTIMATE --
elif menu == "3. Calculation & Final Estimate":
    st.title("Step 3: Calculation, Box Management & BOQ Estimate")
    if not st.session_state.get('customer'):
        st.warning("Please register or select a customer first from '1. Customer Registration'.")
    else:
        cust = st.session_state['customer']
        st.info(f"**Customer:** {cust.get('name')} | **Mobile:** {cust.get('mobile')}")
        
        selections = cust.get('selections', [])
        if not selections:
            st.info("No tile selections added yet. Please go to '2. Tile Selection & BOQ' to add areas.")
        else:
            st.markdown("### 📋 Final Bill of Quantities (BOQ)")
            total_grand_boxes = 0
            total_grand_cost = 0.0
            
            for idx, item in enumerate(selections):
                st.write(f"**{idx+1}. {item.get('floor')} - {item.get('area')}**")
                st.write(f"Area: {item.get('sqft')} sq.ft | Boxes: **{item.get('boxes')}** | Cost: ₹{item.get('total_cost')}")
                total_grand_boxes += item.get('boxes', 0)
                total_grand_cost += item.get('total_cost', 0.0)
                st.markdown("---")
            
            st.markdown(f"### Grand Total Boxes: **{total_grand_boxes} Boxes**")
            st.markdown(f"### Grand Total Estimate: **₹ {total_grand_cost}**")
            
            # WhatsApp Share Link Generator
            whatsapp_msg = f"*Tile Estimation BOQ - {cust.get('name')}*\n"
            whatsapp_msg += f"Mobile: {cust.get('mobile')}\n"
            whatsapp_msg += f"Total Boxes: {total_grand_boxes}\n"
            whatsapp_msg += f"Total Amount: ₹{total_grand_cost}\n"
            
            encoded_msg = whatsapp_msg.replace(' ', '%20').replace('\n', '%0A')
            whatsapp_url = f"https://wa.me/{cust.get('mobile')}?text={encoded_msg}"
            
            st.markdown(f"[📲 Send Estimate via WhatsApp]({whatsapp_url})", unsafe_allow_html=True)

#-- DASHBOARD & SALESMAN SUMMARY --
elif menu == "Dashboard & Salesman Summary":
    st.title("📊 Dashboard & Salesman Summary")
    st.write("Summary metrics and analytics.")

#-- ADMIN USER MANAGEMENT --
elif menu == "Admin User Management":
    st.title("⚙️ Admin User Management")
    if st.session_state.get('role') != 'ADMIN':
        st.error("Access Denied! Only ADMIN can access this page.")
    else:
        st.write("Manage system users here.")
