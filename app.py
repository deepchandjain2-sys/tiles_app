import streamlit as st
import pandas as pd
import math
from datetime import datetime, date

# -------------------------------------------------------------
# 1. PAGE SETUP & FULL DARK THEME UI
# -------------------------------------------------------------
st.set_page_config(
    page_title="Jay Granite Tile Selection",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stApp { background-color: #0b0f19; color: #f1f5f9; }
    .css-1d391kg, .css-12oz5g7 { background-color: #0f172a; }
    .card-panel {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 15px;
    }
    .info-banner {
        background-color: #1d4ed8;
        color: #ffffff;
        border-radius: 6px;
        padding: 10px 14px;
        margin: 10px 0;
        font-weight: 500;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 2. AUTHENTICATION & LOGIN GATEWAY
# -------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h2 style='color:#38bdf8;'>🏢 JAY GRANITE & TILES</h2>", unsafe_allow_html=True)
    st.caption("Sales Selection & Estimation Portal")
    st.markdown("---")
    
    col_l1, _ = st.columns([1.2, 2])
    with col_l1:
        st.subheader("🔐 Staff Login")
        entered_pass = st.text_input("Enter PIN / Passcode", type="password", key="login_pin")
        if st.button("Unlock System", type="primary", use_container_width=True):
            if entered_pass in ["1234", "2026", ""]:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect PIN. Please try again.")
    st.stop()

# -------------------------------------------------------------
# 3. LIVE BUSY STOCK CSV LOADER (100% FIXED CSV LINK)
# -------------------------------------------------------------
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRMgTzS4kNWfaIOByOAZ-RS_XQP7zqiKXAgEkgVhrHNYQU5Jn-srXAfuOW_yPcAmW1G_FrEa59S-RyJ/pub?gid=0&single=true&output=csv"

@st.cache_data(ttl=30)
def load_busy_live_data():
    try:
        raw_df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
        if raw_df.empty:
            return pd.DataFrame()
        
        raw_df = raw_df.dropna(how='all')
        cols = list(raw_df.columns)
        
        c_id = cols[0]
        c_name = cols[1] if len(cols) > 1 else cols[0]
        c_con = cols[3] if len(cols) > 3 else None
        c_pack = cols[4] if len(cols) > 4 else None

        items = []
        for _, r in raw_df.iterrows():
            item_n = str(r[c_name]).strip() if pd.notna(r[c_name]) else ""
            if not item_n or item_n.lower() == "nan" or "item name" in item_n.lower():
                continue
            
            try:
                con_f = float(r[c_con]) if (c_con and pd.notna(r[c_con])) else 8.0
            except:
                con_f = 8.0
                
            try:
                pack_u = float(r[c_pack]) if (c_pack and pd.notna(r[c_pack])) else 2.0
            except:
                pack_u = 2.0
                
            box_area = round(con_f * pack_u, 2)
            if box_area <= 0:
                box_area = 16.0
                
            cat = "Floor"
            if "GRAN" in item_n.upper():
                cat = "Granite"
            elif "WALL" in item_n.upper() or "HL" in item_n.upper() or "12X18" in item_n.upper() or "10X15" in item_n.upper():
                cat = "Wall"
                
            items.append({
                "ITEM_ID": str(r[c_id]).strip() if pd.notna(r[c_id]) else "NA",
                "ITEM_NAME": item_n,
                "CON_FACTOR": con_f,
                "PACKING_UNIT": int(pack_u),
                "BOX_SQFT": box_area,
                "CATEGORY": cat
            })
            
        return pd.DataFrame(items)
    except Exception as e:
        st.error(f"Google Sheet Fetch Error: {e}")
        return pd.DataFrame()

# Session State Variables
if "customer_info" not in st.session_state:
    st.session_state.customer_info = {
        "name": "DEEPCHAND JAIN",
        "phone": "9876543210",
        "address": "Hiriyur",
        "date": date.today().strftime("%d-%b-%Y")
    }

if "boq_records" not in st.session_state:
    st.session_state.boq_records = []

busy_df = load_busy_live_data()

# -------------------------------------------------------------
# 4. SIDEBAR NAVIGATION FLOW
# -------------------------------------------------------------
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.customer_info['name']}")
    st.caption("Designation: Admin")
    
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

    st.markdown("---")
    st.markdown("#### **Navigation Flow**")
    active_screen = st.radio(
        "Navigation",
        [
            "1️⃣ Customer Registration",
            "2️⃣ Tile Multi-Selection Hub",
            "3️⃣ Executive Dashboard",
            "4️⃣ Admin & Live Stock"
        ],
        index=1,
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    if st.button("🔄 Refresh BUSY Live Stock", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# -------------------------------------------------------------
# SCREEN 1: CUSTOMER REGISTRATION
# -------------------------------------------------------------
if "Customer Registration" in active_screen:
    st.markdown("## 👤 Customer Registration")
    st.caption("Manage customer details and project address.")
    
    with st.container():
        c_name = st.text_input("Customer Name", value=st.session_state.customer_info["name"])
        c_phone = st.text_input("Mobile / Phone Number", value=st.session_state.customer_info["phone"])
        c_addr = st.text_area("Site / Delivery Address", value=st.session_state.customer_info["address"])
        c_dt = st.date_input("Entry Date", value=datetime.today())
        
        if st.button("💾 Save Customer Details", type="primary"):
            st.session_state.customer_info = {
                "name": c_name,
                "phone": c_phone,
                "address": c_addr,
                "date": c_dt.strftime("%d-%b-%Y")
            }
            st.success("Customer Profile Updated Successfully!")

# -------------------------------------------------------------
# SCREEN 2: TILE MULTI-SELECTION HUB (MAIN SELECTION & SIZING)
# -------------------------------------------------------------
elif "Tile Multi-Selection Hub" in active_screen:
    st.markdown("## 📐 Add Surface Specification")
    
    col_floor, col_surface, col_area = st.columns([1.2, 1.2, 1.5])
    with col_floor:
        floor_lvl = st.selectbox("Floor Level", ["Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "Terrace", "Parking"])
    with col_surface:
        surf_type = st.radio("Surface Type", ["Floor", "Wall"], horizontal=True)
    with col_area:
        desig_area = st.selectbox("Designated Area", ["Living Room", "Hall", "Master Bedroom", "Bedroom 2", "Kitchen", "Bathroom", "Balcony", "Parking", "Pooja Room", "Custom"])

    st.markdown("---")
    st.markdown("### 🔲 Tile Search & Dimensions")
    
    tile_search = st.text_input("🔍 Type Tile Code / Name to Search (e.g. 1002, 16X16, 2X4, ITALICA):", "")
    
    filtered_items = busy_df.copy()
    if not filtered_items.empty and tile_search:
        filtered_items = filtered_items[
            filtered_items["ITEM_NAME"].str.contains(tile_search, case=False, na=False) |
            filtered_items["ITEM_ID"].str.contains(tile_search, case=False, na=False)
        ]
        
    tile_names_list = filtered_items["ITEM_NAME"].tolist() if not filtered_items.empty else ["No matching tiles found"]
    chosen_tile_name = st.selectbox(f"Select Tile ({len(filtered_items)} available)", tile_names_list)
    
    cov_box = 16.0
    c_factor = 8.0
    p_unit = 2.0
    
    if not filtered_items.empty and chosen_tile_name in filtered_items["ITEM_NAME"].values:
        matched_obj = filtered_items[filtered_items["ITEM_NAME"] == chosen_tile_name].iloc[0]
        cov_box = matched_obj["BOX_SQFT"]
        c_factor = matched_obj["CON_FACTOR"]
        p_unit = matched_obj["PACKING_UNIT"]
        
    # --- DUAL MEASUREMENT INPUT: DIRECT SQFT vs L x W ---
    m_col1, m_col2, m_col3, m_col4 = st.columns([1.5, 1.2, 1.2, 1.2])
    
    with m_col1:
        measure_mode = st.radio("Measurement Mode", ["Direct Sq.Ft", "Length × Width (Ft)"], horizontal=True)
        
    if measure_mode == "Direct Sq.Ft":
        with m_col2:
            input_sqft = st.number_input("Total Area (Sq.Ft)", value=100.0, step=10.0)
        with m_col3:
            wastage = st.number_input("Wastage %", value=0.0, step=1.0)
        dimension_label = f"Direct: {input_sqft:.1f} Sq.Ft"
        total_sqft = input_sqft * (1 + (wastage / 100.0))
    else:
        with m_col2:
            len_ft = st.number_input("Length (Ft)", value=10.0, step=0.5)
        with m_col3:
            wid_ft = st.number_input("Width / Height (Ft)", value=10.0, step=0.5)
        with m_col4:
            wastage = st.number_input("Wastage %", value=0.0, step=1.0)
        dimension_label = f"{len_ft:.1f} × {wid_ft:.1f} Ft"
        total_sqft = (len_ft * wid_ft) * (1 + (wastage / 100.0))

    st.caption(f"📦 **Box Coverage:** {cov_box} Sq.Ft / Box (Con Factor: {c_factor} × Packing Unit: {p_unit})")
    
    boxes_decimal = total_sqft / cov_box if cov_box > 0 else 0
    boxes_order = math.ceil(boxes_decimal)
    total_area_supplied = boxes_order * cov_box

    st.markdown(f"""
    <div class='info-banner'>
        💡 Area: <b>{total_sqft:.2f} Sq.Ft</b> | Box Estimate: <b>{boxes_decimal:.2f} Boxes</b> (Order: <b>{boxes_order} Boxes</b> = {total_area_supplied:.2f} Sq.Ft)
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("➕ Add This Area to Selection List", type="primary", use_container_width=True):
        if chosen_tile_name and chosen_tile_name != "No matching tiles found":
            st.session_state.boq_records.append({
                "Floor Level": floor_lvl,
                "Designated Area": desig_area,
                "Surface Type": surf_type,
                "Tile Selection": chosen_tile_name,
                "Dimensions / Mode": dimension_label,
                "Required Sq.Ft": round(total_sqft, 2),
                "Box Coverage": f"{cov_box} Sq.Ft",
                "Boxes To Order": f"{boxes_order} Boxes",
                "Exact Boxes": round(boxes_decimal, 2),
                "Total Coverage (Sq.Ft)": round(total_area_supplied, 2)
            })
            st.success(f"Added {chosen_tile_name} for {desig_area} successfully!")
            st.rerun()

    # BILL OF QUANTITIES (BOQ) TABLE
    st.markdown("---")
    st.markdown("### 📋 Final Bill of Quantities (BOQ)")
    
    if st.session_state.boq_records:
        boq_table = pd.DataFrame(st.session_state.boq_records)
        st.dataframe(boq_table, use_container_width=True)
        
        act1, _ = st.columns([1, 4])
        with act1:
            if st.button("🗑️ Clear BOQ List"):
                st.session_state.boq_records = []
                st.rerun()
    else:
        st.info("No tiles added yet. Configure above and click 'Add This Area to Selection List'.")

# -------------------------------------------------------------
# SCREEN 3: EXECUTIVE DASHBOARD & PRINT ESTIMATION
# -------------------------------------------------------------
elif "Executive Dashboard" in active_screen:
    st.markdown("## 📊 Executive Estimate & Billing Summary")
    st.write(f"**Customer Name:** {st.session_state.customer_info['name']} | **Phone:** {st.session_state.customer_info['phone']}")
    st.write(f"**Site Address:** {st.session_state.customer_info['address']} | **Date:** {st.session_state.customer_info['date']}")
    st.markdown("---")
    
    if st.session_state.boq_records:
        df_dash = pd.DataFrame(st.session_state.boq_records)
        st.table(df_dash[["Floor Level", "Designated Area", "Tile Selection", "Required Sq.Ft", "Boxes To Order", "Total Coverage (Sq.Ft)"]])
        
        tot_boxes = sum([int(str(x).split()[0]) for x in df_dash["Boxes To Order"]])
        tot_sqft_cov = sum(df_dash["Total Coverage (Sq.Ft)"])
        
        st.markdown(f"### 📦 Grand Total Requirement: **{tot_boxes} Boxes** ({tot_sqft_cov:.2f} Sq.Ft)")
        st.info("💡 **Print Tip:** Press `Ctrl + P` to print this quotation directly for the customer.")
    else:
        st.warning("No selections recorded in BOQ. Please select tiles in 'Tile Multi-Selection Hub'.")

# -------------------------------------------------------------
# SCREEN 4: ADMIN & LIVE STOCK INVENTORY
# -------------------------------------------------------------
elif "Admin & Live Stock" in active_screen:
    st.markdown("## 📊 Admin & Live Stock Inventory")
    st.write(f"Total Live Items Synced from BUSY: **{len(busy_df)}**")
    
    if not busy_df.empty:
        st.dataframe(busy_df, use_container_width=True)
    else:
        st.warning("No live stock items found. Please verify Google Sheet link.")
