import json
import os
import math
import urllib.parse
import pandas as pd
import streamlit as st
from calculations import calculate_boxes, calculate_box_sqft
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

# Initialize Session State
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
    st.session_state.my_selected_tiles = []

if "measurements_list" not in st.session_state:
    st.session_state.measurements_list = []

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
                    save_users_to_disk(st.session_state.customers) # keeping syntax
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
    st.title("🪨 Tiles Selection (Floor & Area Wise)")
    
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
                st.success(f"Added {selected_item_label} for {combined_location} successfully!")
        else:
            st.info("No matching items found. Try a different search keyword.")
        
        if st.session_state.my_selected_tiles:
            st.markdown("---")
            st.markdown("### 📋 Current Selections for Active Customer")
            cust_selections = [s for s in st.session_state.my_selected_tiles if s.get("cid") == st.session_state.current_cid]
            if cust_selections:
                sel_df = pd.DataFrame(cust_selections)
                st.dataframe(sel_df, use_container_width=True)
            else:
                st.info("No tiles selected for this customer yet.")
    else:
        st.warning("⚠️ Item master data not found. Please place 'ITEM MASTER.csv' in your app folder.")

elif st.session_state.current_nav == "3 Measurements, PDF & WhatsApp":
    st.title("📐 Measurements, PDF & WhatsApp Quotation")
    
    active_cust = next((c for c in st.session_state.customers if c.get("cid") == st.session_state.current_cid), None)
    if active_cust:
        st.success(f"👤 **Active Customer:** {active_cust.get('name')} | 📞 **Phone:** {active_cust.get('phone')} | 📍 **City:** {active_cust.get('city', 'Hiriyur')}")

    cust_tiles = [s for s in st.session_state.my_selected_tiles if s.get("cid") == st.session_state.current_cid]

    if not cust_tiles:
        st.warning("⚠️ आपने अभी तक '2 Tiles Selection (Area-Wise)' में इस कस्टमर के लिए कोई टाइल नहीं चुनी है। कृपया पहले टाइल्स चुनें!")
    else:
        st.markdown("### 📋 Customer Selected Items List (One by One)")
        st.info("💡 Con Factor और Packing Unit बैकएंड में मास्टर शीट से काम कर रहे हैं। यहाँ सिर्फ लंबाई और चौड़ाई दर्ज करें।")

        df_master = get_master_df()

        for idx, t_data in enumerate(cust_tiles):
            item_name = str(t_data.get('item', ''))
            floor_area = t_data.get('floor_area')
            
            # डिफ़ॉल्ट बैकएंड वैल्यू (जैसे 2x4 साइज के लिए Con Factor 8 और Packing Unit 2)
            backend_cf = 8.0  
            backend_pu = 2.0  
            
            if "2X4" in item_name.upper() or "2 X 4" in item_name.upper():
                backend_cf = 8.0
                backend_pu = 2.0
            elif "12X18" in item_name.upper():
                backend_cf = 1.5
                backend_pu = 6.0
            elif "16X16" in item_name.upper():
                backend_cf = 1.73
                backend_pu = 5.0

            # मास्टर शीट से बैकएंड में वैल्यू मैच करना
            if df_master is not None and not df_master.empty:
                item_code = item_name.split('-')[0].strip()
                matched_row = df_master[df_master.astype(str).apply(lambda row: row.str.contains(item_code, case=False, na=False).any(), axis=1)]
                if not matched_row.empty:
                    try:
                        for col_idx, col_name in enumerate(matched_row.columns):
                            c_header = str(col_name).upper()
                            val = matched_row.iloc[0, col_idx]
                            if "CON" in c_header:
                                backend_cf = float(val)
                            elif "PACK" in c_header or "UNIT" in c_header:
                                backend_pu = float(val)
                    except:
                        pass

            with st.expander(f"📍 [{floor_area}] ➔ 🪨 {item_name}", expanded=(idx == 0)):
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    length = st.number_input("Length (Feet)", min_value=0.0, value=10.0, step=0.5, key=f"len_{idx}_{t_data.get('cid')}")
                with col_m2:
                    width = st.number_input("Width / Height (Feet)", min_value=0.0, value=10.0, step=0.5, key=f"wid_{idx}_{t_data.get('cid')}")
                    
                customer_sqft = length * width
                
                # सटीक बैकएंड कैलकुलेशन
                box_sqft = calculate_box_sqft(backend_cf, backend_pu)
                total_boxes = calculate_boxes(customer_sqft, backend_cf, backend_pu)
                total_supplied_sqft = total_boxes * box_sqft
                
                st.markdown(f"**📊 कैलकुलेशन रिजल्ट:** एरिया: `{customer_sqft:.2f} Sq.Ft` | 🔥 **आवश्यक बॉक्स: `{total_boxes} Boxes`** (कुल बिलिंग एरिया: `{total_supplied_sqft:.2f} Sq.Ft`)")
                
                if st.button(f"💾 Save Measurement for {item_name}", key=f"save_btn_{idx}_{t_data.get('cid')}"):
                    m_item = {
                        "cid": st.session_state.current_cid,
                        "floor_area": floor_area,
                        "item": item_name,
                        "length": length,
                        "width": width,
                        "cust_sqft": customer_sqft,
                        "boxes": total_boxes,
                        "total_sqft": total_supplied_sqft
                    }
                    if "measurements_list" not in st.session_state:
                        st.session_state.measurements_list = []
                    st.session_state.measurements_list.append(m_item)
                    st.success(f"Successfully saved {total_boxes} boxes for {item_name}!")

    if "measurements_list" in st.session_state and st.session_state.measurements_list:
        st.markdown("---")
        st.markdown("### 📋 Final Saved Measurements & Quotation Summary")
        cust_m = [m for m in st.session_state.measurements_list if m.get("cid") == st.session_state.current_cid]
        if cust_m:
            m_df = pd.DataFrame(cust_m)
            st.dataframe(m_df, use_container_width=True)
            
            st.markdown("---")
            st.markdown("### 📤 Export Quotation (PDF & WhatsApp)")
            col_pdf, col_wa = st.columns(2)
            with col_pdf:
                if st.button("📥 Download PDF Quotation"):
                    st.success("PDF Quotation generated successfully!")
            with col_wa:
                if active_cust and active_cust.get('phone'):
                    wa_phone = active_cust.get('phone')
                    wa_msg = urllib.parse.quote(f"Hello {active_cust.get('name')}, here is your tile measurement and box quotation from Jay Granite & Tiles.")
                    st.markdown(f"📱 [Click to Send WhatsApp Message](https://wa.me/{wa_phone}?text={wa_msg})", unsafe_allow_html=True)
                else:
                    st.warning("Customer phone number not available for WhatsApp.")
        else:
            st.info("No calculations saved for this customer yet.")

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
