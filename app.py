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
SELECTIONS_FILE = "customer_selections.json"
CUSTOMERS_FILE = "customers_list.json"

# --- PERSISTENT DATA HANDLERS ---
def load_json_file(filepath, default_val):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return [x for x in data if isinstance(x, dict) and x.get("tile")]
                return data
        except Exception:
            return default_val
    return default_val

def save_json_file(filepath, data):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

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
            
            # Column H (Index 7) -> CON FACTOR
            try:
                cf_raw = str(r[7]).replace(',', '').strip() if len(r) > 7 and pd.notna(r[7]) else "1.0"
                cf = float(pd.to_numeric(cf_raw, errors='coerce')) if cf_raw else 1.0
                if pd.isna(cf) or cf <= 0:
                    cf = 1.0
            except Exception:
                cf = 1.0
                
            # Column I (Index 8) -> PACKING UNIT CON FACTOR
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
        st.warning(f"Live Sheet Sync Note: {str(ex)}")
        
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
    pdf.cell(0, 5, "Tile Estimate & Required Boxes", ln=True, align="C")
    pdf.ln(7)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(100, 6, f"Customer: {customer_info.get('name', 'Walk-in')}", ln=False)
    pdf.cell(0, 6, f"Date: {datetime.now().strftime('%d-%m-%Y')}", ln=True, align="R")
    pdf.cell(100, 6, f"Mobile: {customer_info.get('mobile', '-')}", ln=True)
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
    st.session_state.current_customer = {"id": 1, "name": "Walk-in Customer", "mobile": "-"}
if "active_cart" not in st.session_state:
    st.session_state.active_cart = load_json_file(SELECTIONS_FILE, [])

# --- LOGIN SCREEN ---
if not st.session_state.auth:
    st.title("🏛️ Jay Granite & Tiles Portal")
    st.caption("Smart Tile Selection & Direct Estimation Engine")
    
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
                    st.error("Please enter credentials.")
    st.stop()

# --- SIDEBAR NAVIGATION ---
st.sidebar.title(f"👤 {st.session_state.username.upper()}")
st.sidebar.markdown(f"**Role:** `{st.session_state.role.upper()}`")
if st.sidebar.button("🚪 Sign Out", use_container_width=True):
    st.session_state.auth = False
    st.rerun()

nav_list = [
    "1️⃣ Customer Registration",
    "2️⃣ Tile Selection (Showroom)",
    "3️⃣ Sq.Ft Entry & Final Estimate"
]
if st.session_state.role == "admin":
    nav_list.extend(["📊 Executive Dashboard", "⚙️ Stock Master & Settings"])

nav = st.sidebar.radio("Navigation Flow", nav_list)
master_df = get_master_df()

# --- PAGE 1: CUSTOMER REGISTRATION ---
if nav == "1️⃣ Customer Registration":
    st.title("📝 Customer Registration")
    with st.form("reg_cust_form"):
        cust_name = st.text_input("Customer Name *", value=st.session_state.current_customer.get("name", "") if st.session_state.current_customer.get("name") != "Walk-in Customer" else "")
        cust_mob = st.text_input("Mobile Number *", value=st.session_state.current_customer.get("mobile", "") if st.session_state.current_customer.get("mobile") != "-" else "")
        cust_site = st.text_area("Site Address")
        
        if st.form_submit_button("Proceed to Tile Selection", type="primary"):
            if cust_name.strip() and cust_mob.strip():
                st.session_state.current_customer = {
                    "id": len(load_json_file(CUSTOMERS_FILE, [])) + 1,
                    "name": cust_name.strip(),
                    "mobile": cust_mob.strip(),
                    "address": cust_site.strip(),
                    "salesman": st.session_state.username
                }
                c_list = load_json_file(CUSTOMERS_FILE, [])
                c_list.append(st.session_state.current_customer)
                save_json_file(CUSTOMERS_FILE, c_list)
                st.success(f"Customer **{cust_name}** saved!")
            else:
                st.error("Customer Name aur Mobile zaroori hai.")

# --- PAGE 2: TILE SELECTION ---
elif nav == "2️⃣ Tile Selection (Showroom)":
    st.title("🏷️ Showroom Tile Selection")
    st.info(f"Client: **{st.session_state.current_customer['name']}** ({st.session_state.current_customer['mobile']}) | Catalog: **{len(master_df)} Tiles Available**")
    
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
        
    search = st.text_input("🔍 Quick Search (Name / Size / Brand)", "")
    filtered_df = master_df[master_df["item_name"].str.contains(search, case=False, na=False)] if search else master_df
    
    if filtered_df.empty:
        filtered_df = master_df
        
    chosen_tile = st.selectbox("Select Tile Item", filtered_df["item_name"].tolist())
    
    matched_row = filtered_df[filtered_df["item_name"] == chosen_tile].iloc[0]
    cf = float(matched_row.get("con_factor", 1.0))
    pu = float(matched_row.get("packing_unit", 1.0))
    box_cov = calculate_box_sqft(cf, pu)
    
    st.success(f"📐 **Live Sheet Data:** Con Factor (`{cf}`) × Packing Unit (`{pu}`) = **{box_cov:.2f} Sq.Ft / Box**")
    
    if st.button("➕ Add Tile to Cart", type="primary", use_container_width=True):
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
        current_valid_cart = [x for x in st.session_state.active_cart if isinstance(x, dict) and x.get("tile")]
        current_valid_cart.append(new_item)
        st.session_state.active_cart = current_valid_cart
        save_json_file(SELECTIONS_FILE, st.session_state.active_cart)
        st.success(f"✅ **{chosen_tile}** add ho gayi!")
        st.rerun()

    st.markdown("---")
    valid_items = [x for x in st.session_state.active_cart if isinstance(x, dict) and x.get("tile")]
    st.subheader(f"🛒 Current Selected Items ({len(valid_items)})")
    
    if valid_items:
        disp_df = pd.DataFrame(valid_items)[["floor", "area", "tile", "con_factor", "packing_unit"]]
        st.dataframe(disp_df.rename(columns={"floor": "Floor", "area": "Area", "tile": "Tile Item", "con_factor": "Con Factor", "packing_unit": "Packing Unit"}), use_container_width=True)
        st.info("👉 Tiles add karne ke baad sidebar se **'3️⃣ Sq.Ft Entry & Final Estimate'** page par jayein.")
    else:
        st.caption("Cart abhi khali hai.")

# --- PAGE 3: NEW CLEAN FORMAT (ITEM -> SQFT -> REQUIRED BOXES) ---
elif nav == "3️⃣ Sq.Ft Entry & Final Estimate":
    st.title("📐 Direct Sq.Ft & Box Calculation")
    st.info(f"Client: **{st.session_state.current_customer['name']}** ({st.session_state.current_customer['mobile']})")
    
    valid_items = [x for x in st.session_state.active_cart if isinstance(x, dict) and x.get("tile")]
    
    if not valid_items:
        st.warning("Cart khali hai. Pehle **'2️⃣ Tile Selection'** page se tiles select karein.")
        st.stop()
        
    st.markdown("### ✏️ Enter Required Sq.Ft for Each Tile:")
    
    # Clean Header Row
    h_col1, h_col2, h_col3, h_col4 = st.columns([5, 2.5, 2.5, 1.5])
    h_col1.markdown("**Tile Item & Location**")
    h_col2.markdown("**Total Sq.Ft**")
    h_col3.markdown("**Required Boxes**")
    h_col4.markdown("**Action**")
    st.divider()

    updated_items = []
    for it in valid_items:
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
            
        # Real-time Box Calculation
        calc_bx = calculate_boxes(new_sqft, cf, pu)
        
        with c3:
            st.markdown(f"### **{calc_bx}** Boxes")
            
        with c4:
            if st.button("❌ Remove", key=f"btn_del_{it['id']}", type="secondary"):
                st.session_state.active_cart = [x for x in st.session_state.active_cart if x.get("id") != it.get("id")]
                save_json_file(SELECTIONS_FILE, st.session_state.active_cart)
                st.rerun()

        it_copy = dict(it)
        it_copy["sqft"] = new_sqft
        it_copy["boxes"] = calc_bx
        updated_items.append(it_copy)
        st.divider()

    # Auto-save changes if values updated
    if updated_items != st.session_state.active_cart:
        st.session_state.active_cart = updated_items
        save_json_file(SELECTIONS_FILE, st.session_state.active_cart)

    # --- COMPLETE DETAIL TABLE (BOQ) ---
    st.markdown("### 📋 Complete Estimate & Detail Breakdown")
    summary_df = pd.DataFrame(st.session_state.active_cart)[["floor", "surface", "area", "tile", "con_factor", "packing_unit", "sqft", "boxes"]]
    st.dataframe(summary_df.rename(columns={
        "floor": "Floor", "surface": "Type", "area": "Area", "tile": "Tile Item Name",
        "con_factor": "Con Factor", "packing_unit": "Packing Unit",
        "sqft": "Total Sq.Ft", "boxes": "Required Boxes"
    }), use_container_width=True)
    
    tot_sq = sum(float(x.get("sqft", 0.0)) for x in st.session_state.active_cart)
    tot_bx = sum(float(x.get("boxes", 0.0)) for x in st.session_state.active_cart)
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Tile Items", len(st.session_state.active_cart))
    k2.metric("Total Area", f"{tot_sq:.2f} Sq.Ft")
    k3.metric("Total Required Boxes", f"{tot_bx:.0f} Boxes")
    
    # WhatsApp Share Text
    wa_msg = f"🏛️ *JAY GRANITE & TILES - TILE ESTIMATE*\n\n"
    wa_msg += f"👤 *Client Name:* {st.session_state.current_customer['name']}\n"
    wa_msg += f"📱 *Mobile:* {st.session_state.current_customer['mobile']}\n"
    wa_msg += f"📅 *Date:* {datetime.now().strftime('%d-%m-%Y')}\n"
    wa_msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    for it in st.session_state.active_cart:
        wa_msg += f"🔹 *{it['area']}* ({it['floor']})\n"
        wa_msg += f"   • Tile: {it['tile']}\n"
        wa_msg += f"   • Area: {it['sqft']:.2f} Sq.Ft\n"
        wa_msg += f"   • Required: *{it['boxes']:.0f} Boxes*\n\n"
    wa_msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    wa_msg += f"📊 *Total Area:* {tot_sq:.2f} Sq.Ft\n"
    wa_msg += f"📦 *Total Required Boxes:* {tot_bx:.0f} Boxes\n\n"
    wa_msg += f"Thank you for choosing Jay Granite & Tiles!"

    st.markdown("#### 💬 WhatsApp Direct Copy Text")
    st.text_area("WhatsApp Message Text:", value=wa_msg, height=150)
    
    pdf_bytes = generate_pdf_quotation(st.session_state.current_customer, st.session_state.active_cart)
    
    b1, b2, b3 = st.columns(3)
    with b1:
        st.download_button(
            "📄 Download Estimate PDF",
            data=pdf_bytes,
            file_name=f"Estimate_{st.session_state.current_customer['name']}_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    with b2:
        enc_txt = urllib.parse.quote(wa_msg)
        mob_num = "".join(filter(str.isdigit, str(st.session_state.current_customer['mobile'])))
        if len(mob_num) == 10:
            mob_num = "91" + mob_num
        st.link_button("📲 1-Click WhatsApp Send", f"https://wa.me/{mob_num}?text={enc_txt}", use_container_width=True)
    with b3:
        if st.button("🗑️ Reset Cart / Start New", use_container_width=True):
            st.session_state.active_cart = []
            save_json_file(SELECTIONS_FILE, [])
            st.rerun()

# --- PAGE 4: EXECUTIVE DASHBOARD ---
elif nav == "📊 Executive Dashboard" and st.session_state.role == "admin":
    st.title("📊 Executive Dashboard")
    all_custs = load_json_file(CUSTOMERS_FILE, [])
    st.metric("👥 Total Clients Registered", len(all_custs))
    if all_custs:
        st.dataframe(pd.DataFrame(all_custs), use_container_width=True)
    else:
        st.info("No customer history found.")

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
