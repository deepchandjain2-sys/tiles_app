import streamlit as st
import pandas as pd
import math
import os
import urllib.parse
from database import get_all_customers, save_customer_to_db, delete_customer_from_db

st.set_page_config(page_title="Jay Granite & Tiles Hub", layout="wide")

# --- GOOGLE SHEET CATALOG SETUP ---
GOOGLE_SHEET_CSV_URL = os.environ.get("GOOGLE_SHEET_CSV_URL", "https://docs.google.com/spreadsheets/d/e/2PACX-1vR4mWSP3s6r7UIwn-kcX8Ogev4yXWTMpMLvL87PGTR_UwxKjkcbU9NNxy__mbkyYplhDHxvsD2nKFvW/pub?gid=1816720040&single=true&output=csv")

@st.cache_data(ttl=60)
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
        
        item_col, cf_col, pu_col = 0, 3, 4
        for idx, h in enumerate(headers):
            if "ITEM" in h or "TILE" in h:
                item_col = idx
            elif "CON" in h:
                cf_col = idx
            elif "PACK" in h:
                pu_col = idx

        parsed_stock = []
        for _, r in data_rows.iterrows():
            if item_col >= len(r) or not pd.notna(r.iloc[item_col]): 
                continue
            item_name = str(r.iloc[item_col]).strip()
            if not item_name or item_name.upper() in ["NAN", "ITEM NAME", "TOTAL", "NONE", "NULL", ""]:
                continue
            
            cf_val = 1.0
            if cf_col < len(r) and pd.notna(r.iloc[cf_col]):
                try: cf_val = float(str(r.iloc[cf_col]).replace(',', '').strip())
                except: cf_val = 1.0
            if cf_val <= 0: cf_val = 1.0

            pu_val = 1.0
            if pu_col < len(r) and pd.notna(r.iloc[pu_col]):
                try: pu_val = float(str(r.iloc[pu_col]).replace(',', '').strip())
                except: pu_val = 1.0
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

# Session State Defaults
for key, default in [
    ('auth', False),
    ('username', ""),
    ('role', "Salesman"),
    ('branch', 'Hiriyur'),
    ('selected_customer', None)
]:
    if key not in st.session_state:
        st.session_state[key] = default

# --- LOGIN SCREEN ---
if not st.session_state['auth']:
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
                if (u.upper() in ["ADMIN", "DEEPCHAND JAIN"] and p in ["admin123", "deep123"]) or (role_type == "Admin" and p == "admin123"):
                    st.session_state['auth'] = True
                    st.session_state['username'] = u if u else "Admin"
                    st.session_state['role'] = "Admin"
                    st.session_state['branch'] = branch_choice
                    st.rerun()
                elif u and p:
                    st.session_state['auth'] = True
                    st.session_state['username'] = u
                    st.session_state['role'] = role_type
                    st.session_state['branch'] = branch_choice
                    st.rerun()
                else:
                    st.error("Invalid Username or Password (Default: admin / admin123)")
        st.stop()

# --- SIDEBAR NAVIGATION ---
st.sidebar.title(f"👤 {st.session_state['username'].upper()}")
st.sidebar.markdown(f"**Role:** `{st.session_state['role']}`")
st.sidebar.markdown(f"**Branch:** `{st.session_state['branch']}`")

if st.sidebar.button("🚪 Sign Out", use_container_width=True):
    st.session_state['auth'] = False
    st.session_state['selected_customer'] = None
    st.rerun()

st.sidebar.markdown("---")
page_options = ["1. Customer Registration", "2. Area & Tile Selection", "3. BOQ Calculation & Finalize"]
page = st.sidebar.selectbox("Navigation Flow", page_options)

# --- PAGE 1: CUSTOMER REGISTRATION ---
if page == "1. Customer Registration":
    st.title("📋 Customer Registration & Management")
    
    col_reg, col_list = st.columns([1, 1])
    with col_reg:
        st.subheader("➕ Register New Customer")
        with st.form("cust_reg_form", clear_on_submit=True):
            c_name = st.text_input("Customer Name *")
            c_mobile = st.text_input("Mobile Number (Unique ID) *")
            c_address = st.text_area("Site Address")
            eng_name = st.text_input("Engineer Name")
            eng_mob = st.text_input("Engineer Mobile Number")
            
            submitted = st.form_submit_button("Register & Save Customer", type="primary")
            if submitted:
                if c_name and c_mobile:
                    cust_data = {
                        "name": c_name,
                        "mobile": c_mobile,
                        "phone": c_mobile,
                        "address": c_address,
                        "engineer_name": eng_name,
                        "engineer_mobile": eng_mob,
                        "branch": st.session_state['branch'],
                        "salesman": st.session_state['username'],
                        "selections": []
                    }
                    if save_customer_to_db(cust_data):
                        st.session_state['selected_customer'] = cust_data
                        st.success(f"Customer {c_name} saved successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to save customer to database.")
                else:
                    st.error("Please enter Customer Name and Mobile Number.")

    with col_list:
        st.subheader("📂 Saved Customers List")
        customers = get_all_customers()
        if customers:
            for idx, c in enumerate(customers):
                c_phone = c.get('mobile') or c.get('phone', 'N/A')
                c_eng = c.get('engineer_name', 'N/A')
                c_eng_m = c.get('engineer_mobile', '')
                
                with st.container(border=True):
                    st.write(f"**{c.get('name')}** | 📱 {c_phone}")
                    st.caption(f"Engineer: {c_eng} ({c_eng_m}) | Branch: {c.get('branch', 'Hiriyur')}")
                    
                    b_col1, b_col2 = st.columns(2)
                    with b_col1:
                        if st.button("Select for Tiles", key=f"sel_c_{c_phone}_{idx}", type="primary"):
                            st.session_state['selected_customer'] = c
                            st.success(f"Loaded {c.get('name')}! Go to Page 2.")
                            st.rerun()
                    with b_col2:
                        if st.button("Delete Customer", key=f"del_c_{c_phone}_{idx}"):
                            delete_customer_from_db(c_phone)
                            if st.session_state.get('selected_customer') and st.session_state['selected_customer'].get('mobile') == c_phone:
                                st.session_state['selected_customer'] = None
                            st.success("Customer deleted.")
                            st.rerun()
        else:
            st.info("No registered customers found in database.")

# --- PAGE 2: AREA-WISE TILE SELECTION ---
elif page == "2. Area-wise Tile Selection":
    st.title("🏗️ Area-wise Tile Selection")
    
    if not st.session_state.get('selected_customer'):
        st.warning("⚠️ Please select or register a customer first from '1. Customer Registration'.")
    else:
        cust = st.session_state['selected_customer']
        cust_mob = cust.get('mobile') or cust.get('phone', 'N/A')
        st.info(f"**Active Customer:** {cust.get('name')} | **Mobile:** {cust_mob} | **Branch:** {cust.get('branch')}")
        
        floor_level = st.selectbox("Select Floor Level", ["Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "Other"])
        app_type = st.radio("Application Category", ["Floor Area", "Wall Area"], horizontal=True)
        
        if app_type == "Floor Area":
            area_options = ["Hall", "Kitchen", "Master Bedroom", "Common Bedroom", "Pooja Room", "Bathroom 1", "Bathroom 2", "Custom Area"]
        else:
            area_options = ["Bathroom 1 Wall", "Bathroom 2 Wall", "Kitchen Dado", "Pooja Wall", "Custom Area"]
            
        room_choice = st.selectbox("Select Room / Area", area_options)
        room_name = st.text_input("Custom Area Name", room_choice) if room_choice == "Custom Area" else room_choice

        st.markdown("---")
        search_q = st.text_input("🔍 Search Tile from Catalog", "")
        filtered_cat = [t for t in CATALOG_ITEMS if search_q.lower() in t.get('item_name', '').lower()]
        if not filtered_cat:
            filtered_cat = CATALOG_ITEMS
            
        tile_names = [t.get('item_name') for t in filtered_cat]
        selected_tile = st.selectbox("Select Tile Item", tile_names)
        chosen_tile = next((t for t in CATALOG_ITEMS if t.get('item_name') == selected_tile), CATALOG_ITEMS[0])

        col_dim1, col_dim2 = st.columns(2)
        with col_dim1:
            calc_mode = st.radio("Measurement Mode", ["Length x Width (Feet)", "Direct Square Feet"])
            if calc_mode == "Length x Width (Feet)":
                l_ft = st.number_input("Length (ft)", min_value=0.0, value=12.0, step=0.1)
                w_ft = st.number_input("Width (ft)", min_value=0.0, value=10.0, step=0.1)
                net_sqft = l_ft * w_ft
            else:
                net_sqft = st.number_input("Total Area (Sq. Ft.)", min_value=0.0, value=120.0, step=1.0)
            st.metric("Net Area", f"{net_sqft} Sq. Ft.")

        with col_dim2:
            cf = float(chosen_tile.get('con_factor', 1.0))
            pu = float(chosen_tile.get('packing_unit', 1.0))
            box_cov = float(chosen_tile.get('box_cov', 16.0))
            st.metric("Box Coverage (Con × Packing)", f"{box_cov} Sq.Ft")
            st.caption(f"Con Factor: {cf} | Packing Unit: {pu}")
            
            wastage_pct = st.slider("Wastage (%)", 0, 20, 5)
            item_price = st.number_input("Price per Box (₹)", min_value=0.0, value=600.0, step=50.0)

        area_with_wastage = net_sqft * (1 + wastage_pct / 100.0)
        exact_boxes = area_with_wastage / box_cov if box_cov > 0 else 0
        rounded_boxes = math.ceil(exact_boxes)
        total_cost = rounded_boxes * item_price

        st.markdown("#### 📦 Calculation Summary")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Area + Wastage", f"{round(area_with_wastage, 2)} sq.ft")
        m2.metric("Exact Boxes", round(exact_boxes, 2))
        m3.metric("Required Boxes", f"{rounded_boxes} Boxes")
        m4.metric("Total Amount", f"₹ {total_cost}")

        if st.button("➕ Add to Queue", type="primary", use_container_width=True):
            entry = {
                "floor": floor_level,
                "category": app_type,
                "area": room_name,
                "tile_name": chosen_tile.get('item_name'),
                "sqft": net_sqft,
                "boxes": rounded_boxes,
                "price": item_price,
                "total": total_cost
            }
            cust.setdefault('selections', []).append(entry)
            save_customer_to_db(cust)
            st.success(f"Added {room_name} to Queue successfully!")

# --- PAGE 3: BOQ CALCULATION & FINAL ESTIMATE ---
elif page == "3. BOQ Calculation & Finalize":
    st.title("📋 BOQ Queue Review & WhatsApp Share")
    
    if not st.session_state.get('selected_customer'):
        st.warning("⚠️ Please select a customer first from Page 1.")
    else:
        cust = st.session_state['selected_customer']
        selections = cust.get('selections', []) or []
        
        st.info(f"**Customer:** {cust.get('name')} | **Mobile:** {cust.get('mobile') or cust.get('phone')}")
        
        if not selections:
            st.info("Queue is empty. Please add items from '2. Area-wise Tile Selection'.")
        else:
            grand_boxes = 0
            grand_amount = 0.0
            
            for idx, s in enumerate(selections):
                col_i1, col_i2 = st.columns([3, 1])
                with col_i1:
                    st.markdown(f"**{idx+1}. [{s.get('floor')}] {s.get('category')} - {s.get('area')}**")
                    st.write(f"Tile: {s.get('tile_name')} | Area: {s.get('sqft')} sq.ft | Boxes: **{s.get('boxes')}** | Rate: ₹{s.get('price')}/box")
                    st.write(f"**Item Total:** ₹{s.get('total')}")
                with col_i2:
                    if st.button(f"Remove #{idx+1}", key=f"rem_item_{idx}"):
                        selections.pop(idx)
                        cust['selections'] = selections
                        save_customer_to_db(cust)
                        st.rerun()
                st.markdown("---")
                grand_boxes += s.get('boxes', 0)
                grand_amount += s.get('total', 0.0)
            
            st.markdown(f"### 📦 Grand Total Boxes: **{grand_boxes} Boxes**")
            st.markdown(f"### 💰 Grand Total Estimate: **₹ {grand_amount}**")
            
            # WhatsApp message formatting
            wa_text = f"*JAY GRANITE & TILES HUB - ESTIMATION*%0A"
            wa_text += f"Customer: *{cust.get('name')}*%0A"
            wa_text += f"Mobile: {cust.get('mobile') or cust.get('phone')}%0A-------------------%0A"
            for s in selections:
                wa_text += f"- {s.get('floor')} ({s.get('area')}): {s.get('boxes')} Boxes ({s.get('tile_name')}) - ₹{s.get('total')}%0A"
            wa_text += f"-------------------%0A*Total Boxes:* {grand_boxes}%0A*Grand Total:* ₹{grand_amount}"
            
            cust_mob = cust.get('mobile') or cust.get('phone', '')
            whatsapp_link = f"https://wa.me/91{cust_mob}?text={wa_text}"
            st.markdown(f"[📲 Send Estimate via WhatsApp]({whatsapp_link})", unsafe_allow_html=True)
