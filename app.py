import json
import os
import math
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

GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1qhlBmCLiDdAKQMxRbYKSrFcEHybFkxfv2XIABLsO6pA/export?format=csv"
CUSTOMERS_FILE = "customers_database.json"

# --- PERSISTENT DATABASE ENGINE ---
def load_json_file(filepath, default_val):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_val
    return default_val

def save_json_file(filepath, data):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def get_all_customers():
    return load_json_file(CUSTOMERS_FILE, [])

def save_customer_record(customer_data):
    custs = get_all_customers()
    found = False
    for i, c in enumerate(custs):
        if str(c.get("id")) == str(customer_data.get("id")) or (c.get("mobile") and c.get("mobile") == customer_data.get("mobile")):
            custs[i] = customer_data
            found = True
            break
    if not found:
        custs.append(customer_data)
    save_json_file(CUSTOMERS_FILE, custs)

# --- DIRECT GOOGLE SHEET STOCK LOADER ---
@st.cache_data(ttl=60)
def get_master_df():
    try:
        raw_df = pd.read_csv(GOOGLE_SHEET_CSV_URL, header=None, dtype=str)
        h_idx = 0
        for i in range(min(15, len(raw_df))):
            row_vals = [str(x).upper() for x in raw_df.iloc[i].values if pd.notna(x)]
            if any("ITEM NAME" in s for s in row_vals):
                h_idx = i
                break
                
        data_rows = raw_df.iloc[h_idx + 1:].copy()
        parsed_stock = []
        for _, r in data_rows.iterrows():
            item_name = str(r[0]).strip() if pd.notna(r[0]) else ""
            if not item_name or item_name.upper() in ["NAN", "ITEM NAME", "TOTAL", "NONE", "NULL", "UNNAMED", ""]:
                continue
            
            # Read Column H (Index 7) -> CON FACTOR
            try:
                cf_raw = str(r[7]).replace(',', '').strip() if len(r) > 7 and pd.notna(r[7]) else "1.0"
                cf = float(pd.to_numeric(cf_raw, errors='coerce')) if cf_raw else 1.0
                if pd.isna(cf) or cf <= 0:
                    cf = 1.0
            except Exception:
                cf = 1.0
                
            # Read Column I (Index 8) -> PACKING UNIT CON FACTOR
            try:
                pu_raw = str(r[8]).replace(',', '').strip() if len(r) > 8 and pd.notna(r[8]) else "1.0"
                pu = float(pd.to_numeric(pu_raw, errors='coerce')) if pu_raw else 1.0
                if pd.isna(pu) or pu <= 0:
                    pu = 1.0
            except Exception:
                pu = 1.0
                
            box_sqft = round(cf * pu, 2)
            parsed_stock.append({
                "item_name": item_name,
                "con_factor": cf,
                "packing_unit": pu,
                "sqft_per_box": box_sqft
            })
            
        df = pd.DataFrame(parsed_stock).drop_duplicates(subset=["item_name"])
        if not df.empty:
            return df
    except Exception as ex:
        st.warning(f"Live Sheet Load Note: {str(ex)}")
        
    return pd.DataFrame([
        {"item_name": "1000 L 12X18 KK", "con_factor": 1.5, "packing_unit": 6.0, "sqft_per_box": 9.0},
        {"item_name": "ALBETA WHITE DAZZEL 2X4 ITALICA", "con_factor": 8.0, "packing_unit": 2.0, "sqft_per_box": 16.0},
        {"item_name": "ATURIO VOLKAS CAR 9MM 4X6 MOT", "con_factor": 23.25, "packing_unit": 2.0, "sqft_per_box": 46.50},
        {"item_name": "AOSTA CARRARA GVT 4X6 15MM VARMORA", "con_factor": 23.25, "packing_unit": 1.0, "sqft_per_box": 23.25}
    ])

def calculate_box_sqft(cf, pu):
    try:
        return round(float(cf) * float(pu), 2)
    except Exception:
        return 16.0

def calculate_boxes(sqft, cf, pu):
    try:
        cov = float(cf) * float(pu)
        if cov <= 0:
            return 0
        return math.ceil(float(sqft) / cov)
    except Exception:
        return 0

# --- PDF GENERATOR ---
def generate_pdf_quotation(customer_info, items_list):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(31, 78, 121)
    pdf.rect(0, 0, 210, 24, 'F')
    
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 8, "JAY GRANITE & TILES", ln=True, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "Tile Selection & Final BOQ Estimate", ln=True, align="C")
    pdf.ln(7)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(100, 6, f"Customer: {customer_info.get('name', 'Walk-in')}", ln=False)
    pdf.cell(0, 6, f"Date: {datetime.now().strftime('%d-%m-%Y')}", ln=True, align="R")
    pdf.cell(100, 6, f"Mobile: {customer_info.get('mobile', '-')}", ln=False)
    pdf.cell(0, 6, f"Staff: {customer_info.get('salesman', 'Admin')}", ln=True, align="R")
    pdf.ln(4)
    
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(22, 7, "Floor", 1, 0, "C", fill=True)
    pdf.cell(32, 7, "Area", 1, 0, "C", fill=True)
    pdf.cell(62, 7, "Tile Item", 1, 0, "L", fill=True)
    pdf.cell(18, 7, "Con Fac", 1, 0, "C", fill=True)
    pdf.cell(16, 7, "Packing", 1, 0, "C", fill=True)
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
if "current_customer" not in st.session_state:
    st.session_state.current_customer = {
        "id": "1",
        "name": "Walk-in Customer",
        "mobile": "-",
        "address": "-",
        "salesman": "DEEPCHAND JAIN",
        "status": "SELECTION ONLY",
        "selections": [],
        "created_at": datetime.now().strftime("%d-%m-%Y %H:%M")
    }

# --- LOGIN SCREEN ---
if not st.session_state.auth:
    st.title("🏛️ Jay Granite & Tiles Portal")
    st.caption("Smart Tile Selection & Quotation Management")
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.subheader("🔐 Staff Sign In")
        with st.form("login_form"):
            role_type = st.radio("Account Role", ["Salesman", "Admin"], horizontal=True)
            u = st.text_input("Username").strip()
            p = st.text_input("Password", type="password").strip()
            submit = st.form_submit_button("🚀 Sign In", type="primary", use_container_width=True)
            
            if submit:
                if (u.upper() in ["DEEPCHAND JAIN", "ADMIN", "GOURAV"] and p in ["deep123", "pass123", "admin123", "GOURAV", "deep1965", "1234"]) or (role_type == "Admin" and p in ["deep123", "admin123", "1234"]):
                    st.session_state.auth = True
                    st.session_state.username = u if u else "DEEPCHAND JAIN"
                    st.session_state.role = "admin"
                    st.rerun()
                elif u and p:
                    st.session_state.auth = True
                    st.session_state.username = u
                    st.session_state.role = "salesman"
                    st.rerun()
                else:
                    st.error("Credentials daalein.")
    st.stop()

# --- SIDEBAR NAVIGATION ---
st.sidebar.title(f"👤 {st.session_state.username.upper()}")
st.sidebar.markdown(f"**Role:** `{st.session_state.role.upper()}`")
if st.sidebar.button("🚪 Sign Out", use_container_width=True):
    st.session_state.auth = False
    st.rerun()

nav_list = [
    "1️⃣ Customer Registration & History",
    "2️⃣ Tile Selection (Showroom)",
    "3️⃣ Sq.Ft Entry & Final Estimate"
]
if st.session_state.role == "admin":
    nav_list.extend(["📊 Executive Dashboard", "⚙️ Stock Master & Settings"])

nav = st.sidebar.radio("Navigation Flow", nav_list)
master_df = get_master_df()

# --- PAGE 1: CUSTOMER REGISTRATION & HISTORY SELECTION ---
if nav == "1️⃣ Customer Registration & History":
    st.title("👥 Customer Management & Selection Resume")
    
    all_clients = get_all_customers()
    tab_new, tab_existing = st.tabs(["➕ Register New Customer", "📂 Open Saved / Existing Customer"])
    
    with tab_new:
        with st.form("new_cust_form"):
            c_name = st.text_input("Customer Name *")
            c_mob = st.text_input("Mobile Number *")
            c_site = st.text_area("Site Address / City")
            c_eng = st.text_input("Contractor / Architect Name (Optional)")
            
            if st.form_submit_button("Save & Start Tile Selection", type="primary"):
                if c_name.strip() and c_mob.strip():
                    new_cust = {
                        "id": str(int(datetime.now().timestamp())),
                        "name": c_name.strip(),
                        "mobile": c_mob.strip(),
                        "address": c_site.strip(),
                        "engineer": c_eng.strip(),
                        "salesman": st.session_state.username,
                        "status": "SELECTION ONLY",
                        "selections": [],
                        "created_at": datetime.now().strftime("%d-%m-%Y %H:%M")
                    }
                    save_customer_record(new_cust)
                    st.session_state.current_customer = new_cust
                    st.success(f"Customer **{c_name}** successfully registered! Sidebar se **'2️⃣ Tile Selection'** par jayein.")
                else:
                    st.error("Customer Name aur Mobile number enter karein.")

    with tab_existing:
        if all_clients:
            st.markdown("#### 🔍 Purane Customer Ko Chunein (Selection Resume Karein):")
            client_options = {
                f"{c['name']} | 📱 {c['mobile']} | 🏷️ {len(c.get('selections', []))} Items ({c.get('status', 'DRAFT')})": c 
                for c in reversed(all_clients)
            }
            selected_label = st.selectbox("Select Customer From List", list(client_options.keys()))
            chosen_cust = client_options[selected_label]
            
            c_info1, c_info2 = st.columns(2)
            with c_info1:
                st.write(f"**Customer:** {chosen_cust['name']}")
                st.write(f"**Mobile:** {chosen_cust['mobile']}")
                st.write(f"**Registered By:** `{chosen_cust.get('salesman', 'Admin')}`")
            with c_info2:
                st.write(f"**Status:** `{chosen_cust.get('status', 'SELECTION ONLY')}`")
                st.write(f"**Previously Selected Items:** **{len(chosen_cust.get('selections', []))} Tiles**")
                
            if st.button("📂 Load Selected Customer Profile", type="primary", use_container_width=True):
                st.session_state.current_customer = chosen_cust
                st.success(f"**{chosen_cust['name']}** ka profile aur chuni hui tiles load ho gayi! Ab aap selection continue kar sakte hain ya measurement daal sakte hain.")
        else:
            st.info("Abhi tak koi saved customer nahi mila.")

# --- PAGE 2: TILE SELECTION (AUTO-SAVE TO CUSTOMER PROFILE) ---
elif nav == "2️⃣ Tile Selection (Showroom)":
    curr_c = st.session_state.current_customer
    st.title("🏷️ Showroom Tile Selection")
    st.info(f"👤 Active Client: **{curr_c['name']}** ({curr_c['mobile']}) | 👔 Staff: **{curr_c.get('salesman', st.session_state.username)}** | 📦 Catalog: **{len(master_df)} Tiles**")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        floor = st.selectbox("Floor Level", ["Ground Floor", "First Floor", "Second Floor", "Third Floor", "Terrace"])
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
    
    st.success(f"📐 **Live Sheet Data:** Con Factor (`{cf}`) × Packing Unit (`{pu}`) = **{box_cov:.2f} Sq.Ft / Box**")
    
    if st.button("➕ Select & Add Tile (Save to Customer)", type="primary", use_container_width=True):
        new_item = {
            "id": int(datetime.now().timestamp() * 1000),
            "floor": floor,
            "surface": surface,
            "area": final_area,
            "tile": chosen_tile,
            "con_factor": cf,
            "packing_unit": pu,
            "sqft": 100.0,
            "boxes": calculate_boxes(100.0, cf, pu)
        }
        
        # Save directly in customer record
        curr_c.setdefault("selections", []).append(new_item)
        curr_c["status"] = "SELECTION ONLY"
        st.session_state.current_customer = curr_c
        save_customer_record(curr_c)
        st.success(f"✅ **{chosen_tile}** add aur save ho gayi!")
        st.rerun()

    st.markdown("---")
    saved_items = curr_c.get("selections", [])
    st.subheader(f"🛒 Currently Selected Tiles ({len(saved_items)})")
    
    if saved_items:
        disp_df = pd.DataFrame(saved_items)[["floor", "surface", "area", "tile", "con_factor", "packing_unit"]]
        st.dataframe(disp_df.rename(columns={"floor": "Floor", "surface": "Type", "area": "Area", "tile": "Tile Item", "con_factor": "Con Factor", "packing_unit": "Packing Unit"}), use_container_width=True)
        st.info("👉 Selection complete hone ke baad sidebar se **'3️⃣ Sq.Ft Entry & Final Estimate'** page par jayein.")
    else:
        st.caption("Is customer ke liye abhi koi tile select nahi hui hai.")

# --- PAGE 3: SQFT ENTRY & FINAL ESTIMATE (UPDATES STATUS TO FINALIZED) ---
elif nav == "3️⃣ Sq.Ft Entry & Final Estimate":
    curr_c = st.session_state.current_customer
    st.title("📐 Direct Sq.Ft & Box Calculation")
    st.info(f"👤 Active Client: **{curr_c['name']}** ({curr_c['mobile']}) | 🏷️ Current Status: `{curr_c.get('status', 'SELECTION ONLY')}`")
    
    saved_items = curr_c.get("selections", [])
    
    if not saved_items:
        st.warning("Cart khali hai. Pehle **'2️⃣ Tile Selection'** page se tiles select karein.")
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
        cf = float(it.get("con_factor", 1.0))
        pu = float(it.get("packing_unit", 1.0))
        cov_per_box = calculate_box_sqft(cf, pu)
        current_sqft = float(it.get("sqft", 100.0))

        c1, c2, c3, c4 = st.columns([5, 2.5, 2.5, 1.5])
        
        with c1:
            st.markdown(f"**{it['area']}** ({it['floor']} - {it['surface']})")
            st.caption(f"🧱 *{it['tile']}*  \n*(1 Box = {cov_per_box:.2f} Sq.Ft | CF: {cf}, Pack: {pu:.0f})*")
            
        with c2:
            new_sqft = st.number_input(
                "Sq.Ft",
                value=current_sqft,
                step=5.0,
                key=f"sqft_in_{it['id']}",
                label_visibility="collapsed"
            )
            
        calc_bx = calculate_boxes(new_sqft, cf, pu)
        
        with c3:
            st.markdown(f"### **{calc_bx}** Boxes")
            
        with c4:
            if st.button("❌ Remove", key=f"btn_del_{it['id']}", type="secondary"):
                curr_c["selections"] = [x for x in curr_c["selections"] if x.get("id") != it.get("id")]
                save_customer_record(curr_c)
                st.session_state.current_customer = curr_c
                st.rerun()

        it_copy = dict(it)
        it_copy["sqft"] = new_sqft
        it_copy["boxes"] = calc_bx
        updated_items.append(it_copy)
        st.divider()

    # Save measurements into customer record
    if updated_items != curr_c.get("selections", []):
        curr_c["selections"] = updated_items
        curr_c["status"] = "FINALIZED"
        curr_c["total_sqft"] = sum(x["sqft"] for x in updated_items)
        curr_c["total_boxes"] = sum(x["boxes"] for x in updated_items)
        save_customer_record(curr_c)
        st.session_state.current_customer = curr_c

    # --- COMPLETE DETAIL BREAKDOWN TABLE ---
    st.markdown("### 📋 Final Bill of Quantities (BOQ)")
    summary_df = pd.DataFrame(curr_c["selections"])[["floor", "surface", "area", "tile", "con_factor", "packing_unit", "sqft", "boxes"]]
    st.dataframe(summary_df.rename(columns={
        "floor": "Floor", "surface": "Type", "area": "Area", "tile": "Tile Item Name",
        "con_factor": "Con Factor", "packing_unit": "Packing Unit",
        "sqft": "Total Sq.Ft", "boxes": "Required Boxes"
    }), use_container_width=True)
    
    tot_sq = sum(float(x.get("sqft", 0.0)) for x in curr_c["selections"])
    tot_bx = sum(float(x.get("boxes", 0.0)) for x in curr_c["selections"])
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Tile Items", len(curr_c["selections"]))
    k2.metric("Total Area", f"{tot_sq:.2f} Sq.Ft")
    k3.metric("Total Required Boxes", f"{tot_bx:.0f} Boxes")
    
    wa_msg = f"🏛️ *JAY GRANITE & TILES - ESTIMATE & BOQ*\n\n"
    wa_msg += f"👤 *Client Name:* {curr_c['name']}\n"
    wa_msg += f"📱 *Mobile:* {curr_c['mobile']}\n"
    wa_msg += f"👔 *Staff:* {curr_c.get('salesman', 'Admin')}\n"
    wa_msg += f"📅 *Date:* {datetime.now().strftime('%d-%m-%Y')}\n"
    wa_msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    for it in curr_c["selections"]:
        wa_msg += f"🔹 *{it['area']}* ({it['floor']})\n"
        wa_msg += f"   • Tile: {it['tile']}\n"
        wa_msg += f"   • Area: {it['sqft']:.2f} Sq.Ft\n"
        wa_msg += f"   • Required: *{it['boxes']:.0f} Boxes*\n\n"
    wa_msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    wa_msg += f"📊 *Grand Total Area:* {tot_sq:.2f} Sq.Ft\n"
    wa_msg += f"📦 *Grand Total Boxes:* {tot_bx:.0f} Boxes\n\n"
    wa_msg += f"Thank you for choosing Jay Granite & Tiles!"

    st.markdown("#### 💬 WhatsApp Direct Share Text")
    st.text_area("WhatsApp Message Text:", value=wa_msg, height=150)
    
    pdf_bytes = generate_pdf_quotation(curr_c, curr_c["selections"])
    
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
        enc_txt = urllib.parse.quote(wa_msg)
        mob_num = "".join(filter(str.isdigit, str(curr_c['mobile'])))
        if len(mob_num) == 10:
            mob_num = "91" + mob_num
        st.link_button("📲 1-Click WhatsApp Send", f"https://wa.me/{mob_num}?text={enc_txt}", use_container_width=True)
    with b3:
        if st.button("🗑️ Reset Cart / Start New Customer", use_container_width=True):
            curr_c["selections"] = []
            save_customer_record(curr_c)
            st.session_state.current_customer = curr_c
            st.rerun()

# --- PAGE 4: EXECUTIVE DASHBOARD (SALESMAN PERFORMANCE & SELECTION VS FINAL) ---
elif nav == "📊 Executive Dashboard" and st.session_state.role == "admin":
    st.title("📊 Executive Business & Salesman Performance Dashboard")
    all_clients = get_all_customers()
    
    if not all_clients:
        st.info("Abhi koi customer data record nahi hua hai.")
        st.stop()
        
    total_customers = len(all_clients)
    draft_count = sum(1 for c in all_clients if c.get("status") == "SELECTION ONLY" and len(c.get("selections", [])) > 0)
    final_count = sum(1 for c in all_clients if c.get("status") == "FINALIZED")
    
    total_sqft_business = sum(sum(float(it.get("sqft", 0)) for it in c.get("selections", [])) for c in all_clients)
    total_boxes_business = sum(sum(float(it.get("boxes", 0)) for it in c.get("selections", [])) for c in all_clients)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("👥 Total Customers", total_customers)
    m2.metric("🟡 Selection Only (Draft)", draft_count)
    m3.metric("🟢 Finalized (BOQ Done)", final_count)
    m4.metric("📦 Total Required Boxes", f"{total_boxes_business:,.0f}")
    
    st.divider()
    d_tab1, d_tab2, d_tab3 = st.tabs(["👔 Salesman Performance Report", "📋 Customer Status Log", "📦 Item-wise Selection Frequency"])
    
    with d_tab1:
        st.subheader("👔 Staff / Salesman Productivity Matrix")
        salesman_records = []
        for c in all_clients:
            s_name = c.get("salesman", "Admin")
            items_count = len(c.get("selections", []))
            sqft = sum(float(it.get("sqft", 0)) for it in c.get("selections", []))
            boxes = sum(float(it.get("boxes", 0)) for it in c.get("selections", []))
            is_final = 1 if c.get("status") == "FINALIZED" else 0
            is_draft = 1 if c.get("status") == "SELECTION ONLY" and items_count > 0 else 0
            
            salesman_records.append({
                "salesman": s_name,
                "clients": 1,
                "draft_selections": is_draft,
                "final_deals": is_final,
                "total_tiles_selected": items_count,
                "total_sqft": sqft,
                "total_boxes": boxes
            })
            
        if salesman_records:
            df_sales = pd.DataFrame(salesman_records)
            summary_salesman = df_sales.groupby("salesman").agg({
                "clients": "count",
                "draft_selections": "sum",
                "final_deals": "sum",
                "total_tiles_selected": "sum",
                "total_sqft": "sum",
                "total_boxes": "sum"
            }).reset_index()
            
            st.dataframe(summary_salesman.rename(columns={
                "salesman": "Salesman Name",
                "clients": "Total Clients",
                "draft_selections": "Selections Pending",
                "final_deals": "Finalized Quotes",
                "total_tiles_selected": "Total Tiles Selected",
                "total_sqft": "Total Sq.Ft",
                "total_boxes": "Total Boxes"
            }), use_container_width=True)
            
    with d_tab2:
        st.subheader("📋 Customer Deal Lifecycle Status")
        cust_list_view = []
        for c in all_clients:
            it_cnt = len(c.get("selections", []))
            sq = sum(float(it.get("sqft", 0)) for it in c.get("selections", []))
            bx = sum(float(it.get("boxes", 0)) for it in c.get("selections", []))
            cust_list_view.append({
                "Customer": c.get("name"),
                "Mobile": c.get("mobile"),
                "Salesman": c.get("salesman", "Admin"),
                "Status": f"🟢 FINALIZED" if c.get("status") == "FINALIZED" else "🟡 SELECTION ONLY",
                "Items Selected": it_cnt,
                "Total Sq.Ft": f"{sq:.2f}",
                "Required Boxes": f"{bx:.0f}",
                "Date": c.get("created_at", "-")
            })
        st.dataframe(pd.DataFrame(cust_list_view), use_container_width=True)

    with d_tab3:
        st.subheader("📦 Most Selected Tiles (Demand Analysis)")
        all_items_flat = []
        for c in all_clients:
            for it in c.get("selections", []):
                all_items_flat.append(it.get("tile"))
        if all_items_flat:
            freq_df = pd.Series(all_items_flat).value_counts().reset_index()
            freq_df.columns = ["Tile Item Name", "Times Selected"]
            st.dataframe(freq_df, use_container_width=True)
        else:
            st.caption("No selections data available.")

# --- PAGE 5: STOCK MASTER ---
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
