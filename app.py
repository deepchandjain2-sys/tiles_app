import streamlit as st
import pandas as pd
import math
import urllib.parse
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
            {"name": "Glossy Vitrified Tile 600x600mm", "category": "Floor", "box_cov": 15.0, "price": 60.0}
        ]

CATALOG_ITEMS = load_catalog_from_google_sheet()

st.set_page_config(page_title="Tiles & BOQ Management App", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "role" not in st.session_state:
    st.session_state["role"] = ""
if "selected_customer" not in st.session_state:
    st.session_state["selected_customer"] = None
if "selections" not in st.session_state:
    st.session_state["selections"] = []
if "clear_form_flag" not in st.session_state:
    st.session_state["clear_form_flag"] = False

for key in ["cust_name_input", "cust_phone_input", "eng_name_input", "eng_mob_input", "cust_addr_input"]:
    if key not in st.session_state:
        st.session_state[key] = ""

if not st.session_state["authenticated"]:
    st.title("🔐 Login - Tiles & BOQ App")
    login_user = st.text_input("Username")
    login_pass = st.text_input("Password", type="password")
    
    if st.button("Login"):
        matched = False
        user_role = "ADMIN"
        
        if login_user == "admin" and login_pass == "admin123":
            matched = True
            user_role = "ADMIN"
        else:
            admins = get_all_admin_users()
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
    st.sidebar.write(f"**User:** {st.session_state['username']}")
    st.sidebar.write(f"**Role:** {st.session_state['role']}")
    
    branch_selection = st.sidebar.selectbox("Showroom Branch", ["Hiriyur", "Davangere", "New Show Room"])
    if branch_selection == "New Show Room":
        custom_branch = st.sidebar.text_input("Enter New Showroom Name", "Showroom Branch 3")
        branch_name = custom_branch
    else:
        branch_name = branch_selection
    
    st.sidebar.markdown(f"**Active Branch:** {branch_name}")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Navigation Flow")
    page = st.sidebar.selectbox("Select Page", ["1. Customer Registration", "2. Area & Tile Selection", "3. BOQ Calculation & Finalize"])
    
    if st.sidebar.button("Sign Out"):
        st.session_state["authenticated"] = False
        st.session_state["username"] = ""
        st.session_state["role"] = ""
        st.session_state["selected_customer"] = None
        st.session_state["selections"] = []
        st.rerun()
        
    if page == "1. Customer Registration":
        st.title("📋 Customer Registration & Management")
        
        if st.session_state["clear_form_flag"]:
            st.session_state["cust_name_input"] = ""
            st.session_state["cust_phone_input"] = ""
            st.session_state["eng_name_input"] = ""
            st.session_state["eng_mob_input"] = ""
            st.session_state["cust_addr_input"] = ""
            st.session_state["clear_form_flag"] = False

        cust_name = st.text_input("Customer Name", key="cust_name_input")
        cust_phone = st.text_input("Phone Number", key="cust_phone_input")
        engineer_name = st.text_input("Engineer Name", key="eng_name_input")
        engineer_mobile = st.text_input("Engineer Mobile", key="eng_mob_input")
        cust_address = st.text_area("Address", key="cust_addr_input")
        
        if st.button("Save Customer to Supabase"):
            if cust_name and cust_phone:
                cust_data = {
                    "name": cust_name,
                    "mobile": cust_phone,
                    "phone": cust_phone,
                    "engineer": engineer_name,
                    "engineer_mobile": engineer_mobile,
                    "address": cust_address,
                    "branch": branch_name
                }
                success = save_customer_to_db(cust_data)
                if success:
                    st.success(f"Customer {cust_name} saved successfully!")
                    st.session_state["clear_form_flag"] = True
                    st.rerun()
                else:
                    st.error("Failed to save customer to database.")
            else:
                st.error("Please enter Customer Name and Phone number.")
                
        st.markdown("### Existing Customers (Supabase Database)")
        customers = get_all_customers()
        if customers:
            for idx, c in enumerate(customers):
                c_id = c.get('id', str(idx))
                c_phone = c.get('mobile', '') or c.get('phone', 'no_phone')
                col1, col2, col3 = st.columns([3, 2, 2])
                with col1:
                    st.write(f"**{c.get('name')}** | Mobile: {c_phone} | Addr: {c.get('address', '')}")
                with col2:
                    if st.button("Select for Tiles", key=f"select_cust_{c_id}_{idx}"):
                        st.session_state["selected_customer"] = c
                        st.success(f"Selected customer: {c.get('name')}. Switch to '2. Area & Tile Selection'.")
                with col3:
                    if st.button("Delete", key=f"del_cust_{c_id}_{idx}"):
                        delete_customer_from_db(c_id)
                        st.success(f"Customer {c.get('name')} deleted successfully!")
                        st.rerun()
        else:
            st.info("No customers found in database.")
            
    elif page == "2. Area & Tile Selection":
        st.title("🏠 Step 2: Floor, Area & Tile Selection")
        
        if st.session_state.get("selected_customer"):
            curr_cust = st.session_state["selected_customer"]
            cust_mob = curr_cust.get('mobile') or curr_cust.get('phone') or 'N/A'
            st.info(f"**Active Customer:** {curr_cust.get('name')} | **Mobile:** {cust_mob} | **Address:** {curr_cust.get('address', 'N/A')}")
            if st.button("Change / Clear Customer"):
                st.session_state["selected_customer"] = None
                st.rerun()
        else:
            st.warning("⚠️ No customer selected. Please select or register a customer from '1. Customer Registration' page first.")
        
        st.markdown("---")
        
        floor_option = st.selectbox("1. Select Floor Level", ["Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "Other (Manual Entry)"])
        if floor_option == "Other (Manual Entry)":
            floor_level = st.text_input("Enter Custom Floor Name", "Basement / Mezzanine")
        else:
            floor_level = floor_option

        category_type = st.selectbox("2. Select Category", ["Floor", "Wall"])

        area_options = [
            "Hall", "Kitchen", "Bedroom 1", "Bedroom 2", "Bedroom 3", 
            "Bathroom 1", "Bathroom 2", "Bathroom 3", "Pooja room", "Parking", "Front wall", "Gallery", "Other (Manual Entry)"
        ]
        selected_area_option = st.selectbox("3. Select Area / Room", area_options)
        
        if selected_area_option == "Other (Manual Entry)":
            specific_area_name = st.text_input("Enter Custom Area Name", "Store Room")
        else:
            specific_area_name = selected_area_option

        st.markdown("---")
        
        st.markdown("### 4. Search & Select Tile / Design")
        search_query = st.text_input("🔍 Search Tile by Name / Category", "")

        filtered_catalog = []
        for item in CATALOG_ITEMS:
            if search_query.lower() in str(item.get('name', '')).lower() or search_query.lower() in str(item.get('category', '')).lower():
                filtered_catalog.append(item)

        if not filtered_catalog:
            filtered_catalog = CATALOG_ITEMS

        tile_names = [item.get('name', 'Unknown') for item in filtered_catalog]
        selected_tile_name = st.selectbox("Select Tile Design", tile_names)

        chosen_tile = None
        for t in filtered_catalog:
            if str(t.get('name', '')) == str(selected_tile_name):
                chosen_tile = t
                break

        if not chosen_tile and CATALOG_ITEMS:
            chosen_tile = CATALOG_ITEMS[0]

        default_box_cov = float(chosen_tile.get('box_cov', 15.0) if chosen_tile else 15.0)
        tile_price = float(chosen_tile.get('price', 0.0) if chosen_tile else 0.0)

        st.info(f"**Selected Design Specs:** Coverage: {default_box_cov} sq.ft/box | Price: ₹{tile_price} per sq.ft")

        if st.button("➕ Add to Queue (Multiple Allowed)"):
            entry = {
                "floor": floor_level,
                "category": category_type,
                "area": specific_area_name,
                "tile_name": selected_tile_name,
                "box_cov": default_box_cov,
                "sqft": 100.0,
                "price": tile_price
            }
            st.session_state["selections"].append(entry)
            st.success(f"Added [{floor_level} - {specific_area_name}] with {selected_tile_name} to queue!")

        if st.session_state["selections"]:
            st.markdown("### 🛒 Current Queue Preview")
            for idx, item in enumerate(st.session_state["selections"]):
                st.write(f"{idx+1}. **{item.get('floor')}** | {item.get('category')} | **{item.get('area')}** -> {item.get('tile_name')}")
            
            if st.button("Proceed to Page 3: BOQ Calculation & Finalize ➡️"):
                st.success("Switching to calculation page...")
                st.rerun()

    elif page == "3. BOQ Calculation & Finalize":
        st.title("📊 Step 3: BOQ Calculation & Professional Summary")
        
        if not st.session_state["selections"]:
            st.warning("⚠️ No items in queue. Please add items in '2. Area & Tile Selection' first.")
        else:
            grand_total = 0.0
            whatsapp_text_lines = ["*BOQ Order Summary - Showroom*"]
            if st.session_state.get("selected_customer"):
                cust = st.session_state["selected_customer"]
                whatsapp_text_lines.append(f"Customer: {cust.get('name')} ({cust.get('mobile') or cust.get('phone')})")
            
            st.markdown("### Enter Square Feet in One Line per Item:")
            
            updated_selections = []
            for idx, item in enumerate(st.session_state["selections"]):
                # Professional single line layout using columns
                col1, col2, col3, col4 = st.columns([4, 2, 2, 1])
                
                with col1:
                    st.markdown(f"**{idx+1}. [{item.get('floor')}] {item.get('category')} - {item.get('area')}**")
                    st.caption(f"Design: {item.get('tile_name')} ({item.get('box_cov')} sq.ft/box)")
                
                with col2:
                    user_sqft = st.number_input(f"Sq.Ft ({idx})", min_value=0.0, value=float(item.get('sqft', 100.0)), step=10.0, key=f"sqft_input_{idx}", label_visibility="collapsed")
                
                box_cov = float(item.get('box_cov', 15.0))
                calc_boxes = math.ceil(user_sqft / box_cov) if box_cov > 0 else 0
                item_total = calc_boxes * box_cov * float(item.get('price', 0.0))
                grand_total += item_total
                
                with col3:
                    st.markdown(f"📦 **{calc_boxes} Boxes**")
                    st.caption(f"({calc_boxes * box_cov} sq.ft)")
                
                with col4:
                    if st.button("❌", key=f"remove_boq_{idx}", help="Remove Item"):
                        st.session_state["selections"].pop(idx)
                        st.rerun()
                
                item["sqft"] = user_sqft
                item["boxes"] = calc_boxes
                item["total"] = item_total
                updated_selections.append(item)
                
                st.markdown("---")
                whatsapp_text_lines.append(f"{idx+1}. {item.get('floor')} ({item.get('category')}) - {item.get('area')}: {item.get('tile_name')} | {user_sqft} sq.ft ({calc_boxes} Boxes)")

            st.markdown(f"### **Total Boxes & Summary Ready for Sharing**")
            
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                if st.button("✅ Finalize Order & Clear"):
                    st.success("Order finalized successfully!")
                    st.session_state["selections"] = []
                    st.rerun()
            with col_f2:
                joined_text = "\n".join(whatsapp_text_lines)
                encoded_text = urllib.parse.quote(joined_text)
                whatsapp_url = f"https://wa.me/?text={encoded_text}"
                st.markdown(f'<a href="{whatsapp_url}" target="_blank"><button style="background-color:#25D366;color:white;padding:10px 20px;border:none;border-radius:5px;font-weight:bold;cursor:pointer;">📤 Share Summary via WhatsApp</button></a>', unsafe_allow_html=True)
