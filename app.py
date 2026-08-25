import json
import os
import math
import urllib.parse
import pandas as pd
import streamlit as st
from fpdf import FPDF
from database import (
    load_stock_from_disk, 
    load_stock_from_upload, 
    save_customers_to_disk, 
    load_customers_from_disk
)

st.set_page_config(
    page_title="Jay Granite & Tiles Hub", page_icon="🪨", layout="wide"
)

USERS_FILE = "users_db.json"
SELECTIONS_FILE = "customer_selections.json"
MEASUREMENTS_FILE = "customer_measurements.json"

def load_json_file(filename, default_val):
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                data = json.load(f)
                if isinstance(data, type(default_val)):
                    return data
        except:
            pass
    return default_val

def save_json_file(filename, data):
    try:
        with open(filename, "w") as f:
            json.dump(data, f)
    except:
        pass

def load_users_from_disk():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except:
            pass
    return [
        {
            "username": "admin",
            "pin": "1234",
            "name": "Deepchand Jain",
            "role": "Admin",
            "phone": "9999999999"
        }
    ]

def save_users_to_disk(users_list):
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(users_list, f)
    except:
        pass

# Initialize Session State & Persistent Storage
if "registered_users" not in st.session_state or not isinstance(st.session_state.registered_users, list):
    st.session_state.registered_users = load_users_from_disk()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "current_user" not in st.session_state:
    st.session_state.current_user = None

if "customers" not in st.session_state or not isinstance(st.session_state.customers, list):
    loaded_cust = load_customers_from_disk()
    st.session_state.customers = loaded_cust if loaded_cust else [{"cid": "CUST-001", "name": "Vansh", "phone": "964444419", "city": "Hiriyur"}]

if "sales_history" not in st.session_state:
    st.session_state.sales_history = []

if "current_cid" not in st.session_state:
    if st.session_state.customers:
        st.session_state.current_cid = st.session_state.customers[0].get("cid", "CUST-001")
    else:
        st.session_state.current_cid = "CUST-001"

if "my_selected_tiles" not in st.session_state:
    st.session_state.my_selected_tiles = load_json_file(SELECTIONS_FILE, [])

if "measurements_list" not in st.session_state:
    st.session_state.measurements_list = load_json_file(MEASUREMENTS_FILE, [])

# --- SIDEBAR LOGIN & NAVIGATION ---
st.sidebar.title("🪨 Jay Granite & Tiles")

if st.session_state.logged_in:
    current_u = st.session_state.current_user
    user_display = f"{current_u.get('name', 'User')} ({current_u.get('role', 'Staff')})"
    st.sidebar.markdown(f"👤 **User:** {user_display}")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Navigation Flow")

    nav_options = [
        "1 Customer Registration",
        "2 Tiles Selection (Area-Wise)",
        "3 Measurements, PDF & WhatsApp",
        "4 Sales Dashboard & History",
    ]
    
    if current_u.get("role") == "Admin":
        nav_options.append("5 Salesman Progress Report")

    if "current_nav" not in st.session_state:
        st.session_state.current_nav = nav_options[0]

    selected_nav = st.sidebar.radio(
        "Go to section",
        nav_options,
        index=nav_options.index(st.session_state.current_nav) if st.session_state.current_nav in nav_options else 0
    )
    st.session_state.current_nav = selected_nav

    st.sidebar.markdown("---")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.current_user = None
        st.rerun()

else:
    st.sidebar.markdown("### 🔐 Access Control Hub")
    auth_tab = st.sidebar.radio("Select Action", ["Login", "Register Salesman", "Forgot PIN"])

    if auth_tab == "Login":
        st.sidebar.markdown("#### Sign In")
        u_input = st.sidebar.text_input("Username / Phone", key="login_user")
        p_input = st.sidebar.text_input("PIN / Password", type="password", key="login_pin")

        if st.sidebar.button("Login Now"):
            matched = None
            if u_input.strip().lower() in ["admin", "deepchand jain"] and p_input in ["1234", "deep1965"]:
                matched = {"username": "admin", "name": "Deepchand Jain", "role": "Admin"}
            else:
                for u in st.session_state.registered_users:
                    if isinstance(u, dict):
                        u_name = u.get("username", "").strip().lower()
                        u_phone = u.get("phone", "").strip()
                        u_pin = str(u.get("pin", ""))
                    else:
                        u_name = str(u).strip().lower()
                        u_phone = ""
                        u_pin = "1234"

                    if (u_name == u_input.strip().lower() or u_phone == u_input.strip()) and u_pin == str(p_input):
                        matched = u if isinstance(u, dict) else {"username": u, "name": u, "role": "Salesman"}
                        break

            if matched:
                st.session_state.logged_in = True
                st.session_state.current_user = matched if isinstance(matched, dict) else {"username": matched, "name": matched, "role": "Salesman"}
                st.sidebar.success("Login Successful!")
                st.rerun()
            else:
                st.sidebar.error("Invalid Username/Phone or PIN!")

    elif auth_tab == "Register Salesman":
        st.sidebar.markdown("#### Register New Staff")
        new_name = st.sidebar.text_input("Full Name", key="reg_name")
        new_phone = st.sidebar.text_input("Phone Number", key="reg_phone")
        new_username = st.sidebar.text_input("Username", key="reg_uname")
        new_pin = st.sidebar.text_input("Create PIN", type="password", key="reg_pin")
        new_role = st.sidebar.selectbox("Role", ["Salesman", "Admin"])

        if st.sidebar.button("Register Account"):
            if new_name and new_phone and new_username and new_pin:
                if not isinstance(st.session_state.registered_users, list):
                    st.session_state.registered_users = [{"username": "admin", "pin": "1234", "name": "Deepchand Jain", "role": "Admin", "phone": "9999999999"}]

                exists = False
                for u in st.session_state.registered_users:
                    if isinstance(u, dict):
                        if u.get("username", "") == new_username.strip():
                            exists = True
                            break
                    elif str(u) == new_username.strip():
                        exists = True
                        break

                if exists:
                    st.sidebar.error("Username already exists!")
                else:
                    new_obj = {
                        "username": new_username.strip(),
                        "pin": new_pin.strip(),
                        "name": new_name.strip(),
                        "role": new_role,
                        "phone": new_phone.strip()
                    }
                    st.session_state.registered_users.append(new_obj)
                    save_users_to_disk(st.session_state.registered_users)
                    st.sidebar.success("Registered successfully! You can now login.")
            else:
                st.sidebar.error("Please fill all fields.")

    elif auth_tab == "Forgot PIN":
        st.sidebar.markdown("#### Reset PIN")
        f_phone = st.sidebar.text_input("Registered Phone", key="forgot_phone")
        f_new_pin = st.sidebar.text_input("New PIN", type="password", key="forgot_new_pin")

        if st.sidebar.button("Update PIN"):
            found = False
            for u in st.session_state.registered_users:
                if isinstance(u, dict) and u.get("phone", "").strip() == f_phone.strip():
                    u["pin"] = f_new_pin.strip()
                    found = True
                    break
            if found:
                save_users_to_disk(st.session_state.registered_users)
                st.sidebar.success("PIN updated successfully!")
            else:
                st.sidebar.error("Phone number not found.")

if not st.session_state.logged_in:
    st.title("🪨 Jay Granite & Tiles Hub")
    st.info("👈 Please use the sidebar to **Login**, **Register Salesman**, or **Reset PIN** to access your application.")
    st.stop()

# --- MASTER LOADER ---
def get_master_df():
    df = load_stock_from_disk()
    if df is not None and not df.empty:
        return df
    
    for fname in ["ITEM MASTER.csv", "item_master.csv", "ITEM_MASTER.csv"]:
        if os.path.exists(fname):
            try:
                df = load_stock_from_upload(fname)
                if df is not None and not df.empty:
                    return df
            except:
                pass
    return None

# --- COLOURFUL PDF GENERATOR FUNCTION ---
def generate_pdf_quotation(customer_info, items_list):
    pdf = FPDF()
    pdf.add_page()
    
    # Header Background Color (Deep Blue)
    pdf.set_fill_color(31, 78, 121)
    pdf.rect(0, 0, 210, 25, 'F')
    
    # Header Title (White Text)
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(255, 255, 255)
    pdf.set_y(7)
    pdf.cell(200, 10, txt="JAY GRANITE & TILES HUB", ln=True, align="C")
    
    # Subheader
    pdf.set_font("Arial", "", 10)
    pdf.set_y(28)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(200, 6, txt="Hiriyur, Karnataka | Phone: 9999999999", ln=True, align="C")
    pdf.ln(5)
    
    # Customer Details Box (Light Grey Background with Blue Border)
    pdf.set_fill_color(240, 244, 248)
    pdf.set_draw_color(31, 78, 121)
    pdf.rect(10, 38, 190, 20, 'DF')
    
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(31, 78, 121)
    pdf.set_xy(15, 41)
    pdf.cell(100, 6, txt=f"Customer Name: {customer_info.get('name', '')}", ln=False)
    
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(50, 50, 50)
    pdf.set_xy(15, 49)
    pdf.cell(180, 6, txt=f"Phone: {customer_info.get('phone', '')}   |   City: {customer_info.get('city', 'Hiriyur')}", ln=True)
    pdf.ln(15)
    
    # Table Header (Colored Background)
    pdf.set_fill_color(31, 78, 121)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 10)
    
    pdf.cell(60, 8, "Design / Area", 1, 0, 'C', True)
    pdf.cell(80, 8, "Item Name", 1, 0, 'C', True)
    pdf.cell(25, 8, "Sq.Ft", 1, 0, 'C', True)
    pdf.cell(25, 8, "Boxes", 1, 1, 'C', True)
    
    # Table Rows (Alternating Colors)
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(20, 20, 20)
    
    fill = False
    for item in items_list:
        if fill:
            pdf.set_fill_color(245, 245, 245)
        else:
            pdf.set_fill_color(255, 255, 255)
            
        pdf.cell(60, 8, str(item.get('area_design', ''))[:30], 1, 0, 'L', True)
        pdf.cell(80, 8, str(item.get('item_name', ''))[:40], 1, 0, 'L', True)
        pdf.cell(25, 8, str(item.get('sqft', '')), 1, 0, 'C', True)
        pdf.cell(25, 8, str(item.get('boxes', '')), 1, 1, 'C', True)
        fill = not fill
        
    pdf.ln(15)
    
    # Footer Note
    pdf.set_font("Arial", "I", 10)
    pdf.set_text_color(31, 78, 121)
    pdf.cell(200, 6, txt="Thank you for visiting Jay Granite & Tiles Hub!", ln=True, align="C")
    
    pdf_output_path = "quotation.pdf"
    pdf.output(pdf_output_path)
    return pdf_output_path

# --- APP SECTIONS ---
if st.session_state.current_nav == "1 Customer Registration":
    st.title("👥 Customer Registration & Selection")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Register New Customer")
        with st.form("new_cust_form"):
            c_name = st.text_input("Customer Name")
            c_phone = st.text_input("Phone Number")
            c_city = st.text_input("City / Location", value="Hiriyur")
            submitted_c = st.form_submit_button("Save Customer")

            if submitted_c:
                if c_name.strip() and c_phone.strip():
                    if not isinstance(st.session_state.customers, list):
                        st.session_state.customers = []
                    new_cid = f"CUST-{len(st.session_state.customers) + 1:03d}"
                    cust_obj = {"cid": new_cid, "name": c_name.strip(), "phone": c_phone.strip(), "city": c_city.strip()}
                    st.session_state.customers.append(cust_obj)
                    save_customers_to_disk(st.session_state.customers)
                    st.session_state.current_cid = new_cid
                    st.success(f"Customer {c_name} registered successfully!")
                    st.rerun()
                else:
                    st.error("Please provide both Name and Phone number.")

    with col2:
        st.markdown("### Select Active Customer")
        if st.session_state.customers:
            cust_options = {f"{c.get('name')} ({c.get('phone')} - {c.get('city', 'Hiriyur')})": c.get('cid') for c in st.session_state.customers if isinstance(c, dict)}
            if cust_options:
                current_label = next((k for k, v in cust_options.items() if v == st.session_state.current_cid), None)
                selected_label = st.selectbox("Existing Customers", options=list(cust_options.keys()), index=list(cust_options.keys()).index(current_label) if current_label and current_label in cust_options else 0)
                if selected_label:
                    st.session_state.current_cid = cust_options[selected_label]
        else:
            st.warning("No customers registered yet.")

elif st.session_state.current_nav == "2 Tiles Selection (Area-Wise)":
    st.title("🪨 Tiles Selection & Saved Items")
    
    active_cust = next((c for c in st.session_state.customers if c.get("cid") == st.session_state.current_cid), None)
    if active_cust:
        st.success(f"👤 **Active Party / Customer:** {active_cust.get('name')} | 📞 **Phone:** {active_cust.get('phone')} | 📍 **City:** {active_cust.get('city', 'Hiriyur')}")
    else:
        st.warning("⚠️ No customer selected! Please select a customer from '1 Customer Registration'.")

    df = get_master_df()
    if df is None:
        uploaded_file = st.file_uploader("Upload Item Master File", type=["csv", "xlsx", "xls"], key="master_uploader")
        if uploaded_file is not None:
            df = load_stock_from_upload(uploaded_file)

    if df is not None and not df.empty:
        st.markdown("---")
        st.markdown("### 🏷️ Select Floor, Building Area & Tiles")
        
        floor_options = ["Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "Staircase", "Elevation / Parking"]
        selected_floor = st.selectbox("Select Floor", floor_options)
        
        area_options = [
            "Living Room / Hall", 
            "Kitchen", 
            "Master Bedroom", 
            "Children Bedroom", 
            "Common Bathroom", 
            "Attached Bathroom", 
            "Balcony", 
            "Verandah", 
            "Dining Area", 
            "Other Area"
        ]
        selected_area = st.selectbox("Select Building Area / Room", area_options)
        
        search_query = st.text_input("🔍 Search Tile / Granite Name or Code")
        
        if search_query.strip():
            mask = df.astype(str).apply(lambda row: row.str.contains(search_query, case=False, na=False).any(), axis=1)
            filtered_df = df[mask]
        else:
            filtered_df = df.head(100)
            
        if not filtered_df.empty:
            options_list = []
            for idx, row in filtered_df.iterrows():
                code_val = str(row.iloc[0]).strip()
                name_val = str(row.iloc[1]).strip() if len(df.columns) > 1 else ""
                display_text = f"{code_val} - {name_val}" if name_val and name_val.lower() != 'nan' else code_val
                options_list.append(display_text)
                
            selected_item_label = st.selectbox("Choose Tile Item", options=options_list)
            
            if st.button("➕ Add Tile to Customer Selection"):
                combined_location = f"{selected_floor} - {selected_area}"
                selection_item = {
                    "cid": st.session_state.current_cid,
                    "customer_name": active_cust.get('name') if active_cust else "Unknown",
                    "floor_area": combined_location,
                    "item": selected_item_label
                }
                st.session_state.my_selected_tiles.append(selection_item)
                save_json_file(SELECTIONS_FILE, st.session_state.my_selected_tiles)
                st.success(f"Added {selected_item_label} for {combined_location} successfully!")
                st.rerun()
        else:
            st.info("No matching items found. Try a different search keyword.")
        
        # --- SAVED SELECTIONS WITH DELETE BUTTON ---
        st.markdown("---")
        st.markdown("### 📋 Saved Selections for Active Customer")
        cust_selections = [s for s in st.session_state.my_selected_tiles if s.get("cid") == st.session_state.current_cid]
        if cust_selections:
            for s_idx, sel_item in enumerate(cust_selections):
                col_d1, col_d2, col_d3 = st.columns([2, 3, 1])
                with col_d1:
                    st.write(f"📍 **{sel_item.get('floor_area')}**")
                with col_d2:
                    st.write(f"🪨 {sel_item.get('item')}")
                with col_d3:
                    if st.button("🗑️ Delete", key=f"del_sel_{s_idx}_{sel_item.get('cid')}"):
                        st.session_state.my_selected_tiles.remove(sel_item)
                        save_json_file(SELECTIONS_FILE, st.session_state.my_selected_tiles)
                        st.success("Item removed successfully!")
                        st.rerun()
        else:
            st.info("No tiles selected for this customer yet.")
    else:
        st.warning("⚠️ Item master data not found. Please check your Google Sheet / CSV.")

elif st.session_state.current_nav == "3 Measurements, PDF & WhatsApp":
    st.title("📐 Direct Square Feet & Exact Box Calculation")
    
    active_cust = next((c for c in st.session_state.customers if c.get("cid") == st.session_state.current_cid), None)
    if active_cust:
        st.success(f"👤 **Active Customer:** {active_cust.get('name')} | 📞 **Phone:** {active_cust.get('phone')} | 📍 **City:** {active_cust.get('city', 'Hiriyur')}")

    cust_tiles = [s for s in st.session_state.my_selected_tiles if s.get("cid") == st.session_state.current_cid]

    if not cust_tiles:
        st.warning("⚠️ आपने अभी तक '2 Tiles Selection (Area-Wise)' में इस कस्टमर के लिए कोई टाइल नहीं चुनी है। कृपया पहले टाइल्स चुनें!")
    else:
        st.markdown("### 📋 Customer Selected Items List")
        st.info("💡 यहाँ आपके द्वारा सेव किए गए सारे आइटम्स दिख रहे हैं। स्क्वायर फीट दर्ज करके बॉक्स निकालें और सेव करें।")

        for idx, t_data in enumerate(cust_tiles):
            item_name = str(t_data.get('item', ''))
            floor_area = t_data.get('floor_area')
            
            # साइज के अनुसार सटीक Con Factor और Packing Unit
            con_factor = 8.0
            packing_unit = 2.0
            
            u_name = item_name.upper()
            if "2X4" in u_name or "2 X 4" in u_name:
                con_factor = 8.0
                packing_unit = 2.0
            elif "12X18" in u_name:
                con_factor = 1.5
                packing_unit = 6.0
            elif "16X16" in u_name:
                con_factor = 1.73
                packing_unit = 5.0
            elif "2X1" in u_name or "2 X 1" in u_name or "1002" in u_name:
                con_factor = 2.0
                packing_unit = 6.0
            elif "2X2" in u_name or "2 X 2" in u_name:
                con_factor = 4.0
                packing_unit = 4.0

            box_coverage = con_factor * packing_unit

            with st.expander(f"📍 Area: {floor_area} ➔ Item: {item_name}", expanded=(idx == 0)):
                col_i1, col_i2 = st.columns([2, 1])
                with col_i1:
                    st.markdown(f"**Item:** {item_name}")
                    st.markdown(f"**Design Area:** {floor_area}")
                    st.caption(f"🔧 [Size Config] Con Factor: {con_factor} | Packing Unit: {packing_unit}")
                with col_i2:
                    customer_sqft = st.number_input("Enter Sq.Ft", min_value=0.0, value=100.0, step=5.0, key=f"sqft_{idx}_{t_data.get('cid')}")
                
                total_boxes = math.ceil(customer_sqft / box_coverage) if box_coverage > 0 else 0
                
                st.markdown(f"📦 **1 Box Coverage:** `{box_coverage:.2f} Sq.Ft` | 🔥 **Required Boxes:** `{total_boxes} Boxes` | 📐 **Input Sq.Ft:** `{customer_sqft:.2f} Sq.Ft`")
                
                if st.button(f"💾 Save Item Quotation", key=f"save_btn_{idx}_{t_data.get('cid')}"):
                    m_item = {
                        "cid": st.session_state.current_cid,
                        "area_design": floor_area,
                        "item_name": item_name,
                        "sqft": customer_sqft,
                        "boxes": total_boxes,
                        "total_sqft": customer_sqft
                    }
                    if "measurements_list" not in st.session_state:
                        st.session_state.measurements_list = []
                    st.session_state.measurements_list.append(m_item)
                    save_json_file(MEASUREMENTS_FILE, st.session_state.measurements_list)
                    st.success(f"Saved: {total_boxes} Boxes for {item_name} ({customer_sqft} Sq.Ft)")

    if "measurements_list" in st.session_state and st.session_state.measurements_list:
        st.markdown("---")
        st.markdown("### 📋 Final Saved Quotation Summary")
        cust_m = [m for m in st.session_state.measurements_list if m.get("cid") == st.session_state.current_cid]
        if cust_m:
            for m_idx, m_row in enumerate(cust_m):
                col_m1, col_m2, col_m3 = st.columns([4, 2, 1])
                with col_m1:
                    st.write(f"📍 {m_row.get('area_design')} | {m_row.get('item_name')}")
                with col_m2:
                    st.write(f"📐 {m_row.get('sqft')} Sq.Ft | 📦 **{m_row.get('boxes')} Boxes**")
                with col_m3:
                    if st.button("🗑️ Remove", key=f"del_quot_{m_idx}_{m_row.get('cid')}"):
                        st.session_state.measurements_list.remove(m_row)
                        save_json_file(MEASUREMENTS_FILE, st.session_state.measurements_list)
                        st.success("Quotation item removed!")
                        st.rerun()
            
            st.markdown("---")
            st.markdown("### 📤 Export Quotation (PDF & WhatsApp)")
            col_pdf, col_wa = st.columns(2)
            with col_pdf:
                if st.button("📥 Download PDF Quotation"):
                    try:
                        pdf_file = generate_pdf_quotation(active_cust, cust_m)
                        with open(pdf_file, "rb") as f:
                            st.download_button(
                                label="📥 Click Here to Download Colourful PDF",
                                data=f,
                                file_name=f"Quotation_{active_cust.get('name', 'Customer')}.pdf",
                                mime="application/pdf"
                            )
                        st.success("Colourful PDF generated successfully! Click above to download.")
                    except Exception as e:
                        st.error(f"Error generating PDF: {e}")
            with col_wa:
                if active_cust and active_cust.get('phone'):
                    wa_phone = active_cust.get('phone')
                    summary_text = f"Quotation for {active_cust.get('name')}:\n"
                    for item in cust_m:
                        summary_text += f"- {item.get('area_design')} | {item.get('item_name')} | {item.get('sqft')} Sq.Ft | {item.get('boxes')} Boxes\n"
                    wa_msg = urllib.parse.quote(summary_text)
                    st.markdown(f"📱 [Click to Send WhatsApp Quotation](https://wa.me/{wa_phone}?text={wa_msg})", unsafe_allow_html=True)
                else:
                    st.warning("Customer phone number not available for WhatsApp.")
        else:
            st.info("No quotation items saved for this customer yet.")

elif st.session_state.current_nav == "4 Sales Dashboard & History":
    st.title("📊 Sales Dashboard & History")
    st.info("Sales history and analytics view.")

elif st.session_state.current_nav == "5 Salesman Progress Report":
    st.title("📈 Salesman Progress Report (Admin Panel)")
    st.markdown("Here you can track performance and sales generated by each salesman.")
    if st.session_state.sales_history:
        st.write(st.session_state.sales_history)
    else:
        st.info("No sales records found yet.")
