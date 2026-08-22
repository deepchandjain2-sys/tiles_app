import streamlit as st
import pandas as pd
import sqlite3
import math
import urllib.parse
from datetime import datetime
from fpdf import FPDF

# -------------------------------------------------------------
# 1. PAGE SETUP & DATABASE HELPERS
# -------------------------------------------------------------
st.set_page_config(page_title="Jay Granite & Tiles Hub", page_icon="🏢", layout="wide")

DB_NAME = "tiles_business.db"

def get_db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

# -------------------------------------------------------------
# 2. GOOGLE SHEET BUSY STOCK LIVE LOADER
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
# 3. PDF GENERATOR
# -------------------------------------------------------------
def generate_pdf(cust, items):
    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "JAY GRANITE & TILES", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, "Opp Reliance Petrol Bunk, Main Road Hiriyur", ln=True, align="C")
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "MATERIAL SELECTION & ESTIMATION SHEET", ln=True, align="C")
    pdf.line(10, 36, 200, 36)
    pdf.ln(5)
    
    # Customer Details
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(100, 6, f"Customer: {cust['name']}", ln=False)
    pdf.cell(90, 6, f"Date: {cust['created_at'][:10]}", ln=True)
    pdf.cell(100, 6, f"Mobile: {cust['mobile']}", ln=False)
    pdf.cell(90, 6, f"Status: {cust['status']}", ln=True)
    pdf.cell(100, 6, f"Site Address: {cust['address']}", ln=False)
    pdf.cell(90, 6, f"Sales Rep: {cust['salesman']}", ln=True)
    if cust['engineer_name']:
        pdf.cell(100, 6, f"Engineer: {cust['engineer_name']} ({cust['engineer_mobile']})", ln=True)
    pdf.ln(4)
    
    # Table Header
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(220, 230, 242)
    pdf.cell(40, 7, "Floor / Area", border=1, fill=True)
    pdf.cell(20, 7, "Type", border=1, fill=True)
    pdf.cell(60, 7, "Selected Tile", border=1, fill=True)
    pdf.cell(25, 7, "Area (SqFt)", border=1, fill=True, align="C")
    pdf.cell(25, 7, "Req Boxes", border=1, fill=True, align="C")
    pdf.cell(20, 7, "Coverage", border=1, fill=True, align="C")
    pdf.ln(7)
    
    # Table Body
    pdf.set_font("Helvetica", "", 8)
    tot_boxes = 0
    tot_sqft = 0.0
    for it in items:
        tot_boxes += it[12] if it[12] else 0
        tot_sqft += (it[12] * it[7]) if it[12] and it[7] else 0.0
        
        pdf.cell(40, 6, f"{it[2]} - {it[4]}", border=1)
        pdf.cell(20, 6, str(it[3]), border=1)
        pdf.cell(60, 6, str(it[6])[:30], border=1)
        pdf.cell(25, 6, f"{it[11]:.1f}" if it[11] else "-", border=1, align="C")
        pdf.cell(25, 6, f"{it[12]} Boxes" if it[12] else "-", border=1, align="C")
        pdf.cell(20, 6, f"{it[12]*it[7]:.1f}" if it[12] and it[7] else "-", border=1, align="C")
        pdf.ln(6)
        
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(120, 7, "Total Estimated Quantity", border=1)
    pdf.cell(25, 7, "", border=1)
    pdf.cell(25, 7, f"{tot_boxes} Boxes", border=1, align="C")
    pdf.cell(20, 7, f"{tot_sqft:.1f} SqFt", border=1, align="C")
    pdf.ln(10)
    
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "* Estimates include standard wastage. Actual usage may vary as per site condition.", ln=True)
    return pdf.output(dest='S')

# -------------------------------------------------------------
# 4. LOGIN & AUTHENTICATION
# -------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

def login(u, p):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT username, role, full_name FROM users WHERE username=? AND password=?", (u, p))
    res = c.fetchone()
    conn.close()
    if res:
        st.session_state.user = {"username": res[0], "role": res[1], "full_name": res[2]}
        return True
    return False

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
                if login(u, p):
                    st.success("Login Successful!")
                    st.rerun()
                else:
                    st.error("Invalid Username or Password!")
        st.info("💡 Default: `admin` / `admin123` or `sales1` / `1234`")
    st.stop()

# -------------------------------------------------------------
# 5. SIDEBAR & NAVIGATION
# -------------------------------------------------------------
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user['full_name']}")
    st.caption(f"Role: **{st.session_state.user['role'].upper()}**")
    
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.user = None
        st.rerun()

    st.markdown("---")
    menu_options = [
        "1️⃣ New Customer Registration",
        "2️⃣ Customer Tile Selection",
        "3️⃣ Site Measurements & BOQ",
        "4️⃣ Sales & Progress Dashboard"
    ]
    if st.session_state.user["role"] == "admin":
        menu_options.append("5️⃣ Admin & Live Stock View")
        
    choice = st.radio("Navigation Flow", menu_options)
    
    st.markdown("---")
    if st.button("🔄 Refresh BUSY Live Stock", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# -------------------------------------------------------------
# MODULE 1: CUSTOMER REGISTRATION
# -------------------------------------------------------------
if choice.startswith("1️⃣"):
    st.header("👤 Customer & Site Registration")
    
    with st.form("cust_reg_form"):
        c1, c2 = st.columns(2)
        with c1:
            c_name = st.text_input("Customer Name *")
            c_mobile = st.text_input("Customer Mobile Number *")
            c_addr = st.text_area("Site / Delivery Address *")
        with c2:
            eng_name = st.text_input("Engineer / Contractor Name")
            eng_mob = st.text_input("Engineer Mobile Number")
            status_init = st.selectbox("Initial Status", ["Shown (सिर्फ दिखाया)", "Selected (पसंद किया)", "Finalized (फाइनल हुआ)"])
            
        submit_cust = st.form_submit_button("💾 Register Customer & Open Selection", type="primary")
        
        if submit_cust:
            if not c_name or not c_mobile:
                st.error("Please enter Customer Name and Mobile Number!")
            else:
                conn = get_db()
                cur = conn.cursor()
                cur.execute('''
                    INSERT INTO customers (name, mobile, address, engineer_name, engineer_mobile, salesman, created_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (c_name, c_mobile, c_addr, eng_name, eng_mob, st.session_state.user['username'], datetime.now().strftime("%Y-%m-%d %H:%M:%S"), status_init.split()[0]))
                conn.commit()
                new_id = cur.lastrowid
                conn.close()
                st.success(f"Customer registered successfully with ID #{new_id}!")
                st.session_state["current_cust_id"] = new_id

# -------------------------------------------------------------
# MODULE 2: TILE SELECTION FORM
# -------------------------------------------------------------
elif choice.startswith("2️⃣"):
    st.header("🎨 Customer Tile Selection")
    
    conn = get_db()
    cust_df = pd.read_sql_query("SELECT id, name, mobile, status, salesman FROM customers ORDER BY id DESC", conn)
    conn.close()
    
    if cust_df.empty:
        st.warning("No customers registered yet. Please register a customer first.")
        st.stop()
        
    cust_options = [f"#{row['id']} - {row['name']} ({row['mobile']}) - [{row['status']}]" for _, row in cust_df.iterrows()]
    selected_cust_str = st.selectbox("🎯 Choose Customer for Selection:", cust_options)
    cust_id = int(selected_cust_str.split()[0].replace("#", ""))
    
    # Selection Form
    with st.expander("➕ Add Tile Selection for Area", expanded=True):
        col_f, col_sec, col_area = st.columns(3)
        with col_f:
            floor_opt = st.selectbox("Floor Level", ["Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "Terrace", "Parking"])
        with col_sec:
            sec_opt = st.radio("Section Type", ["Floor", "Wall"], horizontal=True)
        with col_area:
            area_opt = st.selectbox("Designated Area", ["Living Room", "Hall", "Kitchen", "Bedroom", "Master Bedroom", "Bathroom", "Balcony", "Parking", "Veranda", "Pooja Room", "Custom"])

        st.markdown("##### 🔍 Choose Tile from BUSY Stock")
        s_query = st.text_input("Search Tile Name / Code", placeholder="e.g. 2X4, Varmora, Sega, Italica, 1002")
        
        filtered = stock_df.copy()
        if s_query:
            filtered = filtered[filtered["ITEM_NAME"].str.contains(s_query, case=False, na=False) | filtered["ITEM_ID"].str.contains(s_query, case=False, na=False)]
            
        tile_names = filtered["ITEM_NAME"].tolist() if not filtered.empty else ["No matching tile found"]
        chosen_tile = st.selectbox(f"Matching Items ({len(filtered)} found)", tile_names)
        
        tile_item = filtered[filtered["ITEM_NAME"] == chosen_tile].iloc[0] if not filtered.empty and chosen_tile in filtered["ITEM_NAME"].values else None
        
        if tile_item is not None:
            st.caption(f"📦 **Coverage:** {tile_item['BOX_SQFT']} SqFt / Box ({tile_item['PACKING_UNIT']} Pcs)")
            
        if st.button("💾 Save Tile Selection", type="primary"):
            if tile_item is not None:
                conn = get_db()
                c = conn.cursor()
                c.execute('''
                    INSERT INTO customer_items (customer_id, floor, section_type, area_name, item_id, item_name, box_sqft)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (cust_id, floor_opt, sec_opt, area_opt, tile_item['ITEM_ID'], tile_item['ITEM_NAME'], tile_item['BOX_SQFT']))
                conn.commit()
                conn.close()
                st.success(f"Saved {tile_item['ITEM_NAME']} for {area_opt}!")
                st.rerun()

    # Show Selected Items
    st.subheader("📋 Selected Items List")
    conn = get_db()
    items_saved = pd.read_sql_query(f"SELECT id, floor, section_type, area_name, item_name, box_sqft FROM customer_items WHERE customer_id={cust_id}", conn)
    conn.close()
    if not items_saved.empty:
        st.dataframe(items_saved, use_container_width=True)
    else:
        st.info("No tiles selected yet.")

# -------------------------------------------------------------
# MODULE 3: SITE MEASUREMENTS, BOX CALCULATION & PDF / WHATSAPP
# -------------------------------------------------------------
elif choice.startswith("3️⃣"):
    st.header("📐 Site Measurements & Final BOQ")
    
    conn = get_db()
    cust_df = pd.read_sql_query("SELECT * FROM customers ORDER BY id DESC", conn)
    conn.close()
    
    if cust_df.empty:
        st.warning("No customers registered yet.")
        st.stop()
        
    cust_options = [f"#{row['id']} - {row['name']} ({row['mobile']})" for _, row in cust_df.iterrows()]
    selected_cust_str = st.selectbox("🎯 Select Customer to Re-open / Enter Measurements:", cust_options)
    cust_id = int(selected_cust_str.split()[0].replace("#", ""))
    
    current_cust = cust_df[cust_df["id"] == cust_id].iloc[0].to_dict()
    
    # Update Status
    st.markdown(f"**Customer:** {current_cust['name']} | **Sales Rep:** {current_cust['salesman']}")
    new_stat = st.selectbox("Update Deal Status", ["Shown", "Selected", "Finalized"], index=["Shown", "Selected", "Finalized"].index(current_cust["status"]))
    if st.button("Update Status"):
        conn = get_db()
        conn.cursor().execute("UPDATE customers SET status=? WHERE id=?", (new_stat, cust_id))
        conn.commit()
        conn.close()
        st.success("Deal status updated!")
        st.rerun()

    st.markdown("---")
    st.subheader("Enter Room Dimensions / Square Feet")
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customer_items WHERE customer_id=?", (cust_id,))
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        st.warning("No tiles selected for this customer. Please choose tiles in Module 2 first.")
    else:
        for r in rows:
            r_id, _, r_floor, r_sec, r_area, r_code, r_name, r_box_sqft, r_mode, r_l, r_w, r_wast, r_sqft, r_boxes, _ = r
            
            with st.container():
                st.markdown(f"**{r_floor} ➔ {r_area} ({r_sec})** | Tile: `{r_name}` (Box: {r_box_sqft} SqFt)")
                
                c_mode, c1, c2, c3, c_btn = st.columns([1.5, 1, 1, 1, 1])
                calc_m = c_mode.radio("Input Mode", ["Direct SqFt", "Length × Width"], key=f"m_{r_id}", horizontal=True)
                
                if calc_m == "Direct SqFt":
                    in_sqft = c1.number_input("Total Sq.Ft", value=float(r_sqft) if r_sqft else 100.0, step=10.0, key=f"sq_{r_id}")
                    wastage = c2.number_input("Wastage %", value=float(r_wast) if r_wast else 0.0, step=1.0, key=f"wst_{r_id}")
                    total_area = in_sqft * (1 + (wastage / 100.0))
                    len_v, wid_v = 0.0, 0.0
                else:
                    len_v = c1.number_input("Length (Ft)", value=float(r_l) if r_l else 10.0, step=0.5, key=f"len_{r_id}")
                    wid_v = c2.number_input("Width (Ft)", value=float(r_w) if r_w else 10.0, step=0.5, key=f"wid_{r_id}")
                    wastage = c3.number_input("Wastage %", value=float(r_wast) if r_wast else 0.0, step=1.0, key=f"wst2_{r_id}")
                    total_area = (len_v * wid_v) * (1 + (wastage / 100.0))
                    
                exact_b = total_area / r_box_sqft if r_box_sqft else 0
                req_b = math.ceil(exact_b)
                
                st.caption(f"Required: **{req_b} Boxes** ({req_b * r_box_sqft:.1f} SqFt) | Exact: {exact_b:.2f} Boxes")
                
                if c_btn.button("💾 Save Area", key=f"save_{r_id}"):
                    conn = get_db()
                    conn.cursor().execute('''
                        UPDATE customer_items 
                        SET calc_mode=?, length=?, width=?, wastage=?, sqft=?, boxes=?, exact_boxes=?
                        WHERE id=?
                    ''', (calc_m, len_v, wid_v, wastage, total_area, req_b, exact_b, r_id))
                    conn.commit()
                    conn.close()
                    st.success("Updated!")
                    st.rerun()
                st.divider()

        # PDF & WhatsApp Section
        st.subheader("📄 Generate PDF & WhatsApp Sharing")
        
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM customer_items WHERE customer_id=?", (cust_id,))
        final_items = cur.fetchall()
        conn.close()
        
        pdf_bytes = generate_pdf(current_cust, final_items)
        
        c_pdf, c_wa = st.columns(2)
        with c_pdf:
            st.download_button(
                label="📥 Download Selection PDF",
                data=bytes(pdf_bytes),
                file_name=f"Estimate_{current_cust['name']}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
            
        with c_wa:
            tot_b = sum([it[12] for it in final_items if it[12]])
            wa_text = f"Namaste {current_cust['name']} ji,\nHere is your Tile Selection Summary from Jay Granite & Tiles:\nTotal Requirement: {tot_b} Boxes.\nPlease check the attached estimate."
            wa_url = f"https://api.whatsapp.com/send?phone=91{current_cust['mobile']}&text={urllib.parse.quote(wa_text)}"
            st.markdown(f'''
                <a href="{wa_url}" target="_blank">
                    <button style="width:100%; background-color:#25D366; color:white; border:none; padding:10px; border-radius:6px; font-weight:bold; cursor:pointer;">
                        💬 Share on WhatsApp
                    </button>
                </a>
            ''', unsafe_allow_html=True)

# -------------------------------------------------------------
# MODULE 4: SALESMAN PROGRESS & BUSINESS DASHBOARD
# -------------------------------------------------------------
elif choice.startswith("4️⃣"):
    st.header("📊 Sales Team Performance & Deal Progress")
    
    conn = get_db()
    all_cust = pd.read_sql_query("SELECT * FROM customers", conn)
    conn.close()
    
    if all_cust.empty:
        st.info("No customer activity recorded yet.")
    else:
        # Top Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Customers", len(all_cust))
        m2.metric("Shown (सिर्फ दिखाया)", len(all_cust[all_cust['status'] == 'Shown']))
        m3.metric("Selected (पसंद किया)", len(all_cust[all_cust['status'] == 'Selected']))
        m4.metric("Finalized (डील फाइनल)", len(all_cust[all_cust['status'] == 'Finalized']))
        
        st.markdown("---")
        st.subheader("👨‍💼 Sales Executive History & Scorecard")
        
        # Salesman Breakdown
        sales_summary = all_cust.groupby('salesman')['status'].value_index_table = pd.crosstab(all_cust['salesman'], all_cust['status'])
        st.dataframe(sales_summary, use_container_width=True)
        
        st.markdown("---")
        st.subheader("📋 Recent Customer Pipeline")
        st.dataframe(all_cust[["id", "name", "mobile", "salesman", "status", "created_at"]], use_container_width=True)

# -------------------------------------------------------------
# MODULE 5: ADMIN & BUSY STOCK
# -------------------------------------------------------------
elif choice.startswith("5️⃣"):
    st.header("📊 Live BUSY Inventory Status")
    st.write(f"Total Active Items in Stock: **{len(stock_df)}**")
    st.dataframe(stock_df, use_container_width=True)
