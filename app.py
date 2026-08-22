import streamlit as st
import pandas as pd
import math
from datetime import datetime
from fpdf import FPDF
import io

# -------------------------------------------------------------
# 1. PAGE SETUP
# -------------------------------------------------------------
st.set_page_config(
    page_title="Jay Granite & Tiles Hub",
    page_icon="🏢",
    layout="wide"
)

# -------------------------------------------------------------
# 2. SESSION STATE INITIALIZATION
# -------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

if "customers_db" not in st.session_state:
    st.session_state.customers_db = [
        {
            "id": 1,
            "name": "Sample Customer",
            "mobile": "9876543210",
            "address": "Hiriyur",
            "engineer_name": "Ramesh",
            "engineer_mobile": "9123456780",
            "salesman": "sales1",
            "status": "Shown",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
    ]

if "items_db" not in st.session_state:
    st.session_state.items_db = []

# -------------------------------------------------------------
# 3. BUSY GOOGLE SHEET DATA FETCHER
# -------------------------------------------------------------
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRMgTzS4kNWfaIOByOAZ-RS_XQP7zqiKXAgEkgVhrHNYQU5Jn-srXAfuOW_yPcAmW1G_FrEa59S-RyJ/pub?gid=0&single=true&output=csv"

@st.cache_data(ttl=60)
def load_busy_stock():
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
    except Exception as e:
        st.error(f"Google Sheet Fetch Error: {e}")
        return pd.DataFrame()

stock_df = load_busy_stock()

# -------------------------------------------------------------
# 4. AUTHENTICATION & LOGIN FORM
# -------------------------------------------------------------
if not st.session_state.user:
    st.markdown("<h2 style='color:#1e3a8a; text-align:center;'>🏢 JAY GRANITE & TILES</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Sales & Material Selection Portal</p>", unsafe_allow_html=True)
    
    col_l1, col_l2, col_l3 = st.columns([1, 1.2, 1])
    with col_l2:
        with st.form("login_form"):
            st.subheader("🔐 Staff & Admin Login")
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            btn = st.form_submit_button("Sign In", use_container_width=True, type="primary")
            if btn:
                if (u == "admin" and p == "admin123") or (u == "deepchand" and p == "1234"):
                    st.session_state.user = {"username": u, "role": "admin", "full_name": "Deepchand Jain"}
                    st.rerun()
                elif (u in ["sales1", "sales2"] and p == "1234"):
                    st.session_state.user = {"username": u, "role": "salesman", "full_name": f"Sales Rep ({u})"}
                    st.rerun()
                else:
                    st.error("Invalid Username or Password! (Use: admin / admin123 or sales1 / 1234)")
    st.stop()

# -------------------------------------------------------------
# 5. SIDEBAR NAVIGATION
# -------------------------------------------------------------
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user['full_name']}")
    st.caption(f"Role: **{st.session_state.user['role'].upper()}**")
    
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.user = None
        st.rerun()

    st.markdown("---")
    menu = [
        "1️⃣ New Customer Registration",
        "2️⃣ Customer Tile Selection",
        "3️⃣ Site Measurements & BOQ",
        "4️⃣ Sales & Progress Dashboard",
        "5️⃣ Admin & Live Stock View"
    ]
    choice = st.radio("Navigation", menu)
    
    st.markdown("---")
    if st.button("🔄 Refresh Data List", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# -------------------------------------------------------------
# SCREEN 1: NEW CUSTOMER REGISTRATION
# -------------------------------------------------------------
if choice.startswith("1️⃣"):
    st.header("👤 Customer & Site Registration")
    
    with st.form("cust_reg"):
        c1, c2 = st.columns(2)
        with c1:
            c_name = st.text_input("Customer Name *")
            c_mobile = st.text_input("Customer Mobile *")
            c_addr = st.text_area("Site / Delivery Address *")
        with c2:
            eng_name = st.text_input("Engineer / Contractor Name")
            eng_mob = st.text_input("Engineer Mobile Number")
            status_init = st.selectbox("Initial Status", ["Shown", "Selected", "Finalized"])
            
        submit = st.form_submit_button("💾 Save Customer & Start Selection", type="primary")
        if submit:
            if not c_name or not c_mobile:
                st.error("Please enter Name and Mobile number!")
            else:
                new_id = len(st.session_state.customers_db) + 1
                st.session_state.customers_db.append({
                    "id": new_id,
                    "name": c_name,
                    "mobile": c_mobile,
                    "address": c_addr,
                    "engineer_name": eng_name,
                    "engineer_mobile": eng_mob,
                    "salesman": st.session_state.user["username"],
                    "status": status_init,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                st.success(f"Customer registered with ID #{new_id}!")

# -------------------------------------------------------------
# SCREEN 2: TILE SELECTION
# -------------------------------------------------------------
elif choice.startswith("2️⃣"):
    st.header("🎨 Customer Tile Selection")
    
    if not st.session_state.customers_db:
        st.warning("No customers available. Register a customer first.")
        st.stop()
        
    c_opts = [f"#{c['id']} - {c['name']} ({c['mobile']}) [{c['status']}]" for c in st.session_state.customers_db]
    sel_str = st.selectbox("Select Customer:", c_opts)
    cust_id = int(sel_str.split()[0].replace("#", ""))

    with st.expander("➕ Add Tile for Room / Area", expanded=True):
        col_f, col_sec, col_area = st.columns(3)
        with col_f:
            fl_val = st.selectbox("Floor Level", ["Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "Terrace", "Parking"])
        with col_sec:
            sec_val = st.radio("Section Type", ["Floor", "Wall"], horizontal=True)
        with col_area:
            area_val = st.selectbox("Area", ["Hall", "Living Room", "Kitchen", "Bedroom", "Master Bedroom", "Bathroom", "Balcony", "Parking", "Veranda", "Pooja Room", "Custom"])

        s_term = st.text_input("🔍 Search Tile (e.g. 2X4, Varmora, Italica, 1002):")
        f_stock = stock_df.copy()
        if s_term:
            f_stock = f_stock[f_stock["ITEM_NAME"].str.contains(s_term, case=False, na=False) | f_stock["ITEM_ID"].str.contains(s_term, case=False, na=False)]
            
        t_list = f_stock["ITEM_NAME"].tolist() if not f_stock.empty else ["No tiles found"]
        t_chosen = st.selectbox(f"Select Tile ({len(f_stock)} available)", t_list)
        
        t_data = f_stock[f_stock["ITEM_NAME"] == t_chosen].iloc[0] if not f_stock.empty and t_chosen in f_stock["ITEM_NAME"].values else None
        
        if t_data is not None:
            st.caption(f"📦 Box Coverage: **{t_data['BOX_SQFT']} Sq.Ft / Box**")
            
        if st.button("💾 Save Selection", type="primary"):
            if t_data is not None:
                item_entry = {
                    "item_db_id": len(st.session_state.items_db) + 1,
                    "customer_id": cust_id,
                    "floor": fl_val,
                    "section_type": sec_val,
                    "area_name": area_val,
                    "item_id": t_data["ITEM_ID"],
                    "item_name": t_data["ITEM_NAME"],
                    "box_sqft": t_data["BOX_SQFT"],
                    "calc_mode": "Direct SqFt",
                    "sqft": 100.0,
                    "length": 10.0,
                    "width": 10.0,
                    "wastage": 0.0,
                    "boxes": math.ceil(100.0 / t_data["BOX_SQFT"]),
                    "exact_boxes": round(100.0 / t_data["BOX_SQFT"], 2)
                }
                st.session_state.items_db.append(item_entry)
                st.success(f"Added {t_data['ITEM_NAME']} for {area_val}!")
                st.rerun()

    st.subheader("📋 Selected Items")
    sel_items = [it for it in st.session_state.items_db if it["customer_id"] == cust_id]
    if sel_items:
        st.dataframe(pd.DataFrame(sel_items)[["floor", "section_type", "area_name", "item_name", "box_sqft"]], use_container_width=True)
    else:
        st.info("No tiles selected yet.")

# -------------------------------------------------------------
# SCREEN 3: SITE MEASUREMENTS, BOX CALCULATION & PDF
# -------------------------------------------------------------
elif choice.startswith("3️⃣"):
    st.header("📐 Site Measurements & Final BOQ")
    
    if not st.session_state.customers_db:
        st.warning("No customers registered.")
        st.stop()
        
    c_opts = [f"#{c['id']} - {c['name']} ({c['mobile']})" for c in st.session_state.customers_db]
    sel_str = st.selectbox("Re-Open Customer for Measurement:", c_opts)
    cust_id = int(sel_str.split()[0].replace("#", ""))
    cust_obj = next(c for c in st.session_state.customers_db if c["id"] == cust_id)
    
    # Status Update
    c_stat1, c_stat2 = st.columns([2, 1])
    with c_stat1:
        st.markdown(f"**Customer:** {cust_obj['name']} | **Sales Rep:** {cust_obj['salesman']}")
    with c_stat2:
        new_s = st.selectbox("Status", ["Shown", "Selected", "Finalized"], index=["Shown", "Selected", "Finalized"].index(cust_obj["status"]))
        cust_obj["status"] = new_s

    st.markdown("---")
    st.subheader("Enter Measurements")
    
    matching_items = [it for it in st.session_state.items_db if it["customer_id"] == cust_id]
    
    if not matching_items:
        st.warning("No tiles selected for this customer. Add tiles in Module 2 first.")
    else:
        for idx, item in enumerate(matching_items):
            with st.container():
                st.markdown(f"**{item['floor']} ➔ {item['area_name']} ({item['section_type']})** | `{item['item_name']}` (Box: {item['box_sqft']} SqFt)")
                
                cm, c1, c2, c3 = st.columns([1.5, 1, 1, 1])
                mode_choice = cm.radio("Input Mode", ["Direct SqFt", "Length × Width"], horizontal=True, key=f"rad_{item['item_db_id']}")
                item["calc_mode"] = mode_choice
                
                if mode_choice == "Direct SqFt":
                    item["sqft"] = c1.number_input("Total Sq.Ft", value=float(item.get("sqft", 100.0)), step=10.0, key=f"sq_{item['item_db_id']}")
                    item["wastage"] = c2.number_input("Wastage %", value=float(item.get("wastage", 0.0)), step=1.0, key=f"w_{item['item_db_id']}")
                    net_sqft = item["sqft"] * (1 + (item["wastage"] / 100.0))
                else:
                    item["length"] = c1.number_input("Length (Ft)", value=float(item.get("length", 10.0)), step=0.5, key=f"l_{item['item_db_id']}")
                    item["width"] = c2.number_input("Width (Ft)", value=float(item.get("width", 10.0)), step=0.5, key=f"wi_{item['item_db_id']}")
                    item["wastage"] = c3.number_input("Wastage %", value=float(item.get("wastage", 0.0)), step=1.0, key=f"w2_{item['item_db_id']}")
                    net_sqft = (item["length"] * item["width"]) * (1 + (item["wastage"] / 100.0))
                    item["sqft"] = net_sqft
                    
                b_sqft = item["box_sqft"] if item["box_sqft"] > 0 else 16.0
                item["exact_boxes"] = round(net_sqft / b_sqft, 2)
                item["boxes"] = math.ceil(net_sqft / b_sqft)
                
                st.caption(f"Required: **{item['boxes']} Boxes** ({item['boxes'] * b_sqft:.1f} SqFt) | Exact: {item['exact_boxes']} Boxes")
                st.divider()

        # PDF Generation
        st.subheader("📄 Export Estimation PDF")
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "JAY GRANITE & TILES", ln=True, align="C")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, "Material Selection & Estimation Sheet", ln=True, align="C")
        pdf.ln(5)
        pdf.cell(100, 6, f"Customer: {cust_obj['name']}", ln=False)
        pdf.cell(90, 6, f"Mobile: {cust_obj['mobile']}", ln=True)
        pdf.cell(100, 6, f"Site Address: {cust_obj['address']}", ln=False)
        pdf.cell(90, 6, f"Sales Rep: {cust_obj['salesman']}", ln=True)
        pdf.ln(5)
        
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(40, 7, "Floor / Area", 1)
        pdf.cell(20, 7, "Type", 1)
        pdf.cell(60, 7, "Selected Tile", 1)
        pdf.cell(25, 7, "Area (SqFt)", 1, 0, "C")
        pdf.cell(25, 7, "Req Boxes", 1, 0, "C")
        pdf.cell(20, 7, "Coverage", 1, 1, "C")
        
        pdf.set_font("Helvetica", "", 8)
        tot_b = 0
        tot_c = 0.0
        for it in matching_items:
            tot_b += it["boxes"]
            cov = it["boxes"] * it["box_sqft"]
            tot_c += cov
            pdf.cell(40, 6, f"{it['floor']} - {it['area_name']}", 1)
            pdf.cell(20, 6, str(it['section_type']), 1)
            pdf.cell(60, 6, str(it['item_name'])[:28], 1)
            pdf.cell(25, 6, f"{it['sqft']:.1f}", 1, 0, "C")
            pdf.cell(25, 6, f"{it['boxes']} Boxes", 1, 0, "C")
            pdf.cell(20, 6, f"{cov:.1f}", 1, 1, "C")
            
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(120, 7, "Total Order Requirement", 1)
        pdf.cell(25, 7, "", 1)
        pdf.cell(25, 7, f"{tot_b} Boxes", 1, 0, "C")
        pdf.cell(20, 7, f"{tot_c:.1f} SqFt", 1, 1, "C")
        
        pdf_bytes = pdf.output(dest='S')
        
        st.download_button(
            label="📥 Download Selection PDF",
            data=bytes(pdf_bytes),
            file_name=f"Estimate_{cust_obj['name']}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )

# -------------------------------------------------------------
# SCREEN 4: PROGRESS & SALES DASHBOARD
# -------------------------------------------------------------
elif choice.startswith("4️⃣"):
    st.header("📊 Sales Team Scorecard & Deal Progress")
    
    df_all = pd.DataFrame(st.session_state.customers_db)
    if not df_all.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Customers", len(df_all))
        c2.metric("Shown (दिखाया)", len(df_all[df_all["status"] == "Shown"]))
        c3.metric("Selected (पसंद किया)", len(df_all[df_all["status"] == "Selected"]))
        c4.metric("Finalized (डील फाइनल)", len(df_all[df_all["status"] == "Finalized"]))
        
        st.markdown("---")
        st.subheader("Sales Rep Summary")
        st.dataframe(pd.crosstab(df_all["salesman"], df_all["status"]), use_container_width=True)
        
        st.markdown("---")
        st.subheader("All Customer Pipeline")
        st.dataframe(df_all[["id", "name", "mobile", "salesman", "status", "created_at"]], use_container_width=True)
    else:
        st.info("No customer data available.")

# -------------------------------------------------------------
# SCREEN 5: ADMIN & LIVE STOCK
# -------------------------------------------------------------
elif choice.startswith("5️⃣"):
    st.header("📊 BUSY Live Stock Status")
    st.write(f"Total Items Synced: **{len(stock_df)}**")
    st.dataframe(stock_df, use_container_width=True)
