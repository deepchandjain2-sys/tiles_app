import streamlit as st
import pandas as pd
import math
import urllib.parse
from datetime import datetime
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

        if cf_col is None: cf_col = 3
        if pu_col is None: pu_col = 4

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

st.set_page_config(page_title="Jay Granite & Tiles Portal", layout="wide")

for key, default in [
    ('auth', False),
    ('username', ""),
    ('role', "Salesman"),
    ('branch', 'Hiriyur'),
    ('customer', None)
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
                branch_choice = st.selectbox("Select Branch / Showroom", ["Hiriyur", "Davangere", "New Show Room"])
            else:
                branch_choice = st.selectbox("Select View / Showroom", ["All Showrooms", "Hiriyur", "Davangere", "New Show Room"])
                
            u = st.text_input("Username").strip()
            p = st.text_input("Password", type="password").strip()
            submit = st.form_submit_button("🚀 Sign In", type="primary", use_container_width=True)
            
            if submit:
                if (u.upper() in ["DEEPCHAND JAIN", "ADMIN", "GOURAV"] and p in ["deep123", "pass123", "admin123", "GOURAV", "deep1965", "1234"]) or (role_type == "Admin" and p in ["deep123", "admin123", "1234"]):
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
                    st.error("Please enter valid credentials.")
        st.stop()

# --- SIDEBAR NAVIGATION ---
st.sidebar.title(f"👤 {st.session_state['username'].upper()}")
st.sidebar.markdown(f"**Role:** `{st.session_state['role']}`")
st.sidebar.markdown(f"**Branch:** `{st.session_state['branch']}`")

if st.sidebar.button("🚪 Sign Out", use_container_width=True):
    st.session_state['auth'] = False
    st.session_state['customer'] = None
    st.rerun()

nav_options = [
    "1. Customer Registration & List", 
    "2. Area-wise Tile Selection", 
    "3. Calculation & Final Estimate"
]
page = st.sidebar.selectbox("Navigation Flow", nav_options)

# --- PAGE 1: CUSTOMER REGISTRATION & LIST ---
if page == "1. Customer Registration & List":
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
                        "salesman": st.session_state['username'],
                        "selections": []
                    }
                    save_customer_to_db(cust_data)
                    st.session_state['customer'] = cust_data
                    st.success(f"Customer '{c_name}' registered successfully!")
                    st.rerun()
                else:
                    st.error("Please enter Name and Mobile Number.")

    with col_list:
        st.markdown("### 📂 Saved Parties List")
        customers = get_all_customers()
        if customers:
            for idx, c in enumerate(customers):
                c_mobile = c.get('mobile') or c.get('phone', '')
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{c.get('name')}** - {c_mobile} [{c.get('branch', 'Hiriyur')}]")
                    st.caption(f"Engineer: {c.get('engineer_name', 'N/A')} ({c.get('engineer_mobile', 'N/A')})")
                with col2:
                    if st.button("Select", key=f"select_cust_{c_mobile}_{idx}"):
                        st.session_state['customer'] = c
                        st.success(f"Selected: {c.get('name')}")
                        st.rerun()
                    if st.button("Delete", key=f"del_cust_{c_mobile}_{idx}"):
                        delete_customer_from_db(c_mobile)
                        if st.session_state.get('customer') and st.session_state['customer'].get('mobile') == c_mobile:
                            st.session_state['customer'] = None
                        st.success("Customer deleted.")
                        st.rerun()
        else:
            st.info("No customers registered yet.")

# --- PAGE 2: AREA-WISE TILE SELECTION ---
elif page == "2. Area-wise Tile Selection":
    st.title("🏗️ Step 2: Area-wise Tile & Wall Selection")
    if not st.session_state.get('customer'):
        st.warning("⚠️ Please select or register a customer first from page 1.")
    else:
        cust = st.session_state['customer']
        st.info(f"**Active Customer:** {cust.get('name')} | **Mobile:** {cust.get('mobile')}")
        
        floor_level = st.selectbox("Select Floor Level", ["Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "Other"])
        app_type = st.radio("Application Category", ["Floor Area", "Wall Area"], horizontal=True)
        room = st.text_input("Area / Room Name", "Hall")
        
        tile_names = [t.get('item_name') for t in CATALOG_ITEMS] if isinstance(CATALOG_ITEMS, list) else ["Default Tile"]
        selected_tile_name = st.selectbox("Select Tile Item from Catalog", tile_names)
        chosen_tile = next((t for t in CATALOG_ITEMS if t.get('item_name') == selected_tile_name), CATALOG_ITEMS[0]) if isinstance(CATALOG_ITEMS, list) else {}
        
        col_dim1, col_dim2 = st.columns(2)
        with col_dim1:
            calc_mode = st.radio("Measurement Mode", ["Length x Width (Feet)", "Direct Square Feet"])
            if calc_mode == "Length x Width (Feet)":
                l_ft = st.number_input("Length (ft)", min_value=0.0, value=12.0, step=0.1)
                w_ft = st.number_input("Width (ft)", min_value=0.0, value=10.0, step=0.1)
                area_sqft = l_ft * w_ft
            else:
                area_sqft = st.number_input("Total Area (Sq. Ft.)", min_value=0.0, value=120.0, step=1.0)
            st.info(f"Net Area: **{area_sqft} Sq. Ft.**")

        with col_dim2:
            cf = float(chosen_tile.get('con_factor', 1.0))
            pu = float(chosen_tile.get('packing_unit', 1.0))
            box_cov = float(chosen_tile.get('box_cov', 16.0))
            st.metric("Box Coverage (Con Factor × Packing)", f"{box_cov} Sq.Ft")
            st.caption(f"Con Factor: {cf} | Packing Unit: {pu}")
            wastage_pct = st.slider("Wastage (%)", min_value=0, max_value=20, value=5)
            item_price = st.number_input("Price per Box (₹)", min_value=0.0, value=600.0, step=50.0)

        total_area_with_wastage = area_sqft * (1 + wastage_pct / 100.0)
        exact_boxes = total_area_with_wastage / box_cov if box_cov > 0 else 0
        rounded_boxes = math.ceil(exact_boxes)
        total_cost = rounded_boxes * item_price
        
        st.markdown("#### 📦 Calculation Summary")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Area with Wastage", f"{round(total_area_with_wastage, 2)} sq.ft")
        m2.metric("Exact Boxes", round(exact_boxes, 2))
        m3.metric("Required Boxes", f"{rounded_boxes} Boxes")
        m4.metric("Total Amount", f"₹ {total_cost}")

        if st.button("Add to Queue", type="primary"):
            entry = {
                "floor": floor_level,
                "category": app_type,
                "area": room,
                "tile_name": chosen_tile.get('item_name', 'Tile'),
                "sqft": area_sqft,
                "boxes": rounded_boxes,
                "price": item_price,
                "total": total_cost
            }
            cust.setdefault('selections', []).append(entry)
            save_customer_to_db(cust)
            st.success("Item added to queue and saved successfully!")

# --- PAGE 3: CALCULATION & FINAL ESTIMATE ---
elif page == "3. Calculation & Final Estimate":
    st.title("📋 Step 3: Queue Review & WhatsApp Share")
    if not st.session_state.get('customer'):
        st.warning("⚠️ Please select a customer first.")
    else:
        cust = st.session_state['customer']
        selections = cust.get('selections', []) or []
        if not selections:
            st.info("Queue is empty.")
        else:
            grand_boxes = 0
            grand_amount = 0.0
            for idx, s in enumerate(selections):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{idx+1}. [{s.get('floor')}] {s.get('category')} - {s.get('area')}**")
                    st.write(f"Tile: {s.get('tile_name')} | {s.get('sqft')} sq.ft | Boxes: **{s.get('boxes')}** | Rate: ₹{s.get('price')}")
                    st.write(f"**Total:** ₹{s.get('total')}")
                with col2:
                    if st.button(f"Remove #{idx+1}", key=f"rem_{idx}"):
                        selections.pop(idx)
                        cust['selections'] = selections
                        save_customer_to_db(cust)
                        st.rerun()
                st.markdown("---")
                grand_boxes += s.get('boxes', 0)
                grand_amount += s.get('total', 0.0)
            
            st.markdown(f"### Grand Total Boxes: **{grand_boxes} Boxes**")
            st.markdown(f"### Grand Total Estimate: **₹ {grand_amount}**")
            
            message = f"*JAY GRANITE & TILES HUB - ESTIMATION*%0A"
            message += f"Customer: *{cust.get('name')}*%0A"
            message += f"Mobile: {cust.get('mobile')}%0A-------------------%0A"
            for s in selections:
                message += f"- {s.get('floor')} ({s.get('area')}): {s.get('boxes')} Boxes ({s.get('tile_name')}) - ₹{s.get('total')}%0A"
            message += f"-------------------%0A*Total Boxes:* {grand_boxes}%0A*Grand Total:* ₹{grand_amount}"
            
            whatsapp_link = f"https://wa.me/91{cust.get('mobile')}?text={message}"
            st.markdown(f"[📲 Send Estimate via WhatsApp]({whatsapp_link})", unsafe_allow_html=True)
