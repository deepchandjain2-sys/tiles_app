import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import calculations
import database

st.set_page_config(page_title="Jay Granite Tile Selection", page_icon="🏛️", layout="wide")

# Initialize Tables
database.create_tables()

def get_connection():
    return database.get_connection()

# Session State Setup
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

# --- LOGIN & ROLE SELECTION SCREEN ---
if not st.session_state.authenticated:
    st.title("🏛️ Jay Granite Tile Selection")
    st.caption("Smart Architectural Tile Selection Portal")
    
    col_mid1, col_mid2, col_mid3 = st.columns([1, 2, 1])
    with col_mid2:
        st.subheader("🔐 Staff Sign In")
        
        login_tab1, login_tab2 = st.tabs(["👤 Existing User Login", "➕ Create Salesman Account"])
        
        with login_tab1:
            with st.form("login_form"):
                role_choice = st.radio("Choose Login Role", ["Salesman", "Admin"], horizontal=True)
                u = st.text_input("Username").strip()
                p = st.text_input("Password", type="password").strip()
                sub = st.form_submit_button("🚀 Login", type="primary", use_container_width=True)
                
                if sub:
                    conn = get_connection()
                    c = conn.cursor()
                    # Check user
                    c.execute("SELECT username, role FROM users WHERE username = ? AND password_hash = ?", (u, database.hash_pass(p)))
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
                        
        with login_tab2:
            with st.form("create_salesman_form"):
                st.caption("Naye Salesman ka account create karein:")
                new_u = st.text_input("New Salesman Username").strip()
                new_p = st.text_input("New Password", type="password").strip()
                new_pin = st.text_input("4-Digit Recovery PIN", max_chars=4, value="1234").strip()
                reg_sub = st.form_submit_button("Create Salesman", use_container_width=True)
                
                if reg_sub:
                    if new_u and new_p:
                        try:
                            conn = get_connection()
                            c = conn.cursor()
                            c.execute("""
                                INSERT INTO users (username, password_hash, role, security_pin)
                                VALUES (?, ?, 'salesman', ?)
                            """, (new_u, database.hash_pass(new_p), new_pin))
                            conn.commit()
                            conn.close()
                            st.success(f"Salesman **{new_u}** successfully created! Ab login tab se login karein.")
                        except Exception as ex:
                            st.error(f"User already exists or error: {str(ex)}")
                    else:
                        st.error("Username aur password dono bharna zaroori hai.")
    st.stop()

# --- SIDEBAR NAVIGATION (AFTER LOGIN) ---
st.sidebar.title(f"👤 {st.session_state.username.upper()}")
st.sidebar.markdown(f"**Role:** `{st.session_state.role.upper()}`")
if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.rerun()

# Dynamic Menu based on Role
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
                    c.execute("""
                        UPDATE customers 
                        SET customer_name = ?, address = ?, engineer_name = ?, engineer_mobile = ? 
                        WHERE id = ?
                    """, (c_name.strip(), c_addr, eng_name, eng_mob, cust_id))
                    st.session_state.cust_id = cust_id
                    st.session_state.cust_name = c_name.strip()
                    st.session_state.cust_mobile = c_mob.strip()
                    conn.commit()
                    conn.close()
                    st.success(f"Existing Customer **{c_name}** loaded!")
                else:
                    c.execute("""
                        INSERT INTO customers (salesman, customer_name, mobile, address, engineer_name, engineer_mobile, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
                    """, (st.session_state.username, c_name.strip(), c_mob.strip(), c_addr, eng_name, eng_mob, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    st.session_state.cust_id = c.lastrowid
                    st.session_state.cust_name = c_name.strip()
                    st.session_state.cust_mobile = c_mob.strip()
                    conn.commit()
                    conn.close()
                    st.success(f"Customer **{c_name}** registered successfully!")
            else:
                st.error("Customer Name aur Mobile Number bharna zaroori hai.")

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
        st.info(f"Active Client: **{st.session_state.cust_name}** ({st.session_state.cust_mobile}) | Handled by: **{st.session_state.username}**")
    else:
        st.warning("Pehle Customer Registration page par jakar customer banayein.")
        st.stop()
        
    conn = get_connection()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS inventory_stock (id INTEGER PRIMARY KEY AUTOINCREMENT, tile_name TEXT UNIQUE, sqft_per_box REAL)")
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
        area_name = st.text_input("Designated Area (e.g. Living Room, Kitchen)", "Living Room")
        
    search_q = st.text_input("🔍 Search Tile Name / Size", "")
    filtered_df = stock_df[stock_df["tile_name"].str.contains(search_q, case=False, na=False)] if search_q else stock_df
    
    if filtered_df.empty:
        filtered_df = stock_df
        st.caption("Tile match nahi hui, saari items show ho rahi hain.")
        
    tile_name = st.selectbox("Select Tile", filtered_df["tile_name"].tolist())
    sqft_box_val = float(filtered_df[filtered_df["tile_name"] == tile_name]["sqft_per_box"].values[0]) if not filtered_df.empty else 16.0
    
    col_l, col_w, col_waste = st.columns(3)
    with col_l:
        length = st.number_input("Length (Ft)", value=10.0, step=0.5)
    with col_w:
        width = st.number_input("Width / Height (Ft)", value=10.0, step=0.5)
    with col_waste:
        waste = st.number_input("Wastage %", value=0.0, step=1.0)
        
    tot_sqft, req_boxes = calculations.calculate_boxes(length, width, sqft_box_val, waste)
    
    st.caption(f"📦 Box Coverage: **{sqft_box_val:.2f} Sq.Ft / Box**")
    st.info(f"💡 Area: **{tot_sqft:.2f} Sq.Ft** | Box Estimate: **{req_boxes:.2f} Boxes**")
    
    if st.button("➕ Add This Area to Selection List", use_container_width=True, type="primary"):
        if not area_name:
            st.error("Area Name bharna zaroori hai.")
        else:
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
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        c_kpi2.metric("Total Square Feet", f"{sum_sqft:.2f} sqft")
        c_kpi3.metric("Total Boxes", f"{sum_boxes:.2f} Boxes")
        
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("💾 Finalize & Lock Estimate", type="primary", use_container_width=True):
                conn = get_connection()
                c = conn.cursor()
                c.execute("UPDATE customer_selections SET status = 'FINALIZED' WHERE customer_id = ? AND status = 'DRAFT'", (st.session_state.cust_id,))
                conn.commit()
                conn.close()
                st.success(f"{st.session_state.cust_name} ka estimate finalize ho gaya!")
                st.rerun()
        with col_b2:
            if st.button("🗑️ Reset Cart", use_container_width=True):
                conn = get_connection()
                c = conn.cursor()
                c.execute("DELETE FROM customer_selections WHERE customer_id = ? AND status = 'DRAFT'", (st.session_state.cust_id,))
                conn.commit()
                conn.close()
                st.rerun()

# --- PAGE 3: DASHBOARD (ADMIN ONLY) ---
elif selected_page == "📊 Executive Dashboard" and st.session_state.role == "admin":
    st.title("📊 Executive Selections Dashboard")
    conn = get_connection()
    all_selections = pd.read_sql_query("SELECT * FROM customer_selections ORDER BY id DESC", conn)
    conn.close()
    st.dataframe(all_selections, use_container_width=True)

# --- PAGE 4: ADMIN CONTROL (ADMIN ONLY) ---
elif selected_page == "⚙️ Admin & Live Stock" and st.session_state.role == "admin":
    st.title("⚙️ Administrative Control")
    t1, t2 = st.tabs(["📦 Inventory Stock Data", "📜 System Audits"])
    
    with t1:
        st.subheader("📥 Upload BUSY Accounting Item Master / Stock Sheet")
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
                        c.execute("CREATE TABLE IF NOT EXISTS inventory_stock (id INTEGER PRIMARY KEY AUTOINCREMENT, tile_name TEXT UNIQUE, sqft_per_box REAL)")
                        c.execute("DELETE FROM inventory_stock")
                        for _, row in final_items.iterrows():
                            c.execute("INSERT OR REPLACE INTO inventory_stock (tile_name, sqft_per_box) VALUES (?, ?)", (str(row["Tile_Name"]), float(row["Sqft_Per_Box"])))
                        conn.commit()
                        conn.close()
                        st.success(f"🎉 Total **{len(final_items)} Tiles** live database mein load ho gayi!")
                        st.rerun()
                except Exception as ex:
                    st.error(f"Error reading file: {str(ex)}")
        
        conn = get_connection()
        stock_view = pd.read_sql_query("SELECT * FROM inventory_stock", conn)
        conn.close()
        st.subheader(f"📦 Current Live Stock ({len(stock_view)} Items Loaded)")
        st.dataframe(stock_view, use_container_width=True)
        
    with t2:
        st.subheader("Recent Sign-in Audits")
        conn = get_connection()
        st.dataframe(pd.read_sql_query("SELECT * FROM login_history ORDER BY id DESC LIMIT 50", conn), use_container_width=True)
        conn.close()
