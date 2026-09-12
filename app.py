import streamlit as st
import pandas as pd
import math
import os
from database import get_all_customers, save_customer_to_db, delete_customer_from_db, get_all_admin_users

GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRAMSp-l-7Ulm-KX80pqxVke8L87GTR_JckbGMwy-_WkYpTInHS02N4r-vV/pub?gid=0&single=true&output=csv"

@st.cache_data(ttl=0)
def load_catalog_from_google_sheet():
    try:
        df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
        df.columns = df.columns.str.strip().str.lower()
        
        rename_map = {}
        for col in df.columns:
            if 'name' in col or 'tile' in col:
                rename_map[col] = 'name'
            elif 'cat' in col:
                rename_map[col] = 'category'
            elif 'cov' in col or 'box' in col:
                rename_map[col] = 'box_cov'
            elif 'price' in col or 'rate' in col:
                rename_map[col] = 'price'
                
        df = df.rename(columns=rename_map)
        
        required_cols = ['name', 'category', 'box_cov', 'price']
        for rc in required_cols:
            if rc not in df.columns:
                df[rc] = 'Default' if rc in ['name', 'category'] else 0.0
                
        return df.to_dict(orient="records")
    except Exception as e:
        st.error(f"Google Sheet Error: {e}")
        return [
            {"name": "Glossy Vitrified Tile 600x600mm", "category": "Floor", "box_cov": 15.0, "price": 600.0}
        ]

CATALOG_ITEMS = load_catalog_from_google_sheet()

def calculate_tile_boxes(area_sqft, box_coverage_sqft):
    if box_coverage_sqft <= 0:
        return 0, 0
    boxes = math.ceil(area_sqft / box_coverage_sqft)
    return boxes, area_sqft

st.set_page_config(page_title="Tiles & BOQ Management App", layout="wide")

# Initialize session state variables
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "role" not in st.session_state:
    st.session_state["role"] = ""
if "selected_customer" not in st.session_state:
    st.session_state["selected_customer"] = None

# Authentication Check
if not st.session_state["authenticated"]:
    st.title("🔐 Login - Tiles & BOQ App")
    login_user = st.text_input("Username")
    login_pass = st.text_input("Password", type="password")
    
    if st.button("Login"):
        admins = get_all_admin_users()
        matched = False
        user_role = "ADMIN"
        
        if login_user == "admin" and login_pass == "admin123":
            matched = True
            user_role = "ADMIN"
        else:
            for adm in admins:
                if adm.get("username") == login_user and adm.get("password") == login_pass:
                    matched = True
                    user_role = adm.get("role", "ADMIN")
                    break
                    
        if matched:
            st.session_state["authenticated"] = True
            st.session_state["username"] = login_user
            st.session_state["role"] = user_role
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Invalid Username or Password")
            
else:
    # Sidebar Navigation & User Info
    st.sidebar.write(f"**User:** {st.session_state['username']}")
    st.sidebar.write(f"**Role:** {st.session_state['role']}")
    
    # Showroom branch options with manual entry support for New Show Room
    branch_selection = st.sidebar.selectbox("Showroom Branch", ["Hiriyur", "Davangere", "New Show Room"])
    if branch_selection == "New Show Room":
        custom_branch = st.sidebar.text_input("Enter New Showroom Name", "Showroom Branch 3")
        branch_name = custom_branch
    else:
        branch_name = branch_selection
    
    st.sidebar.markdown(f"**Active Branch:** {branch_name}")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Navigation Flow")
    page = st.sidebar.selectbox("Select Page", ["1. Customer Registration", "2. Area-wise Tile Selection"])
    
    if st.sidebar.button("Sign Out"):
        st.session_state["authenticated"] = False
        st.session_state["username"] = ""
        st.session_state["role"] = ""
        st.session_state["selected_customer"] = None
        st.rerun()
        
    if page == "1. Customer Registration":
        st.title("📋 Customer Registration & Management")
        
        with st.form("customer_form"):
            cust_name = st.text_input("Customer Name")
            cust_phone = st.text_input("Phone Number")
            engineer_name = st.text_input("Engineer Name")
            engineer_mobile = st.text_input("Engineer Mobile")
            cust_address = st.text_area("Address")
            
            submitted = st.form_submit_button("Save Customer to Supabase")
            if submitted:
                if cust_name and cust_phone:
                    cust_data = {
                        "name": cust_name,
                        "phone": cust_phone,
                        "engineer_name": engineer_name,
                        "engineer_mobile": engineer_mobile,
                        "address": cust_address,
                        "branch": branch_name
                    }
                    try:
                        save_customer_to_db(cust_data)
                        st.success(f"Customer {cust_name} ({cust_phone}) saved to Supabase successfully!")
                    except Exception as err:
                        # Fallback if database.py expects positional parameters
                        try:
                            save_customer_to_db(cust_name, cust_phone, cust_address, st.session_state['username'])
                            st.success(f"Customer {cust_name} saved successfully!")
                        except Exception as e2:
                            st.error(f"Database Error: {e2}")
                else:
                    st.error("Please enter Customer Name and Phone number.")
                
        st.markdown("### Existing Customers (Supabase Database)")
        customers = get_all_customers()
        if customers:
            for idx, c in enumerate(customers):
                c_id = c.get('id', str(idx))
                c_phone = c.get('phone', 'no_phone')
                col1, col2, col3 = st.columns([3, 2, 2])
                with col1:
                    st.write(f"**{c.get('name')}** | Mobile: {c_phone} | Addr: {c.get('address', '')}")
                with col2:
                    if st.button("Select for Tiles", key=f"select_cust_{c_id}_{idx}"):
                        st.session_state["selected_customer"] = c
                        st.success(f"Selected customer: {c.get('name')}. Switch to 'Area-wise Tile Selection'.")
                with col3:
                    if st.button("Edit / View", key=f"edit_cust_{c_id}_{idx}"):
                        st.session_state["selected_customer"] = c
                        st.info(f"Loaded {c.get('name')} for selection/editing.")
        else:
            st.info("No customers found in database.")
            
    elif page == "2. Area-wise Tile Selection":
        st.title("🏠 Area-wise Tile Selection")
        
        # Active Selected Customer Banner
        if st.session_state.get("selected_customer"):
            curr_cust = st.session_state["selected_customer"]
            st.info(f"**Active Customer:** {curr_cust.get('name')} | **Mobile/Phone:** {curr_cust.get('phone')} | **Address:** {curr_cust.get('address', 'N/A')}")
            if st.button("Change / Clear Customer"):
                st.session_state["selected_customer"] = None
                st.rerun()
        else:
            st.warning("⚠️ No customer selected. Please select or register a customer from '1. Customer Registration' page first.")
        
        floor_level = st.selectbox("Select Room / Area", ["Hall", "Bedroom", "Kitchen", "Bathroom", "Balcony"])
        app_type = st.selectbox("Category", ["Floor", "Wall"])
        specific_area_name = st.text_input("Area Name", "Main Hall")

        search_query = st.text_input("Search Tile by Name / Category", "")

        filtered_catalog = []
        for item in CATALOG_ITEMS:
            if search_query.lower() in str(item.get('name', '')).lower() or search_query.lower() in str(item.get('category', '')).lower():
                filtered_catalog.append(item)

        if not filtered_catalog:
            filtered_catalog = CATALOG_ITEMS

        tile_names = [item.get('name', 'Unknown') for item in filtered_catalog]
        selected_tile_name = st.selectbox("Select Tile Item", tile_names)

        chosen_tile = None
        for t in filtered_catalog:
            if str(t.get('name', '')) == str(selected_tile_name):
                chosen_tile = t
                break

        if not chosen_tile and CATALOG_ITEMS:
            chosen_tile = CATALOG_ITEMS[0]

        default_box_cov = float(chosen_tile.get('box_cov', 15.0) if chosen_tile else 15.0)

        st.write(f"**Selected Item Specs:** Coverage: {default_box_cov} sq.ft/box")

        if st.button("Add Area & Tile to Queue", key="add_to_queue_btn"):
            entry = {
                "floor": floor_level,
                "category": app_type,
                "area": specific_area_name,
                "tile_name": selected_tile_name,
                "box_cov": default_box_cov,
                "sqft": 0.0,
                "boxes": 0,
                "total": 0.0
            }
            
            if "selections" not in st.session_state or st.session_state["selections"] is None:
                st.session_state["selections"] = []
            
            st.session_state["selections"].append(entry)
            st.success("Item added to queue successfully!")

        if "selections" in st.session_state and st.session_state["selections"]:
            st.write("### Added Items in Queue:")
            for idx, item in enumerate(st.session_state["selections"]):
                q_num = idx + 1
                q_floor = str(item.get('floor', ''))
                q_area = str(item.get('area', ''))
                q_tile = str(item.get('tile_name', ''))
                q_cov = str(item.get('box_cov', 0.0))
                
                row_text = str(q_num) + ". " + q_floor + " -> " + q_area + " | " + q_tile + " (Coverage: " + q_cov + " sq.ft)"
                st.text(row_text)
