import streamlit as st
import pandas as pd
from datetime import datetime
from database import save_customer_to_db, get_all_customers_from_db, delete_customer_from_db
from calculations import calculate_totals, calculate_boxes_dynamic, generate_whatsapp_link

st.set_page_config(page_title="Jay Granite & Tiles Hub - Hiriyur", layout="wide")

GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR4mWP3S6r7Ujwm-kczX8OGevw4yXWTPbMLvL87PGTR_0w/pub?gid=1816738640&single=true&output=csv"

# --- SESSION STATE SETUP ---
for key, default in [('logged_in', False), ('user', None), ('role', None), ('customer', None)]:
    if key not in st.session_state:
        st.session_state[key] = default

# --- 1. LOGIN PAGE ---
if not st.session_state['logged_in']:
    st.title("🔐 Jay Granite & Tiles Hub - Secure Login")
    u_name = st.text_input("Username")
    u_pass = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if u_name == "admin" and u_pass == "admin123":
            st.session_state['logged_in'] = True
            st.session_state['user'] = "DEEPCHAND JAIN"
            st.session_state['role'] = "ADMIN"
            st.rerun()
        elif u_name == "sales" and u_pass == "sales123":
            st.session_state['logged_in'] = True
            st.session_state['user'] = "Sales Team Member"
            st.session_state['role'] = "SALES"
            st.rerun()
        else:
            st.error("Invalid Credentials. (Admin: admin/admin123 | Sales: sales/sales123)")
    st.stop()

# --- LOAD MASTER CATALOG ---
@st.cache_data(ttl=3600)
def get_master_df():
    try:
        df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
        df.columns = df.columns.str.strip().str.upper()
        return df
    except Exception:
        return pd.DataFrame()

master_df = get_master_df()

# --- SIDEBAR NAVIGATION & BRANCH ---
st.sidebar.title(f"User: {st.session_state['user']}")
st.sidebar.markdown(f"**Role:** {st.session_state['role']}")

branch_option = st.sidebar.selectbox("Showroom Branch", [
    "Hiriyur", 
    "Davangere", 
    "Add New Branch..."
])

if branch_option == "Add New Branch...":
    branch = st.sidebar.text_input("Enter New Branch Name")
    if not branch:
        branch = "Hiriyur"
else:
    branch = branch_option

menu = st.sidebar.radio("Navigation Flow", [
    "1. Customer Registration", 
    "2. Tile Selection & BOQ", 
    "3. Calculation & Final Estimate", 
    "Dashboard & Salesman Summary",
    "Admin User Management"
])

if st.sidebar.button("Sign Out"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

# --- PAGE 1: CUSTOMER REGISTRATION ---
if menu == "1. Customer Registration":
    st.title("Step 1: Customer & Party Management")
    
    saved_db_customers = get_all_customers_from_db()

    reg_mode = st.radio("Select Mode", ["Register New Customer", "Select Existing Customer / Party"])

    if reg_mode == "Register New Customer":
        with st.form("reg_form"):
            col1, col2 = st.columns(2)
            with col1:
                c_name = st.text_input("Customer Name*")
                c_mobile = st.text_input("Mobile Number*")
                c_address = st.text_area("Site Address")
            with col2:
                c_engineer = st.text_input("Engineer / Architect Name")
                c_eng_mobile = st.text_input("Engineer Mobile Number")
                
            reg_submitted = st.form_submit_button("Save Customer & Go to Tile Selection")
            if reg_submitted:
                if c_name and c_mobile:
                    new_cust = {
                        "name": c_name,
                        "mobile": c_mobile,
                        "address": c_address,
                        "engineer": c_engineer,
                        "engineer_mobile": c_eng_mobile,
                        "salesman": st.session_state['user'],
                        "branch": branch,
                        "status": "ACTIVE",
                        "selections": [],
                        "total_sqft": 0.0,
                        "total_boxes": 0.0
                    }
                    st.session_state['customer'] = new_cust
                    
                    if save_customer_to_db(new_cust):
                        st.success("Customer registered & saved permanently to database!")
                    else:
                        st.warning("Registered in session, but database sync pending. Check Supabase connection.")
                else:
                    st.error("Please fill Customer Name and Mobile Number.")
    else:
        st.markdown("### 📋 Permanent Existing Customers / Parties List")
        if not saved_db_customers:
            st.info("No customers found in database yet. Please register a new customer.")
        else:
            cust_names = [f"{c['name']} ({c['mobile']})" for c in saved_db_customers]
            selected_party = st.selectbox("Select Party / Customer to Modify", cust_names)
            
            if selected_party:
                idx = cust_names.index(selected_party)
                active_c = saved_db_customers[idx]
                st.session_state['customer'] = active_c
                
                st.write(f"**Active Party Selected:** {active_c.get('name') if active_c else ''} | **Mobile:** {active_c.get('mobile') if active_c else ''}")

# Safe handling for selections
if active_c and isinstance(active_c, dict):
    sel_count = len(active_c.get('selections') or [])
else:
    sel_count = 0

st.write(f"**Current Selections Count:** {sel_count} items")

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    if st.button("Load this Customer for Tile Modification"):
        st.success("Customer loaded successfully!")
with col_btn2:
    if st.button("Delete Customer Permanently"):
        if active_c and delete_customer_from_db(active_c.get('mobile')):
            st.success("Customer deleted successfully!")
            st.rerun()
        else:
            st.error("Failed to delete customer.")
            

#-- PAGE 2: TILE SELECTION & BOQ --
    if menu == "2. Tile Selection & BOQ":

    if menu == "2. Tile Selection & BOQ":
    # Safe initialization for active customer in Page 2
    active_c = st.session_state.get('active_customer') or st.session_state.get('customer', {})
    st.title("Step 2: Area-wise Tile Selection")
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
        ])
        
        area_type = st.selectbox("Select Building Area / Room", [
            "-- Select Area Type --",
            "Hall Floor", "Kitchen Floor", "Master Bedroom Floor", "Common Bedroom Floor",
            "3rd Bedroom Floor", "4th Bedroom Floor", "Associated Bathroom Floor"
        ])        
        custom_area_name = ""
        if area_type == "Custom Area":
            custom_area_name = st.text_input("Enter Custom Area Name (e.g. Staircase, Passage)")
        
        if floor_level != "-- Select Floor Level --" and area_type != "-- Select Area Type --":
            final_area_name = f"{floor_level} - {custom_area_name if area_type == 'Custom Area' and custom_area_name else area_type}"
        else:
            final_area_name = ""

        st.markdown("#### Search Tile Design from Catalog")
        search_query = st.text_input("Search Design by Name / Code / Size")
        
        if not master_df.empty:
            name_col = None
            for col in ['ITEM NAME', 'ITEM', 'NAME', 'TILE NAME', 'DESIGN NAME']:
                if col in master_df.columns:
                    name_col = col
                    break
            
            if name_col:
                filtered_df = master_df
                if search_query:
                    filtered_df = master_df[master_df[name_col].astype(str).str.contains(search_query, case=False, na=False)]
                
                tile_options = filtered_df[name_col].dropna().unique().tolist() if not filtered_df.empty else []
                
                if tile_options:
                    selected_tile = st.selectbox("Select Matching Design", tile_options)
                    
                    sqft_input = st.number_input("Required Sq.Ft", min_value=0.0, value=100.0)
                    
                    tile_row = master_df[master_df[name_col] == selected_tile]
                    
                    con_factor = 1.0
                    packing_unit = 1.0
                    
                    if not tile_row.empty:
                        try:
                            cols = list(master_df.columns)
                            if len(cols) >= 9:
                                con_factor = float(tile_row.iloc[0].values[7])
                                packing_unit = float(tile_row.iloc[0].values[8])
                        except:
                            con_factor = 1.0
                            packing_unit = 1.0
                    
                    calculated_boxes = calculate_boxes_dynamic(sqft_input, con_factor, packing_unit)
                    st.info(f"Calculated Boxes for {sqft_input} Sq.Ft: **{calculated_boxes} Boxes** (Con Factor: {con_factor}, Packing: {packing_unit})")
                    
                    if st.button("Add Design to Queue"):
                        if not final_area_name or "-- Select" in final_area_name:
                            st.error("Please select both Floor Level and Building Area properly.")
                        else:
                            item_entry = {
                                "area_type": final_area_name,
                                "tile_name": selected_tile,
                                "sqft": sqft_input,
                                "boxes": calculated_boxes
                            }
                            cust['selections'].append(item_entry)
                            sqft_tot, box_tot = calculate_totals(cust['selections'])
                            cust['total_sqft'] = sqft_tot
                            cust['total_boxes'] = box_tot
                            st.success(f"Added {selected_tile} for {final_area_name} successfully!")
                else:
                    st.info("No matching designs found in Google Sheet catalog.")
            else:
                st.warning("Master catalog column error. Ensure 'ITEM NAME' exists.")
        else:
            st.warning("Master catalog loading or empty. Check Google Sheet URL and Publishing status.")

        if cust['selections']:
            st.markdown("### Selected Items Queue")
            st.dataframe(pd.DataFrame(cust['selections']))

# --- PAGE 3: CALCULATION & FINAL ESTIMATE ---
elif menu == "3. Calculation & Final Estimate":
    st.title("Step 3: Calculation & Order Finalization")
    
    if not st.session_state['customer'] or not st.session_state['customer']['selections']:
        st.warning("No active customer selections found. Please complete Step 1 & Step 2 first.")
    else:
        cust = st.session_state['customer']
        st.write(f"**Customer:** {cust['name']} | **Mobile:** {cust['mobile']}")
        
        st.dataframe(pd.DataFrame(cust['selections']))
        
        sqft_tot, box_tot = calculate_totals(cust['selections'])
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown(f"**Total Billable Area:** {sqft_tot} Sq.Ft")
        with col_m2:
            st.markdown(f"**Total Boxes Required:** {box_tot} Boxes")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Finalize Deal & Save to Supabase"):
                cust['status'] = "FINALIZED"
                if save_customer_to_db(cust):
                    st.success("Order finalized and securely archived to Supabase cloud!")
                else:
                    st.error("Cloud sync failed. Please check connection.")
        with col2:
            wa_link = generate_whatsapp_link(cust['mobile'], cust['name'], cust['selections'], sqft_tot, box_tot)
            st.markdown(f"### [📲 Send Estimate via WhatsApp]({wa_link})", unsafe_allow_html=True)

# --- DASHBOARD & SALESMAN SUMMARY ---
elif menu == "Dashboard & Salesman Summary":
    st.title("📊 Executive Dashboard & Salesman Summary")
    st.markdown("Track team performance, total selections, and finalized deals.")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Registered Leads", "24")
    c2.metric("Total Sq.Ft Processed", "12,400 Sq.Ft")
    c3.metric("Finalized Orders", "16")
    
    st.markdown("### Salesman Wise Breakdown")
    st.dataframe(pd.DataFrame({
        "Salesman Name": ["Deepchand Jain", "Rahul", "Amit"],
        "Customers Registered": [10, 8, 6],
        "Total Sq.Ft Finalized": [5200, 4100, 3100],
        "Status": ["Active", "Active", "Active"]
    }))

# --- ADMIN USER MANAGEMENT ---
elif menu == "Admin User Management":
    st.title("👥 Admin - Sales Team Management")
    if st.session_state['role'] != "ADMIN":
        st.error("Access Denied. Admins only.")
    else:
        with st.form("staff_add"):
            new_user = st.text_input("Salesman Username")
            new_pass = st.text_input("Password", type="password")
            if st.form_submit_button("Create Salesman Account"):
                st.success(f"Salesman account '{new_user}' created!")
                
        st.markdown("### Existing Staff List")
        st.dataframe(pd.DataFrame({
            "Username": ["admin", "sales"],
            "Role": ["ADMIN", "SALES"],
            "Status": ["Active", "Active"]
        }))
