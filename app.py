import json
import os
import math
import sqlite3
import urllib.parse
import pandas as pd
import streamlit as st
from fpdf import FPDF
from datetime import datetime

st.set_page_config(
    page_title="Jay Granite & Tiles Hub",
    page_icon="🏛️",
    layout="wide"
)

GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR4mWSP3s6r7UIwn-kcX8Ogev4yXWTMpMLvL87PGTR_UwxKjkcbU9NNxy__mbkyYplhDHxvsD2nKFvW/pub?gid=1816720040&single=true&output=csv"
DB_FILE = "jay_granite_master.db"

# --- SQLITE DATABASE ENGINE ---
def get_db():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_database():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS customers_master (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT,
            address TEXT,
            engineer TEXT,
            salesman TEXT,
            branch TEXT DEFAULT 'Hiriyur',
            status TEXT DEFAULT 'SELECTION ONLY',
            selections_json TEXT DEFAULT '[]',
            total_sqft REAL DEFAULT 0.0,
            total_boxes REAL DEFAULT 0.0,
            created_at TEXT
        )
    """)
    conn.commit()
    try:
        c.execute("ALTER TABLE customers_master ADD COLUMN branch TEXT DEFAULT 'Hiriyur'")
        conn.commit()
    except Exception:
        pass
    conn.close()

init_database()

def get_all_customers_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, mobile, address, engineer, salesman, status, selections_json, total_sqft, total_boxes, created_at, branch FROM customers_master ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    
    clients = []
    for r in rows:
        try:
            sels = json.loads(r[7])
        except Exception:
            sels = []
        clients.append({
            "id": r[0],
            "name": r[1],
            "mobile": r[2],
            "address": r[3],
            "engineer": r[4],
            "salesman": r[5],
            "status": r[6],
            "selections": sels,
            "total_sqft": r[8],
            "total_boxes": r[9],
            "created_at": r[10],
            "branch": r[11] if len(r) > 11 and r[11] else "Hiriyur"
        })
    return clients

def insert_new_customer(name, mobile, address, engineer, salesman, branch):
    conn = get_db()
    c = conn.cursor()
    now_str = datetime.now().strftime("%d-%m-%Y %H:%M")
    c.execute("""
        INSERT INTO customers_master (name, mobile, address, engineer, salesman, branch, status, selections_json, total_sqft, total_boxes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'SELECTION ONLY', '[]', 0.0, 0.0, ?)
    """, (name, mobile, address, engineer, salesman, branch, now_str))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return {
        "id": new_id,
        "name": name,
        "mobile": mobile,
        "address": address,
        "engineer": engineer,
        "salesman": salesman,
        "branch": branch,
        "status": "SELECTION ONLY",
        "selections": [],
        "total_sqft": 0.0,
        "total_boxes": 0.0,
        "created_at": now_str
    }

def update_customer_db(cust_dict):
    conn = get_db()
    c = conn.cursor()
    sels_json = json.dumps(cust_dict.get("selections", []), ensure_ascii=False)
    c.execute("""
        UPDATE customers_master 
        SET name = ?, mobile = ?, address = ?, engineer = ?, salesman = ?, branch = ?, status = ?, selections_json = ?, total_sqft = ?, total_boxes = ?
        WHERE id = ?
    """, (
        cust_dict.get("name"),
        cust_dict.get("mobile"),
        cust_dict.get("address"),
        cust_dict.get("engineer"),
        cust_dict.get("salesman"),
        cust_dict.get("branch", "Hiriyur"),
        cust_dict.get("status", "SELECTION ONLY"),
        sels_json,
        float(cust_dict.get("total_sqft", 0.0)),
        float(cust_dict.get("total_boxes", 0.0)),
        cust_dict.get("id")
    ))
    conn.commit()
    conn.close()

def delete_customer_db(cust_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM customers_master WHERE id = ?", (cust_id,))
    conn.commit()
    conn.close()

# --- DIRECT GOOGLE SHEET STOCK LOADER (HEADER NAME MATCHING) ---
@st.cache_data(ttl=5)
def get_master_df():
    try:
        raw_df = pd.read_csv(GOOGLE_SHEET_CSV_URL, header=None, dtype=str)
        
        # Header row (ITEM NAME, CON FACTOR, PACKING UNIT) dhoondhein
        h_idx = 0
        for i in range(min(15, len(raw_df))):
            row_vals = [str(x).upper() for x in raw_df.iloc[i].values if pd.notna(x)]
            if any("ITEM NAME" in s for s in row_vals):
                h_idx = i
                break
                
        headers = [str(x).strip().upper() for x in raw_df.iloc[h_idx].values]
        data_rows = raw_df.iloc[h_idx + 1:].copy()
        
        # Columns ke exact index pata lagayein
        item_col = 0
        cf_col = None
        pu_col = None
        
        for idx, h in enumerate(headers):
            if "ITEM" in h:
                item_col = idx
            elif "CON FACTOR" in h:
                if cf_col is None:  # Pehla wala Con Factor (Column H)
                    cf_col = idx
            elif "PACKING" in h:
                pu_col = idx

        parsed_stock = []
        for _, r in data_rows.iterrows():
            item_name = str(r.iloc[item_col]).strip() if len(r) > item_col and pd.notna(r.iloc[item_col]) else ""
            if not item_name or item_name.upper() in ["NAN", "ITEM NAME", "TOTAL", "NONE", "NULL", "UNNAMED", ""]:
                continue
            
            # Con Factor (Column H)
            cf_val = 1.0
            if cf_col is not None and len(r) > cf_col and pd.notna(r.iloc[cf_col]):
                try:
                    cf_val = float(str(r.iloc[cf_col]).replace(',', '').strip())
                except Exception:
                    cf_val = 1.0
            if cf_val <= 0: cf_val = 1.0

            # Packing Unit (Column I)
            pu_val = 1.0
            if pu_col is not None and len(r) > pu_col and pd.notna(r.iloc[pu_col]):
                try:
                    pu_val = float(str(r.iloc[pu_col]).replace(',', '').strip())
                except Exception:
                    pu_val = 1.0
            if pu_val <= 0: pu_val = 1.0
                
            box_cov = round(cf_val * pu_val, 2)
            parsed_stock.append({
                "item_name": item_name,
                "con_factor": cf_val,
                "packing_unit": pu_val,
                "sqft_per_box": box_cov if box_cov > 0 else 1.0
            })
            
        df = pd.DataFrame(parsed_stock).drop_duplicates(subset=["item_name"])
        if not df.empty:
            return df
    except Exception as ex:
        st.error(f"Google Sheet Sync Error: {str(ex)}")
    return pd.DataFrame()
# --- PDF GENERATOR ---
def generate_pdf_quotation(customer_info, items_list):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(31, 78, 121)
    pdf.rect(0, 0, 210, 24, 'F')
    
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 15)
    branch_name = customer_info.get('branch', 'HIRIYUR').upper()
    pdf.cell(0, 8, f"JAY GRANITE & TILES - {branch_name} SHOWROOM", ln=True, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "Tile Selection & Final BOQ Estimate", ln=True, align="C")
    pdf.ln(7)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(100, 6, f"Customer: {customer_info.get('name', 'Walk-in')}", ln=False)
    pdf.cell(0, 6, f"Date: {datetime.now().strftime('%d-%m-%Y')}", ln=True, align="R")
    pdf.cell(100, 6, f"Mobile: {customer_info.get('mobile', '-')}", ln=False)
    pdf.cell(0, 6, f"Staff: {customer_info.get('salesman', 'Admin')} ({customer_info.get('branch', 'Hiriyur')})", ln=True, align="R")
    pdf.ln(4)
    
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(22, 7, "Floor", 1, 0, "C", fill=True)
    pdf.cell(32, 7, "Area", 1, 0, "C", fill=True)
    pdf.cell(62, 7, "Tile Item", 1, 0, "L", fill=True)
    pdf.cell(18, 7, "Con Fac (H)", 1, 0, "C", fill=True)
    pdf.cell(16, 7, "Pack (I)", 1, 0, "C", fill=True)
    pdf.cell(20, 7, "Total Sq.Ft", 1, 0, "R", fill=True)
    pdf.cell(20, 7, "Req. Boxes", 1, 1, "R", fill=True)
    
    pdf.set_font("Helvetica", "", 8)
    tot_sqft = 0.0
    tot_boxes = 0.0
    for it in items_list:
        sq = float(it.get("sqft", 0.0))
        bx = float(it.get("boxes", 0.0))
        tot_sqft += sq
        tot_boxes += bx
        
        pdf.cell(22, 6, str(it.get("floor", "-"))[:12], 1, 0, "C")
        pdf.cell(32, 6, str(it.get("area", "-"))[:18], 1, 0, "L")
        pdf.cell(62, 6, str(it.get("tile", "-"))[:34], 1, 0, "L")
        pdf.cell(18, 6, f"{float(it.get('con_factor', 1.0)):.2f}", 1, 0, "C")
        pdf.cell(16, 6, f"{float(it.get('packing_unit', 1.0)):.0f}", 1, 0, "C")
        pdf.cell(20, 6, f"{sq:.2f}", 1, 0, "R")
        pdf.cell(20, 6, f"{bx:.0f}", 1, 1, "R")
        
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(150, 7, "Grand Total", 1, 0, "R", fill=True)
    pdf.cell(20, 7, f"{tot_sqft:.2f}", 1, 0, "R", fill=True)
    pdf.cell(20, 7, f"{tot_boxes:.0f}", 1, 1, "R", fill=True)
    
    return bytes(pdf.output())

# --- SESSION INITIALIZATION ---
if "auth" not in st.session_state:
    st.session_state.auth = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = "salesman"
if "branch" not in st.session_state:
    st.session_state.branch = "Hiriyur"
if "current_customer" not in st.session_state:
    st.session_state.current_customer = None

# --- LOGIN SCREEN ---
if not st.session_state.auth:
    st.title("🏛️ Jay Granite & Tiles Portal")
    st.caption("Enterprise Tile Selection & Quotation Engine")
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.subheader("🔐 Staff Sign In")
        with st.form("login_form"):
            role_type = st.radio("Account Role", ["Salesman", "Admin"], horizontal=True)
            if role_type == "Salesman":
                branch_choice = st.selectbox("Select Branch / Showroom", ["Hiriyur", "Davangere"])
            else:
                branch_choice = st.selectbox("Select View / Showroom", ["All Showrooms", "Hiriyur", "Davangere"])
                
            u = st.text_input("Username").strip()
            p = st.text_input("Password", type="password").strip()
            submit = st.form_submit_button("🚀 Sign In", type="primary", use_container_width=True)
            
            if submit:
                if (u.upper() in ["DEEPCHAND JAIN", "ADMIN", "GOURAV"] and p in ["deep123", "pass123", "admin123", "GOURAV", "deep1965", "1234"]) or (role_type == "Admin" and p in ["deep123", "admin123", "1234"]):
                    st.session_state.auth = True
                    st.session_state.username = u if u else "DEEPCHAND JAIN"
                    st.session_state.role = "admin"
                    st.session_state.branch = branch_choice
                    st.rerun()
                elif u and p:
                    st.session_state.auth = True
                    st.session_state.username = u
                    st.session_state.role = "salesman"
                    st.session_state.branch = branch_choice
                    st.rerun()
                else:
                    st.error("Credentials enter karein.")
    st.stop()

# --- SIDEBAR NAVIGATION ---
st.sidebar.title(f"👤 {st.session_state.username.upper()}")
st.sidebar.markdown(f"**Role:** `{st.session_state.role.upper()}`")

if st.session_state.role == "admin":
    st.session_state.branch = st.sidebar.selectbox(
        "🏢 Active Showroom View",
        ["All Showrooms", "Hiriyur", "Davangere"],
        index=["All Showrooms", "Hiriyur", "Davangere"].index(st.session_state.branch)
    )
else:
    st.sidebar.markdown(f"**🏢 Showroom:** `{st.session_state.branch}`")

if st.sidebar.button("🚪 Sign Out", use_container_width=True):
    st.session_state.auth = False
    st.session_state.current_customer = None
    st.rerun()

nav_list = [
    "1️⃣ Customer Registration & History",
    "2️⃣ Tile Selection (Showroom)",
    "3️⃣ Sq.Ft Entry & Final Estimate",
    "📈 Salesman Progress Report"
]
if st.session_state.role == "admin":
    nav_list.extend(["📊 Executive Dashboard", "⚙️ Stock Master & Settings"])

nav = st.sidebar.radio("Navigation Flow", nav_list)
master_df = get_master_df()

# --- PAGE 1: CUSTOMER REGISTRATION & HISTORY ---
if nav == "1️⃣ Customer Registration & History":
    st.title("👥 Customer Registration & Selection History")
    all_clients = get_all_customers_db()
    if st.session_state.role == "salesman":
        filtered_clients = [c for c in all_clients if c.get("branch") == st.session_state.branch]
    elif st.session_state.branch != "All Showrooms":
        filtered_clients = [c for c in all_clients if c.get("branch") == st.session_state.branch]
    else:
        filtered_clients = all_clients

    tab_new, tab_existing = st.tabs(["➕ Register New Customer", f"📂 Active / Draft Customers ({len(filtered_clients)} in {st.session_state.branch})"])
    
    with tab_new:
        with st.form("new_cust_form"):
            c_name = st.text_input("Customer Name *")
            c_mob = st.text_input("Mobile Number *")
            c_site = st.text_area("Site Address / City")
            c_eng = st.text_input("Contractor / Architect Name (Optional)")
            assigned_branch = st.session_state.branch if st.session_state.branch != "All Showrooms" else "Hiriyur"
            st.info(f"Showroom Branch: **{assigned_branch}**")
            
            if st.form_submit_button("💾 Save Customer & Start Selection", type="primary"):
                if c_name.strip() and c_mob.strip():
                    new_cust = insert_new_customer(c_name.strip(), c_mob.strip(), c_site.strip(), c_eng.strip(), st.session_state.username, assigned_branch)
                    st.session_state.current_customer = new_cust
                    st.success(f"🎉 Customer **{c_name}** (#ID: {new_cust['id']}) register ho gaya! Sidebar se **'2️⃣ Tile Selection'** par jayein.")
                else:
                    st.error("Customer Name aur Mobile zaroori hai.")

    with tab_existing:
        if filtered_clients:
            st.markdown(f"#### 🔍 Customer List:")
            client_options = {
                f"#{c['id']} | {c['name']} | 📱 {c['mobile']} | 🏢 {c.get('branch', 'Hiriyur')} | 🏷️ {len(c.get('selections', []))} Items [{c.get('status', 'SELECTION ONLY')}]": c 
                for c in filtered_clients
            }
            selected_label = st.selectbox("Customer Chuniye", list(client_options.keys()))
            chosen_cust = client_options[selected_label]
            
            c_info1, c_info2 = st.columns(2)
            with c_info1:
                st.write(f"**Customer ID:** `#{chosen_cust['id']}`")
                st.write(f"**Name:** {chosen_cust['name']}")
                st.write(f"**Mobile:** {chosen_cust['mobile']}")
                st.write(f"**Showroom:** `{chosen_cust.get('branch', 'Hiriyur')}`")
                st.write(f"**Registered By:** `{chosen_cust.get('salesman', 'Admin')}`")
            with c_info2:
                st.write(f"**Status:** `{chosen_cust.get('status', 'SELECTION ONLY')}`")
                st.write(f"**Selected Tiles:** **{len(chosen_cust.get('selections', []))} Items**")
                st.write(f"**Date:** {chosen_cust.get('created_at', '-')}")
                
            b_load, b_del = st.columns([2, 1])
            with b_load:
                if st.button("📂 Load Selected Customer Profile", type="primary", use_container_width=True):
                    st.session_state.current_customer = chosen_cust
                    st.success(f"**{chosen_cust['name']}** load ho gaya!")
            with b_del:
                if st.button("🗑️ Delete Customer", type="secondary", use_container_width=True):
                    delete_customer_db(chosen_cust['id'])
                    if st.session_state.get("current_customer") and st.session_state.current_customer.get("id") == chosen_cust['id']:
                        st.session_state.current_customer = None
                    st.success(f"Customer delete kar diya gaya hai!")
                    st.rerun()
        else:
            st.info("Abhi koi saved customer nahi hai.")

# --- PAGE 2: TILE SELECTION ---
elif nav == "2️⃣ Tile Selection (Showroom)":
    if not st.session_state.current_customer:
        st.warning("Pehle Customer Registration page se koi customer select ya create karein.")
        st.stop()
        
    curr_c = st.session_state.current_customer
    st.title("🏷️ Showroom Tile Selection")
    st.info(f"👤 Active Client: **{curr_c['name']}** (#{curr_c['id']} - {curr_c['mobile']}) | 🏢 Branch: **{curr_c.get('branch', 'Hiriyur')}** | 👔 Staff: **{curr_c.get('salesman', st.session_state.username)}** | 📦 Catalog: **{len(master_df)} Tiles**")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        floor_options = ["Ground Floor", "First Floor", "Second Floor", "Third Floor", "Terrace", "✏️ Custom Floor"]
        sel_floor = st.selectbox("Floor Level", floor_options)
        final_floor = st.text_input("Custom Floor Name", "Basement / Mezzanine") if sel_floor == "✏️ Custom Floor" else sel_floor
    with col2:
        surface = st.radio("Surface Type", ["Floor", "Wall"], horizontal=True)
    with col3:
        area_options = [
            "Living Room / Hall", "Master Bedroom", "Bedroom 2", "Bedroom 3",
            "Kitchen", "Kitchen Dado / Wall", "Dining Area", "Pooja Room",
            "Master Bathroom", "Common Bathroom", "Balcony", "Parking / Porch", "✏️ Custom Area"
        ]
        sel_area = st.selectbox("Designated Area", area_options)
        final_area = st.text_input("Custom Area Name", "Store Room") if sel_area == "✏️ Custom Area" else sel_area
        
    search = st.text_input("🔍 Quick Search (Tile Code / Size / Name)", "")
    filtered_df = master_df[master_df["item_name"].str.contains(search, case=False, na=False)] if search else master_df
    
    if filtered_df.empty:
        filtered_df = master_df
        
    chosen_tile = st.selectbox("Select Tile Item", filtered_df["item_name"].tolist())
    
    matched_row = filtered_df[filtered_df["item_name"] == chosen_tile].iloc[0]
    cf = float(matched_row.get("con_factor", 1.0))
    pu = float(matched_row.get("packing_unit", 1.0))
    box_cov = calculate_box_sqft(cf, pu)
    
    st.success(f"📐 **Sheet Specs (Col H & I):** Con Factor (`{cf}`) × Packing (`{pu}`) = **{box_cov:.2f} Sq.Ft / Box**")
    
    if st.button("➕ Select & Add Tile (Save to Database)", type="primary", use_container_width=True):
        new_item = {
            "id": int(datetime.now().timestamp() * 1000),
            "floor": final_floor,
            "surface": surface,
            "area": final_area,
            "tile": chosen_tile,
            "con_factor": cf,
            "packing_unit": pu,
            "sqft": 100.0,
            "boxes": calculate_boxes(100.0, cf, pu)
        }
        
        curr_c.setdefault("selections", []).append(new_item)
        curr_c["status"] = "SELECTION ONLY"
        update_customer_db(curr_c)
        st.session_state.current_customer = curr_c
        st.success(f"✅ **{chosen_tile}** permanently save ho gayi!")
        st.rerun()

    st.markdown("---")
    saved_items = curr_c.get("selections", [])
    st.subheader(f"🛒 Currently Selected Tiles ({len(saved_items)})")
    
    if saved_items:
        disp_df = pd.DataFrame(saved_items)[["floor", "surface", "area", "tile", "con_factor", "packing_unit"]]
        st.dataframe(disp_df.rename(columns={"floor": "Floor", "surface": "Type", "area": "Area", "tile": "Tile Item", "con_factor": "Con Factor (Col H)", "packing_unit": "Packing (Col I)"}), use_container_width=True)
        st.info("👉 Selection ke baad sidebar se **'3️⃣ Sq.Ft Entry & Final Estimate'** page par jayein.")
    else:
        st.caption("Abhi koi tile select nahi hui hai.")

# --- PAGE 3: SQFT ENTRY & FINAL ESTIMATE ---
elif nav == "3️⃣ Sq.Ft Entry & Final Estimate":
    if not st.session_state.current_customer:
        st.warning("Pehle Customer Registration page se koi customer select karein.")
        st.stop()
        
    curr_c = st.session_state.current_customer
    st.title("📐 Direct Sq.Ft & Box Calculation")
    st.info(f"👤 Active Client: **{curr_c['name']}** (#{curr_c['id']} - {curr_c['mobile']}) | 🏢 Branch: `{curr_c.get('branch', 'Hiriyur')}` | 🏷️ Status: `{curr_c.get('status', 'SELECTION ONLY')}`")
    
    saved_items = curr_c.get("selections", [])
    if not saved_items:
        st.warning("Is customer ke paas abhi koi tile item nahi hai.")
        st.stop()
        
    st.markdown("### ✏️ Enter Required Sq.Ft for Each Tile:")
    
    h_col1, h_col2, h_col3, h_col4 = st.columns([5, 2.5, 2.5, 1.5])
    h_col1.markdown("**Tile Item & Location**")
    h_col2.markdown("**Total Sq.Ft**")
    h_col3.markdown("**Required Boxes**")
    h_col4.markdown("**Action**")
    st.divider()

    updated_items = []
    for it in saved_items:
        tile_name = it.get("tile")
        matched_tile = master_df[master_df["item_name"] == tile_name]
        if not matched_tile.empty:
            cf = float(matched_tile.iloc[0]["con_factor"])
            pu = float(matched_tile.iloc[0]["packing_unit"])
        else:
            cf = float(it.get("con_factor", 1.0))
            pu = float(it.get("packing_unit", 1.0))

        cov_per_box = round(cf * pu, 2)
        if cov_per_box <= 0:
            cov_per_box = 1.0

        current_sqft = float(it.get("sqft", 100.0))

        c1, c2, c3, c4 = st.columns([5, 2.5, 2.5, 1.5])
        with c1:
            st.markdown(f"**{it['area']}** ({it['floor']} - {it['surface']})")
            st.caption(f"🧱 *{tile_name}* \n*(1 Box = {cov_per_box:.2f} Sq.Ft | Col H (CF): {cf} × Col I (Pack): {pu})*")
            
        with c2:
            new_sqft = st.number_input(
                "Sq.Ft",
                value=current_sqft,
                step=5.0,
                key=f"sqft_in_{it['id']}",
                label_visibility="collapsed"
            )
            
        # Calculation: Sq.Ft / (Con Factor * Packing Unit) -> Rounded up in Bold
        calc_bx = math.ceil(new_sqft / cov_per_box)
        
        with c3:
            st.markdown(f"### **{calc_bx} Boxes**")
            
        with c4:
            if st.button("❌ Remove", key=f"btn_del_{it['id']}", type="secondary"):
                curr_c["selections"] = [x for x in curr_c["selections"] if x.get("id") != it.get("id")]
                update_customer_db(curr_c)
                st.session_state.current_customer = curr_c
                st.rerun()

        it_copy = dict(it)
        it_copy["con_factor"] = cf
        it_copy["packing_unit"] = pu
        it_copy["sqft"] = new_sqft
        it_copy["boxes"] = calc_bx
        updated_items.append(it_copy)
        st.divider()

    if updated_items != curr_c.get("selections", []):
        curr_c["selections"] = updated_items
        curr_c["total_sqft"] = sum(x["sqft"] for x in updated_items)
        curr_c["total_boxes"] = sum(x["boxes"] for x in updated_items)
        update_customer_db(curr_c)
        st.session_state.current_customer = curr_c

    st.markdown("### 📋 Final Bill of Quantities (BOQ)")
    summary_df = pd.DataFrame(curr_c["selections"])[["floor", "surface", "area", "tile", "con_factor", "packing_unit", "sqft", "boxes"]]
    st.dataframe(summary_df.rename(columns={
        "floor": "Floor", "surface": "Type", "area": "Area", "tile": "Tile Item Name",
        "con_factor": "Con Factor (H)", "packing_unit": "Packing (I)",
        "sqft": "Total Sq.Ft", "boxes": "Required Boxes"
    }), use_container_width=True)
    
    tot_sq = sum(float(x.get("sqft", 0.0)) for x in curr_c["selections"])
    tot_bx = sum(float(x.get("boxes", 0.0)) for x in curr_c["selections"])
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Tile Items", len(curr_c["selections"]))
    k2.metric("Total Area", f"{tot_sq:.2f} Sq.Ft")
    k3.metric("Total Required Boxes", f"{tot_bx:.0f} Boxes")
    
    wa_msg = f"🏛️ *JAY GRANITE & TILES - {curr_c.get('branch', 'HIRIYUR').upper()} SHOWROOM*\n"
    wa_msg += f"ESTIMATE & BOQ QUOTATION\n\n"
    wa_msg += f"👤 *Client Name:* {curr_c['name']}\n"
    wa_msg += f"📱 *Mobile:* {curr_c['mobile']}\n"
    wa_msg += f"👔 *Staff:* {curr_c.get('salesman', 'Admin')} ({curr_c.get('branch', 'Hiriyur')})\n"
    wa_msg += f"📅 *Date:* {datetime.now().strftime('%d-%m-%Y')}\n"
    wa_msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    for it in curr_c["selections"]:
        wa_msg += f"🔹 *{it['area']}* ({it['floor']} - {it['surface']})\n"
        wa_msg += f"   • Tile: {it['tile']}\n"
        wa_msg += f"   • Area: {it['sqft']:.2f} Sq.Ft\n"
        wa_msg += f"   • Required: *{it['boxes']:.0f} Boxes*\n\n"
    wa_msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    wa_msg += f"📊 *Grand Total Area:* {tot_sq:.2f} Sq.Ft\n"
    wa_msg += f"📦 *Grand Total Boxes:* {tot_bx:.0f} Boxes\n\n"
    wa_msg += f"Thank you for choosing Jay Granite & Tiles!"

    with st.expander("👁️ View / Copy WhatsApp Message Text"):
        st.text_area("Message Preview:", value=wa_msg, height=180)

    pdf_bytes = generate_pdf_quotation(curr_c, curr_c["selections"])
    enc_txt = urllib.parse.quote(wa_msg)
    mob_num = "".join(filter(str.isdigit, str(curr_c['mobile'])))
    if len(mob_num) == 10:
        mob_num = "91" + mob_num

    st.markdown("---")
    b1, b2, b3 = st.columns(3)
    with b1:
        st.download_button(
            "📄 Download Estimate PDF",
            data=pdf_bytes,
            file_name=f"Estimate_{curr_c['name']}_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    with b2:
        st.link_button("📲 1-Click WhatsApp Send", f"https://wa.me/{mob_num}?text={enc_txt}", use_container_width=True)
    with b3:
        if st.button("✅ Finalize Deal & Archive Customer", type="primary", use_container_width=True):
            curr_c["status"] = "FINALIZED"
            curr_c["total_sqft"] = tot_sq
            curr_c["total_boxes"] = tot_bx
            update_customer_db(curr_c)
            st.session_state.current_customer = None
            st.success(f"🎉 **{curr_c['name']}** finalize ho gaya!")
            st.rerun()

# --- PAGE 4: SALESMAN PROGRESS REPORT ---
elif nav == "📈 Salesman Progress Report":
    st.title("📈 Salesman Progress & Performance Tracking")
    all_clients = get_all_customers_db()
    curr_user = st.session_state.username
    curr_role = st.session_state.role
    curr_branch = st.session_state.branch

    if curr_role == "salesman":
        my_clients = [c for c in all_clients if c.get("salesman", "").lower() == curr_user.lower()]
        st.info(f"👤 Salesman: **{curr_user}** | 🏢 Showroom: **{curr_branch}**")
        my_total_quotes = len(my_clients)
        my_finalized = sum(1 for c in my_clients if c.get("status") == "FINALIZED")
        my_total_boxes = sum(float(c.get("total_boxes", 0.0)) for c in my_clients)
        target_boxes = 1500.0
        progress_pct = min(100, int((my_total_boxes / target_boxes) * 100))

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("My Total Clients", my_total_quotes)
        s2.metric("Final Deals Closed", my_finalized)
        s3.metric("Total Boxes Estimated", f"{my_total_boxes:,.0f}")
        s4.metric("Monthly Target", f"{progress_pct}%")

        st.write("🎯 **Monthly Target Progress:**")
        st.progress(progress_pct / 100)
    else:
        st.subheader(f"📊 All Staff Performance ({curr_branch})")
        df_clients = pd.DataFrame(all_clients)
        if not df_clients.empty:
            if curr_branch != "All Showrooms":
                df_clients = df_clients[df_clients["branch"] == curr_branch]
            if not df_clients.empty:
                summary = df_clients.groupby(["salesman", "branch"]).agg(
                    Total_Clients=("id", "count"),
                    Total_Boxes=("total_boxes", "sum"),
                    Total_SqFt=("total_sqft", "sum")
                ).reset_index()
                st.dataframe(summary, use_container_width=True)

# --- PAGE 5: EXECUTIVE DASHBOARD ---
elif nav == "📊 Executive Dashboard" and st.session_state.role == "admin":
    st.title("📊 Executive Business & Showroom Comparison Dashboard")
    all_clients = get_all_customers_db()
    if not all_clients:
        st.info("Abhi koi customer data record nahi hua hai.")
        st.stop()

    curr_branch = st.session_state.branch
    view_clients = all_clients if curr_branch == "All Showrooms" else [c for c in all_clients if c.get("branch") == curr_branch]
    total_customers = len(view_clients)
    draft_count = sum(1 for c in view_clients if c.get("status") == "SELECTION ONLY" and len(c.get("selections", [])) > 0)
    final_count = sum(1 for c in view_clients if c.get("status") == "FINALIZED")
    total_boxes_business = sum(float(c.get("total_boxes", 0)) for c in view_clients)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("👥 Total Customers", total_customers)
    m2.metric("🟡 Selection Only (Draft)", draft_count)
    m3.metric("🟢 Finalized (BOQ Done)", final_count)
    m4.metric("📦 Total Required Boxes", f"{total_boxes_business:,.0f}")
    
    st.divider()
    d_tab1, d_tab2, d_tab3 = st.tabs(["🏢 Showroom vs Showroom Comparison", "📋 Customer Status Log", "📦 Item-wise Selection Frequency"])
    with d_tab1:
        df_all = pd.DataFrame(all_clients)
        if "branch" in df_all.columns:
            branch_summary = df_all.groupby("branch").agg(
                Total_Customers=("id", "count"),
                Total_SqFt=("total_sqft", "sum"),
                Total_Boxes=("total_boxes", "sum")
            ).reset_index()
            st.dataframe(branch_summary, use_container_width=True)
    with d_tab2:
        cust_list_view = []
        for c in view_clients:
            cust_list_view.append({
                "ID": f"#{c.get('id')}",
                "Customer": c.get("name"),
                "Mobile": c.get("mobile"),
                "Branch": c.get("branch", "Hiriyur"),
                "Status": c.get("status", "SELECTION ONLY")
            })
        st.dataframe(pd.DataFrame(cust_list_view), use_container_width=True)
    with d_tab3:
        all_items_flat = [it.get("tile") for c in view_clients for it in c.get("selections", [])]
        if all_items_flat:
            freq_df = pd.Series(all_items_flat).value_counts().reset_index()
            freq_df.columns = ["Tile Item Name", "Times Selected"]
            st.dataframe(freq_df, use_container_width=True)

# --- PAGE 6: STOCK MASTER ---
elif nav == "⚙️ Stock Master & Settings" and st.session_state.role == "admin":
    st.title("⚙️ Live Stock Master (Google Sheet Linked)")
    st.info(f"Loaded **{len(master_df)} Tiles** directly from Google Sheet.")
    if st.button("🔄 Refresh Sheet Cache"):
        st.cache_data.clear()
        st.rerun()
    st.dataframe(master_df.rename(columns={
        "item_name": "Tile Item Name",
        "con_factor": "Con Factor (Col H)",
        "packing_unit": "Packing Unit (Col I)",
        "sqft_per_box": "Coverage SqFt/Box"
    }), use_container_width=True)
