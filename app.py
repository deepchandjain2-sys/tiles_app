import streamlit as st
import pandas as pd
import math

st.set_page_config(
    page_title="Jay Granite Tile Selection",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 1. AUTHENTICATION & PROPER LOGOUT
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h2 style='color:#38bdf8;'>🏢 JAY GRANITE & TILES</h2>", unsafe_allow_html=True)
    st.caption("Admin & Sales Staff Portal")
    st.markdown("---")
    
    col1, _ = st.columns([1.2, 2])
    with col1:
        st.subheader("🔐 Staff Login")
        entered_pin = st.text_input("Enter Passcode / PIN", type="password")
        if st.button("Unlock System", type="primary", use_container_width=True):
            if entered_pin in ["1234", "2026", ""]:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Invalid PIN! (Use: 1234)")
    st.stop()

# 2. GOOGLE SHEET LIVE CSV DATA FETCHER
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRMgTzS4kNWfaIOByOAZ-RS_XQP7zqiKXAgEkgVhrHNYQU5Jn-srXAfuOW_yPcAmW1G_FrEa59S-RyJ/pub?gid=0&single=true&output=csv"

@st.cache_data(ttl=15)
def fetch_busy_inventory():
    try:
        df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
        if df.empty:
            return pd.DataFrame()
        
        df = df.dropna(how='all')
        cols = list(df.columns)
        
        id_col = cols[0]
        name_col = cols[1] if len(cols) > 1 else cols[0]
        con_col = cols[3] if len(cols) > 3 else None
        pack_col = cols[4] if len(cols) > 4 else None

        records = []
        for _, row in df.iterrows():
            name = str(row[name_col]).strip() if pd.notna(row[name_col]) else ""
            if not name or name.lower() == "nan" or "item name" in name.lower():
                continue
            
            try:
                con_val = float(row[con_col]) if (con_col and pd.notna(row[con_col])) else 8.0
            except:
                con_val = 8.0
                
            try:
                pack_val = float(row[pack_col]) if (pack_col and pd.notna(row[pack_col])) else 2.0
            except:
                pack_val = 2.0
                
            box_sqft = round(con_val * pack_val, 2)
            if box_sqft <= 0:
                box_sqft = 16.0
                
            records.append({
                "ITEM_ID": str(row[id_col]).strip() if pd.notna(row[id_col]) else "NA",
                "ITEM_NAME": name,
                "CON_FACTOR": con_val,
                "PACKING_UNIT": int(pack_val),
                "BOX_SQFT": box_sqft,
                "CATEGORY": "Granite" if "GRAN" in name.upper() else ("Wall" if any(x in name.upper() for x in ["WALL", "HL", "12X18"]) else "Floor")
            })
            
        return pd.DataFrame(records)
    except Exception as err:
        st.error(f"Google Sheet Fetch Error: {err}")
        return pd.DataFrame()

if "boq_items" not in st.session_state:
    st.session_state.boq_items = []

stock_df = fetch_busy_inventory()

# 3. SIDEBAR NAVIGATION
with st.sidebar:
    st.markdown("### 👤 DEEPCHAND JAIN")
    st.caption("Designation: Admin")
    
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.markdown("#### **Navigation Flow**")
    nav_option = st.radio(
        "Menu",
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

# 4. TILE MULTI-SELECTION HUB
if "Tile Multi-Selection Hub" in nav_option:
    st.markdown("## 📐 Add Surface Specification")
    
    col_fl, col_stype, col_area = st.columns([1.2, 1.2, 1.5])
    with col_fl:
        floor_level = st.selectbox("Floor Level", ["Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "Terrace", "Parking"])
    with col_stype:
        surface_type = st.radio("Surface Type", ["Floor", "Wall"], horizontal=True)
    with col_area:
        designated_area = st.selectbox("Designated Area", ["Living Room", "Hall", "Master Bedroom", "Bedroom 2", "Kitchen", "Bathroom", "Balcony", "Parking", "Pooja Room", "Custom"])

    st.markdown("---")
    st.markdown("### 🔲 Tile Search & Dimensions")
    
    search_term = st.text_input("🔍 Type Tile Code / Name to Search (e.g. 1002, 16X16, 2X4, ITALICA):", "")
    
    filtered_stock = stock_df.copy()
    if not filtered_stock.empty and search_term:
        filtered_stock = filtered_stock[
            filtered_stock["ITEM_NAME"].str.contains(search_term, case=False, na=False) |
            filtered_stock["ITEM_ID"].str.contains(search_term, case=False, na=False)
        ]
        
    tile_list = filtered_stock["ITEM_NAME"].tolist() if not filtered_stock.empty else ["No matching tiles found"]
    selected_tile_name = st.selectbox(f"Select Tile ({len(filtered_stock)} available)", tile_list)
    
    box_sqft = 16.0
    con_factor = 8.0
    pack_unit = 2.0
    
    if not filtered_stock.empty and selected_tile_name in filtered_stock["ITEM_NAME"].values:
        selected_tile_obj = filtered_stock[filtered_stock["ITEM_NAME"] == selected_tile_name].iloc[0]
        box_sqft = selected_tile_obj["BOX_SQFT"]
        con_factor = selected_tile_obj["CON_FACTOR"]
        pack_unit = selected_tile_obj["PACKING_UNIT"]
        
    dim_col1, dim_col2, dim_col3, dim_col4 = st.columns([1.5, 1.2, 1.2, 1.2])
    
    with dim_col1:
        entry_mode = st.radio("Measurement Mode", ["Direct Sq.Ft", "Length × Width (Ft)"], horizontal=True)
        
    if entry_mode == "Direct Sq.Ft":
        with dim_col2:
            direct_area = st.number_input("Total Area (Sq.Ft)", value=100.0, step=10.0)
        with dim_col3:
            wastage_pct = st.number_input("Wastage %", value=0.0, step=1.0)
        dim_summary = f"Direct: {direct_area:.1f} Sq.Ft"
        net_sqft = direct_area * (1 + (wastage_pct / 100.0))
    else:
        with dim_col2:
            length_val = st.number_input("Length (Ft)", value=10.0, step=0.5)
        with dim_col3:
            width_val = st.number_input("Width / Height (Ft)", value=10.0, step=0.5)
        with dim_col4:
            wastage_pct = st.number_input("Wastage %", value=0.0, step=1.0)
        dim_summary = f"{length_val:.1f} × {width_val:.1f} Ft"
        calc_area = length_val * width_val
        net_sqft = calc_area * (1 + (wastage_pct / 100.0))

    st.caption(f"📦 **Box Coverage:** {box_sqft} Sq.Ft / Box (Con Factor: {con_factor} × Packing Unit: {pack_unit})")
    
    exact_boxes = net_sqft / box_sqft if box_sqft > 0 else 0
    rounded_boxes = math.ceil(exact_boxes)
    total_coverage_delivered = rounded_boxes * box_sqft

    st.info(f"💡 Area: **{net_sqft:.2f} Sq.Ft** | Box Estimate: **{exact_boxes:.2f} Boxes** (Order: **{rounded_boxes} Boxes** = {total_coverage_delivered:.2f} Sq.Ft)")
    
    if st.button("➕ Add This Area to Selection List", type="primary", use_container_width=True):
        if selected_tile_name and selected_tile_name != "No matching tiles found":
            st.session_state.boq_items.append({
                "Floor Level": floor_level,
                "Designated Area": designated_area,
                "Surface": surface_type,
                "Tile Name": selected_tile_name,
                "Dimensions / Mode": dim_summary,
                "Net Area (Sq.Ft)": round(net_sqft, 2),
                "Box Coverage": f"{box_sqft} Sq.Ft",
                "Boxes Required": f"{rounded_boxes} Boxes ({exact_boxes:.2f})",
                "Total Sq.Ft": round(total_coverage_delivered, 2)
            })
            st.success(f"Added {selected_tile_name} for {designated_area}!")
            st.rerun()

    st.markdown("---")
    st.markdown("### 📋 Final Bill of Quantities (BOQ)")
    
    if st.session_state.boq_items:
        boq_df = pd.DataFrame(st.session_state.boq_items)
        st.dataframe(boq_df, use_container_width=True)
        
        c_act1, _ = st.columns([1, 4])
        with c_act1:
            if st.button("🗑️ Clear BOQ List"):
                st.session_state.boq_items = []
                st.rerun()
    else:
        st.info("No selection added yet. Configure above and click 'Add This Area to Selection List'.")

elif "Customer Registration" in nav_option:
    st.markdown("## 👤 Customer Registration")
    st.text_input("Customer Name", value="DEEPCHAND JAIN")
    st.text_input("Phone Number")
    st.text_area("Site Address")
    st.button("Save Customer")

elif "Executive Dashboard" in nav_option or "Admin & Live Stock" in nav_option:
    st.markdown(f"## 📊 {nav_option}")
    st.write(f"Total Live Items in BUSY: **{len(stock_df)}**")
    st.dataframe(stock_df, use_container_width=True)
