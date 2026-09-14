import streamlit as st
import pandas as pd
import math
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

st.set_page_config(page_title="Jay Granite & Tiles Hub", layout="wide")

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
        
        if app_type == "Floor Area":
            area_options = ["Hall", "Kitchen", "Master Bedroom", "Common Bedroom", "3rd Bedroom", "Bathroom 1", "Bathroom 2", "Bathroom 3", "Pooja Room", "Parking", "Gallery", "Custom Area"]
        else:
            area_options = ["Bathroom 1 Wall", "Bathroom 2 Wall", "Kitchen Dado", "Pooja Wall", "Front Wall", "Custom Area"]
            
        room_choice = st.selectbox("Select Area / Room", area_options)
        room = st.text_input("Custom Area Name", room_choice) if room_choice == "Custom Area" else room_choice
        
        search_q = st.text_input("🔍 Search Tile from Catalog", "")
        filtered_cat = [t for t in CATALOG_ITEMS if search_q.lower() in t.get('item_name', '').lower()]
        if not filtered_cat:
            filtered_cat = CATALOG_ITEMS
            
        tile_names = [t.get('item_name') for t in filtered_cat]
        selected_tile_name = st.selectbox("Select Tile Item from Catalog", tile_names)
        chosen_tile = next((t for t in CATALOG_ITEMS if t.get('item_name') == selected_tile_name), CATALOG_ITEMS[0]) if isinstance(CATALOG_ITEMS, list) else {}
        
        cf = float(chosen_tile.get('con_factor', 1.0))
        pu = float(chosen_tile.get('packing_unit', 1.0))
        box_cov = float(chosen_tile.get('box_cov', 16.0))
        
        st.success(f"📐 **Catalog Specs:** Con Factor: {cf} | Packing Unit: {pu} | **Coverage: {box_cov} Sq.Ft / Box**")
        item_price = st.number_input("Price per Box (₹)", min_value=0.0, value=600.0, step=50.0)

        if st.button("➕ Add to Queue (Multiple Allowed)", type="primary"):
            entry = {
                "floor": floor_level,
                "category": app_type,
                "area": room,
                "tile_name": chosen_tile.get('item_name', 'Tile'),
                "con_factor": cf,
                "packing_unit": pu,
                "box_cov": box_cov,
                "sqft": 100.0,
                "price": item_price,
                "boxes": 0,
                "total": 0.0
            }
            cust.setdefault('selections', []).append(entry)
            save_customer_to_db(cust)
            st.success("Item added to queue successfully!")

# --- PAGE 3: CALCULATION & FINAL ESTIMATE ---
elif page == "3. Calculation & Final Estimate":
    st.title("📋 Step 3: Queue Review & Manual Sq.Ft Entry")
    if not st.session_state.get('customer'):
        st.warning("⚠️ Please select a customer first.")
    else:
        cust = st.session_state['customer']
        selections = cust.get('selections', []) or []
        if not selections:
            st.info("Queue is empty. Please add items from Step 2.")
        else:
            grand_boxes = 0
            grand_amount = 0.0
            whatsapp_text_lines = []
            
            for idx, item in enumerate(selections):
                matched_tile = next((t for t in CATALOG_ITEMS if str(t.get('item_name')) == str(item.get('tile_name'))), {})
                
                c_factor = float(item.get('con_factor', matched_tile.get('con_factor', 1.0)))
                p_unit = float(item.get('packing_unit', matched_tile.get('packing_unit', 1.0)))

                effective_coverage = c_factor * p_unit
                if effective_coverage <= 0:
                    effective_coverage = 1.0

                col1, col2, col3, col4 = st.columns([4, 2, 2, 1])
                with col1:
                    st.markdown(f"**{idx+1}. [{item.get('floor')}] {item.get('category')} - {item.get('area')}**")
                    st.caption(f"Design: {item.get('tile_name')} (Con: {c_factor} × Pack: {p_unit})")
                with col2:
                    user_sqft = st.number_input(f"Sq.Ft ({idx})", min_value=0.0, value=float(item.get('sqft', 100.0)), step=10.0, key=f"sqft_input_{idx}", label_visibility="collapsed")
                
                calc_boxes = math.ceil(user_sqft / effective_coverage)
                item_total = calc_boxes * float(item.get('price', 600.0))
                
                with col3:
                    st.markdown(f"📦 **{calc_boxes} Boxes**")
                    st.caption(f"(₹ {item_total})")
                with col4:
                    if st.button("❌", key=f"remove_boq_{idx}"):
                        selections.pop(idx)
                        cust['selections'] = selections
                        save_customer_to_db(cust)
                        st.rerun()
                
                item["sqft"] = user_sqft
                item["boxes"] = calc_boxes
                item["total"] = item_total
                item["con_factor"] = c_factor
                item["packing_unit"] = p_unit
                
                st.markdown("---")
                grand_boxes += calc_boxes
                grand_amount += item_total    
                grand_boxes += calc_boxes
                grand_amount += item_total
            
            st.markdown(f"### Grand Total Boxes: **{grand_boxes} Boxes**")
            st.markdown(f"### Grand Total Estimate: **₹ {grand_amount}**")
            
            wa_text = f"*JAY GRANITE & TILES HUB - ESTIMATION*%0A"
            wa_text += f"Customer: *{cust.get('name')}*%0A"
            wa_text += f"Mobile: {cust.get('mobile')}%0A-------------------%0A"
            for s in selections:
                wa_text += f"- {s.get('floor')} ({s.get('area')}): {s.get('boxes')} Boxes ({s.get('tile_name')}) - ₹{s.get('total')}%0A"
            wa_text += f"-------------------%0A*Total Boxes:* {grand_boxes}%0A*Grand Total:* ₹{grand_amount}"
            
            clean_mob = ''.join(filter(str.isdigit, str(cust.get('mobile'))))
            if len(clean_mob) == 10:
                clean_mob = "91" + clean_mob
            whatsapp_link = f"https://wa.me/{clean_mob}?text={wa_text}"
            
            st.markdown(f"[📲 Send Estimate via WhatsApp]({whatsapp_link})", unsafe_allow_html=True)
            
            if st.button("✅ Finalize Order & Clear Queue", type="primary"):
                cust['selections'] = []
                save_customer_to_db(cust)
                st.session_state['customer'] = None
                st.success("Order finalized and queue cleared successfully!")
                st.rerun()
