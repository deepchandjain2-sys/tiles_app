import streamlit as st
import pandas as pd
import math
from datetime import datetime
from fpdf import FPDF

st.set_page_config(page_title="Jay Granite & Tiles Hub", page_icon="🏢", layout="wide")

if "user" not in st.session_state:
    st.session_state.user = None
if "customers" not in st.session_state:
    st.session_state.customers = []
if "items" not in st.session_state:
    st.session_state.items = []

# -------------------------------------------------------------
# GOOGLE SHEET LIVE STOCK LOADER (ITEM MASTER FORMAT)
# -------------------------------------------------------------
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1qhlBmCLldDAkQMXrbYKSrFcEhYvFdXv2XIABLxO6pA/export?format=csv&gid=0"

@st.cache_data(ttl=30)
def load_busy_inventory():
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
                con_val = float(row[con_col]) if (con_col and pd.notna(row[con_col])) else 1.5
            except:
                con_val = 1.5
            try:
                pack_val = float(row[pack_col]) if (pack_col and pd.notna(row[pack_col])) else 6.0
            except:
                pack_val = 6.0
                
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
    except Exception as e:
        return pd.DataFrame()

stock_df = load_busy_inventory()

# -------------------------------------------------------------
# LOGIN SCREEN
# -------------------------------------------------------------
if not st.session_state.user:
    st.markdown("<h2 style='color:#1e3a8a; text-align:center;'>🏢 JAY GRANITE & TILES</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Sales & Material Selection Portal</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In", use_container_width=True, type="primary"):
                if (u == "admin" and p == "admin123") or (u in ["sales1", "sales2"] and p == "1234"):
                    st.session_state.user = {"username": u, "role": "admin" if u=="admin" else "salesman", "full_name": f"User ({u})"}
                    st.rerun()
                else:
                    st.error("Invalid Credentials! (Use admin/admin123 or sales1/1234)")
    st.stop()

# -------------------------------------------------------------
# SIDEBAR NAVIGATION
# -------------------------------------------------------------
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user['username']}")
    st.caption(f"Role: {st.session_state.user['role'].upper()}")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.user = None
        st.rerun()
    st.markdown("---")
    menu = st.radio("Navigation Flow", [
        "1️⃣ New Customer Registration",
        "2️⃣ Customer Tile Selection",
        "3️⃣ Site Measurements & PDF",
        "4️⃣ Sales Dashboard"
    ])
    st.markdown("---")
    if st.button("🔄 Refresh Live Stock", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# -------------------------------------------------------------
# 1. CUSTOMER REGISTRATION
# -------------------------------------------------------------
if menu.startswith("1️⃣"):
    st.header("👤 Customer & Site Registration")
    with st.form("cust_reg"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Customer Name *")
            mob = st.text_input("Mobile Number *")
            addr = st.text_area("Site Address *")
        with c2:
            eng_name = st.text_input("Engineer / Contractor Name")
            eng_mob = st.text_input("Engineer Mobile")
            status = st.selectbox("Initial Status", ["Shown", "Selected", "Finalized"])
            
        if st.form_submit_button("💾 Save Customer & Open Selection", type="primary"):
            if name and mob:
                new_id = len(st.session_state.customers) + 1
                st.session_state.customers.append({
                    "id": new_id, "name": name, "mobile": mob, "address": addr,
                    "engineer": eng_name, "salesman": st.session_state.user['username'], "status": status
                })
                st.success(f"Customer registered successfully with ID #{new_id}!")
            else:
                st.error("Please enter Name and Mobile number!")

# -------------------------------------------------------------
# 2. TILE SELECTION (CONNECTED WITH GOOGLE SHEET)
# -------------------------------------------------------------
elif menu.startswith("2️⃣"):
    st.header("🎨 Customer Tile Selection")
    if not st.session_state.customers:
        st.warning("Please register a customer first.")
    else:
        custs = [f"#{c['id']} - {c['name']} ({c['mobile']})" for c in st.session_state.customers]
        sel = st.selectbox("Choose Customer:", custs)
        cid = int(sel.split()[0].replace("#", ""))
        
        with st.expander("➕ Add Tile from BUSY Stock for Room / Area", expanded=True):
            col_f, col_sec, col_area = st.columns(3)
            with col_f:
                fl = st.selectbox("Floor Level", ["Ground Floor", "1st Floor", "2nd Floor", "Parking"])
            with col_sec:
                sec = st.radio("Section Type", ["Floor", "Wall"], horizontal=True)
            with col_area:
                area = st.selectbox("Area", ["Living Room", "Hall", "Kitchen", "Bedroom", "Master Bedroom", "Bathroom", "Balcony", "Parking"])
                
            search_query = st.text_input("🔍 Search Tile Code / Name from Google Sheet (e.g. 1000, 10015, CIGAR, 12X18):", "")
            
            filtered_stock = stock_df.copy()
            if not filtered_stock.empty and search_query:
                filtered_stock = filtered_stock[
                    filtered_stock["ITEM_NAME"].str.contains(search_query, case=False, na=False) |
                    filtered_stock["ITEM_ID"].str.contains(search_query, case=False, na=False)
                ]
                
            tile_list = filtered_stock["ITEM_NAME"].tolist() if not filtered_stock.empty else ["No matching tiles found"]
            selected_tile_name = st.selectbox(f"Select Tile ({len(filtered_stock)} available in stock):", tile_list)
            
            box_sqft = 16.0
            if not filtered_stock.empty and selected_tile_name in filtered_stock["ITEM_NAME"].values:
                tile_obj = filtered_stock[filtered_stock["ITEM_NAME"] == selected_tile_name].iloc[0]
                box_sqft = tile_obj["BOX_SQFT"]
                st.info(f"📦 **Auto-Calculated Box Coverage:** {box_sqft} Sq.Ft / Box (Con Factor: {tile_obj['CON_FACTOR']} × Packing: {tile_obj['PACKING_UNIT']})")
            
            if st.button("💾 Save Tile Selection", type="primary"):
                if selected_tile_name and selected_tile_name != "No matching tiles found":
                    st.session_state.items.append({
                        "cid": cid, "floor": fl, "section": sec, "area": area,
                        "tile": selected_tile_name, "box_sqft": box_sqft, "sqft": 100.0, "boxes": math.ceil(100.0/box_sqft)
                    })
                    st.success(f"Added {selected_tile_name} for {area}!")
                    st.rerun()
                else:
                    st.error("Please select a valid tile from stock.")
                    
        st.subheader("📋 Selected Items")
        curr_items = [i for i in st.session_state.items if i["cid"] == cid]
        if curr_items:
            st.dataframe(pd.DataFrame(curr_items)[["floor", "section", "area", "tile", "box_sqft"]], use_container_width=True)
        else:
            st.info("No tiles selected yet.")

# -------------------------------------------------------------
# 3. MEASUREMENTS & PDF
# -------------------------------------------------------------
elif menu.startswith("3️⃣"):
    st.header("📐 Site Measurements & PDF Quotation")
    if not st.session_state.customers:
        st.warning("No customers found.")
    else:
        custs = [f"#{c['id']} - {c['name']}" for c in st.session_state.customers]
        sel = st.selectbox("Select Customer:", custs)
        cid = int(sel.split()[0].replace("#", ""))
        c_obj = next(c for c in st.session_state.customers if c["id"] == cid)
        
        items = [i for i in st.session_state.items if i["cid"] == cid]
        if items:
            for it in items:
                st.markdown(f"**{it['floor']} - {it['area']} ({it['section']})** | Tile: `{it['tile']}` (Box: {it['box_sqft']} SqFt)")
                it['sqft'] = st.number_input("Total Area (SqFt)", value=float(it['sqft']), key=f"sq_{it['tile']}_{it['area']}")
                it['boxes'] = math.ceil(it['sqft'] / it['box_sqft'])
                st.caption(f"Required Boxes: **{it['boxes']} Boxes**")
                st.divider()
                
            if st.button("📄 Generate PDF Quotation", type="primary"):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Helvetica", "B", 16)
                pdf.cell(0, 10, "JAY GRANITE & TILES", ln=True, align="C")
                pdf.set_font("Helvetica", "", 10)
                pdf.cell(0, 6, "Material Selection & Estimation Sheet", ln=True, align="C")
                pdf.ln(5)
                pdf.cell(100, 6, f"Customer: {c_obj['name']}", ln=False)
                pdf.cell(90, 6, f"Mobile: {c_obj['mobile']}", ln=True)
                pdf.cell(100, 6, f"Address: {c_obj['address']}", ln=False)
                pdf.cell(90, 6, f"Sales Rep: {c_obj['salesman']}", ln=True)
                pdf.ln(5)
                
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(40, 7, "Floor/Area", 1)
                pdf.cell(20, 7, "Type", 1)
                pdf.cell(60, 7, "Tile Name", 1)
                pdf.cell(35, 7, "Area (SqFt)", 1, 0, "C")
                pdf.cell(35, 7, "Req Boxes", 1, 1, "C")
                
                pdf.set_font("Helvetica", "", 8)
                tot_b = 0
                for it in items:
                    tot_b += it['boxes']
                    pdf.cell(40, 6, f"{it['floor']} - {it['area']}", 1)
                    pdf.cell(20, 6, str(it['section']), 1)
                    pdf.cell(60, 6, str(it['tile'])[:28], 1)
                    pdf.cell(35, 6, f"{it['sqft']:.1f}", 1, 0, "C")
                    pdf.cell(35, 6, f"{it['boxes']} Boxes", 1, 1, "C")
                    
                pdf.ln(5)
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(0, 6, f"Total Boxes Required: {tot_b} Boxes", ln=True)
                
                pdf_bytes = pdf.output(dest='S')
                st.download_button(
                    label="📥 Download PDF Quotation",
                    data=bytes(pdf_bytes),
                    file_name=f"Estimate_{c_obj['name']}.pdf",
                    mime="application/pdf",
                    type="primary"
                )
        else:
            st.info("No items added for this customer yet.")

# -------------------------------------------------------------
# 4. SALES DASHBOARD
# -------------------------------------------------------------
elif menu.startswith("4️⃣"):
    st.header("📊 Sales Team Scorecard & Dashboard")
    if st.session_state.customers:
        df = pd.DataFrame(st.session_state.customers)
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Customers", len(df))
        col2.metric("Shown", len(df[df['status'] == 'Shown']))
        col3.metric("Finalized", len(df[df['status'] == 'Finalized']))
        st.markdown("---")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No data available.")
