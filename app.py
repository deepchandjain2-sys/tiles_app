import json
import os
import math
import urllib.parse
import io
import pandas as pd
import streamlit as st
from fpdf import FPDF
from datetime import datetime

# --- DATABASE & MODULE IMPORTS / FALLBACKS ---
try:
    from database import (
        load_stock_from_disk,
        load_stock_from_upload,
        save_customers_to_disk,
        load_customers_from_disk
    )
except ImportError:
    def load_stock_from_disk():
        return None
    def load_stock_from_upload(file):
        return pd.read_csv(file)
    def save_customers_to_disk(data):
        with open("customers.json", "w") as f:
            json.dump(data, f)
    def load_customers_from_disk():
        if os.path.exists("customers.json"):
            with open("customers.json", "r") as f:
                return json.load(f)
        return []

try:
    from calculations import calculate_boxes, calculate_box_sqft
except ImportError:
    def calculate_box_sqft(con_factor, packing_unit):
        try:
            return round(float(con_factor) * float(packing_unit), 2)
        except Exception:
            return 16.0

    def calculate_boxes(sqft, con_factor, packing_unit):
        try:
            sqft_val = float(sqft)
            coverage = float(con_factor) * float(packing_unit)
            if coverage <= 0:
                return 0
            return math.ceil(sqft_val / coverage)
        except Exception:
            return 0

st.set_page_config(
    page_title="Jay Granite & Tiles Hub",
    page_icon="🏛️",
    layout="wide"
)

DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1qhlBmCLiDdAKQMxRbYKSrFcEHybFkxfv2XIABLsO6pA/edit"

# --- PERSISTENT DATA FILE PATHS ---
USERS_FILE = "users_data.json"
SELECTIONS_FILE = "customer_selections.json"
MEASUREMENTS_FILE = "measurements_data.json"

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

# --- DYNAMIC GOOGLE SHEET STOCK LOADER (ROBUST URL FIX) ---
@st.cache_data(ttl=300)
def load_dynamic_sheet_stock(sheet_url):
    try:
        url = sheet_url.strip()
        if "/pubhtml" in url:
            url = url.replace("/pubhtml", "/pub?output=csv")
        elif "/pub?" in url:
            if "output=csv" not in url:
                url = url + "&output=csv"
        elif "/edit" in url:
            url = url.split("/edit")[0] + "/export?format=csv"
        elif not url.endswith("output=csv") and not url.endswith("format=csv"):
            url = url.rstrip("/") + "/export?format=csv"
        
        raw_df = pd.read_csv(url, header=None, dtype=str)
        
        # Locate header row containing ITEM NAME
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
            if not item_name or item_name.upper() in ["NAN", "ITEM NAME", "TOTAL", "NONE", "NULL", "UNNAMED"]:
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
        return df
    except Exception as ex:
        st.error(f"Sheet Sync Notice: {str(ex)}")
        return pd.DataFrame()

def get_master_df():
    df = load_dynamic_sheet_stock(DEFAULT_SHEET_URL)
    if df is not None and not df.empty:
        return df
    
    for fname in ["ITEM MASTER.csv", "item_master.csv", "ITEM_MASTER.csv"]:
        if os.path.exists(fname):
            try:
                df = load_stock_from_upload(fname)
                if df is not None and not df.empty:
                    return df
            except Exception:
                pass
    return pd.DataFrame([
        {"item_name": "1000 L 12X18 KK", "con_factor": 1.5, "packing_unit": 6.0, "sqft_per_box": 9.0},
        {"item_name": "ALBETA WHITE DAZZEL 2X4 ITALICA", "con_factor": 8.0, "packing_unit": 2.0, "sqft_per_box": 16.0},
        {"item_name": "AOSTA CARRARA GVT 4X6 15MM VARMORA", "con_factor": 23.25, "packing_unit": 1.0, "sqft_per_box": 23.25}
    ])

def clean_item_name(raw_name):
    name_str = str(raw_name).strip()
    if name_str.lower().startswith("nan -"):
        name_str = name_str[5:].strip()
    elif name_str.lower().startswith("nan"):
        name_str = name_str[3:].strip()
    return name_str

# --- PDF QUOTATION ENGINE ---
def generate_pdf_quotation(customer_info, items_list):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(31, 78, 121)
    pdf.rect(0, 0, 210, 25, 'F')
    
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "JAY GRANITE & TILES", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, "Architectural Selection & Estimate", ln=True, align="C")
    pdf.ln(8)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(100, 6, f"Customer: {customer_info.get('name', 'Walk-in')}", ln=False)
    pdf.cell(0, 6, f"Date: {datetime.now().strftime('%d-%m-%Y')}", ln=True, align="R")
    pdf.cell(100, 6, f"Mobile: {customer_info.get('mobile', '-')}", ln=True)
    pdf.ln(4)
    
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(20, 7, "Floor", 1, 0, "C", fill=True)
    pdf.cell(32, 7, "Area", 1, 0, "C", fill=True)
    pdf.cell(50, 7, "Tile Item", 1, 0, "L", fill=True)
    pdf.cell(18, 7, "Size (Ft)", 1, 0, "C", fill=True)
    pdf.cell(16, 7, "Con Fac", 1, 0, "C", fill=True)
    pdf.cell(16, 7, "Pack", 1, 0, "C", fill=True)
    pdf.cell(18, 7, "Sq.Ft", 1, 0, "R", fill=True)
    pdf.cell(20, 7, "Boxes", 1, 1, "R", fill=True)
    
    pdf.set_font("Helvetica", "", 8)
    tot_sqft = 0.0
    tot_boxes = 0.0
    for it in items_list:
        sq = float(it.get("sqft", 0.0))
        bx = float(it.get("boxes", 0.0))
        tot_sqft += sq
        tot_boxes += bx
        
        pdf.cell(20, 6, str(it.get("floor", "-"))[:10], 1, 0, "C")
        pdf.cell(32, 6, str(it.get("area", "-"))[:18], 1, 0, "L")
        pdf.cell(50, 6, str(it.get("tile", "-"))[:26], 1, 0, "L")
        pdf.cell(18, 6, str(it.get("dimensions", "-")), 1, 0, "C")
        pdf.cell(16, 6, f"{float(it.get('con_factor', 1.0)):.2f}", 1, 0, "C")
        pdf.cell(16, 6, f"{float(it.get('packing_unit', 1.0)):.0f}", 1, 0, "C")
        pdf.cell(18, 6, f"{sq:.2f}", 1, 0, "R")
        pdf.cell(20, 6, f"{bx:.0f}", 1, 1, "R")
        
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(152, 7, "Grand Total", 1, 0, "R", fill=True)
    pdf.cell(18, 7, f"{tot_sqft:.2f}", 1, 0, "R", fill=True)
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
    st.caption("Integrated Architecture & Tile Management System")
    
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

# --- NAVIGATION ---
st.sidebar.title(f"👤 {st.session_state.username.upper()}")
st.sidebar.markdown(f"**Role:** `{st.session_state.role.upper()}`")
if st.sidebar.button("🚪 Sign Out", use_container_width=True):
    st.session_state.auth = False
    st.rerun()

nav_list = [
    "1️⃣ Customer Registration",
    "2️⃣ Tile Selection (Showroom)",
    "3️⃣ Measurement, BOQ & Share PDF"
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
        
        if st.form_submit_button("Proceed to Selection", type="primary"):
            if cust_name.strip() and cust_mob.strip():
                st.session_state.current_customer = {
                    "id": len(load_json_file("customers_list.json", [])) + 1,
                    "name": cust_name.strip(),
                    "mobile": cust_mob.strip(),
                    "address": cust_site.strip(),
                    "salesman": st.session_state.username
                }
                c_list = load_json_file("customers_list.json", [])
                c_list.append(st.session_state.current_customer)
                save_json_file("customers_list.json", c_list)
                st.success(f"Customer **{cust_name}** selected!")
            else:
                st.error("Name aur Mobile number enter karein.")

# --- PAGE 2: TILE SELECTION (SHOWROOM PITCH) ---
elif nav == "2️⃣ Tile Selection (Showroom)":
    st.title("🏷️ Showroom Tile Selection")
    st.info(f"Active Client: **{st.session_state.current_customer['name']}** ({st.session_state.current_customer['mobile']}) | Staff: **{st.session_state.username}**")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        floor = st.selectbox("Floor Level", ["Ground Floor", "First Floor", "Second Floor", "Third Floor", "Terrace"])
    with col2:
        surface = st.radio("Surface Type", ["Floor", "Wall"], horizontal=True)
    with col3:
        area_options = [
            "Living Room / Hall", "Master Bedroom", "Bedroom 2", "Kitchen", 
            "Kitchen Dado / Wall", "Dining Area", "Pooja Room", "Master Bathroom", 
            "Common Bathroom", "Balcony", "Parking / Porch", "✏️ Custom Area"
        ]
        sel_area = st.selectbox("Designated Area", area_options)
        final_area = st.text_input("Custom Area Name", "Store Room") if sel_area == "✏️ Custom Area" else sel_area
        
    search = st.text_input("🔍 Search Tile (Code / Size / Name)", "")
    filtered_df = master_df[master_df["item_name"].str.contains(search, case=False, na=False)] if search else master_df
    
    if filtered_df.empty:
        filtered_df = master_df
        
    chosen_tile = st.selectbox("Select Tile Item", filtered_df["item_name"].tolist())
    
    # Exact Dynamic Values from Google Sheet / Master
    matched_row = filtered_df[filtered_df["item_name"] == chosen_tile].iloc[0]
    cf = float(matched_row.get("con_factor", 1.0))
    pu = float(matched_row.get("packing_unit", 1.0))
    box_cov = calculate_box_sqft(cf, pu)
    
    st.success(f"📐 **Live Master Formula:** Con Factor (`{cf}`) × Packing Unit (`{pu}`) = **{box_cov:.2f} Sq.Ft / Box**")
    
    if st.button("➕ Add Tile to Customer Cart", type="primary", use_container_width=True):
        new_item = {
            "id": int(datetime.now().timestamp() * 1000),
            "customer_id": st.session_state.current_customer.get("id", 1),
            "customer_name": st.session_state.current_customer.get("name", "Walk-in"),
            "floor": floor,
            "surface": surface,
            "area": final_area,
            "tile": chosen_tile,
            "con_factor": cf,
            "packing_unit": pu,
            "length": 10.0,
            "width": 10.0,
            "dimensions": "10.0x10.0 ft",
            "sqft": 100.0,
            "boxes": calculate_boxes(100.0, cf, pu)
        }
        st.session_state.active_cart.append(new_item)
        save_json_file(SELECTIONS_FILE, st.session_state.active_cart)
        st.success(f"✅ **{chosen_tile}** added successfully!")
        st.rerun()

    st.markdown("---")
    st.subheader(f"🛒 Current Cart Items ({len(st.session_state.active_cart)})")
    if st.session_state.active_cart:
        disp_df = pd.DataFrame(st.session_state.active_cart)[["floor", "area", "tile", "con_factor", "packing_unit"]]
        st.dataframe(disp_df.rename(columns={"floor": "Floor", "area": "Area", "tile": "Tile Item", "con_factor": "Con Factor", "packing_unit": "Packing Unit"}), use_container_width=True)
        st.info("👉 Please proceed to **'3️⃣ Measurement, BOQ & Share PDF'** to update exact dimensions.")
    else:
        st.caption("No tiles selected yet.")

# --- PAGE 3: MEASUREMENT, BOQ & PDF SHARE ---
elif nav == "3️⃣ Measurement, BOQ & Share PDF":
    st.title("📐 Measurement & Quotation Share")
    st.info(f"Client: **{st.session_state.current_customer['name']}** ({st.session_state.current_customer['mobile']})")
    
    if not st.session_state.active_cart:
        st.warning("Please select tiles from **'2️⃣ Tile Selection'** page first.")
        st.stop()
        
    st.subheader("✏️ Enter Site Dimensions (Length x Width in Feet):")
    
    for it in list(st.session_state.active_cart):
        cf = float(it.get("con_factor", 1.0))
        pu = float(it.get("packing_unit", 1.0))
        cov = calculate_box_sqft(cf, pu)
        
        c_desc, c_del = st.columns([4, 1])
        with c_desc:
            st.markdown(f"**{it['area']}** ({it['floor']} - {it['surface']}) — *{it['tile']}*")
            st.caption(f"🔹 **Con Factor:** `{cf}` | **Packing Unit:** `{pu}` | **Coverage/Box:** `{cov:.2f} Sq.Ft`")
        with c_del:
            if st.button("❌ Remove", key=f"del_{it['id']}", type="secondary"):
                st.session_state.active_cart = [x for x in st.session_state.active_cart if x["id"] != it["id"]]
                save_json_file(SELECTIONS_FILE, st.session_state.active_cart)
                st.rerun()

    with st.form("measurement_boq_form"):
        updated_list = []
        for it in st.session_state.active_cart:
            cf = float(it.get("con_factor", 1.0))
            pu = float(it.get("packing_unit", 1.0))
            
            cl, cw = st.columns(2)
            with cl:
                l_val = st.number_input(f"Length (Ft) - {it['area']}", value=float(it.get("length", 10.0)), step=0.5, key=f"len_{it['id']}")
            with cw:
                w_val = st.number_input(f"Width (Ft) - {it['area']}", value=float(it.get("width", 10.0)), step=0.5, key=f"wid_{it['id']}")
                
            sq = round(l_val * w_val, 2)
            bx = calculate_boxes(sq, cf, pu)
            
            it_copy = dict(it)
            it_copy["length"] = l_val
            it_copy["width"] = w_val
            it_copy["dimensions"] = f"{l_val}x{w_val} ft"
            it_copy["sqft"] = sq
            it_copy["boxes"] = bx
            updated_list.append(it_copy)
            st.markdown("---")
            
        if st.form_submit_button("💾 Calculate & Update All Boxes", type="primary", use_container_width=True):
            st.session_state.active_cart = updated_list
            save_json_file(SELECTIONS_FILE, st.session_state.active_cart)
            st.success("All measurements updated accurately!")
            st.rerun()

    st.markdown("### 📋 Final Bill of Quantities (BOQ)")
    summary_df = pd.DataFrame(st.session_state.active_cart)[["floor", "surface", "area", "tile", "dimensions", "con_factor", "packing_unit", "sqft", "boxes"]]
    st.dataframe(summary_df.rename(columns={
        "floor": "Floor", "surface": "Type", "area": "Area", "tile": "Tile Item",
        "dimensions": "Dimensions", "con_factor": "Con Factor", "packing_unit": "Packing Unit",
        "sqft": "Sq.Ft", "boxes": "Boxes Required"
    }), use_container_width=True)
    
    tot_sq = sum(float(x.get("sqft", 0.0)) for x in st.session_state.active_cart)
    tot_bx = sum(float(x.get("boxes", 0.0)) for x in st.session_state.active_cart)
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Items", len(st.session_state.active_cart))
    k2.metric("Total Area", f"{tot_sq:.2f} Sq.Ft")
    k3.metric("Total Required Boxes", f"{tot_bx:.0f} Boxes")
    
    wa_msg = f"🏛️ *JAY GRANITE & TILES - TILE ESTIMATE*\n\n"
    wa_msg += f"👤 *Client Name:* {st.session_state.current_customer['name']}\n"
    wa_msg += f"📱 *Mobile:* {st.session_state.current_customer['mobile']}\n"
    wa_msg += f"📅 *Date:* {datetime.now().strftime('%d-%m-%Y')}\n"
    wa_msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    for it in st.session_state.active_cart:
        wa_msg += f"🔹 *{it['area']}* ({it['floor']})\n"
        wa_msg += f"   • Tile: {it['tile']}\n"
        wa_msg += f"   • Size: {it['dimensions']} | Area: {it['sqft']} Sq.Ft\n"
        wa_msg += f"   • Quantity: *{it['boxes']:.0f} Boxes*\n\n"
    wa_msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    wa_msg += f"📊 *Total Area:* {tot_sq:.2f} Sq.Ft\n"
    wa_msg += f"📦 *Total Required Boxes:* {tot_bx:.0f} Boxes\n\n"
    wa_msg += f"Thank you for choosing Jay Granite & Tiles!"

    st.markdown("#### 💬 WhatsApp Quick Copy Text")
    st.text_area("Copy and share directly on WhatsApp:", value=wa_msg, height=160)
    
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
        if st.button("🗑️ Reset Cart", use_container_width=True):
            st.session_state.active_cart = []
            save_json_file(SELECTIONS_FILE, [])
            st.rerun()

# --- PAGE 4: EXECUTIVE DASHBOARD (ADMIN ONLY) ---
elif nav == "📊 Executive Dashboard" and st.session_state.role == "admin":
    st.title("📊 Executive Dashboard")
    all_custs = load_json_file("customers_list.json", [])
    st.metric("👥 Total Clients Registered", len(all_custs))
    if all_custs:
        st.dataframe(pd.DataFrame(all_custs), use_container_width=True)
    else:
        st.info("No customer history found.")

# --- PAGE 5: STOCK MASTER & SETTINGS (ADMIN ONLY) ---
elif nav == "⚙️ Stock Master & Settings" and st.session_state.role == "admin":
    st.title("⚙️ Live Stock Master (Google Sheet Linked)")
    sheet_input = st.text_input("Google Sheet Master URL", value=DEFAULT_SHEET_URL)
    
    if st.button("🔄 Sync Live Master Now", type="primary"):
        st.cache_data.clear()
        new_df = load_dynamic_sheet_stock(sheet_input.strip())
        if not new_df.empty:
            st.success(f"🎉 Successfully loaded **{len(new_df)} tiles** directly from Google Sheet!")
            st.rerun()
        else:
            st.error("Could not sync with Google Sheet. Please check the URL.")
            
    st.markdown("---")
    st.subheader(f"📦 Master Live Stock Catalog ({len(master_df)} Items)")
    st.dataframe(master_df.rename(columns={
        "item_name": "Tile Item Name",
        "con_factor": "Con Factor (Col H)",
        "packing_unit": "Packing Unit (Col I)",
        "sqft_per_box": "Coverage SqFt/Box"
    }), use_container_width=True)
