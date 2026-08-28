import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import urllib.parse
from datetime import datetime
from fpdf import FPDF

st.set_page_config(page_title="Jay Granite Tile Selection", page_icon="🏛️", layout="wide")

# --- CALCULATION LOGIC ---
def calculate_boxes(length, width, sqft_per_box):
    try:
        l = float(length)
        w = float(width)
        box_sqft = float(sqft_per_box) if float(sqft_per_box) > 0 else 16.0
        total_area = round(l * w, 2)
        boxes = round(total_area / box_sqft, 2)
        return total_area, boxes
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
            length REAL DEFAULT 10.0,
            width REAL DEFAULT 10.0,
            sqft_per_box REAL DEFAULT 16.0,
            dimensions TEXT,
            sqft_covered REAL,
            boxes_required REAL,
            status TEXT,
            timestamp TEXT
        )
    """)
    
    c.execute("PRAGMA table_info(customer_selections)")
    cols = [col[1] for col in c.fetchall()]
    if "length" not in cols:
        c.execute("ALTER TABLE customer_selections ADD COLUMN length REAL DEFAULT 10.0")
    if "width" not in cols:
        c.execute("ALTER TABLE customer_selections ADD COLUMN width REAL DEFAULT 10.0")
    if "sqft_per_box" not in cols:
        c.execute("ALTER TABLE customer_selections ADD COLUMN sqft_per_box REAL DEFAULT 16.0")

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
    pdf.cell(0, 6, "Architectural Tile Selection & Measurement Estimate", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(100, 6, f"Customer: {customer_name}", ln=False)
    pdf.cell(0, 6, f"Date: {datetime.now().strftime('%d-%m-%Y')}", ln=True, align="R")
    pdf.cell(100, 6, f"Mobile: {mobile}", ln=True)
    pdf.ln(5)
    
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(22, 7, "Floor", 1, 0, "C", fill=True)
    pdf.cell(32, 7, "Area", 1, 0, "C", fill=True)
    pdf.cell(60, 7, "Tile Name", 1, 0, "L", fill=True)
    pdf.cell(20, 7, "Dimensions", 1, 0, "C", fill=True)
    pdf.cell(18, 7, "Box Coverage", 1, 0, "C", fill=True)
    pdf.cell(20, 7, "Sq.Ft", 1, 0, "R", fill=True)
    pdf.cell(20, 7, "Boxes", 1, 1, "R", fill=True)
    
    pdf.set_font("Helvetica", "", 8)
    for _, row in df.iterrows():
        pdf.cell(22, 6, str(row["Floor"]), 1, 0, "C")
        pdf.cell(32, 6, str(row["Area"])[:18], 1, 0, "L")
        pdf.cell(60, 6, str(row["Tile"])[:32], 1, 0, "L")
        pdf.cell(20, 6, str(row["Dimensions"]), 1, 0, "C")
        pdf.cell(18, 6, f"{float(row['Sqft_Box']):.2f}", 1, 0, "C")
        pdf.cell(20, 6, f"{float(row['SqFt']):.2f}", 1, 0, "R")
        pdf.cell(20, 6, f"{float(row['Boxes']):.2f}", 1, 1, "R")
        
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(152, 7, "Grand Total", 1, 0, "R", fill=True)
    pdf.cell(20, 7, f"{total_sqft:.2f}", 1, 0, "R", fill=True)
    pdf.cell(20, 7, f"{total_boxes:.2f}", 1, 1, "R", fill=True)
    
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
                            st.success(f"Salesman **{new_u}** ban gaya! Sign in karein.")
                        except Exception as ex:
                            st.error(f"User error: {str(ex)}")
                    else:
                        st.error("Username aur Password enter karein.")
    st.stop()

# --- SIDEBAR NAVIGATION ---
st.sidebar.title(f"👤 {st.session_state.username.upper()}")
st.sidebar.markdown(f"**Role:** `{st.session_state.role.upper()}`")
if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.role = "salesman"
    st.rerun()

nav_options = [
    "1️⃣ Customer Registration", 
    "2️⃣ Tile Selection Only", 
    "3️⃣ Measurement, BOQ & Share PDF"
]
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
        
        if st.form_submit_button("Save & Proceed to Tile Selection", type="primary"):
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

# --- PAGE 2: TILE SELECTION ONLY ---
elif selected_page == "2️⃣ Tile Selection Only":
    st.title("🏷️ Showroom Tile Selection (Quick Add)")
    
    conn = get_connection()
    all_custs = pd.read_sql_query("SELECT id, customer_name, mobile FROM customers ORDER BY id DESC", conn)
    conn.close()
    
    if not all_custs.empty:
        cust_options = {f"{row['customer_name']} ({row['mobile']})": (row['id'], row['customer_name'], row['mobile']) for _, row in all_custs.iterrows()}
        default_label = next((k for k, v in cust_options.items() if v[0] == st.session_state.get('cust_id')), list(cust_options.keys())[0])
        default_idx = list(cust_options.keys()).index(default_label)
        
        selected_cust_label = st.selectbox("👤 Active Customer", list(cust_options.keys()), index=default_idx)
        st.session_state.cust_id, st.session_state.cust_name, st.session_state.cust_mobile = cust_options[selected_cust_label]
        st.info(f"Client: **{st.session_state.cust_name}** ({st.session_state.cust_mobile}) | Attended By: **{st.session_state.username}**")
    else:
        st.warning("Pehle Customer Registration page par customer add karein.")
        st.stop()
        
    conn = get_connection()
    stock_df = pd.read_sql_query("SELECT tile_name, sqft_per_box FROM inventory_stock", conn)
    conn.close()
    
    if stock_df.empty:
        stock_df = pd.DataFrame([{"tile_name": "AKROS STEEL TEXTURA 2X4 ITALICA", "sqft_per_box": 16.0}])
        
    st.markdown("---")
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
        
    search_q = st.text_input("🔍 Quick Tile Search (Code / Size / Name)", "")
    filtered_df = stock_df[stock_df["tile_name"].str.contains(search_q, case=False, na=False)] if search_q else stock_df
    
    if filtered_df.empty:
        filtered_df = stock_df
        
    tile_name = st.selectbox("Select Tile Item", filtered_df["tile_name"].tolist())
    sqft_box_val = float(filtered_df[filtered_df["tile_name"] == tile_name]["sqft_per_box"].values[0]) if not filtered_df.empty else 16.0
    
    st.success(f"📦 Tile Packing: **{sqft_box_val:.2f} Sq.Ft per Box** (From Master)")
    
    if st.button("➕ Select & Add Tile to Customer Cart", type="primary", use_container_width=True):
        if not area_name:
            st.error("Area Name enter karein.")
        else:
            tot_sqft, req_boxes = calculate_boxes(10.0, 10.0, sqft_box_val)
            curr_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = get_connection()
            c = conn.cursor()
            c.execute("""
                INSERT INTO customer_selections 
                (customer_id, customer_name, mobile, salesman, floor, area_type, area_name, tile_name, length, width, sqft_per_box, dimensions, sqft_covered, boxes_required, status, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 10.0, 10.0, ?, '10.0x10.0 ft', ?, ?, 'DRAFT', ?)
            """, (
                st.session_state.cust_id,
                st.session_state.cust_name,
                st.session_state.cust_mobile,
                st.session_state.username,
                floor,
                area_type,
                area_name,
                tile_name,
                sqft_box_val,
                tot_sqft,
                req_boxes,
                curr_time
            ))
            conn.commit()
            conn.close()
            st.success(f"✅ **{tile_name}** ({area_name}) add ho gayi!")
            st.rerun()

    st.markdown("---")
    st.subheader(f"🛒 Currently Selected Tiles ({st.session_state.cust_name})")
    conn = get_connection()
    quick_cart = pd.read_sql_query("SELECT id, floor as Floor, area_type as Type, area_name as Area, tile_name as Tile, sqft_per_box as [SqFt/Box] FROM customer_selections WHERE customer_id = ? AND status = 'DRAFT'", conn, params=(st.session_state.cust_id,))
    conn.close()
    
    if not quick_cart.empty:
        st.dataframe(quick_cart[["Floor", "Type", "Area", "Tile", "SqFt/Box"]], use_container_width=True)
        st.info("👉 Tiles select karne ke baad left sidebar se **'3️⃣ Measurement, BOQ & Share PDF'** page par jayein.")
    else:
        st.caption("Abhi koi tile select nahi hui hai.")

# --- PAGE 3: MEASUREMENT & SHARE PDF ---
elif selected_page == "3️⃣ Measurement, BOQ & Share PDF":
    st.title("📐 Measurement, Calculations & Quotation Share")
    
    conn = get_connection()
    all_custs = pd.read_sql_query("SELECT id, customer_name, mobile FROM customers ORDER BY id DESC", conn)
    conn.close()
    
    if not all_custs.empty:
        cust_options = {f"{row['customer_name']} ({row['mobile']})": (row['id'], row['customer_name'], row['mobile']) for _, row in all_custs.iterrows()}
        default_label = next((k for k, v in cust_options.items() if v[0] == st.session_state.get('cust_id')), list(cust_options.keys())[0])
        default_idx = list(cust_options.keys()).index(default_label)
        
        selected_cust_label = st.selectbox("👤 Active Customer", list(cust_options.keys()), index=default_idx)
        st.session_state.cust_id, st.session_state.cust_name, st.session_state.cust_mobile = cust_options[selected_cust_label]
    
    conn = get_connection()
    cart_df = pd.read_sql_query(
        "SELECT id, floor as Floor, area_type as Type, area_name as Area, tile_name as Tile, length, width, sqft_per_box, dimensions as Dimensions, sqft_covered as SqFt, boxes_required as Boxes "
        "FROM customer_selections WHERE customer_id = ? AND status = 'DRAFT'",
        conn, params=(st.session_state.cust_id,)
    )
    conn.close()

    if cart_df.empty:
        st.warning("Is customer ke liye pehle **'2️⃣ Tile Selection Only'** page se tiles add karein.")
        st.stop()

    st.subheader("✏️ Enter Site Measurements (Length x Width):")
    with st.form("measurement_update_form"):
        updated_rows = []
        for idx, r in cart_df.iterrows():
            box_sqft = float(r['sqft_per_box']) if r['sqft_per_box'] else 16.0
            st.markdown(f"**{idx+1}. {r['Area']}** ({r['Floor']} - {r['Type']}) — *{r['Tile']}*  `(Box Coverage: {box_sqft:.2f} Sq.Ft)`")
            c_l, c_w, c_del = st.columns([2, 2, 1])
            with c_l:
                l_val = st.number_input(f"Length (Ft) - #{r['id']}", value=float(r['length']) if r['length'] else 10.0, step=0.5, key=f"len_{r['id']}")
            with c_w:
                w_val = st.number_input(f"Width / Height (Ft) - #{r['id']}", value=float(r['width']) if r['width'] else 10.0, step=0.5, key=f"wid_{r['id']}")
            with c_del:
                del_me = st.checkbox("Remove ❌", key=f"del_{r['id']}")
            
            new_sqft, new_boxes = calculate_boxes(l_val, w_val, box_sqft)
            updated_rows.append((r['id'], l_val, w_val, f"{l_val}x{w_val} ft", new_sqft, new_boxes, del_me))
            st.markdown("---")
            
        if st.form_submit_button("💾 Save All Measurements & Update BOQ", type="primary", use_container_width=True):
            conn = get_connection()
            c = conn.cursor()
            for r_id, l_v, w_v, dim_str, s_v, b_v, should_del in updated_rows:
                if should_del:
                    c.execute("DELETE FROM customer_selections WHERE id = ?", (r_id,))
                else:
                    c.execute("""
                        UPDATE customer_selections 
                        SET length = ?, width = ?, dimensions = ?, sqft_covered = ?, boxes_required = ?
                        WHERE id = ?
                    """, (l_v, w_v, dim_str, s_v, b_v, r_id))
            conn.commit()
            conn.close()
            st.success("Measurements calculate aur save ho gaye!")
            st.rerun()

    conn = get_connection()
    summary_df = pd.read_sql_query(
        "SELECT id, floor as Floor, area_type as Type, area_name as Area, tile_name as Tile, dimensions as Dimensions, sqft_per_box as Sqft_Box, sqft_covered as SqFt, boxes_required as Boxes "
        "FROM customer_selections WHERE customer_id = ? AND status = 'DRAFT'",
        conn, params=(st.session_state.cust_id,)
    )
    conn.close()

    st.markdown(f"### 📋 Final Bill of Quantities (BOQ) - {st.session_state.cust_name}")
    st.dataframe(summary_df[["Floor", "Type", "Area", "Tile", "Dimensions", "Sqft_Box", "SqFt", "Boxes"]], use_container_width=True)
    
    sum_sqft = summary_df["SqFt"].sum()
    sum_boxes = round(summary_df["Boxes"].sum(), 2)
    
    c_k1, c_k2, c_k3 = st.columns(3)
    c_k1.metric("Total Items", len(summary_df))
    c_k2.metric("Total Area", f"{sum_sqft:.2f} Sq.Ft")
    c_k3.metric("Total Boxes Required", f"{sum_boxes:.2f} Boxes")
    
    wa_text = f"🏛️ *JAY GRANITE & TILES - TILE SELECTION ESTIMATE*\n\n"
    wa_text += f"👤 *Client Name:* {st.session_state.cust_name}\n"
    wa_text += f"📱 *Mobile:* {st.session_state.cust_mobile}\n"
    wa_text += f"📅 *Date:* {datetime.now().strftime('%d-%m-%Y')}\n"
    wa_text += f"━━━━━━━━━━━━━━━━━━━━\n"
    for _, r in summary_df.iterrows():
        wa_text += f"🔹 *{r['Area']}* ({r['Floor']} - {r['Type']})\n"
        wa_text += f"   • Tile: {r['Tile']}\n"
        wa_text += f"   • Size: {r['Dimensions']} | Area: {r['SqFt']} Sq.Ft\n"
        wa_text += f"   • Box Coverage: {r['Sqft_Box']} Sq.Ft/Box\n"
        wa_text += f"   • Quantity: *{r['Boxes']} Boxes*\n\n"
    wa_text += f"━━━━━━━━━━━━━━━━━━━━\n"
    wa_text += f"📊 *Total Area:* {sum_sqft:.2f} Sq.Ft\n"
    wa_text += f"📦 *Total Required Boxes:* {sum_boxes:.2f} Boxes\n\n"
    wa_text += f"Thank you for choosing Jay Granite & Tiles!"

    st.markdown("#### 💬 WhatsApp Direct Copy-Paste Text")
    st.text_area("Yahan se message copy karke WhatsApp par share karein:", value=wa_text, height=180)

    pdf_bytes = generate_pdf(st.session_state.cust_name, st.session_state.cust_mobile, summary_df, sum_sqft, sum_boxes)
    
    b1, b2, b3 = st.columns(3)
    with b1:
        st.download_button(
            label="📄 Download Estimate PDF",
            data=pdf_bytes,
            file_name=f"Estimate_{st.session_state.cust_name}_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    with b2:
        encoded_text = urllib.parse.quote(wa_text)
        clean_mob = "".join(filter(str.isdigit, str(st.session_state.cust_mobile)))
        if not clean_mob.startswith("91") and len(clean_mob) == 10:
            clean_mob = "91" + clean_mob
        st.link_button("📲 1-Click WhatsApp Send", f"https://wa.me/{clean_mob}?text={encoded_text}", use_container_width=True)
    with b3:
        if st.button("🗑️ Reset Cart", use_container_width=True):
            conn = get_connection()
            c = conn.cursor()
            c.execute("DELETE FROM customer_selections WHERE customer_id = ? AND status = 'DRAFT'", (st.session_state.cust_id,))
            conn.commit()
            conn.close()
            st.rerun()

# --- PAGE 4: EXECUTIVE DASHBOARD (ADMIN ONLY) ---
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
    dash_tab1, dash_tab2, dash_tab3 = st.tabs(["👥 Customer-wise Summary", "👔 Salesman Performance", "📑 Detailed Master Log"])

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

# --- PAGE 5: ADMIN CONTROL & GOOGLE SHEET SYNC (CON FACTOR * PACKING UNIT) ---
elif selected_page == "⚙️ Admin & Live Stock" and st.session_state.role == "admin":
    st.title("⚙️ Administrative Control")
    t1, t2, t3 = st.tabs(["🔗 Direct Google Sheet Live Stock", "👥 Manage Staff / Salesmen", "📜 System Audits"])
    
    with t1:
        st.subheader("🔗 Live Connect Google Sheet (BUSY Master Auto-Calculation)")
        st.caption("Formula: `Con Factor * Packing Unit = SqFt Per Box`")
        sheet_url_input = st.text_input("Google Sheet Link", placeholder="https://docs.google.com/spreadsheets/d/...")
        
        if st.button("🔄 Sync Live Stock From Google Sheet", type="primary"):
            if sheet_url_input.strip():
                try:
                    url = sheet_url_input.strip()
                    if "/edit" in url:
                        url = url.split("/edit")[0] + "/export?format=csv"
                    
                    df_live = pd.read_csv(url)
                    
                    # Columns cleaning
                    df_live.columns = [str(c).strip().upper() for c in df_live.columns]
                    
                    name_col = next((c for c in df_live.columns if "ITEM" in c or "NAME" in c or "TILE" in c), df_live.columns[0])
                    cf_col = next((c for c in df_live.columns if "CON FACTOR" in c or "CONVERSION" in c), None)
                    pack_col = next((c for c in df_live.columns if "PACKING" in c or "UNIT" in c or "PCS" in c), None)
                    sqft_direct = next((c for c in df_live.columns if "SQFT" in c or "COVERAGE" in c), None)
                    
                    if cf_col and pack_col:
                        c1 = pd.to_numeric(df_live[cf_col].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(1.0)
                        c2 = pd.to_numeric(df_live[pack_col].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(1.0)
                        df_live["Sqft_Per_Box"] = (c1 * c2).round(2)
                    elif sqft_direct:
                        df_live["Sqft_Per_Box"] = pd.to_numeric(df_live[sqft_direct].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(16.0)
                    else:
                        df_live["Sqft_Per_Box"] = 16.0
                        
                    df_live["Tile_Name"] = df_live[name_col].astype(str).str.strip()
                    df_clean = df_live[["Tile_Name", "Sqft_Per_Box"]].dropna().drop_duplicates(subset=["Tile_Name"])
                    df_clean = df_clean[df_clean["Tile_Name"] != ""]
                    df_clean = df_clean[~df_clean["Tile_Name"].str.upper().isin(["NAN", "ITEM NAME", "TOTAL", "NONE"])]
                    
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute("DELETE FROM inventory_stock")
                    for _, row in df_clean.iterrows():
                        c.execute("INSERT OR REPLACE INTO inventory_stock (tile_name, sqft_per_box) VALUES (?, ?)", 
                                  (str(row["Tile_Name"]), float(row["Sqft_Per_Box"])))
                    conn.commit()
                    conn.close()
                    
                    st.success(f"🎉 Google Sheet se total **{len(df_clean)} Tiles** accurate `Con Factor * Packing Unit` formula ke saath sync ho gayi!")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Google Sheet read error: {str(ex)}")
            else:
                st.warning("Google Sheet ka link paste karein.")
        
        conn = get_connection()
        stock_view = pd.read_sql_query("SELECT tile_name as [Tile Name], sqft_per_box as [SqFt Per Box] FROM inventory_stock", conn)
        conn.close()
        st.markdown("---")
        st.subheader(f"📦 Current Live Stock ({len(stock_view)} Items with exact SqFt/Box)")
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
                    st.success(f"Salesman **{del_user}** delete ho gaya!")
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
