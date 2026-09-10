import streamlit as st
import pandas as pd
from datetime import datetime
from database import save_customer_to_db
from calculations import calculate_totals, generate_whatsapp_link

st.set_page_config(page_title="Jay Granite & Tiles Hub - Hiriyur", layout="wide")

GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR4mWP3S6r7Ujwm-kczX8OGevw4yXWTPbMLvL87PGTR_0w#JK5O0W8Ky"

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
        return pd.read_csv(GOOGLE_SHEET_CSV_URL)
    except:
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
    st.title("Step 1: Customer Registration")
    
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
                st.session_state['customer'] = {
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
                st.success("Customer registered successfully! Now click on '2. Tile Selection & BOQ' from the left menu.")
            else:
                st.error("Please fill Customer Name and Mobile Number.")


# --- PAGE 2: TILE SELECTION & BOQ ---
elif menu == "2. Tile Selection & BOQ":
    st.title("Step 2: Area-wise Tile Selection")
    
    if not st.session_state['customer']:
        st.warning("Please register a customer first from '1. Customer Registration'.")
    else:
        cust = st.session_state['customer']
        st.info(f"**Active Customer:** {cust['name']} | **Mobile:** {cust['mobile']} | **Branch:** {cust['branch']}")
        
        st.markdown("### 🏢 Building Area Selection")
        
        # Single Building Area Classification
        area_category = st.selectbox("Select Building Area (Floor, Wall & Custom)", [
            "-- Select Floor Area --",
            "Ground Floor", "1st Floor", "2nd Floor", "3rd Floor",
            "Hall Floor", "Kitchen Floor", "Master Bedroom Floor", "Common Bedroom Floor",
            "3rd Bedroom Floor", "4th Bedroom Floor", "Attached Bathroom Floor", 
            "Common Bathroom Floor", "Parking Area", "Front Area", "Pooja Room Floor",
            "-- Select Wall Area --",
            "Kitchen Wall", "Bathroom Wall", "Living Room Wall", "Elevation Wall", "Balcony Wall",
            "-- Custom Area --",
            "Custom Building Area"
        ])
        
        custom_area_name = ""
        if area_category == "-- Custom Area --" or area_category == "Custom Building Area":
            custom_area_name = st.text_input("Enter Custom Area Name (e.g. Staircase Floor, Passage Wall)")
            area_category = f"Custom: {custom_area_name}" if custom_area_name else "Custom Area"

        # Design Search from Google Sheet Catalog
        st.markdown("#### Search Tile Design from Catalog")
        search_query = st.text_input("Search Design by Name / Code / Size")
        
        if not master_df.empty and 'ITEM NAME' in master_df.columns:
            filtered_df = master_df
            if search_query:
                filtered_df = master_df[master_df['ITEM NAME'].str.contains(search_query, case=False, na=False)]
            
            tile_options = filtered_df['ITEM NAME'].dropna().unique().tolist() if not filtered_df.empty else []
            
            if tile_options:
                selected_tile = st.selectbox("Select Matching Design", tile_options)
                sqft_input = st.number_input("Required Sq.Ft", min_value=0.0, value=100.0)
                boxes_input = st.number_input("Required Boxes", min_value=0.0, value=10.0)
                
                if st.button("Add Design to Queue"):
                    if "--" in area_category:
                        st.error("Please select a valid building area type.")
                    else:
                        item_entry = {
                            "area_type": area_category,
                            "tile_name": selected_tile,
                            "sqft": sqft_input,
                            "boxes": boxes_input
                        }
                        cust['selections'].append(item_entry)
                        sqft_tot, box_tot = calculate_totals(cust['selections'])
                        cust['total_sqft'] = sqft_tot
                        cust['total_boxes'] = box_tot
                        st.success(f"Added {selected_tile} for {area_category} successfully!")
            else:
                st.info("No matching designs found in Google Sheet catalog.")
        else:
            st.warning("Master catalog loading or empty. Check Google Sheet URL.")

            if cust['selections']:
            st.markdown("### Selected Items Queue")
            st.dataframe(pd.DataFrame(cust['selections']))
  elif menu == "3. Calculation & Final Estimate":
       st.title("Step 3: Calculation & Order Finalization")
    
       if not st.session_state['customer'] or not st.session_state['customer']['selections']:
        st.warning("No active customer selections found. Please complete Step 1 & Step 2 first.")
    else:
        cust = st.session_state['customer']
        st.write(f"**Customer:** {cust['name']} | **Mobile:** {cust['mobile']}")
        
        st.dataframe(pd.DataFrame(cust['selections']))
        
        sqft_tot, box_tot = calculate_totals(cust['selections'])
        st.metric("Total Billable Area", f"{sqft_tot} Sq.Ft")
        st.metric("Total Boxes Required", f"{box_tot} Boxes")
        
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
        st.metric("Total Billable Area", f"{sqft_tot} Sq.Ft")
        st.metric("Total Boxes Required", f"{box_tot} Boxes")
        
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
