import streamlit as st
import pandas as pd
import math
from datetime import datetime
from fpdf import FPDF
import urllib.parse

from calculations import calculate_boxes, calculate_box_sqft
from database import (
    load_stock_from_upload, 
    save_customers_to_disk, 
    load_customers_from_disk,
    save_stock_to_disk,
    load_stock_from_disk
)

st.set_page_config(page_title="Jay Granite & Tiles Hub", page_icon="🏢", layout="wide")

# Persistent State Initialization with Disk Recovery
if "user" not in st.session_state:
    st.session_state.user = None
if "customers" not in st.session_state:
    st.session_state.customers = load_customers_from_disk()
if "items" not in st.session_state:
    st.session_state.items = []
if "stock_df" not in st.session_state:
    saved_stock = load_stock_from_disk()
    st.session_state.stock_df = saved_stock if not saved_stock.empty else pd.DataFrame()
if "login_history" not in st.session_state:
    st.session_state.login_history = []

# -------------------------------------------------------------
# 1. LOGIN & USER MANAGEMENT
# -------------------------------------------------------------
if not st.session_state.user:
    st.markdown("<h2 style='color:#1e3a8a; text-align:center;'>🏢 JAY GRANITE & TILES</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Sales & Material Selection Portal</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        tab_login, tab_forgot = st.tabs(["🔑 Sign In", "❓ Forgot Password"])
        
        with tab_login:
            with st.form("login_form"):
                u = st.text_input("Username (Text/Number)")
                p = st.text_input("Password (Text/Number/Special Chars)", type="password")
                if st.form_submit_button("Sign In", use_container_width=True, type="primary"):
                    if (u == "admin" and p == "admin123") or (u in ["sales1", "sales2"] and p == "@1234_pass"):
                        role_val = "admin" if u == "admin" else "salesman"
                        st.session_state.user = {"username": u, "role": role_val}
                        st.session_state.login_history.append({
                            "Username": u,
                            "Role": role_val,
                            "Login Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        st.rerun()
                    else:
                        st.error("Invalid Credentials! (Use admin/admin123 or sales1/@1234_pass)")
                        
        with tab_forgot:
            with st.form("forgot_form"):
                st.info("Default Credentials:\n- Admin: `admin` / `admin123`\n- Salesman: `sales1` / `@1234_pass`")
                f_user = st.text_input("Enter Username")
                if st.form_submit_button("Recover Password", use_container_width=True):
                    if f_user == "admin":
                        st.success("Admin Password: `admin123`")
                    elif f_user in ["sales1", "sales2"]:
                        st.success("Salesman Password: `@1234_pass`")
                    else:
                        st.error("User not found!")
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
    
    st.subheader("📁 Upload Master (CSV / Excel)")
    uploaded_file = st.file_uploader("Upload Item Master File", type=["csv", "xlsx", "xls"], key="master_uploader")
    if uploaded_file is not None:
        df = load_stock_from_upload(uploaded_file)
        if df is not None:
            try:
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
                        
                    box_sqft = calculate_box_sqft(con_val, pack_val)
                        
                    records.append({
                        "ITEM_ID": str(row[id_col]).strip() if pd.notna(row[id_col]) else "NA",
                        "ITEM_NAME": name,
                        "CON_FACTOR": con_val,
                        "PACKING_UNIT": int(pack_val),
                        "BOX_SQFT": box_sqft
                    })
                st.session_state.stock_df = pd.DataFrame(records)
                save_stock_to_disk(st.session_state.stock_df) # Save permanently to disk
                st.success(f"Successfully loaded and saved {len(records)} items!")
            except Exception as e:
                st.error(f"Error processing records: {e}")

    st.markdown("---")
    menu = st.radio("Navigation Flow", [
        "1️⃣ Customer Registration",
        "2️⃣ Tiles Selection (Area-Wise)",
        "3️⃣ Measurements, PDF & WhatsApp",
        "4️⃣ Sales Dashboard & History"
    ])

# Fallback Stock if none uploaded
if st.session_state.stock_df.empty:
    st.session_state.stock_df = pd.DataFrame([
        {"ITEM_ID": "1000", "ITEM_NAME": "1000 L 12X18 KK", "CON_FACTOR": 1.5, "PACKING_UNIT": 6, "BOX_SQFT": 9.0},
        {"ITEM_ID": "10015", "ITEM_NAME": "10015 16X16 CIBELA", "CON_FACTOR": 1.73, "PACKING_UNIT": 5, "BOX_SQFT": 8.65},
        {"ITEM_ID": "1002", "ITEM_NAME": "1002 EJ 2x1 Torino", "CON_FACTOR": 2.0, "PACKING_UNIT": 6, "BOX_SQFT": 12.0}
    ])

# -------------------------------------------------------------
# 2. CUSTOMER REGISTRATION
# -------------------------------------------------------------
if menu.startswith("1️⃣"):
    st.header("👤 Customer & Site Registration")
    with st.form("cust_reg_form"):
        c1, c2 = st.columns(2)
        with c1:
            c_name = st.text_input("Customer Name *")
            c_mob = st.text_input("Mobile Number *")
            c_addr = st.text_area("Site Address *")
        with c2:
            eng_name = st.text_input("Engineer / Contractor Name")
            eng_mob = st.text_input("Engineer Mobile Number")
            status = st.selectbox("Initial Status", ["Shown", "Selected", "Finalized"])
            
        submitted_cust = st.form_submit_button("💾 Save Customer & Open Selection", type="primary")
        if submitted_cust:
            if c_name and c_mob:
                new_id = len(st.session_state.customers) + 1
                cust_dict = {
                    "id": new_id,
                    "name": c_name,
                    "mobile": c_mob,
                    "address": c_addr,
                    "engineer": eng_name,
                    "engineer_mobile": eng_mob,
                    "salesman": st.session_state.user['username'],
                    "status": status,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                st.session_state.customers.append(cust_dict)
                save_customers_to_disk(st.session_state.customers) # Save permanently to disk
                st.success(f"Customer registered successfully with ID #{new_id}!")
            else:
                st.error("Please enter Customer Name and Mobile Number!")
                
    if st.session_state.customers:
        st.subheader("📋 Registered Customers List")
        df_cust = pd.DataFrame(st.session_state.customers)
        st.dataframe(df_cust, use_container_width=True)
        csv_data = df_cust.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Customers CSV",
            data=csv_data,
            file_name="customers_history.csv",
            mime="text/csv"
        )

# -------------------------------------------------------------
# 3. TILES SELECTION (Area-Wise)
# -------------------------------------------------------------
elif menu.startswith("2️⃣"):
    st.header("🎨 Customer Tile Selection (Area-Wise)")
    if not st.session_state.customers:
        st.warning("Please register a customer first in Section 1.")
    else:
        custs = [f"#{c['id']} - {c['name']} ({c['mobile']})" for c in st.session_state.customers]
        sel_cust = st.selectbox("Choose Customer:", custs)
        cid = int(sel_cust.split()[0].replace("#", ""))
        
        with st.form("tile_selection_form"):
            c_f1, c_f2 = st.columns(2)
            with c_f1:
                floor_name = st.selectbox("Floor Name", ["Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "Parking", "Other"])
            with c_f2:
                section_type = st.radio("Section Type", ["Floor Area", "Wall Area"], horizontal=True)
                
            if section_type == "Floor Area":
                default_areas = ["Hall", "Kitchen", "Master Bedroom", "Common Bathroom", "Master Bathroom", "Common Bathroom 1", "Pooja Room", "Balcony", "Staircase", "Type Manually..."]
                chosen_area = st.selectbox("Select Floor Area", default_areas)
                if chosen_area == "Type Manually...":
                    area_name = st.text_input("Enter Custom Floor Area Name")
                else:
                    area_name = chosen_area
            else:
                default_wall = ["Kitchen Wall", "Master Bathroom Wall", "Common Bathroom Wall", "Elevation Wall", "Type Manually..."]
                chosen_wall = st.selectbox("Select Wall Area", default_wall)
                if chosen_wall == "Type Manually...":
                    area_name = st.text_input("Enter Custom Wall Area Name")
                else:
                    area_name = chosen_wall
                    
            search_query = st.text_input("🔍 Search Tile Code / Name from Stock:", "")
            
            filtered_stock = st.session_state.stock_df.copy()
            if not filtered_stock.empty and search_query:
                filtered_stock = filtered_stock[
                    filtered_stock["ITEM_NAME"].str.contains(search_query, case=False, na=False) |
                    filtered_stock["ITEM_ID"].str.contains(search_query, case=False, na=False)
                ]
                
            tile_list = filtered_stock["ITEM_NAME"].tolist() if not filtered_stock.empty else ["No matching tiles found"]
            selected_tile = st.selectbox(f"Select Tile ({len(filtered_stock)} available):", tile_list)
            
            box_sqft = 16.0
            if not filtered_stock.empty and selected_tile in filtered_stock["ITEM_NAME"].values:
                t_obj = filtered_stock[filtered_stock["ITEM_NAME"] == selected_tile].iloc[0]
                box_sqft = float(t_obj["BOX_SQFT"])
                st.info(f"📦 **Box Coverage:** {box_sqft} Sq.Ft / Box")
                
            submitted_tile = st.form_submit_button("➕ Add This Tile Selection", type="primary")
            if submitted_tile:
                if selected_tile and selected_tile != "No matching tiles found" and area_name.strip():
                    if not isinstance(st.session_state.items, list):
                        st.session_state.items = []
                    st.session_state.items.append({
                        "cid": cid,
                        "floor": str(floor_name),
                        "section": str(section_type),
                        "area": str(area_name.strip()),
                        "tile": str(selected_tile),
                        "box_sqft": float(box_sqft),
                        "sqft": 100.0,
                        "boxes": calculate_boxes(100.0, box_sqft)
                    })
                    st.success(f"Added {selected_tile} for {area_name} successfully!")
                else:
                    st.error("Please enter a valid Area Name and select a Tile.")
                    
        st.subheader("📋 Selected Items for this Customer")
        curr_items = []
        if isinstance(st.session_state.items, list):
            for i in st.session_state.items:
                if isinstance(i, dict) and i.get("cid") == cid:
                    curr_items.append({
                        "Floor": i.get("floor"),
                        "Type": i.get("section"),
                        "Area": i.get("area"),
                        "Tile": i.get("tile"),
                        "Box SqFt": i.get("box_sqft")
                    })
                    
        if curr_items:
            st.dataframe(pd.DataFrame(curr_items), use_container_width=True)
            if st.button("🗑️ Clear All Selections for Customer"):
                st.session_state.items = [i for i in st.session_state.items if not (isinstance(i, dict) and i.get("cid") == cid)]
                st.rerun()
        else:
            st.info("No tiles selected yet for this customer.")

# -------------------------------------------------------------
# 4. MEASUREMENTS, BOX CALCULATION, PDF & WHATSAPP
# -------------------------------------------------------------
elif menu.startswith("3️⃣"):
    st.header("📐 Measurements, Box Calculation & WhatsApp PDF")
    if not st.session_state.customers:
        st.warning("No customers found.")
    else:
        custs = [f"#{c['id']} - {c['name']}" for c in st.session_state.customers]
        sel_cust = st.selectbox("Select Customer:", custs)
        cid = int(sel_cust.split()[0].replace("#", ""))
        c_obj = next(c for c in st.session_state.customers if c["id"] == cid)
        
        items = [i for i in st.session_state.items if isinstance(i, dict) and i.get("cid") == cid]
        if items:
            st.markdown("### Enter Actual Area (SqFt) for Each Selection:")
            total_boxes = 0
            for idx, it in enumerate(items):
                col_m1, col_m2 = st.columns([2, 1])
                with col_m1:
                    st.markdown(f"**{it.get('floor')} - {it.get('area')} ({it.get('section')})**<br>Tile: `{it.get('tile')}` (Box Coverage: {it.get('box_sqft')} SqFt)", unsafe_allow_html=True)
                with col_m2:
                    it['sqft'] = st.number_input("Area in SqFt", value=float(it.get('sqft', 100.0)), key=f"sqft_{cid}_{idx}_{it.get('tile')}")
                
                it['boxes'] = calculate_boxes(it['sqft'], it['box_sqft'])
                total_boxes += it['boxes']
                st.caption(f"Required Boxes: **{it['boxes']} Boxes**")
                st.divider()
                
            st.markdown(f"### Total Material Required: **{total_boxes} Boxes**")
            
            if st.button("📄 Generate PDF Quotation & Save", type="primary"):
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
                if c_obj.get('engineer'):
                    pdf.cell(100, 6, f"Reference Engineer: {c_obj['engineer']} ({c_obj.get('engineer_mobile', '')})", ln=True)
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
                pdf.cell(0, 6, f"Total Boxes Required: {total_boxes} Boxes", ln=True)
                
                pdf_bytes = pdf.output(dest='S')
                st.success("Quotation Generated Successfully!")
                
                st.download_button(
                    label="📥 Download PDF Quotation",
                    data=bytes(pdf_bytes),
                    file_name=f"Quotation_{c_obj['name']}.pdf",
                    mime="application/pdf",
                    type="primary"
                )
                
                wa_msg = f"Hello {c_obj['name']}, here is your material estimation quotation from JAY GRANITE & TILES. Total Boxes: {total_boxes}. Thank you!"
                encoded_msg = urllib.parse.quote(wa_msg)
                wa_url = f"https://wa.me/91{c_obj['mobile']}?text={encoded_msg}"
                st.markdown(f"### 📱 Send via WhatsApp:<br><a href='{wa_url}' target='_blank'><button style='background-color:#25D366; color:white; padding:12px 24px; border:none; border-radius:5px; font-weight:bold; cursor:pointer;'>💬 Click to Send WhatsApp to {c_obj['name']}</button></a>", unsafe_allow_html=True)
        else:
            st.info("No items added for this customer yet.")

# -------------------------------------------------------------
# 5. SALES DASHBOARD & LOGIN HISTORY
# -------------------------------------------------------------
elif menu.startswith("4️⃣"):
    st.header("📊 Sales Team Scorecard & Login History")
    if st.session_state.customers:
        df_c = pd.DataFrame(st.session_state.customers)
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Customers", len(df_c))
        col2.metric("Shown", len(df_c[df_c['status'] == 'Shown']))
        col3.metric("Finalized", len(df_c[df_c['status'] == 'Finalized']))
        st.markdown("---")
        st.subheader("Customer Records")
        st.dataframe(df_c, use_container_width=True)
    else:
        st.info("No customer data available.")
        
    st.markdown("---")
    st.subheader("🔐 Salesman Login History")
    if st.session_state.login_history:
        st.dataframe(pd.DataFrame(st.session_state.login_history), use_container_width=True)
    else:
        st.info("No login history recorded in this session.")
