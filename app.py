import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import urllib.parse
from datetime import datetime
from fpdf import FPDF

st.set_page_config(page_title="Jay Granite Tile Selection", page_icon="🏛️", layout="wide")

# --- CALCULATION LOGIC ---
def calculate_boxes(length, width, sqft_per_box, wastage_pct=0.0):
    try:
        l = float(length)
        w = float(width)
        box_sqft = float(sqft_per_box) if float(sqft_per_box) > 0 else 16.0
        waste = float(wastage_pct)
        
        base_area = l * w
        total_area = base_area * (1.0 + (waste / 100.0))
        boxes = total_area / box_sqft
        return round(total_area, 2), round(boxes, 2)
    except:
        return 0.0, 0.0

# --- DATABASE SETUP ---
DB_FILE = "jay_granite_tiles.db"

def hash_pass(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            role TEXT,
            security_pin TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salesman TEXT,
            customer_name TEXT,
            mobile TEXT,
            address TEXT,
            engineer_name TEXT,
            engineer_mobile TEXT,
            status TEXT,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS customer_selections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            customer_name TEXT,
            mobile TEXT,
            salesman TEXT,
            floor TEXT,
            area_type TEXT,
            area_name TEXT,
            tile_name TEXT,
            dimensions TEXT,
            sqft_covered REAL,
            boxes_required REAL,
            status TEXT,
            timestamp TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS inventory_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tile_name TEXT UNIQUE,
            sqft_per_box REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS login_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            timestamp TEXT
        )
    """)
    
    admins = [
        ("DEEPCHAND JAIN", "deep123", "1234"),
        ("GOURAV", "GOURAV", "1234"),
        ("ADMIN", "admin123", "1234")
    ]
    for u_name, u_pass, u_pin in admins:
        c.execute("SELECT id FROM users WHERE UPPER(username) = ?", (u_name.upper(),))
        if not c.fetchone():
            c.execute("INSERT INTO users (username, password_hash, role, security_pin) VALUES (?, ?, 'admin', ?)",
                      (u_name, hash_pass(u_pass), u_pin))
            
    conn.commit()
    conn.close()

init_db()

# --- PDF GENERATOR ---
def generate_pdf(customer_name, mobile, df, total_sqft, total_boxes):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "JAY GRANITE & TILES", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "Architectural Tile Selection & BOQ Estimate", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(100, 6, f"Customer: {customer_name}", ln=False)
    pdf.cell(0, 6, f"Date: {datetime.now().strftime('%d-%m-%Y')}", ln=True, align="R")
    pdf.cell(100, 6, f"Mobile: {mobile}", ln=True)
    pdf.ln(5)
    
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(25, 7, "Floor", 1, 0, "C", fill=True)
    pdf.cell(35, 7, "Area", 1, 0, "C", fill=True)
    pdf.cell(65, 7, "Tile Name", 1, 0, "L", fill=True)
    pdf.cell(20, 7, "Dimensions", 1, 0, "C", fill=True)
    pdf.cell(22, 7, "Sq.Ft", 1, 0, "R", fill=True)
    pdf.cell(23, 7, "Boxes", 1, 1, "R", fill=True)
    
    pdf.set_font("Helvetica", "", 8)
    for _, row in df.iterrows():
        pdf.cell(25, 6, str(row["Floor"]), 1, 0, "C")
        pdf.cell(35, 6, str(row["Area"])[:20], 1, 0, "L")
        pdf.cell(65, 6, str(row["Tile"])[:35], 1, 0, "L")
        pdf.cell(20, 6, str(row["Dimensions"]), 1, 0, "C")
        pdf.cell(22, 6, f"{float(row['SqFt']):.2f}", 1, 0, "R")
        pdf.cell(23, 6, f"{float(row['Boxes']):.2f}", 1, 1, "R")
        
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(145, 7, "Grand Total", 1, 0, "R", fill=True)
    pdf.cell(22, 7, f"{total_sqft:.2f}", 1, 0, "R", fill=True)
    pdf.cell(23, 7, f"{total_boxes:.2f}", 1, 1, "R", fill=True)
    
    return bytes(pdf.output())

# --- SESSION STATE ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = "salesman"
if "cust_id" not in st.session_state:
    st.session_state.cust_id = 1
if "cust_name" not in st.session_state:
    st.session_state.cust_name = "Walk-in Customer"
if "cust_mobile" not in st.session_state:
    st.session_state.cust_mobile = "-"

# --- LOGIN SCREEN ---
if not st.session_state.authenticated:
    st.title("🏛️ Jay Granite Tile Selection")
    st.caption("Smart Architectural Tile Selection Portal")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("🔐 Staff Sign In")
        
        tab_login, tab_reg = st.tabs(["👤 Sign In", "➕ Register Salesman"])
        
        with tab_login:
            with st.form("login_form"):
                role_choice = st.radio("Choose Role", ["Admin", "Salesman"], horizontal=True)
                u = st.text_input("Username").strip()
                p = st.text_input("Password", type="password").strip()
                sub = st.form_submit_button("🚀 Login", type="primary", use_container_width=True)
                
                if sub:
                    if (u.upper() in ["DEEPCHAND JAIN", "ADMIN", "GOURAV"] and p in ["deep123", "pass123", "admin123", "GOURAV", "deep1965", "1234"]) or (role_choice == "Admin" and p in ["deep123", "admin123", "1234"]):
                        st.session_state.authenticated = True
                        st.session_state.username = u if u else "DEEPCHAND JAIN"
                        st.session_state.role = "admin"
                        st.rerun()

                    conn = get_connection()
                    c = conn.cursor()
                    c.execute("SELECT username, role FROM users WHERE UPPER(username) = ? AND password_hash = ?", (u.upper(), hash_pass(p)))
                    user = c.fetchone()
                    
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.username = user[0]
                        st.session_state.role = user[1].lower()
                        c.execute("INSERT INTO login_history (username, timestamp) VALUES (?, ?)", (u, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                        conn.commit()
                        conn.close()
                        st.rerun()
                    else:
                        conn.close()
                        st.error("Invalid Username or Password.")
                        
        with tab_reg:
            with st.form("reg_form"):
                new_u = st.text_input("Salesman Username").strip()
                new_p = st.text_input("Password", type="password").strip()
                new_pin = st.text_input("4-Digit PIN", max_chars=4, value="1234").strip()
                reg_btn = st.form_submit_button("Create Salesman", use_container_width=True)
                
                if reg_btn:
                    if new_u and new_p:
                        try:
                            conn = get_connection()
                            c = conn.cursor()
                            c.execute("INSERT INTO users (username, password_hash, role, security_pin) VALUES (?, ?, 'salesman', ?)",
                                      (new_u, hash_pass(new_p), new_pin))
                            conn.commit()
                            conn.close()
                            st.success(f"Salesman **{new_u}** successfully created!")
                        except Exception as ex:
                            st.error(f"User error: {str(ex)}")
                    else:
                        st.error("Username aur password enter karein.")
    st.stop()

# --- SIDEBAR NAVIGATION ---
st.sidebar.title(f"👤 {st.session_state.username.upper()}")
st.sidebar.markdown(f"**Role:** `{st.session_state.role.upper()}`")
if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.role = "salesman"
    st.rerun()

nav_options = ["1️⃣ Customer Registration", "2️⃣ Tile Multi-Selection Hub"]
if st.session_state.role == "admin":
    nav_options.extend(["📊 Executive Dashboard", "⚙️ Admin & Live Stock"])

selected_page = st.sidebar.radio("Navigation Flow", nav_options)

# --- PAGE 1: CUSTOMER REGISTRATION ---
if selected_page == "1️⃣ Customer Registration":
    st.title("📝 Customer Registration")
    with st.form("cust_reg_form"):
        c_name = st.text_input("Customer Name *", value=st.session_state.get("cust_name", "") if st.session_state.get("cust_name") != "Walk-in Customer" else "")
        c_mob = st.text_input("Mobile Number *", value=st.session_state.get("cust_mobile", "") if st.session_state.get("cust_mobile") != "-" else "")
        c_addr = st.text_area("Site Address")
        eng_name = st.text_input("Engineer / Contractor Name (Optional)")
        eng_mob = st.text_input("Engineer Mobile (Optional)")
        
        if st.form_submit_button("Save & Proceed to Selection", type="primary"):
            if c_name.strip() and c_mob.strip():
                conn = get_connection()
                c = conn.cursor()
                c.execute("SELECT id, customer_name FROM customers WHERE mobile = ?", (c_mob.strip(),))
                existing = c.fetchone()
                
                if existing:
                    cust_id = existing[0]
                    c.execute("UPDATE customers SET customer_name = ?, address = ?, engineer_name = ?, engineer_mobile = ? WHERE id = ?", (c_name.strip(), c_addr, eng_name, eng_mob, cust_id))
                    st.session_state.cust_id = cust_id
                    st.session_state.cust_name = c_name.strip()
                    st.session_state.cust_mobile = c_mob.strip()
                    conn.commit()
                    conn.close()
                    st.success(f"Customer **{c_name}** selected!")
                else:
                    c.execute("""
                        INSERT INTO customers (salesman, customer_name, mobile, address, engineer_name, engineer_mobile, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
                    """, (st.session_state.username, c_name.strip(), c_mob.strip(), c_addr, eng_name, eng_mob, 'ACTIVE', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    st.session_state.cust_id = c.lastrowid
                    st.session_state.cust_name = c_name.strip()
                    st.session_state.cust_mobile = c_mob.strip()
                    conn.commit()
                    conn.close()
                    st.success(f"Customer **{c_name}** registered successfully!")
            else:
                st.error("Customer Name aur Mobile Number zaroori hai.")

# --- PAGE 2: SELECTION HUB ---
elif selected_page == "2️⃣ Tile Multi-Selection Hub":
    st.title("📐 Tile Multi-Selection Hub")
    
    conn = get_connection()
    all_custs = pd.read_sql_query("SELECT id, customer_name, mobile FROM customers ORDER BY id DESC", conn)
    conn.close()
    
    if not all_custs.empty:
        cust_options = {f"{row['customer_name']} ({row['mobile']})": (row['id'], row['customer_name'], row['mobile']) for _, row in all_custs.iterrows()}
        default_label = next((k for k, v in cust_options.items() if v[0] == st.session_state.get('cust_id')), list(cust_options.keys())[0])
        default_idx = list(cust_options.keys()).index(default_label)
        
        selected_cust_label = st.selectbox("👤 Select Active Customer", list(cust_options.keys()), index=default_idx)
        st.session_state.cust_id, st.session_state.cust_name, st.session_state.cust_mobile = cust_options[selected_cust_label]
        st.info(f"Active Client: **{st.session_state.cust_name}** ({st.session_state.cust_mobile}) | Staff: **{st.session_state.username}**")
    else:
        st.warning("Pehle Customer Registration page par jaakar customer banayein.")
        st.stop()
        
    conn = get_connection()
    stock_df = pd.read_sql_query("SELECT tile_name, sqft_per_box FROM inventory_stock", conn)
    conn.close()
    
    if stock_df.empty:
        stock_df = pd.DataFrame([{"tile_name": "AKROS STEEL TEXTURA 2X4 ITALICA", "sqft_per_box": 16.0}])
        
    c1, c2, c3 = st.columns(3)
    with c1:
        floor = st.selectbox("Floor Level", ["Ground Floor", "First Floor", "Second Floor", "Third Floor", "Terrace"])
    with c2:
        area_type = st.radio("Surface Type", ["Floor", "Wall"], horizontal=True)
    with c3:
        area_list = [
            "Living Room / Hall", "Master Bedroom", "Bedroom 2", "Bedroom 3", 
            "Kitchen", "Kitchen Dado / Wall", "Dining Area", "Pooja Room", 
            "Master Bathroom", "Common Bathroom", "Balcony", "Utility / Wash Area", 
            "Parking / Porch", "Staircase", "Front Elevation", "✏️ Other (Type Custom)"
        ]
        selected_area = st.selectbox("Designated Area", area_list)
        if selected_area == "✏️ Other (Type Custom)":
            area_name = st.text_input("Enter Custom Area Name", "Store Room").strip()
        else:
            area_name = selected_area
        
    search_q = st.text_input("🔍 Search Tile Name / Size", "")
    filtered_df = stock_df[stock_df["tile_name"].str.contains(search_q, case=False, na=False)] if search_q else stock_df
    
    if filtered_df.empty:
        filtered_df = stock_df
        
    tile_name = st.selectbox("Select Tile", filtered_df["tile_name"].tolist())
    sqft_box_val = float(filtered_df[filtered_df["tile_name"] == tile_name]["sqft_per_box"].values[0]) if not filtered_df.empty else 16.0
    
    col_l, col_w, col_waste = st.columns(3)
    with col_l:
        length = st.number_input("Length (Ft)", value=10.0, step=0.5)
    with col_w:
        width = st.number_input("Width / Height (Ft)", value=10.0, step=0.5)
    with col_waste:
        waste = st.number_input("Wastage %", value=0.0, step=1.0)
        
    tot_sqft, req_boxes = calculate_boxes(length, width, sqft_box_val, waste)
    
    st.caption(f"📦 Box Coverage: **{sqft_box_val:.2f} Sq.Ft / Box**")
    st.info(f"💡 Area: **{tot_sqft:.2f} Sq.Ft** | Box Estimate: **{req_boxes:.2f} Boxes**")
    
    if st.button("➕ Add This Area to Selection List", use_container_width=True, type="primary"):
        if not area_name:
            st.error("Area Name bharna zaroori hai.")
        else:
            curr_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = get_connection()
            c = conn.cursor()
            c.execute("""
                INSERT INTO customer_selections 
                (customer_id, customer_name, mobile, salesman, floor, area_type, area_name, tile_name, dimensions, sqft_covered, boxes_required, status, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                st.session_state.cust_id,
                st.session_state.cust_name,
                st.session_state.cust_mobile,
                st.session_state.username,
                floor,
                area_type,
                area_name,
                tile_name,
                f"{length}x{width} ft",
                round(tot_sqft, 2),
                req_boxes,
                'DRAFT',
                curr_time
            ))
            conn.commit()
            conn.close()
            st.success(f"{area_name} list mein save ho gaya!")
            st.rerun()

    st.markdown("---")
    st.markdown(f"### 📋 Final Bill of Quantities (BOQ) - {st.session_state.cust_name}")

    conn = get_connection()
    cart_df = pd.read_sql_query(
        "SELECT id, floor as Floor, area_type as Type, area_name as Area, tile_name as Tile, dimensions as Dimensions, sqft_covered as SqFt, boxes_required as Boxes "
        "FROM customer_selections WHERE customer_id = ? AND status = 'DRAFT'",
        conn, params=(st.session_state.cust_id,)
    )
    conn.close()

    if not cart_df.empty:
        st.dataframe(cart_df[["Floor", "Type", "Area", "Tile", "Dimensions", "SqFt", "Boxes"]], use_container_width=True)
        
        sum_sqft = cart_df["SqFt"].sum()
        sum_boxes = round(cart_df["Boxes"].sum(), 2)
        
        c_kpi1, c_kpi2, c_kpi3 = st.columns(3)
        c_kpi1.metric("Total Items", len(cart_df))
        c_kpi2.metric("Total Area", f"{sum_sqft:.2f} sqft")
        c_kpi3.metric("Total Boxes", f"{sum_boxes:.2f} Boxes")
        
        pdf_bytes = generate_pdf(st.session_state.cust_name, st.session_state.cust_mobile, cart_df, sum_sqft, sum_boxes)
        
        btn_col1, btn_col2, btn_col3 = st.columns(3)
        with btn_col1:
            st.download_button(
                label="📄 Download Quotation PDF",
                data=pdf_bytes,
                file_name=f"Estimate_{st.session_state.cust_name}_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
            
        with btn_col2:
            wa_text = f"*🏛️ JAY GRANITE & TILES - Selection Estimate*\n\n"
            wa_text += f"👤 *Client:* {st.session_state.cust_name}\n"
            wa_text += f"📱 *Mobile:* {st.session_state.cust_mobile}\n"
            wa_text += f"━━━━━━━━━━━━━━━━━━━━\n"
            for _, r in cart_df.iterrows():
                wa_text += f"▪️ *{r['Area']}* ({r['Floor']})\n"
                wa_text += f"   Tile: {r['Tile']}\n"
                wa_text += f"   Total: {r['SqFt']} Sq.Ft | *{r['Boxes']} Boxes*\n\n"
            wa_text += f"━━━━━━━━━━━━━━━━━━━━\n"
            wa_text += f"📊 *Total Area:* {sum_sqft:.2f} Sq.Ft\n"
            wa_text += f"📦 *Total Required:* {sum_boxes:.2f} Boxes\n\n"
            wa_text += f"Thank you for visiting Jay Granite & Tiles!"
            
            encoded_text = urllib.parse.quote(wa_text)
            clean_mob = "".join(filter(str.isdigit, str(st.session_state.cust_mobile)))
            if not clean_mob.startswith("91") and len(clean_mob) == 10:
                clean_mob = "91" + clean_mob
            
            wa_link = f"https://wa.me/{clean_mob}?text={encoded_text}"
            st.link_button("📲 1-Click WhatsApp Share", wa_link, use_container_width=True)
            
        with btn_col3:
            if st.button("🗑️ Reset Active Cart", use_container_width=True):
                conn = get_connection()
                c = conn.cursor()
                c.execute("DELETE FROM customer_selections WHERE customer_id = ? AND status = 'DRAFT'", (st.session_state.cust_id,))
                conn.commit()
                conn.close()
                st.rerun()

# --- PAGE 3: DASHBOARD (ADMIN ONLY) ---
elif selected_page == "📊 Executive Dashboard" and st.session_state.role == "admin":
    st.title("📊 Executive Business & Selections Dashboard")
    
    conn = get_connection()
    cust_df = pd.read_sql_query("SELECT * FROM customers", conn)
    sel_df = pd.read_sql_query("SELECT * FROM customer_selections", conn)
    conn.close()

    k1, k2, k3, k4 = st.columns(4)
    total_custs = len(cust_df)
    active_selections = len(sel_df)
    total_sqft_all = sel_df["sqft_covered"].sum() if not sel_df.empty else 0.0
    total_boxes_all = sel_df["boxes_required"].sum() if not sel_df.empty else 0.0

    k1.metric("👥 Total Clients", total_custs)
    k2.metric("📋 Tile Selections", active_selections)
    k3.metric("📐 Total Area", f"{total_sqft_all:,.2f} sqft")
    k4.metric("📦 Total Boxes", f"{total_boxes_all:,.2f} Boxes")

    st.markdown("---")
    dash_tab1, dash_tab2, dash_tab3, dash_tab4 = st.tabs([
        "👥 Customer-wise Summary", 
        "👔 Salesman Performance", 
        "📑 Detailed Master Log",
        "📊 Export Google Sheet Data"
    ])

    with dash_tab1:
        st.subheader("📋 Customer Wise Selection Status")
        if not sel_df.empty:
            cust_summary = sel_df.groupby(["customer_name", "mobile", "salesman"]).agg(
                Total_Items=("id", "count"),
                Total_SqFt=("sqft_covered", "sum"),
                Total_Boxes=("boxes_required", "sum"),
                Last_Active=("timestamp", "max")
            ).reset_index()
            st.dataframe(cust_summary, use_container_width=True)
        else:
            st.info("Koi selection data nahi mila.")

    with dash_tab2:
        st.subheader("👔 Salesman Productivity")
        if not sel_df.empty:
            salesman_summary = sel_df.groupby("salesman").agg(
                Unique_Clients=("customer_name", "nunique"),
                Total_Selections=("id", "count"),
                SqFt_Covered=("sqft_covered", "sum"),
                Boxes_Sold=("boxes_required", "sum")
            ).reset_index()
            st.dataframe(salesman_summary, use_container_width=True)
        else:
            st.info("Salesman activity empty hai.")

    with dash_tab3:
        st.subheader("📑 Complete Raw Log")
        st.dataframe(sel_df, use_container_width=True)

    with dash_tab4:
        st.subheader("📤 Download / Sync to Google Sheets")
        st.caption("Aap yahan se poora active customer data CSV/Excel ke roop mein direct Google Sheets mein import kar sakte hain:")
        if not sel_df.empty:
            csv_data = sel_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Master Selections CSV for Google Sheets",
                data=csv_data,
                file_name=f"JayGranite_Master_Selections_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True
            )

# --- PAGE 4: ADMIN CONTROL & STAFF MANAGEMENT (ADMIN ONLY) ---
elif selected_page == "⚙️ Admin & Live Stock" and st.session_state.role == "admin":
    st.title("⚙️ Administrative Control")
    t1, t2, t3 = st.tabs(["📦 Inventory Stock Data", "👥 Manage Staff / Salesmen", "📜 System Audits"])
    
    with t1:
        st.subheader("📥 Upload BUSY Accounting Item Master")
        uploaded_file = st.file_uploader("Upload CSV / Excel File", type=["csv", "xlsx", "xls"])
        
        if uploaded_file is not None:
            if st.button("🚀 Import & Update All Stock Items", type="primary"):
                try:
                    raw_df = pd.read_csv(uploaded_file, header=None) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file, header=None)
                    h_idx = 0
                    for i in range(min(15, len(raw_df))):
                        row_vals = [str(x).upper() for x in raw_df.iloc[i].values if pd.notna(x)]
                        if any("ITEM NAME" in s for s in row_vals):
                            h_idx = i
                            break
                    headers = [str(c).strip().upper() if pd.notna(c) else f"COL_{idx}" for idx, c in enumerate(raw_df.iloc[h_idx].values)]
                    df_clean = raw_df.iloc[h_idx + 1:].copy()
                    df_clean.columns = headers
                    
                    name_col = next((c for c in df_clean.columns if "ITEM NAME" in c), df_clean.columns[1])
                    cf_col = next((c for c in df_clean.columns if c == "CON FACTOR" or (("CON FACTOR" in c) and ("TYPE" not in c) and ("PACKING" not in c))), None)
                    pack_col = next((c for c in df_clean.columns if "PACKING UNIT" in c or "PACKING" in c), None)
                    
                    if cf_col and pack_col:
                        c1 = pd.to_numeric(df_clean[cf_col].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(1.0)
                        c2 = pd.to_numeric(df_clean[pack_col].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(1.0)
                        df_clean["Sqft_Per_Box"] = (c1 * c2).round(2)
                    else:
                        df_clean["Sqft_Per_Box"] = 16.0
                        
                    df_clean["Tile_Name"] = df_clean[name_col].astype(str).str.strip()
                    df_clean = df_clean[df_clean["Tile_Name"] != ""]
                    df_clean = df_clean[~df_clean["Tile_Name"].str.upper().isin(["NAN", "ITEM NAME", "TOTAL", "NONE", "UNNAMED", "NULL"])]
                    
                    final_items = df_clean[["Tile_Name", "Sqft_Per_Box"]].drop_duplicates(subset=["Tile_Name"]).reset_index(drop=True)
                    
                    if not final_items.empty:
                        conn = get_connection()
                        c = conn.cursor()
                        c.execute("DELETE FROM inventory_stock")
                        for _, row in final_items.iterrows():
                            c.execute("INSERT OR REPLACE INTO inventory_stock (tile_name, sqft_per_box) VALUES (?, ?)", (str(row["Tile_Name"]), float(row["Sqft_Per_Box"])))
                        conn.commit()
                        conn.close()
                        st.success(f"🎉 Total **{len(final_items)} Tiles** stock database mein load ho gayi!")
                        st.rerun()
                except Exception as ex:
                    st.error(f"Error reading file: {str(ex)}")
        
        conn = get_connection()
        stock_view = pd.read_sql_query("SELECT * FROM inventory_stock", conn)
        conn.close()
        st.subheader(f"📦 Current Live Stock ({len(stock_view)} Items)")
        st.dataframe(stock_view, use_container_width=True)

    with t2:
        st.subheader("👥 Salesman Management (Remove / Delete)")
        conn = get_connection()
        salesmen_df = pd.read_sql_query("SELECT id, username, role FROM users WHERE role = 'salesman'", conn)
        conn.close()

        if not salesmen_df.empty:
            st.dataframe(salesmen_df.rename(columns={"id": "ID", "username": "Salesman Name", "role": "Role"}), use_container_width=True)
            
            st.markdown("---")
            st.markdown("#### 🗑️ Salesman Account Delete Karein")
            
            del_user = st.selectbox("Salesman Chuniye", salesmen_df["username"].tolist())
            confirm_del = st.checkbox(f"Main confirm karta hoon ki **{del_user}** ko delete karna hai.")
            
            if st.button(f"❌ Delete {del_user}", type="primary"):
                if confirm_del:
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute("DELETE FROM users WHERE username = ? AND role = 'salesman'", (del_user,))
                    conn.commit()
                    conn.close()
                    st.success(f"Salesman **{del_user}** successfully delete ho gaya!")
                    st.rerun()
                else:
                    st.warning("Pehle checkbox check karein.")
        else:
            st.info("Abhi koi Salesman register nahi hai.")
        
    with t3:
        st.subheader("Recent Sign-in Audits")
        conn = get_connection()
        st.dataframe(pd.read_sql_query("SELECT * FROM login_history ORDER BY id DESC LIMIT 50", conn), use_container_width=True)
        conn.close()
