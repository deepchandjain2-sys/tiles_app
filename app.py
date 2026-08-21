import streamlit as st
import pandas as pd
import sqlite3
import math
from datetime import datetime
import urllib.parse
from fpdf import FPDF
from database import create_tables, get_connection, hash_pass
from calculations import calculate_boxes

st.set_page_config(page_title="Jay Granite Tile Selection", layout="wide", page_icon="🏛️")
create_tables()

# Database setup for Inventory
conn = get_connection()
c = conn.cursor()
c.execute("""
    CREATE TABLE IF NOT EXISTS inventory_stock (
        tile_name TEXT PRIMARY KEY,
        sqft_per_box REAL
    )
""")
conn.commit()
conn.close()

# Custom UI Styling
st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #1f2937, #111827);
        border: 1px solid #374151;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
    .step-badge {
        display: inline-block;
        padding: 6px 14px;
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        color: white;
        font-weight: bold;
        border-radius: 20px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# Session States
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.role = None
if "reset_mode" not in st.session_state:
    st.session_state.reset_mode = False
if "current_cart" not in st.session_state:
    st.session_state.current_cart = []

# --- PDF GENERATOR ---
def generate_pdf_estimate(cust_info, cart_items, total_sqft, total_boxes, staff_user):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(41, 128, 185)
    pdf.cell(0, 10, "JAY GRANITE & TILES", ln=True, align="C")
    
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 6, "TILES SELECTION & ESTIMATE QUOTATION", ln=True, align="C")
    pdf.ln(4)
    
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(100, 5, f"Customer: {cust_info['customer_name']}", ln=False)
    pdf.cell(0, 5, f"Date: {datetime.now().strftime('%d-%m-%Y %H:%M')}", ln=True)
    pdf.cell(100, 5, f"Mobile: {cust_info['mobile']}", ln=False)
    pdf.cell(0, 5, f"Prepared By: {staff_user}", ln=True)
    if cust_info.get('address'):
        pdf.cell(0, 5, f"Site: {cust_info['address']}", ln=True)
    pdf.ln(4)
    
    # Table Header
    pdf.set_fill_color(41, 128, 185)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(12, 7, "#", 1, 0, "C", True)
    pdf.cell(45, 7, "Floor / Area", 1, 0, "L", True)
    pdf.cell(75, 7, "Tile Specification", 1, 0, "L", True)
    pdf.cell(30, 7, "Dimensions (SqFt)", 1, 0, "C", True)
    pdf.cell(28, 7, "Estimate", 1, 1, "C", True)
    
    # Table Rows
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 8)
    for idx, itm in enumerate(cart_items, 1):
        area_txt = f"{itm['Floor'][:10]} - {itm['Area'][:12]}"
        tile_txt = str(itm['Tile'])[:42]
        size_txt = f"{itm['Dimensions']} ({itm['SqFt']} sf)"
        box_txt = f"{itm['Boxes']} Boxes"
        
        pdf.cell(12, 6, str(idx), 1, 0, "C")
        pdf.cell(45, 6, area_txt, 1, 0, "L")
        pdf.cell(75, 6, tile_txt, 1, 0, "L")
        pdf.cell(30, 6, size_txt, 1, 0, "C")
        pdf.cell(28, 6, box_txt, 1, 1, "C")
        
    # Footer Total
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(132, 7, "GRAND TOTAL", 1, 0, "R", True)
    pdf.cell(30, 7, f"{total_sqft:.2f} SqFt", 1, 0, "C", True)
    pdf.cell(28, 7, f"{total_boxes} Boxes", 1, 1, "C", True)
    
    return bytes(pdf.output())

# --- PAGE 1: LOGIN ---
def login_view():
    st.markdown("<div style='text-align: center; margin-top: 30px;'><h1 style='color:#3b82f6;'>🏛️ Jay Granite Tile Selection</h1><p style='color:#9ca3af;'>Smart Architectural Tile Selection Portal</p></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.6, 1])
    
    with c2:
        with st.container(border=True):
            if not st.session_state.reset_mode:
                st.subheader("🔐 Staff Sign In")
                uname = st.text_input("Username")
                pword = st.text_input("Password", type="password")
                
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("Login", type="primary", use_container_width=True):
                        conn = get_connection()
                        c = conn.cursor()
                        c.execute("SELECT role FROM users WHERE username = ? AND password_hash = ?", (uname, hash_pass(pword)))
                        data = c.fetchone()
                        if data:
                            st.session_state.authenticated = True
                            st.session_state.user = uname
                            st.session_state.role = data[0]
                            c.execute("INSERT INTO login_history (username, timestamp) VALUES (?, ?)", (uname, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                            conn.commit()
                            conn.close()
                            st.rerun()
                        else:
                            st.error("Invalid credentials.")
                            conn.close()
                with b2:
                    if st.button("Forgot PIN/Pass?", use_container_width=True):
                        st.session_state.reset_mode = True
                        st.rerun()
            else:
                st.subheader("🔑 Password Recovery")
                r_user = st.text_input("Username")
                r_pin = st.text_input("4-Digit Security PIN", type="password")
                r_pass = st.text_input("New Password", type="password")
                
                rb1, rb2 = st.columns(2)
                with rb1:
                    if st.button("Update", type="primary", use_container_width=True):
                        conn = get_connection()
                        c = conn.cursor()
                        c.execute("SELECT * FROM users WHERE username = ? AND security_pin = ?", (r_user, r_pin))
                        if c.fetchone():
                            c.execute("UPDATE users SET password_hash = ? WHERE username = ?", (hash_pass(r_pass), r_user))
                            conn.commit()
                            conn.close()
                            st.success("Password reset done!")
                            st.session_state.reset_mode = False
                            st.rerun()
                        else:
                            st.error("Invalid Username or PIN")
                            conn.close()
                with rb2:
                    if st.button("Cancel", use_container_width=True):
                        st.session_state.reset_mode = False
                        st.rerun()

if not st.session_state.authenticated:
    login_view()
    st.stop()

# --- SIDEBAR ---
st.sidebar.markdown(f"""
<div style='background:#1f2937; padding:12px; border-radius:8px; border-left:4px solid #3b82f6;'>
    <h4 style='margin:0; color:#f3f4f6;'>👤 {st.session_state.user.upper()}</h4>
    <small style='color:#9ca3af;'>Designation: {st.session_state.role.title()}</small>
</div>
""", unsafe_allow_html=True)

if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.current_cart = []
    st.rerun()

st.sidebar.markdown("---")
nav_pages = [
    "1️⃣ Customer Registration",
    "2️⃣ Tile Multi-Selection Hub",
    "📊 Executive Dashboard"
]
if st.session_state.role == "admin":
    nav_pages.append("⚙️ Admin & Live Stock")

selected_page = st.sidebar.radio("Navigation Flow", nav_pages)

def get_all_stock():
    conn = get_connection()
    df = pd.read_sql_query("SELECT tile_name AS Tile_Name, sqft_per_box AS Sqft_Per_Box FROM inventory_stock ORDER BY tile_name ASC", conn)
    conn.close()
    if df.empty:
        return pd.DataFrame([{"Tile_Name": "AKROS STEEL TEXTURA 2X4 ITALICA", "Sqft_Per_Box": 16.0}])
    return df

stock_df = get_all_stock()

# --- PAGE 1: CUSTOMER REGISTRATION ---
if selected_page == "1️⃣ Customer Registration":
    st.markdown("<span class='step-badge'>STEP 1 : PARTY ONBOARDING</span>", unsafe_allow_html=True)
    st.title("👤 Customer & Site Profiling")
    
    with st.form("party_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Customer Data")
            c_name = st.text_input("Customer Full Name *")
            c_mobile = st.text_input("Customer Contact / WhatsApp *")
            c_address = st.text_area("Site / Delivery Address")
        with c2:
            st.markdown("#### Technical Lead Details")
            eng_name = st.text_input("Architect / Contractor Name")
            eng_mob = st.text_input("Architect Contact Number")
            status = st.selectbox("Initial Lead Stage", ["New Visit", "Tile Selection", "Follow-up", "Finalised"])
            
        save_party = st.form_submit_button("💾 Save Customer & Continue to Selection", type="primary", use_container_width=True)
        
    if save_party:
        if not c_name or not c_mobile:
            st.error("Customer Name aur Mobile number bharna zaroori hai.")
        else:
            conn = get_connection()
            c = conn.cursor()
            try:
                c.execute("""INSERT INTO customers (
                    salesman, customer_name, mobile, address, engineer_name, engineer_mobile, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (
                    st.session_state.user, c_name, c_mobile, c_address, eng_name, eng_mob, status, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
                conn.commit()
                st.success(f"Customer '{c_name}' successfully register ho gaya! Ab Step 2 me jayein.")
            except sqlite3.IntegrityError:
                st.warning("Yeh Mobile number pehle se registered hai.")
            finally:
                conn.close()

# --- PAGE 2: SELECTION & ESTIMATE ---
elif selected_page == "2️⃣ Tile Multi-Selection Hub":
    st.markdown("<span class='step-badge'>STEP 2 : ROOM-WISE SELECTION & CALCULATION</span>", unsafe_allow_html=True)
    st.title("📦 Multi-Area Tile Estimator")
    
    conn = get_connection()
    customers_df = pd.read_sql_query("SELECT id, customer_name, mobile, address, status FROM customers ORDER BY id DESC", conn)
    conn.close()
    
    if customers_df.empty:
        st.warning("Pehle Step 1 me jaakar Customer Register karein.")
        st.stop()
        
    cust_options = {f"{row['customer_name']} ({row['mobile']})": row for _, row in customers_df.iterrows()}
    chosen_label = st.selectbox("🎯 Select Active Customer", list(cust_options.keys()))
    active_cust = cust_options[chosen_label]
    
    st.markdown("---")
    st.markdown("### 📐 Add Surface Specification")
    f1, f2, f3 = st.columns(3)
    with f1:
        floor = st.selectbox("Floor Level", ["Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "Basement", "Terrace"])
    with f2:
        area_type = st.radio("Surface Type", ["Floor", "Wall"], horizontal=True)
    with f3:
        area_preset = st.selectbox("Designated Area", 
                                   ["Living Room", "Master Bedroom", "Kitchen Floor", "Kitchen Dado", "Master Bath", "Common Bath", "Balcony", "Custom / Manual"])
        if area_preset == "Custom / Manual":
            area_name = st.text_input("Type Area Name (e.g. Pooja Room, Porch)")
        else:
            area_name = area_preset

    st.markdown("#### 🔲 Tile Search & Dimensions")
    search_query = st.text_input("🔍 Type Tile Code / Name to Search (e.g. 1002, 16X16, 2X4, ITALICA):", value="")
    all_tiles = stock_df["Tile_Name"].dropna().unique().tolist()
    
    if search_query:
        tile_list = [t for t in all_tiles if search_query.lower() in t.lower()]
        if not tile_list:
            st.warning("Matching tile nahi mili. Saari list show ho rahi hai.")
            tile_list = all_tiles
    else:
        tile_list = all_tiles

    t_col, d1, d2, d3 = st.columns([2.5, 1, 1, 1])
    with t_col:
        tile_name = st.selectbox(f"Select Tile ({len(tile_list)} available)", tile_list)
        
        # Con Factor & Packing Unit Calculation
        t_str = str(tile_name).upper()
        if "2X4" in t_str or "4X2" in t_str:
            con_factor = 8.0
            packing_unit = 2.0
        elif "12X18" in t_str:
            con_factor = 1.5
            packing_unit = 6.0
        elif "16X16" in t_str:
            con_factor = 1.73
            packing_unit = 5.0
        elif "2X2" in t_str:
            con_factor = 4.0
            packing_unit = 4.0
        elif "1X1" in t_str:
            con_factor = 1.0
            packing_unit = 10.0
        else:
            con_factor = 8.0
            packing_unit = 2.0
            
    with d1:
        length = st.number_input("Length (Ft)", min_value=0.0, value=10.0, step=0.5)
    with d2:
        width = st.number_input("Width / Height (Ft)", min_value=0.0, value=10.0, step=0.5)
    with d3:
        wastage = st.number_input("Wastage %", value=0.0, step=1.0)

    tot_sqft, box_sqft, req_boxes = calculate_boxes(length, width, con_factor, packing_unit, wastage)

    st.caption(f"📦 Box Coverage: **{box_sqft:.2f} Sq.Ft / Box** (Con Factor: {con_factor} × Packing Unit: {packing_unit})")
    st.info(f"💡 Area: **{tot_sqft:.2f} Sq.Ft** | Box Estimate: **{req_boxes} Boxes**")

    if st.button("➕ Add This Area to Selection List", use_container_width=True):
        if not area_name:
            st.error("Area Name enter karna zaroori hai.")
        else:
            st.session_state.current_cart.append({
                "Floor": floor,
                "Type": area_type,
                "Area": area_name,
                "Tile": tile_name,
                "Dimensions": f"{length}x{width} ft",
                "SqFt": round(tot_sqft, 2),
                "Boxes": req_boxes
            })
            st.success(f"{area_name} list mein add ho gaya!")

    st.markdown("---")
    st.markdown("### 📋 Final Bill of Quantities (BOQ)")
    if st.session_state.current_cart:
        cart_table = pd.DataFrame(st.session_state.current_cart)
        st.dataframe(cart_table[["Floor", "Type", "Area", "Tile", "Dimensions", "SqFt", "Boxes"]], use_container_width=True)
        
        sum_sqft = sum(i["SqFt"] for i in st.session_state.current_cart)
        sum_boxes = round(sum(i["Boxes"] for i in st.session_state.current_cart), 2)
        
        c_kpi1, c_kpi2, c_kpi3 = st.columns(3)
        c_kpi1.metric("Total Line Items", len(st.session_state.current_cart))
        c_kpi2.metric("Total Square Feet", f"{sum_sqft:.2f} sqft")
        c_kpi3.metric("Total Boxes Required", f"{sum_boxes} Boxes")
        
        # Generate PDF Bytes
        pdf_bytes = generate_pdf_estimate(active_cust, st.session_state.current_cart, sum_sqft, sum_boxes, st.session_state.user)

        b1, b2, b3 = st.columns([1.5, 1.5, 1])
        with b1:
            if st.button("💾 Finalize & Save Estimate", type="primary", use_container_width=True):
                conn = get_connection()
                c = conn.cursor()
                now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for itm in st.session_state.current_cart:
                    c.execute("""INSERT INTO customer_selections (
                        customer_id, customer_name, mobile, salesman, floor, area_type, area_name,
                        tile_name, dimensions, sqft_covered, boxes_required, status, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                        int(active_cust["id"]), active_cust["customer_name"], active_cust["mobile"],
                        st.session_state.user, itm["Floor"], itm["Type"], itm["Area"],
                        itm["Tile"], itm["Dimensions"], itm["SqFt"], itm["Boxes"], active_cust["status"], now_time
                    ))
                conn.commit()
                conn.close()
                st.success("Quotation database mein save ho gayi!")

        with b2:
            st.download_button(
                label="📄 Download Quotation PDF",
                data=pdf_bytes,
                file_name=f"JayGranite_Estimate_{active_cust['customer_name']}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        with b3:
            if st.button("🗑️ Reset Cart", use_container_width=True):
                st.session_state.current_cart = []
                st.rerun()

        # WhatsApp Open Button
        clean_phone = str(active_cust["mobile"]).replace("+", "").replace(" ", "").replace("-", "")
        msg_text = f"Namaste {active_cust['customer_name']} ji, Jay Granite ki taraf se aapka Tile Selection Estimate PDF generate kar diya gaya hai. Total Area: {sum_sqft:.2f} sqft, Total Boxes: {sum_boxes} Boxes. Estimate PDF attached hai."
        wa_url = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(msg_text)}"
        st.markdown(f"""<a href="{wa_url}" target="_blank"><button style="background:linear-gradient(90deg,#25D366,#128C7E);color:white;padding:12px;border:none;border-radius:8px;width:100%;font-size:15px;font-weight:bold;cursor:pointer;margin-top:10px;">📲 1-Click WhatsApp Open (Send PDF)</button></a>""", unsafe_allow_html=True)
    else:
        st.info("Area aur tile select karke '➕ Add This Area to Selection List' button dabayein.")

# --- PAGE 3: DASHBOARD ---
elif selected_page == "📊 Executive Dashboard":
    st.title("📊 Business & Sales Performance")
    conn = get_connection()
    df_cust = pd.read_sql_query("SELECT * FROM customers", conn)
    df_items = pd.read_sql_query("SELECT * FROM customer_selections", conn)
    conn.close()

    if df_cust.empty:
        st.info("No records available.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        total_p = len(df_cust)
        finalized_p = len(df_cust[df_cust["status"] == "Finalised"])
        followup_p = len(df_cust[df_cust["status"] == "Follow-up"])
        rate = (finalized_p / total_p * 100) if total_p > 0 else 0
        
        m1.metric("Registered Parties", total_p)
        m2.metric("Finalised Orders", finalized_p)
        m3.metric("Follow-ups Pending", followup_p)
        m4.metric("Conversion Ratio", f"{rate:.1f}%")

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Salesman Lead Conversion")
            st.bar_chart(df_cust.groupby(["salesman", "status"]).size().unstack(fill_value=0))
        with c2:
            st.subheader("Most Demanded Tile Areas")
            if not df_items.empty:
                st.bar_chart(df_items["area_name"].value_counts().head(6))

        st.subheader("Recent Selection Log")
        st.dataframe(df_items.sort_values(by="id", ascending=False), use_container_width=True)

# --- PAGE 4: ADMIN ---
# --- PAGE 4: ADMIN & LIVE STOCK ---
elif selected_page == "⚙️ Admin & Live Stock" and st.session_state.role == "admin":
    st.title("⚙️ Administrative Control")
    t1, t2 = st.tabs(["📦 Inventory Stock Data", "📜 System Audits"])
    
    with t1:
        st.subheader("📥 Upload BUSY Accounting Item Master / Stock Sheet")
        st.markdown("Yahan apni Google Sheet ya BUSY se nikli **CSV / Excel** file upload karein:")
        
        uploaded_file = st.file_uploader("Upload CSV / Excel File", type=["csv", "xlsx", "xls"])
        
        if uploaded_file is not None:
            if st.button("🚀 Import & Update All Stock Items", type="primary"):
                try:
                    if uploaded_file.name.endswith(".csv"):
                        raw_df = pd.read_csv(uploaded_file, header=None)
                    else:
                        raw_df = pd.read_excel(uploaded_file, header=None)
                        
                    # Find Header row with 'ITEM NAME'
                    h_idx = 0
                    for i in range(min(15, len(raw_df))):
                        row_vals = [str(x).upper() for x in raw_df.iloc[i].values if pd.notna(x)]
                        if any("ITEM NAME" in s for s in row_vals):
                            h_idx = i
                            break
                            
                    headers = [str(c).strip().upper() if pd.notna(c) else f"COL_{idx}" for idx, c in enumerate(raw_df.iloc[h_idx].values)]
                    df_clean = raw_df.iloc[h_idx + 1:].copy()
                    df_clean.columns = headers
                    
                    # Identify Columns (Item Name, Con Factor, Packing Unit)
                    name_col = next((c for c in df_clean.columns if "ITEM NAME" in c), df_clean.columns[1])
                    cf_col = next((c for c in df_clean.columns if c == "CON FACTOR" or (("CON FACTOR" in c) and ("TYPE" not in c) and ("PACKING" not in c))), None)
                    pack_col = next((c for c in df_clean.columns if "PACKING UNIT" in c or "PACKING" in c), None)
                    
                    # Calculate Sqft_Per_Box = Con Factor * Packing Unit
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
                        st.success(f"🎉 Total **{len(final_items)} Tiles** successfully live database mein load ho gayi!")
                        st.rerun()
                except Exception as ex:
                    st.error(f"Error reading file: {str(ex)}")
                    
        st.markdown("---")
        st.subheader(f"📦 Current Live Stock ({len(stock_df)} Items Loaded)")
        st.dataframe(stock_df, use_container_width=True)
        
    with t2:
        st.subheader("Recent Sign-in Audits")
        conn = get_connection()
        st.dataframe(pd.read_sql_query("SELECT * FROM login_history ORDER BY id DESC LIMIT 50", conn), use_container_width=True)
        conn.close()
