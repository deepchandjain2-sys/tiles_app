import streamlit as st
import pandas as pd
import math
from datetime import datetime
from fpdf import FPDF
import urllib.parse

st.set_page_config(page_title="Jay Granite & Tiles Hub", page_icon="🏢", layout="wide")

# Safe initialization without corrupt state risks
if "user" not in st.session_state:
    st.session_state.user = None
if "customers" not in st.session_state:
    st.session_state.customers = []
if "items" not in st.session_state:
    st.session_state.items = []
if "stock_df" not in st.session_state:
    st.session_state.stock_df = pd.DataFrame()

# -------------------------------------------------------------
# LOGIN & FORGOT PASSWORD SCREEN
# -------------------------------------------------------------
if not st.session_state.user:
    st.markdown("<h2 style='color:#1e3a8a; text-align:center;'>🏢 JAY GRANITE & TILES</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Sales & Material Selection Portal</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        tab_login, tab_forgot = st.tabs(["🔑 Sign In", "❓ Forgot Password"])
        
        with tab_login:
            with st.form("login_form"):
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Sign In", use_container_width=True, type="primary"):
                    if (u == "admin" and p == "admin123") or (u in ["sales1", "sales2"] and p == "1234"):
                        st.session_state.user = {"username": u, "role": "admin" if u=="admin" else "salesman", "full_name": f"User ({u})"}
                        st.rerun()
                    else:
                        st.error("Invalid Credentials! (Use admin/admin123 or sales1/1234)")
                        
        with tab_forgot:
            with st.form("forgot_form"):
                st.info("Default Passwords:\n- Admin: `admin123`\n- Salesmen (sales1/sales2): `1234`")
                f_user = st.text_input("Enter Username")
                if st.form_submit_button("Recover Password", use_container_width=True):
                    if f_user == "admin":
                        st.success("Admin Password is: `admin123`")
                    elif f_user in ["sales1", "sales2"]:
                        st.success(f"Salesman {f_user} Password is: `1234`")
                    else:
                        st.error("Unknown username!")
    st.stop()

# -------------------------------------------------------------
# SIDEBAR NAVIGATION & FILE UPLOAD
# -------------------------------------------------------------
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user['username']}")
    st.caption(f"Role: {st.session_state.user['role'].upper()}")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.user = None
        st.rerun()
    st.markdown("---")
    
    st.subheader("📁 Upload BUSY Item Master")
    uploaded_file = st.file_uploader("Upload CSV / Excel File", type=["csv", "xlsx", "xls"], key="stock_file_uploader")
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
                
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
                    "BOX_SQFT": box_sqft
                })
            st.session_state.stock_df = pd.DataFrame(records)
            st.success(f"Successfully loaded {len(records)} items!")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    st.markdown("---")
    menu = st.radio("Navigation Flow", [
        "1️⃣ New Customer Registration",
        "2️⃣ Customer Tile Selection",
        "3️⃣ Site Measurements & PDF",
        "4️⃣ Sales Dashboard"
    ])

# Fallback stock if none uploaded
if st.session_state.stock_df.empty:
    st.session_state.stock_df = pd.DataFrame([
        {"ITEM_ID": "1000", "ITEM_NAME": "1000 L 12X18 KK", "CON_FACTOR": 1.5, "PACKING_UNIT": 6, "BOX_SQFT": 9.0},
        {"ITEM_ID": "10015", "ITEM_NAME": "10015 16X16 CIBELA", "CON_FACTOR": 1.73, "PACKING_UNIT": 5, "BOX_SQFT": 8.65},
        {"ITEM_ID": "1002", "ITEM_NAME": "1002 EJ 2x1 Torino", "CON_FACTOR": 2.0, "PACKING_UNIT": 6, "BOX_SQFT": 12.0}
    ])

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
# 2. TILE SELECTION (AREA-WISE)
# -------------------------------------------------------------
elif menu.startswith("2️⃣"):
    st.header("🎨 Customer Tile Selection")
    if not st.session_state.customers:
        st.warning("Please register a customer first.")
    else:
        custs = [f"#{c['id']} - {c['name']} ({c['mobile']})" for c in st.session_state.customers]
        sel = st.selectbox("Choose Customer:", custs)
        cid = int(sel.split()[0].replace("#", ""))
        
        with st.form("add_tile_form"):
            st.markdown("### ➕ Add Tile Area-Wise (Room, Kitchen, Bathroom, etc.)")
            col_f, col_sec, col_area = st.columns(3)
            with col_f:
                fl = st.selectbox("Floor Level", ["Ground Floor", "1st Floor", "2nd Floor", "Parking"])
            with col_sec:
                sec = st.radio("Section Type", ["Floor", "Wall"], horizontal=True)
            with col_area:
                area = st.selectbox("Area / Room", ["Living Room", "Hall", "Kitchen", "Bedroom", "Master Bedroom", "Bathroom", "Balcony", "Parking", "Staircase", "Elevation"])
                
            search_query = st.text_input("🔍 Search Tile Code / Name from Stock:", "")
            
            filtered_stock = st.session_state.stock_df.copy()
            if not filtered_stock.empty and search_query:
                filtered_stock = filtered_stock[
                    filtered_stock["ITEM_NAME"].str.contains(search_query, case=False, na=False) |
                    filtered_stock["ITEM_ID"].str.contains(search_query, case=False, na=False)
                ]
                
            tile_list = filtered_stock["ITEM_NAME"].tolist() if not filtered_stock.empty else ["No matching tiles found"]
            selected_tile_name = st.selectbox(f"Select Tile ({len(filtered_stock)} available):", tile_list)
            
            box_sqft = 16.0
            if not filtered_stock.empty and selected_tile_name in filtered_stock["ITEM_NAME"].values:
                tile_obj = filtered_stock[filtered_stock["ITEM_NAME"] == selected_tile_name].iloc[0]
                box_sqft = float(tile_obj["BOX_SQFT"])
                st.info(f"📦 **Box Coverage:** {box_sqft} Sq.Ft / Box")
            
            submitted = st.form_submit_button("➕ Add This Area Tile", type="primary")
            if submitted:
                if selected_tile_name and selected_tile_name != "No matching tiles found":
                    st.session_state.items.append({
                        "cid": cid,
                        "floor": str(fl),
                        "section": str(sec),
                        "area": str(area),
                        "tile": str(selected_tile_name),
                        "box_sqft": float(box_sqft),
                        "sqft": 100.0,
                        "boxes": math.ceil(100.0 / box_sqft)
                    })
                    st.success(f"Added {selected_tile_name} for {area} successfully!")
                else:
                    st.error("Please select a valid tile.")
                    
        st.subheader("📋 Selected Items for this Customer")
        
       # Ensure items is always a clean list of dictionaries
        if not isinstance(st.session_state.items, list):
            st.session_state.items = []
        else:
            st.session_state.items = [i for i in st.session_state.items if isinstance(i, dict)]

            curr_items = []
            for i in st.session_state.items:
                if isinstance(i, dict) and i.get("cid") == cid:
                    curr_items.append({
                        "floor": str(i.get("floor", "")),
                        "section": str(i.get("section", "")),
                        "area": str(i.get("area", "")),
                        "tile": str(i.get("tile", "")),
                        "box_sqft": float(i.get("box_sqft", 16.0))
                    })
                
        if curr_items:
            df_display = pd.DataFrame(curr_items)
            st.dataframe(df_display, use_container_width=True)
            
            if st.button("🗑️ Clear All Selected Items for Customer"):
                st.session_state.items = [i for i in st.session_state.items if not (isinstance(i, dict) and i.get("cid") == cid)]
                st.rerun()
        else:
            st.info("No tiles selected yet. Add items above.")

# -------------------------------------------------------------
# 3. MEASUREMENTS & WHATSAPP PDF QUOTATION
# -------------------------------------------------------------
elif menu.startswith("3️⃣"):
    st.header("📐 Site Measurements & WhatsApp PDF Quotation")
    if not st.session_state.customers:
        st.warning("No customers found.")
    else:
        custs = [f"#{c['id']} - {c['name']}" for c in st.session_state.customers]
        sel = st.selectbox("Select Customer:", custs)
        cid = int(sel.split()[0].replace("#", ""))
        c_obj = next(c for c in st.session_state.customers if c["id"] == cid)
        
        items = [i for i in st.session_state.items if isinstance(i, dict) and i.get("cid") == cid]
        if items:
            st.markdown("### Enter Total Area (SqFt) for Each Area:")
            tot_b = 0
            for idx, it in enumerate(items):
                col_i1, col_i2 = st.columns([2, 1])
                with col_i1:
                    st.markdown(f"**{it.get('floor')} - {it.get('area')} ({it.get('section')})**<br>Tile: `{it.get('tile')}` (Box: {it.get('box_sqft')} SqFt)", unsafe_allow_html=True)
                with col_i2:
                    it['sqft'] = st.number_input("Area (SqFt)", value=float(it.get('sqft', 100.0)), key=f"sq_{cid}_{idx}_{it.get('tile')}")
                
                it['boxes'] = math.ceil(it['sqft'] / float(it.get('box_sqft', 16.0)))
                tot_b += it['boxes']
                st.caption(f"Required: **{it['boxes']} Boxes**")
                st.divider()
                
            st.markdown(f"### Total Boxes Required Across All Areas: **{tot_b} Boxes**")
            
            if st.button("📄 Generate PDF Quotation", type="primary"):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Helvetica", "B", 16)
                pdf.cell(0, 10, "JAY GRANITE & TILES", ln=True, align="C")
                pdf.set_font("Helvetica", "", 10)
                pdf.cell(0, 6, "Material Selection & Estimation Quotation", ln=True, align="C")
                pdf.ln(5)
                pdf.cell(100, 6, f"Customer: {c_obj['name']}", ln=False)
                pdf.cell(90, 6, f"Mobile: {c_obj['mobile']}", ln=True)
                pdf.cell(100, 6, f"Address: {c_obj['address']}", ln=False)
                pdf.cell(90, 6, f"Sales Rep: {c_obj['salesman']}", ln=True)
                pdf.ln(5)
                
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(45, 7, "Floor / Area", 1)
                pdf.cell(18, 7, "Type", 1)
                pdf.cell(62, 7, "Tile Name", 1)
                pdf.cell(32, 7, "SqFt", 1, 0, "C")
                pdf.cell(33, 7, "Boxes", 1, 1, "C")
                
                pdf.set_font("Helvetica", "", 8)
                for it in items:
                    pdf.cell(45, 6, f"{it.get('floor')} - {it.get('area')}", 1)
                    pdf.cell(18, 6, str(it.get('section')), 1)
                    pdf.cell(62, 6, str(it.get('tile'))[:28], 1)
                    pdf.cell(32, 6, f"{float(it.get('sqft', 0)):.1f}", 1, 0, "C")
                    pdf.cell(33, 6, f"{it.get('boxes', 0)} Boxes", 1, 1, "C")
                    
                pdf.ln(5)
                pdf.set_font("Helvetica", "B", 11)
                pdf.cell(0, 6, f"Total Boxes Required: {tot_b} Boxes", ln=True)
                
                pdf_bytes = pdf.output(dest='S')
                
                st.success("PDF Generated Successfully!")
                st.download_button(
                    label="📥 Download PDF Quotation",
                    data=bytes(pdf_bytes),
                    file_name=f"Estimate_{c_obj['name']}.pdf",
                    mime="application/pdf",
                    type="primary"
                )
                
                wa_msg = f"Hello {c_obj['name']}, here is your material estimation from JAY GRANITE & TILES. Total Boxes: {tot_b}. Thank you!"
                encoded_msg = urllib.parse.quote(wa_msg)
                wa_url = f"https://wa.me/91{c_obj['mobile']}?text={encoded_msg}"
                st.markdown(f"### 📱 Send via WhatsApp:<br><a href='{wa_url}' target='_blank'><button style='background-color:#25D366; color:white; padding:10px 20px; border:none; border-radius:5px; font-weight:bold; cursor:pointer;'>💬 Send WhatsApp Message to {c_obj['name']}</button></a>", unsafe_allow_html=True)
        else:
            st.info("No items added for this customer yet. Go to 'Customer Tile Selection' to add items.")

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
