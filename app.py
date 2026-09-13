import streamlit as st
import pandas as pd
import math
import datetime
import urllib.parse
from database import get_all_customers, save_customer_to_db, delete_customer_from_db

GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR4mWSP3s6r7UIwn-kcX8Ogev4yXWTMpMLvL87PGTR_UwxKjkcbU9NNxy__mbkyYplhDHxvsD2nKFvW/pub?gid=1816720040&single=true&output=csv"

@st.cache_data(ttl=600)
def load_catalog_from_google_sheet():
    try:
        raw_df = pd.read_csv(GOOGLE_SHEET_CSV_URL, header=None, dtype=str)
        h_idx = 0
        for i in range(min(15, len(raw_df))):
            row_vals = [str(x).upper().strip() for x in raw_df.iloc[i].values if pd.notna(x)]
            if "ITEM NAME" in row_vals or "TILE NAME" in row_vals:
                h_idx = i
                break
                
        headers = [str(x).strip().upper() for x in raw_df.iloc[h_idx].values]
        data_rows = raw_df.iloc[h_idx + 1:].copy()
        
        item_col = 0
        cf_col = None
        pu_col = None
        
        for idx, h in enumerate(headers):
            if "ITEM" in h or "TILE" in h:
                item_col = idx
            elif "CON" in h:
                cf_col = idx
            elif "PACK" in h:
                pu_col = idx

        if cf_col is None: cf_col = 3  # Column D index usually
        if pu_col is None: pu_col = 4  # Column E index usually

        parsed_stock = []
        for _, r in data_rows.iterrows():
            if item_col >= len(r) or not pd.notna(r.iloc[item_col]): 
                continue
            item_name = str(r.iloc[item_col]).strip()
            if not item_name or item_name.upper() in ["NAN", "ITEM NAME", "TOTAL", "NONE", "NULL", ""]:
                continue
            
            cf_val = 1.0
            if cf_col < len(r) and pd.notna(r.iloc[cf_col]):
                try:
                    cf_val = float(str(r.iloc[cf_col]).replace(',', '').strip())
                except Exception:
                    cf_val = 1.0
            if cf_val <= 0: cf_val = 1.0

            pu_val = 1.0
            if pu_col < len(r) and pd.notna(r.iloc[pu_col]):
                try:
                    pu_val = float(str(r.iloc[pu_col]).replace(',', '').strip())
                except Exception:
                    pu_val = 1.0
            if pu_val <= 0: pu_val = 1.0
                
            box_cov = round(cf_val * pu_val, 2)
            parsed_stock.append({
                "item_name": item_name,
                "con_factor": cf_val,
                "packing_unit": pu_val,
                "box_cov": box_cov if box_cov > 0 else 1.0
            })
            
        df = pd.DataFrame(parsed_stock).drop_duplicates(subset=["item_name"])
        if not df.empty:
            return df.to_dict(orient="records")
    except Exception:
        pass
    return [
        {"item_name": "Glossy Vitrified Tile 600x600mm", "con_factor": 4.0, "packing_unit": 4.0, "box_cov": 16.0},
        {"item_name": "Matte Anti-Skid Tile 300x300mm", "con_factor": 1.0, "packing_unit": 10.0, "box_cov": 10.0}
    ]

CATALOG_ITEMS = load_catalog_from_google_sheet()

st.set_page_config(page_title="Tiles & BOQ Management App", layout="wide")

for key, default in [
    ('authenticated', True),
    ('user', "Admin"),
    ('role', "ADMIN"),
    ('branch', 'Hiriyur'),
    ('customer', None)
]:
    if key not in st.session_state:
        st.session_state[key] = default

st.sidebar.title(f"👤 {st.session_state['user'].upper()}")
st.sidebar.markdown(f"**Branch:** `{st.session_state['branch']}`")

nav = st.sidebar.selectbox("Navigation Flow", [
    "1. Customer Registration & List", 
    "2. Area-wise Tile Selection", 
    "3. Calculation & Final Estimate"
], key="main_navigation_selectbox")

# PAGE 1: CUSTOMER REGISTRATION & LIST
if nav == "1. Customer Registration & List":
    st.title("👥 Customer Management & Party List")
    
    col_reg, col_list = st.columns([1, 1])
    
    with col_reg:
        st.markdown("### 📝 Register New Customer / Party")
        with st.form("customer_reg_form", clear_on_submit=True):
            c_name = st.text_input("Customer / Party Name")
            c_mobile = st.text_input("Mobile Number (Unique ID)")
            c_address = st.text_area("Site Address")
            c_eng_name = st.text_input("Engineer Name")
            c_eng_mobile = st.text_input("Engineer Mobile Number")
            
            submitted = st.form_submit_button("Register & Save Party", type="primary")
            if submitted:
                if c_name and c_mobile:
                    cust_data = {
                        "name": c_name,
                        "mobile": c_mobile,
                        "address": c_address,
                        "engineer_name": c_eng_name,
                        "engineer_mobile": c_eng_mobile,
                        "branch": st.session_state['branch'],
                        "selections": []
                    }
                    save_customer_to_db(cust_data)
                    st.session_state['customer'] = cust_data
                    st.success(f"Customer '{c_name}' registered successfully and saved to Supabase!")
                    st.rerun()
                else:
                    st.error("Please enter Name and Mobile Number.")

    with col_list:
        st.markdown("### 📂 Saved Parties List (Select to Edit/Add Tiles)")
        customers = get_all_customers()
        if customers:
            cust_options = {f"{c.get('name')} ({c.get('mobile')}) - [{c.get('branch', 'Hiriyur')}]": c for c in customers}
            selected_key = st.selectbox("Select Party to Load / Modify", list(cust_options.keys()), key="party_select_box_unique")
            if selected_key:
                active_party = cust_options[selected_key]
                st.session_state['customer'] = active_party
                st.info(f"Loaded: **{active_party.get('name')}** | Mobile: {active_party.get('mobile')} | Branch: {active_party.get('branch')}")
                st.write(f"Engineer: {active_party.get('engineer_name', 'N/A')} ({active_party.get('engineer_mobile', 'N/A')})")
                st.write(f"Added Items Count: {len(active_party.get('selections', []) or [])}")
                
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    if st.button("Proceed to Tile Selection", key="go_to_tiles_btn_unique", type="primary"):
                        st.success("Customer loaded! Switch to page '2. Area-wise Tile Selection'.")
                with c_btn2:
                    if st.button("Delete Party", key="del_party_btn_unique"):
                        delete_customer_from_db(active_party.get('id'))
                        if st.session_state.get('customer') and st.session_state['customer'].get('mobile') == active_party.get('mobile'):
                            st.session_state['customer'] = None
                        st.success("Party deleted successfully.")
                        st.rerun()
        else:
            st.info("No customers registered yet in Supabase database.")

# PAGE 2: AREA-WISE TILE SELECTION
elif nav == "2. Area-wise Tile Selection":
    st.title("🏗️ Step 2: Area-wise Tile & Wall Selection")

    if not st.session_state.get('customer'):
        st.warning("⚠️ Please select or register a customer first from '1. Customer Registration & List'.")
    else:
        cust = st.session_state['customer']
        st.info(f"**Active Customer:** {cust.get('name')} | **Mobile:** {cust.get('mobile')} | **Branch:** {cust.get('branch')}")
        
        st.markdown("### Select Location & Application Type")
        floor_level = st.selectbox("Select Floor Level", [
            "-- Select Floor Level --", "Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "Other / Independent Area"
        ], key="fl_lvl_box_unique")
        
        app_type = st.radio("Application Category", ["Floor Area", "Wall Area"], horizontal=True, key="app_type_radio_unique")
        
        if app_type == "Floor Area":
            area_options = [
                "-- Select Floor Area --", "Hall", "Kitchen", "Bedroom 1", "Bedroom 2", 
                "Bedroom 3", "Pooja Room", "Bathroom 1", "Bathroom 2", "Custom Floor Area"
            ]
        else:
            area_options = [
                "-- Select Wall Area --", "Bathroom 1 Wall", "Bathroom 2 Wall", "Pooja Wall", "Kitchen Dado Wall", "Custom Wall Area"
            ]
            
        selected_area_choice = st.selectbox("Select Room / Area", area_options, key="area_choice_box_unique")
        
        if selected_area_choice in ["Custom Floor Area", "Custom Wall Area"]:
            specific_area_name = st.text_input("Enter Custom Area Name", key="custom_area_name_input_unique")
        else:
            specific_area_name = selected_area_choice

        if floor_level != "-- Select Floor Level --" and selected_area_choice not in ["-- Select Floor Area --", "-- Select Wall Area --"]:
            st.markdown("---")
            st.markdown(f"### 🔍 Search Item from Catalog")
            
            search_query = st.text_input("Search Tile by Name / Category", "", key="tile_search_input_unique")
            filtered_catalog = [item for item in CATALOG_ITEMS if search_query.lower() in str(item.get('item_name', '')).lower()]
            if not filtered_catalog:
                filtered_catalog = CATALOG_ITEMS
                
            selected_tile_name = st.selectbox("Select Tile Item", [t.get('item_name', 'Tile') for t in filtered_catalog], key="tile_item_selectbox_unique")
            chosen_tile = next((t for t in CATALOG_ITEMS if t.get('item_name') == selected_tile_name), CATALOG_ITEMS[0])
            
            col_dim1, col_dim2 = st.columns(2)
            with col_dim1:
                calc_mode = st.radio("Measurement Mode", ["Length x Width (Feet)", "Direct Square Feet"], key="meas_mode_radio_unique")
                if calc_mode == "Length x Width (Feet)":
                    l_ft = st.number_input("Length (ft)", min_value=0.0, value=12.0, step=0.1, key="len_ft_unique")
                    w_ft = st.number_input("Width (ft)", min_value=0.0, value=10.0, step=0.1, key="wid_ft_unique")
                    area_sqft = l_ft * w_ft
                else:
                    area_sqft = st.number_input("Total Area (Sq. Ft.)", min_value=0.0, value=120.0, step=1.0, key="dir_sqft_unique")
                
                st.info(f"Net Area: **{area_sqft} Sq. Ft.**")

            with col_dim2:
                box_cov = float(chosen_tile.get('box_cov', 15.0))
                st.metric("Box Coverage (Col D × Col E)", f"{box_cov} Sq.Ft")
                wastage_pct = st.slider("Wastage (%)", min_value=0, max_value=20, value=5, key="wastage_slider_p2_unique")
                item_price = st.number_input("Price per Box (₹)", min_value=0.0, value=600.0, step=50.0, key="price_input_p2_unique")

            area_with_wastage = area_sqft * (1 + wastage_pct / 100.0)
            exact_boxes = area_with_wastage / box_cov if box_cov > 0 else 0
            rounded_boxes = math.ceil(exact_boxes)
            total_cost = rounded_boxes * item_price
            
            st.markdown("#### 📦 Calculation Summary")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Area with Wastage", f"{round(area_with_wastage, 2)} sq.ft")
            m2.metric("Exact Boxes", round(exact_boxes, 2))
            m3.metric("Required Boxes", f"{rounded_boxes} Boxes")
            m4.metric("Total Amount", f"₹ {total_cost}")

            if st.button("Add to Queue (Send for Estimation)", key="add_to_queue_btn_unique", type="primary"):
                entry = {
                    "floor": floor_level,
                    "category": app_type,
                    "area": specific_area_name,
                    "tile_name": chosen_tile.get('item_name', 'Tile'),
                    "sqft": area_sqft,
                    "boxes": rounded_boxes,
                    "price": item_price,
                    "total": total_cost
                }
                if 'selections' not in cust or cust['selections'] is None:
                    cust['selections'] = []
                cust['selections'].append(entry)
                save_customer_to_db(cust)
                st.success(f"Added {specific_area_name} to Queue and saved to Supabase successfully!")

# PAGE 3: CALCULATION & FINAL ESTIMATE
elif nav == "3. Calculation & Final Estimate":
    st.title("📋 Step 3: Queue Review, BOQ Estimate & WhatsApp Share")
    if not st.session_state.get('customer'):
        st.warning("⚠️ Please select a customer from '1. Customer Registration & List'.")
    else:
        cust = st.session_state['customer']
        st.info(f"**Customer:** {cust.get('name')} | **Mobile:** {cust.get('mobile')} | **Engineer:** {cust.get('engineer_name', 'N/A')}")
        
        selections = cust.get('selections', []) or []
        if not selections:
            st.info("Queue is empty. Please add items from '2. Area-wise Tile Selection'.")
        else:
            st.markdown("### 🛒 Queued Selections Summary")
            grand_boxes = 0
            grand_amount = 0.0
            
            for i, sel in enumerate(selections):
                col_i1, col_i2 = st.columns([3, 1])
                with col_i1:
                    st.markdown(f"**{i+1}. [{sel.get('floor')}] {sel.get('category')} - {sel.get('area')}**")
                    st.write(f"Tile: {sel.get('tile_name')} | Area: {sel.get('sqft')} sq.ft | Boxes: **{sel.get('boxes')}** | Rate: ₹{sel.get('price')}/box")
                    st.write(f"**Item Total:** ₹{sel.get('total')}")
                with col_i2:
                    if st.button(f"Remove #{i+1}", key=f"remove_item_unique_{i}"):
                        selections.pop(i)
                        cust['selections'] = selections
                        save_customer_to_db(cust)
                        st.rerun()
                st.markdown("---")
                grand_boxes += sel.get('boxes', 0)
                grand_amount += sel.get('total', 0.0)
            
            st.markdown(f"### 📦 Grand Total Boxes: **{grand_boxes} Boxes**")
            st.markdown(f"### 💰 Grand Total Estimate: **₹ {grand_amount}**")
            
            wa_text = f"*Showroom Tile BOQ Estimation*%0A"
            wa_text += f"Customer: {cust.get('name')}%0A"
            wa_text += f"Mobile: {cust.get('mobile')}%0A-------------------%0A"
            for s in selections:
                wa_text += f"- {s.get('floor')} ({s.get('area')}): {s.get('boxes')} Boxes ({s.get('tile_name')}) - ₹{s.get('total')}%0A"
            wa_text += f"-------------------%0A*Total Boxes:* {grand_boxes}%0A*Grand Total:* ₹{grand_amount}"
            
            whatsapp_link = f"https://wa.me/{cust.get('mobile')}?text={wa_text}"
            st.markdown(f"[📲 Send Estimate via WhatsApp]({whatsapp_link})", unsafe_allow_html=True)
