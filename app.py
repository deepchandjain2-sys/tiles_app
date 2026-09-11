import streamlit as st
import math

# --- IN-LINE DATABASE & SESSION FUNCTIONS ---
def get_all_customers():
    if 'mock_customers' not in st.session_state:
        st.session_state['mock_customers'] = []
    return st.session_state['mock_customers']

def save_customer_to_db(cust_data):
    if 'mock_customers' not in st.session_state:
        st.session_state['mock_customers'] = []
    existing = [c for c in st.session_state['mock_customers'] if c.get('mobile') == cust_data.get('mobile')]
    if existing:
        st.session_state['mock_customers'].remove(existing[0])
    st.session_state['mock_customers'].append(cust_data)
    return True

def delete_customer_from_db(mobile):
    if 'mock_customers' in st.session_state:
        st.session_state['mock_customers'] = [c for c in st.session_state['mock_customers'] if c.get('mobile') != mobile]
    return True

def get_all_admin_users():
    return [{"username": "admin", "password": "password", "role": "ADMIN", "branch": "Hiriyur"}]

def calculate_tile_boxes(area_sqft, tile_length_mm, tile_width_mm, box_coverage_sqft, wastage_pct=5):
    if area_sqft <= 0 or box_coverage_sqft <= 0:
        return {
            "total_area_with_wastage": 0.0,
            "exact_boxes": 0,
            "rounded_boxes": 0,
            "total_tiles_count": 0
        }
    area_with_wastage = area_sqft * (1 + wastage_pct / 100.0)
    exact_boxes = area_with_wastage / box_coverage_sqft
    rounded_boxes = math.ceil(exact_boxes)
    tile_sqft = (tile_length_mm * tile_width_mm) / 92903.0
    tiles_per_box = math.ceil(box_coverage_sqft / tile_sqft) if tile_sqft > 0 else 0
    total_tiles = rounded_boxes * tiles_per_box
    return {
        "total_area_with_wastage": round(area_with_wastage, 2),
        "exact_boxes": round(exact_boxes, 2),
        "rounded_boxes": rounded_boxes,
        "total_tiles_count": total_tiles
    }

# Page Configuration
st.set_page_config(page_title="Tiles & BOQ Management App", layout="wide")

# Session State Initialization
for key, default in [
    ('authenticated', False),
    ('user', None),
    ('role', None),
    ('branch', 'Hiriyur'),
    ('customer', None),
    ('current_selections', [])
]:
    if key not in st.session_state:
        st.session_state[key] = default

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
branch = st.sidebar.selectbox("Showroom Branch", ["Hiriyur", "Other Branch"], index=0, key="sidebar_branch_select")
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
                    st.error("Failed to save customer.")
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
            st.markdown(f"### 📐 Dimensions & Tile Configuration for: {floor_level} -> {custom_area_name}")
            
            col1, col2 = st.columns(2)
            with col1:
                calc_mode = st.radio("Calculation Input Mode", ["Length x Width (Feet)", "Direct Square Feet"], key="calc_mode_radio")
                if calc_mode == "Length x Width (Feet)":
                    length_ft = st.number_input("Length (ft)", min_value=0.0, value=10.0, step=0.1, key="length_ft_input")
                    width_ft = st.number_input("Width (ft)", min_value=0.0, value=10.0, step=0.1, key="width_ft_input")
                    area_sqft = length_ft * width_ft
                else:
                    area_sqft = st.number_input("Total Area (Sq. Ft.)", min_value=0.0, value=100.0, step=1.0, key="direct_sqft_input")
                
                st.info(f"Calculated Net Area: **{area_sqft} Sq. Ft.**")

            with col2:
                box_coverage = st.number_input("Box Coverage (Sq. Ft. per Box)", min_value=0.1, value=15.0, step=0.5, key="box_cov_input")
                wastage = st.slider("Wastage Percentage (%)", min_value=0, max_value=20, value=5, key="wastage_slider")
                tile_price = st.number_input("Price per Box (₹)", min_value=0.0, value=600.0, step=50.0, key="tile_price_input")

            calc_result = calculate_tile_boxes(area_sqft, 600, 600, box_coverage, wastage)
            
            st.markdown("#### 📦 Calculation Summary")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Area + Wastage", f"{calc_result['total_area_with_wastage']} sq.ft")
            m2.metric("Exact Boxes", calc_result['exact_boxes'])
            m3.metric("Rounded Boxes (Order)", f"{calc_result['rounded_boxes']} Boxes")
            total_est_cost = calc_result['rounded_boxes'] * tile_price
            m4.metric("Estimated Cost", f"₹ {total_est_cost}")

            if st.button("Add This Area to Customer Order", key="add_area_btn"):
                selection_entry = {
                    "floor": floor_level,
                    "area": custom_area_name,
                    "sqft": area_sqft,
                    "boxes": calc_result['rounded_boxes'],
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
    st.write("Summary metrics and analytics for showroom sales.")

#-- ADMIN USER MANAGEMENT --
elif menu == "Admin User Management":
    st.title("⚙️ Admin User Management")
    if st.session_state.get('role') != 'ADMIN':
        st.error("Access Denied! Only ADMIN can access this page.")
    else:
        st.write("Manage system users here.")
