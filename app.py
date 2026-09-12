import streamlit as st
import pandas as pd
import math
import json
import urllib.parse
from database import get_all_customers, save_customer_to_db, delete_customer_from_db, get_all_admin_users

GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR4mWSP3s6r7UIwn-kcX8Ogev4yXWTMpMLvL87PGTR_UwxKjkcbU9NNxy__mbkyYplhDHxvsD2nKFvW/pub?gid=1816720040&single=true&output=csv"

@st.cache_data(ttl=1)
def load_catalog_from_google_sheet():
    try:
        df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
        if len(df) > 0 and str(df.iloc[0, 0]).strip().upper() == "ITEM NAME":
            df = df.iloc[1:].reset_index(drop=True)
            
        parsed_items = []
        for idx, row in df.iterrows():
            name_val = str(row.iloc[0]) if len(row) > 0 and pd.notna(row.iloc[0]) else f"Item {idx}"
            if name_val.lower() == 'nan' or not name_val.strip() or name_val.lower() == 'item name':
                continue
                
            cat_val = str(row.iloc[2]) if len(row) > 2 and pd.notna(row.iloc[2]) else "Floor"
            
            # Column D (Index 3) -> Con Factor
            try:
                con_factor = float(row.iloc[3]) if len(row) > 3 and pd.notna(row.iloc[3]) else 1.0
            except:
                con_factor = 1.0
                
            # Column E (Index 4) -> Packing Unit
            try:
                packing_unit = float(row.iloc[4]) if len(row) > 4 and pd.notna(row.iloc[4]) else 1.0
            except:
                packing_unit = 1.0
                
            try:
                price = float(row.iloc[6]) if len(row) > 6 and pd.notna(row.iloc[6]) else 0.0
            except:
                price = 0.0

            parsed_items.append({
                "name": name_val.strip(),
                "category": cat_val.strip(),
                "con_factor": con_factor,
                "packing_unit": packing_unit,
                "price": price,
                "box_cov": con_factor * packing_unit
            })
        return parsed_items
    except Exception as e:
        return []

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
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "1. Customer Registration"

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
                    user_role = adm.get("role", "SALESMAN")
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
    branch_name = st.sidebar.text_input("Enter New Showroom Name", "Showroom Branch 3") if branch_selection == "New Show Room" else branch_selection
    
    st.sidebar.markdown(f"**Active Branch:** {branch_name}")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Navigation Flow")
    
    page_options = ["1. Customer Registration", "2. Area & Tile Selection", "3. BOQ Calculation & Finalize"]
    page = st.sidebar.selectbox("Select Page", page_options, index=page_options.index(st.session_state["current_page"]))
    st.session_state["current_page"] = page
    
    if st.sidebar.button("Sign Out"):
        st.session_state["authenticated"] = False
        st.session_state["username"] = ""
        st.session_state["role"] = ""
        st.session_state["selected_customer"] = None
        st.session_state["selections"] = []
        st.session_state["current_page"] = "1. Customer Registration"
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
                    "name": cust_name, "mobile": cust_phone, "phone": cust_phone,
                    "engineer": engineer_name, "engineer_mobile": engineer_mobile,
                    "address": cust_address, "branch": branch_name,
                    "selections": json.dumps([])
                }
                if save_customer_to_db(cust_data):
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
                        raw_sel = c.get("selections", "[]")
                        try:
                            if isinstance(raw_sel, str):
                                st.session_state["selections"] = json.loads(raw_sel)
                            elif isinstance(raw_sel, list):
                                st.session_state["selections"] = raw_sel
                            else:
                                st.session_state["selections"] = []
                        except:
                            st.session_state["selections"] = []
                            
                        st.session_state["current_page"] = "2. Area & Tile Selection"
                        st.success(f"Selected customer: {c.get('name')}.")
                        st.rerun()
                with col3:
                    if st.button("Delete", key=f"del_cust_{c_id}_{idx}"):
                        delete_customer_from_db(c_id)
                        st.rerun()
        else:
            st.info("No customers found in database.")
            
    elif page == "2. Area & Tile Selection":
        st.title("🏠 Step 2: Floor, Area & Tile Selection")
        if st.session_state["selections"]:
            st.markdown("### 🛒 Current Queue Preview")
            for idx, item in enumerate(st.session_state["selections"]):
                col_q1, col_q2 = st.columns([5, 1])
                with col_q1:
                    st.write(f"{idx+1}. **{item.get('floor')}** | {item.get('category')} | **{item.get('area')}** -> {item.get('tile_name')}")
                with col_q2:
                    if st.button("❌", key=f"remove_queue_{idx}"):
                        st.session_state["selections"].pop(idx)
                        st.rerun()
                        
            if st.button("Proceed to Page 3: BOQ Calculation & Finalize ➡️"):
                st.session_state["current_page"] = "3. BOQ Calculation & Finalize"
                st.rerun()        else:
            st.warning("⚠️ No customer selected.")
        
        st.markdown("---")
        floor_option = st.selectbox("1. Select Floor Level", ["Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "Other (Manual Entry)"])
        floor_level = st.text_input("Enter Custom Floor Name", "Basement") if floor_option == "Other (Manual Entry)" else floor_option

        category_type = st.selectbox("2. Select Category", ["Floor", "Wall"])
        area_options = ["Hall", "Kitchen", "Bedroom 1", "Bedroom 2", "Bedroom 3", "Bathroom 1", "Bathroom 2", "Bathroom 3", "Pooja room", "Parking", "Front wall", "Gallery", "Other (Manual Entry)"]
        selected_area_option = st.selectbox("3. Select Area / Room", area_options)
        specific_area_name = st.text_input("Enter Custom Area Name", "Store Room") if selected_area_option == "Other (Manual Entry)" else selected_area_option

        st.markdown("---")
        search_query = st.text_input("🔍 Search Tile by Name / Category", "")
        filtered_catalog = [item for item in CATALOG_ITEMS if search_query.lower() in str(item.get('name', '')).lower() or search_query.lower() in str(item.get('category', '')).lower()] or CATALOG_ITEMS

        tile_names = [item.get('name', 'Unknown') for item in filtered_catalog]
        selected_tile_name = st.selectbox("Select Tile Design", tile_names)
        chosen_tile = next((t for t in filtered_catalog if str(t.get('name')) == str(selected_tile_name)), CATALOG_ITEMS[0] if CATALOG_ITEMS else {})

        con_factor = float(chosen_tile.get('con_factor', 1.0))
        packing_unit = float(chosen_tile.get('packing_unit', 1.0))
        box_cov = float(chosen_tile.get('box_cov', con_factor * packing_unit))
        tile_price = float(chosen_tile.get('price', 0.0))

        st.info(f"**Specs (Col D x E):** Con Factor: {con_factor} | Packing Unit: {packing_unit} | Effective Box Coverage: {box_cov} sq.ft")

        if st.button("➕ Add to Queue (Multiple Allowed)"):
            st.session_state["selections"].append({
                "floor": floor_level, "category": category_type, "area": specific_area_name,
                "tile_name": selected_tile_name, "con_factor": con_factor, "packing_unit": packing_unit,
                "box_cov": box_cov, "sqft": 100.0, "price": tile_price
            })
            st.success("Added to queue!")

        if st.session_state["selections"]:
            st.markdown("### 🛒 Current Queue Preview")
            for idx, item in enumerate(st.session_state["selections"]):
                st.write(f"{idx+1}. **{item.get('floor')}** | {item.get('category')} | **{item.get('area')}** -> {item.get('tile_name')}")
            if st.button("Proceed to Page 3: BOQ Calculation & Finalize ➡️"):
                st.session_state["current_page"] = "3. BOQ Calculation & Finalize"
                st.rerun()

    elif page == "3. BOQ Calculation & Finalize":
        st.title("📊 Step 3: BOQ Calculation & Professional Summary")
        if not st.session_state["selections"]:
            st.warning("⚠️ No items in queue.")
        else:
            if st.session_state.get("selected_customer"):
                if st.button("💾 Save Selections Draft"):
                    try:
                        curr_cust = st.session_state["selected_customer"]
                        curr_cust["selections"] = json.dumps(st.session_state["selections"])
                        save_customer_to_db(curr_cust)
                        st.success("Selections saved as draft successfully!")
                    except Exception as e:
                        st.error(f"Error saving draft: {e}")

            whatsapp_text_lines = ["*BOQ Order Summary - Showroom*"]
            if st.session_state.get("selected_customer"):
                cust = st.session_state["selected_customer"]
                whatsapp_text_lines.append(f"Customer: {cust.get('name')} ({cust.get('mobile') or cust.get('phone')})")
            
            for idx, item in enumerate(st.session_state["selections"]):
                col1, col2, col3, col4 = st.columns([4, 2, 2, 1])
                
                matched_tile = next((t for t in CATALOG_ITEMS if str(t.get('name')) == str(item.get('tile_name'))), {})
                
                c_factor = item.get('con_factor')
                if c_factor is None or str(c_factor) == 'None':
                    c_factor = matched_tile.get('con_factor', 1.0)
                c_factor = float(c_factor)
                
                p_unit = item.get('packing_unit')
                if p_unit is None or str(p_unit) == 'None':
                    p_unit = matched_tile.get('packing_unit', 1.0)
                p_unit = float(p_unit)

                effective_coverage = c_factor * pu
                if effective_coverage <= 0:
                    effective_coverage = 1.0
                    st.markdown(f"**{idx+1}. [{item.get('floor')}] {item.get('category')} - {item.get('area')}**")
                    pass
                    st.caption(f"Design: {item.get('tile_name')} (Con: {c_factor} × Pack: {p_unit})")
                with col2:
                    user_sqft = st.number_input(f"Sq.Ft ({idx})", min_value=0.0, value=float(item.get('sqft', 100.0)), step=10.0, key=f"sqft_input_{idx}", label_visibility="collapsed")
                
                calc_boxes = math.ceil(user_sqft / effective_coverage)
                item_total = calc_boxes * effective_coverage * float(matched_tile.get('price', item.get('price', 0.0)))
                
                with col3:
                    st.markdown(f"📦 **{calc_boxes} Boxes**")
                    st.caption(f"({calc_boxes * effective_coverage:.1f} sq.ft)")
                with col4:
                    if st.button("❌", key=f"remove_boq_{idx}"):
                        st.session_state["selections"].pop(idx)
                        st.rerun()
                
                item["sqft"] = user_sqft
                item["boxes"] = calc_boxes
                item["total"] = item_total
                item["con_factor"] = c_factor
                item["packing_unit"] = p_unit
                
                st.markdown("---")
                summary_line = str(idx+1) + ". " + str(item.get('floor')) + " (" + str(item.get('category')) + ") - " + str(item.get('area')) + ": " + str(item.get('tile_name')) + " | " + str(user_sqft) + " sq.ft (" + str(calc_boxes) + " Boxes)"
                whatsapp_text_lines.append(summary_line)
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                if st.button("✅ Finalize Order & Clear"):
                    st.session_state["selections"] = []
                    st.session_state["current_page"] = "1. Customer Registration"
                    st.success("Order finalized!")
                    st.rerun()
            with col_f2:
                whatsapp_url = f"https://wa.me/?text={urllib.parse.quote('\n'.join(whatsapp_text_lines))}"
                st.markdown(f'<a href="{whatsapp_url}" target="_blank"><button style="background-color:#25D366;color:white;padding:10px 20px;border:none;border-radius:5px;font-weight:bold;cursor:pointer;">📤 Share Summary via WhatsApp</button></a>', unsafe_allow_html=True)
