import streamlit as st
import pandas as pd
import math
import os
from database import get_all_customers, save_customer_to_db, delete_customer_from_db, get_all_admin_users

GOOGLE_SHEET_CSV_URL = os.environ.get("GOOGLE_SHEET_CSV_URL", "https://docs.google.com/spreadsheets/d/1VrRwP3s6e7UlW-kcX8Qgev4y7_nxFU6E1GWnXxz67bKmWuTPmmw/export?format=csv")

@st.cache_data(ttl=0)
def load_catalog_from_google_sheet():
    try:
        df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
        df.columns = df.columns.str.strip().str.lower()
        return df.to_dict(orient="records")
    except Exception as e:
        st.error(f"Google Sheet Error: {e}")
        return [
            {"name": "Glossy Vitrified Tile 600x600mm", "category": "Floor", "box_cov": 15.0, "price": 600.0}
        ]

CATALOG_ITEMS = load_catalog_from_google_sheet()

def calculate_tile_boxes(area_sqft, box_coverage_sqft, wastage_pct=5):
    if box_coverage_sqft <= 0:
        return 0, 0
    total_area = area_sqft * (1 + wastage_pct / 100.0)
    boxes = math.ceil(total_area / box_coverage_sqft)
    return boxes, total_areast.set_page_config(page_title="Tiles & BOQ Management App", layout="wide")

for key, default in [
    ('authenticated', False),
    ('user', None),
    ('role', None),
    ('branch', 'Hiriyur'),
    ('customer', None)
]:
    if key not in st.session_state:
        st.session_state[key] = default

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

# --- SHOWROOM BRANCH SELECTION ---
st.sidebar.markdown(f"**User:** {st.session_state.get('user')}")
st.sidebar.markdown(f"**Role:** {st.session_state.get('role')}")

branch_options = ["Hiriyur", "Davangere", "Other / New Branch"]
selected_branch_option = st.sidebar.selectbox("Showroom Branch", branch_options, index=0, key="sidebar_branch_select")

if selected_branch_option == "Other / New Branch":
    custom_branch_name = st.sidebar.text_input("Enter New Branch Name", "Branch 3", key="custom_branch_input")
    st.session_state['branch'] = custom_branch_name
else:
    st.session_state['branch'] = selected_branch_option

st.sidebar.markdown("---")
st.sidebar.markdown("### Navigation Flow")
menu = st.sidebar.selectbox("Select Page", [
    "1. Customer Registration & List", 
    "2. Area-wise Tile Selection", 
    "3. Calculation & Final Estimate", 
    "Dashboard & Salesman Summary", 
    "Admin User Management"
], key="main_navigation_selectbox")

if st.sidebar.button("Sign Out", key="signout_btn"):
    st.session_state['authenticated'] = False
    st.session_state['user'] = None
    st.session_state['role'] = None
    st.rerun()

#-- PAGE 1: CUSTOMER REGISTRATION & LIST --
if menu == "1. Customer Registration & List":
    st.title("👥 Customer Management & Party List")
    
    col_reg, col_list = st.columns([1, 1])
    
    with col_reg:
        st.markdown("### 📝 Register New Customer / Party")
        with st.form("customer_reg_form", clear_on_submit=True):
            c_name = st.text_input("Customer / Party Name")
            c_mobile = st.text_input("Mobile Number (Unique ID)")
            c_address = st.text_area("Site Address")
            
            submitted = st.form_submit_button("Register & Save Party")
            if submitted:
                if c_name and c_mobile:
                    cust_data = {
                        "name": c_name,
                        "mobile": c_mobile,
                        "address": c_address,
                        "branch": st.session_state['branch'],
                        "selections": []
                    }
                    save_customer_to_db(cust_data)
                    st.session_state['customer'] = cust_data
                    st.success(f"Customer '{c_name}' registered successfully!")
                    st.rerun()
                else:
                    st.error("Please enter Name and Mobile Number.")

    with col_list:
        st.markdown("### 📂 Saved Parties List (Select to Edit/Add Tiles)")
        customers = get_all_customers()
        if customers:
            cust_options = {f"{c.get('name')} ({c.get('mobile')}) - [{c.get('branch', 'Hiriyur')}]": c for c in customers}
            selected_key = st.selectbox("Select Party to Load / Modify", list(cust_options.keys()), key="party_select_box")
            if selected_key:
                active_party = cust_options[selected_key]
                st.session_state['customer'] = active_party
                st.info(f"Loaded: **{active_party.get('name')}** | Mobile: {active_party.get('mobile')}")
                st.write(f"Added Items in Queue: {len(active_party.get('selections', []) or [])}")
                
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    if st.button("Proceed to Tile Selection", key="go_to_tiles_btn"):
                        st.success("Customer loaded! Switch to page '2. Area-wise Tile Selection' from sidebar.")
                with c_btn2:
                    if st.button("Delete Party", key="del_party_btn"):
                        delete_customer_from_db(active_party.get('mobile'))
                        st.success("Party deleted successfully.")
                        st.rerun()
        else:
            st.info("No customers registered yet.")

#-- PAGE 2: AREA-WISE TILE SELECTION (CLEAN SELECTION & QUEUE) --
elif menu == "2. Area-wise Tile Selection":
    st.title("🏗️ Step 2: Area-wise Tile & Wall Selection (Queue)")

    if not st.session_state.get('customer'):
        st.warning("⚠️ Please select or register a customer first from '1. Customer Registration & List'.")
    else:
        cust = st.session_state['customer']
        st.info(f"**Active Customer:** {cust.get('name')} | **Mobile:** {cust.get('mobile')}")
        
        st.markdown("### Select Location & Application Type")
        floor_level = st.selectbox("Select Floor Level", [
            "-- Select Floor Level --", "Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "Other / Independent Area"
        ], key="fl_lvl_box")
        
        app_type = st.radio("Application Category", ["Floor Area", "Wall Area"], horizontal=True, key="app_type_radio")
        
        if app_type == "Floor Area":
            area_options = [
                "-- Select Floor Area --", "Hall", "Kitchen", "Bedroom 1", "Bedroom 2", 
                "Bedroom 3", "Pooja Room", "Bathroom 1", "Bathroom 2", "Custom Floor Area"
            ]
        else:
            area_options = [
                "-- Select Wall Area --", "Bathroom 1 Wall", "Bathroom 2 Wall", "Pooja Wall", "Kitchen Dado Wall", "Custom Wall Area"
            ]
            
        selected_area_choice = st.selectbox("Select Room / Area", area_options, key="area_choice_box")
        
        if selected_area_choice in ["Custom Floor Area", "Custom Wall Area"]:
            specific_area_name = st.text_input("Enter Custom Area Name", key="custom_area_name_input")
        else:
            specific_area_name = selected_area_choice

        if floor_level != "-- Select Floor Level --" and selected_area_choice not in ["-- Select Floor Area --", "-- Select Wall Area --"]:
            st.markdown("---")
            st.markdown(f"### 🔍 Search Item from Catalog (Google Sheet)")
            
            search_query = st.text_input("Search Tile by Name / Category", "", key="tile_search_input")
            
            filtered_catalog = []
            for item in CATALOG_ITEMS:
                name_val = str(item.get('name', item.get('item', 'Tile')))
                cat_val = str(item.get('category', ''))
                if search_query.lower() in name_val.lower() or search_query.lower() in cat_val.lower():
                    filtered_catalog.append(item)
            
            if not filtered_catalog:
                filtered_catalog = CATALOG_ITEMS
                
            tile_names = [str(t.get('name', t.get('item', 'Tile'))) for t in filtered_catalog]
            selected_tile_name = st.selectbox("Select Tile Item", tile_names, key="tile_item_selectbox")
            
            chosen_tile = next((t for t in CATALOG_ITEMS if str(t.get('name', t.get('item', 'Tile'))) == selected_tile_name), CATALOG_ITEMS[0])
            
            default_box_cov = float(chosen_tile.get('box_cov', chosen_tile.get('coverage', 15.0)))
            default_price = float(chosen_tile.get('price', 600.0))

            st.write(f"**Selected Item Specs:** Coverage: {default_box_cov} sq.ft/box | Rate: ₹{default_price}/box")

            if st.button("Add Area & Tile to Queue", key="add_to_queue_btn"):
                entry = {
                    "floor": floor_level,
                    "category": app_type,
                    "area": specific_area_name,
                    "tile_name": selected_tile_name,
                    "box_cov": default_box_cov,
                    "price": default_price,
                    "sqft": 0.0,
                    "boxes": 0,
                    "total": 0.0
                }
                if 'selections' not in cust or cust['selections'] is None:
                    cust['selections'] = []
                cust['selections'].append(entry)
                save_customer_to_db(cust)
                st.success(f"Added [{floor_level} -> {specific_area_name}] with {selected_tile_name} to Queue! Go to Step 3 to enter Sqft and calculate.")

#-- PAGE 3: CALCULATION & FINAL ESTIMATE --
elif menu == "3. Calculation & Final Estimate":
    st.title("📋 Step 3: Enter Sqft, Box Calculation & BOQ Estimate")
    if not st.session_state.get('customer'):
        st.warning("⚠️ Please select a customer from '1. Customer Registration & List'.")
    else:
        cust = st.session_state['customer']
        st.info(f"**Customer:** {cust.get('name')} | **Mobile:** {cust.get('mobile')} | **Address:** {cust.get('address', 'N/A')}")
        
        selections = cust.get('selections', []) or []
        if not selections:
            st.info("Queue is empty. Please add items from '2. Area-wise Tile Selection'.")
        else:
            st.markdown("### 🛒 Enter Square Footage for Queued Areas")
            grand_boxes = 0
            grand_amount = 0.0
            
            updated_selections = []
            for i, sel in enumerate(selections):
                st.markdown(f"#### **{i+1}. [{sel.get('floor')}] {sel.get('category')} - {sel.get('area')}**")
                st.write(f"**Tile:** {sel.get('tile_name')} | **Rate:** ₹{sel.get('price')}/box | **Coverage:** {sel.get('box_cov', 15.0)} sq.ft/box")
                
                col_c1, col_c2, col_c3 = st.columns([2, 2, 1])
                with col_c1:
                    manual_sqft = st.number_input("Enter Net Area (Sq. Ft.)", min_value=0.0, value=float(sel.get('sqft', 100.0)), step=1.0, key=f"sqft_input_{i}")
                with col_c2:
                    wastage_pct = st.slider("Wastage (%)", min_value=0, max_value=20, value=5, key=f"wastage_slider_{i}")
                
                calc_res = calculate_tile_boxes(manual_sqft, float(sel.get('box_cov', 15.0)), wastage_pct)
                item_total_cost = calc_res['rounded_boxes'] * float(sel.get('price', 600.0))
                
                with col_c3:
                    st.metric("Req. Boxes", f"{calc_res['rounded_boxes']}")
                
                st.write(f"Area with Wastage: {calc_res['total_area_with_wastage']} sq.ft | **Item Cost:** ₹{item_total_cost}")
                
                updated_entry = sel.copy()
                updated_entry['sqft'] = manual_sqft
                updated_entry['boxes'] = calc_res['rounded_boxes']
                updated_entry['total'] = item_total_cost
                updated_selections.append(updated_entry)
                
                if st.button(f"Remove Item #{i+1}", key=f"remove_item_{i}"):
                    selections.pop(i)
                    cust['selections'] = selections
                    save_customer_to_db(cust)
                    st.rerun()
                    
                st.markdown("---")
                grand_boxes += calc_res['rounded_boxes']
                grand_amount += item_total_cost
            
            cust['selections'] = updated_selections
            save_customer_to_db(cust)

            st.markdown(f"### 📦 Grand Total Boxes: **{grand_boxes} Boxes**")
            st.markdown(f"### 💰 Grand Total Estimate: **₹ {grand_amount}**")
            
            wa_text = f"*Showroom Tile BOQ Estimation*%0A"
            wa_text += f"Customer: {cust.get('name')}%0A"
            wa_text += f"Mobile: {cust.get('mobile')}%0A-------------------%0A"
            for s in updated_selections:
                wa_text += f"- {s.get('floor')} ({s.get('area')}): {s.get('boxes')} Boxes ({s.get('tile_name')}) - ₹{s.get('total')}%0A"
                
            wa_text += f"-------------------%0A*Total Boxes:* {grand_boxes}%0A*Grand Total:* ₹{grand_amount}"
            
            whatsapp_link = f"https://wa.me/{cust.get('mobile')}?text={wa_text}"
            st.markdown(f"[📲 Send Estimate via WhatsApp]({whatsapp_link})", unsafe_allow_html=True)

elif menu == "Dashboard & Salesman Summary":
    st.title("📊 Dashboard & Salesman Summary")
    st.write("Overview of all showroom customer estimations.")

elif menu == "Admin User Management":
    st.title("⚙️ Admin User Management")
    if st.session_state.get('role') != 'ADMIN':
        st.error("Access Denied! Only ADMIN users can manage accounts.")
    else:
        st.write("Admin settings and user control panel.")
