import streamlit as st
import pandas as pd
import os
import math
import urllib.parse
import json
from calculations import calculate_boxes, calculate_box_sqft
from database import load_stock_from_upload, save_stock_to_disk, load_items_from_disk, save_items_to_disk

st.set_page_config(page_title="Jay Granite & Tiles Hub", page_icon="🏢", layout="wide")

# Persistent JSON files for Users and Customers sync across devices/sessions
USERS_FILE = "users_db.json"
CUSTOMERS_FILE = "customers_db.json"

def load_users_from_disk():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"admin": {"password": "123", "role": "Admin", "name": "Jayantilal"}}

def save_users_to_disk(users_dict):
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(users_dict, f)
    except:
        pass

def load_customers_from_disk():
    if os.path.exists(CUSTOMERS_FILE):
        try:
            with open(CUSTOMERS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return []

def save_customers_to_disk(cust_list):
    try:
        with open(CUSTOMERS_FILE, "w") as f:
            json.dump(cust_list, f)
    except:
        pass

# Initialize session state from disk
if "stock_df" not in st.session_state:
    st.session_state.stock_df = load_stock_from_upload(None)

if "my_selected_tiles" not in st.session_state:
    st.session_state.my_selected_tiles = load_items_from_disk()

if "registered_users" not in st.session_state:
    st.session_state.registered_users = load_users_from_disk()

if "customers" not in st.session_state:
    st.session_state.customers = load_customers_from_disk()

if "sales_history" not in st.session_state:
    st.session_state.sales_history = []

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "current_nav" not in st.session_state:
    st.session_state.current_nav = "1 Customer Registration"

# --- AUTHENTICATION SCREEN ---
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>🏢 Jay Granite & Tiles Hub - Portal</h2>", unsafe_allow_html=True)
    
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        auth_tab1, auth_tab2, auth_tab3 = st.tabs(["🔐 Login", "📝 New User Register", "🔄 Forgot Password"])
        
        with auth_tab1:
            with st.form("login_form"):
                l_user = st.text_input("User ID (Text / Number)", key="l_user")
                l_pass = st.text_input("Password", type="password", key="l_pass")
                l_btn = st.form_submit_button("Login", type="primary")
                
                if l_btn:
                    clean_user = l_user.strip().lower()
                    # Refresh users from disk in case registered elsewhere
                    st.session_state.registered_users = load_users_from_disk()
                    if clean_user in st.session_state.registered_users:
                        if st.session_state.registered_users[clean_user]["password"] == l_pass.strip():
                            st.session_state.logged_in = True
                            st.session_state.username = st.session_state.registered_users[clean_user]["name"]
                            st.session_state.user_role = st.session_state.registered_users[clean_user]["role"]
                            st.session_state.current_nav = "1 Customer Registration"
                            st.success("Login Successful!")
                            st.rerun()
                        else:
                            st.error("Incorrect Password!")
                    else:
                        st.error("User ID not found! Please register first.")
                        
        with auth_tab2:
            with st.form("register_form"):
                r_name = st.text_input("Full Name")
                r_user = st.text_input("Choose User ID (Text / Number)")
                r_pass = st.text_input("Choose Password", type="password")
                r_role = st.selectbox("Select Role", ["Admin", "Salesman"])
                r_btn = st.form_submit_button("Register Account", type="primary")
                
                if r_btn:
                    clean_r_user = r_user.strip().lower()
                    st.session_state.registered_users = load_users_from_disk()
                    if clean_r_user and r_pass.strip() and r_name.strip():
                        if clean_r_user in st.session_state.registered_users:
                            st.warning("User ID already exists! Choose another ID.")
                        else:
                            st.session_state.registered_users[clean_r_user] = {
                                "password": r_pass.strip(),
                                "role": r_role,
                                "name": r_name.strip()
                            }
                            save_users_to_disk(st.session_state.registered_users)
                            st.success("Registration successful! Now go to Login tab and sign in.")
                    else:
                        st.error("Please fill all fields correctly.")
                        
        with auth_tab3:
            with st.form("forgot_form"):
                f_user = st.text_input("Enter your User ID")
                f_new_pass = st.text_input("Enter New Password", type="password")
                f_btn = st.form_submit_button("Reset Password", type="primary")
                
                if f_btn:
                    clean_f_user = f_user.strip().lower()
                    st.session_state.registered_users = load_users_from_disk()
                    if clean_f_user in st.session_state.registered_users:
                        if f_new_pass.strip():
                            st.session_state.registered_users[clean_f_user]["password"] = f_new_pass.strip()
                            save_users_to_disk(st.session_state.registered_users)
                            st.success("Password updated successfully! You can login now.")
                        else:
                            st.error("Please enter a new password.")
                    else:
                        st.error("User ID does not exist.")
    st.stop()

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("🏢 Jay Granite & Tiles")
st.sidebar.markdown(f"👤 **User:** {st.session_state.get('username', 'User')} ({st.session_state.get('user_role', 'Staff')})")

nav_options = [
    "1 Customer Registration",
    "2 Tiles Selection (Area-Wise)",
    "3 Measurements, PDF & WhatsApp",
    "4 Sales Dashboard & History"
]

selected_menu = st.sidebar.radio("Navigation Flow", nav_options, index=nav_options.index(st.session_state.current_nav) if st.session_state.current_nav in nav_options else 0)
st.session_state.current_nav = selected_menu

if st.sidebar.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.session_state.current_nav = "1 Customer Registration"
    st.rerun()

# --- 1. CUSTOMER REGISTRATION ---
if st.session_state.current_nav == "1 Customer Registration":
    st.header("👤 Customer Registration")
    
    # Reload customers from disk to sync across devices
    st.session_state.customers = load_customers_from_disk()
    
    with st.form("customer_form"):
        col1, col2 = st.columns(2)
        with col1:
            cust_name = st.text_input("Customer Name")
            cust_phone = st.text_input("Phone Number")
        with col2:
            cust_city = st.text_input("City / Location", value="Hiriyur")
            cust_gst = st.text_input("GSTIN (Optional)")
            
        submitted = st.form_submit_button("Register & Proceed to Tiles Selection", type="primary")
        if submitted:
            if cust_name.strip():
                new_cid = len(st.session_state.customers) + 1
                cust_data = {
                    "cid": new_cid,
                    "name": cust_name,
                    "phone": cust_phone,
                    "city": cust_city,
                    "gst": cust_gst,
                    "salesman": st.session_state.get('username', 'Admin'),
                    "status": "Registered"
                }
                st.session_state.customers.append(cust_data)
                save_customers_to_disk(st.session_state.customers)
                st.session_state.current_cid = new_cid
                st.success(f"Customer {cust_name} registered successfully!")
                st.session_state.current_nav = "2 Tiles Selection (Area-Wise)"
                st.rerun()
            else:
                st.error("Please enter the customer name.")

    if st.session_state.customers:
        st.subheader("Select Existing Customer")
        c_options = {f"{c['cid']} - {c['name']} ({c['city']}) [Attended by: {c.get('salesman', 'Admin')}]": c['cid'] for c in st.session_state.customers}
        selected_c_label = st.selectbox("Registered Customers", list(c_options.keys()))
        if selected_c_label:
            st.session_state.current_cid = c_options[selected_c_label]
            col_go1, col_go2 = st.columns([1, 4])
            with col_go1:
                if st.button("➡️ Proceed to Selection"):
                    st.session_state.current_nav = "2 Tiles Selection (Area-Wise)"
                    st.rerun()

# --- 2. TILES SELECTION (AREA-WISE) ---
elif st.session_state.current_nav == "2 Tiles Selection (Area-Wise)":
    st.header("🏠 Tiles Selection (Area-Wise)")
    
    st.session_state.customers = load_customers_from_disk()
    if not st.session_state.customers:
        st.warning("Please register a customer first.")
        if st.button("Go to Customer Registration"):
            st.session_state.current_nav = "1 Customer Registration"
            st.rerun()
    else:
        cid = st.session_state.get("current_cid", st.session_state.customers[0]["cid"])
        current_cust = next((c for c in st.session_state.customers if c['cid'] == cid), {"name": "Unknown", "phone": "", "city": ""})
        
        st.markdown(f"### 👤 Active Customer: **{current_cust['name']}** | 📞 Phone: **{current_cust.get('phone', 'N/A')}** | 📍 City: **{current_cust.get('city', '')}**")
        st.markdown("---")
        
        st.subheader("📁 Upload Master (CSV / Excel)")
        uploaded_file = st.file_uploader("Upload Item Master File", type=["csv", "xlsx", "xls"], key="master_uploader")
        
        if uploaded_file is not None:
            df = load_stock_from_upload(uploaded_file)
            if df is not None:
                try:
                    records = []
                    for _, row in df.iterrows():
                        name = str(row.iloc[1]).strip() if len(row) > 1 and pd.notna(row.iloc[1]) else ""
                        if not name or name.lower() == "nan" or "item name" in name.lower():
                            continue
                        try:
                            con_val = abs(float(row.iloc[8])) if len(row) > 8 and pd.notna(row.iloc[8]) else 1.5
                        except:
                            con_val = 1.5
                        try:
                            pack_val = abs(float(row.iloc[9])) if len(row) > 9 and pd.notna(row.iloc[9]) else 6.0
                        except:
                            pack_val = 6.0
                        
                        box_sqft = con_val * pack_val
                        records.append({
                            "ITEM_ID": str(row.iloc[0]).strip() if len(row) > 0 and pd.notna(row.iloc[0]) else "NA",
                            "ITEM_NAME": name,
                            "CON_FACTOR": con_val,
                            "PACKING_UNIT": int(pack_val),
                            "BOX_SQFT": box_sqft
                        })
                    st.session_state.stock_df = pd.DataFrame(records)
                    save_stock_to_disk(st.session_state.stock_df)
                    st.success(f"Successfully loaded {len(records)} items!")
                except Exception as e:
                    st.error(f"Error processing records: {e}")

        if (st.session_state.stock_df is None or st.session_state.stock_df.empty):
            disk_stock = load_stock_from_upload(None)
            if disk_stock is not None and not disk_stock.empty:
                st.session_state.stock_df = disk_stock

        stock_df = st.session_state.stock_df
        if stock_df is None or stock_df.empty:
            st.info("Please upload your Item Master file above.")
        else:
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                floor_name = st.selectbox("Select Floor", ["Ground Floor", "First Floor", "Second Floor", "Elevation", "Other"])
            with col_f2:
                section_type = st.selectbox("Section Type", ["Floor Area", "Wall Area", "Skirting", "Border", "Highlight"])
            with col_f3:
                predefined_areas = [
                    "Hall", "Kitchen", "Master Bedroom", 
                    "Common Bedroom Attach Bathroom", "Common Bathroom", "Parking"
                ]
                area_choice = st.selectbox("Select Area Name", predefined_areas + ["Other (Type Manually)"])
                if area_choice == "Other (Type Manually)":
                    area_name = st.text_input("Enter Custom Area Name")
                else:
                    area_name = area_choice

            search_query = st.text_input("🔍 Search Tile Code / Name from Stock:")
            filtered_stock = stock_df[stock_df["ITEM_NAME"].str.contains(search_query, case=False, na=False)] if search_query else stock_df
            
            tile_options = filtered_stock["ITEM_NAME"].tolist() if not filtered_stock.empty else ["No matching tiles found"]
            selected_tile = st.selectbox("Select Tile", tile_options)

            if st.button("➕ Add This Tile Selection", type="primary"):
                if selected_tile and selected_tile != "No matching tiles found" and str(area_name).strip():
                    if "my_selected_tiles" not in st.session_state or not isinstance(st.session_state.my_selected_tiles, list):
                        st.session_state.my_selected_tiles = []
                    
                    t_obj = filtered_stock[filtered_stock["ITEM_NAME"] == selected_tile].iloc[0]
                    c_factor = float(t_obj.get("CON_FACTOR", 1.5))
                    p_unit = float(t_obj.get("PACKING_UNIT", 6.0))
                    
                    new_item = {
                        "cid": int(cid),
                        "floor": str(floor_name),
                        "section": str(section_type),
                        "area": str(area_name).strip(),
                        "tile": str(selected_tile),
                        "con_factor": c_factor,
                        "packing_unit": p_unit,
                        "sqft": 100.0,
                        "boxes": math.ceil(100.0 / (c_factor * p_unit)) if (c_factor * p_unit) > 0 else 0
                    }
                    st.session_state.my_selected_tiles.append(new_item)
                    save_items_to_disk(st.session_state.my_selected_tiles)
                    
                    for c in st.session_state.customers:
                        if c['cid'] == cid:
                            c['status'] = 'Selected'
                    save_customers_to_disk(st.session_state.customers)
                            
                    st.success(f"Added {selected_tile} for {area_name} successfully!")
                    st.rerun()
                else:
                    st.error("Please enter/select a valid Area Name and Tile.")

            st.markdown("---")
            st.subheader("📋 Selected Items for this Customer")
            
            if "my_selected_tiles" not in st.session_state or not isinstance(st.session_state.my_selected_tiles, list):
                st.session_state.my_selected_tiles = []
                
            customer_items = [i for i in st.session_state.my_selected_tiles if isinstance(i, dict) and i.get("cid") == cid]
            
            if customer_items:
                item_to_remove = None
                for idx, i in enumerate(customer_items):
                    col_d1, col_d2 = st.columns([5, 1])
                    with col_d1:
                        st.markdown(f"🔹 **{i.get('floor')} - {i.get('area')} ({i.get('section')})**: `{i.get('tile')}`")
                    with col_d2:
                        if st.button("❌ Delete", key=f"del_sec2_{cid}_{idx}_{i.get('tile')}"):
                            item_to_remove = i
                
                if item_to_remove:
                    st.session_state.my_selected_tiles = [item for item in st.session_state.my_selected_tiles if item != item_to_remove]
                    save_items_to_disk(st.session_state.my_selected_tiles)
                    st.success("Item deleted successfully!")
                    st.rerun()
                    
                if st.button("🗑️ Clear All Selections"):
                    st.session_state.my_selected_tiles = [i for i in st.session_state.my_selected_tiles if not (isinstance(i, dict) and i.get("cid") == cid)]
                    save_items_to_disk(st.session_state.my_selected_tiles)
                    st.rerun()
                    
                st.markdown("---")
                if st.button("➡️ Proceed to Measurements", type="primary"):
                    st.session_state.current_nav = "3 Measurements, PDF & WhatsApp"
                    st.rerun()
            else:
                st.info("No tiles selected yet for this customer.")

# --- 3. MEASUREMENTS, PDF & WHATSAPP ---
elif st.session_state.current_nav == "3 Measurements, PDF & WhatsApp":
    st.header("📐 Measurements, PDF & WhatsApp")
    
    st.session_state.customers = load_customers_from_disk()
    if not st.session_state.customers:
        st.warning("Please register a customer first.")
    else:
        cid = st.session_state.get("current_cid", st.session_state.customers[0]["cid"])
        current_cust = next((c for c in st.session_state.customers if c['cid'] == cid), {"name": "Customer", "phone": ""})
        items = [i for i in st.session_state.get("my_selected_tiles", []) if isinstance(i, dict) and i.get("cid") == cid]
        
        if not items:
            st.info("No items selected for this customer yet. Go to step 2.")
        else:
            st.markdown(f"### 👤 Customer: **{current_cust['name']}** | 📞 Phone: **{current_cust.get('phone', 'N/A')}**")
            st.markdown("### Enter Actual Area (SqFt) for Each Selection:")
            total_boxes = 0
            item_to_delete = None
            
            for idx, it in enumerate(items):
                col_m1, col_m2, col_m3 = st.columns([2, 1, 0.5])
                with col_m1:
                    st.markdown(f"**{it.get('floor')} - {it.get('area')} ({it.get('section')})**<br>Tile: `{it.get('tile')}`", unsafe_allow_html=True)
                with col_m2:
                    it['sqft'] = st.number_input("Area in SqFt", value=float(it.get('sqft', 100.0)), key=f"sqft_{cid}_{idx}_{it.get('tile')}")
                with col_m3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("❌", key=f"del_sec3_{cid}_{idx}_{it.get('tile')}", help="Delete this item"):
                        item_to_delete = it
                
                cf = float(it.get('con_factor', 1.5))
                pu = float(it.get('packing_unit', 6.0))
                box_cov = cf * pu
                it['boxes'] = math.ceil(float(it['sqft']) / box_cov) if box_cov > 0 else 0
                
                total_boxes += it['boxes']
                st.caption(f"Required Boxes: **{it['boxes']} Boxes**")
                st.divider()
                
            if item_to_delete:
                st.session_state.my_selected_tiles = [item for item in st.session_state.my_selected_tiles if item != item_to_delete]
                save_items_to_disk(st.session_state.my_selected_tiles)
                st.success("Item deleted successfully!")
                st.rerun()
                
            st.markdown(f"### Total Material Required: **{total_boxes} Boxes**")
            
            summary_text = f"JAY GRANITE & TILES - QUOTATION\n" \
                           f"----------------------------------------\n" \
                           f"Customer Name: {current_cust['name']}\n" \
                           f"Phone: {current_cust.get('phone', '')}\n" \
                           f"City: {current_cust['city']}\n\n" \
                           f"Selected Items:\n"
            for it in items:
                summary_text += f"- {it.get('floor')} | {it.get('area')} ({it.get('section')}): {it.get('tile')} -> Area: {it.get('sqft')} SqFt -> Boxes: {it.get('boxes')}\n"
            summary_text += f"\nTotal Boxes Required: {total_boxes}\n" \
                           f"----------------------------------------"

            col_btn1, col_btn2, col_btn3 = st.columns(3)
            with col_btn1:
                st.download_button(
                    label="Download Quotation File",
                    data=summary_text,
                    file_name=f"Quotation_{current_cust['name']}.txt",
                    mime="text/plain",
                    type="primary"
                )
            with col_btn2:
                encoded_message = urllib.parse.quote(summary_text)
                whatsapp_url = f"https://wa.me/?text={encoded_message}"
                st.markdown(f'<a href="{whatsapp_url}" target="_blank"><button style="background-color:#25D366; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer; font-weight:bold; width:100%;">💬 WhatsApp</button></a>', unsafe_allow_html=True)
            with col_btn3:
                if st.button("✅ Finalize & Dashboard", type="primary"):
                    for c in st.session_state.customers:
                        if c['cid'] == cid:
                            c['status'] = 'Finalized'
                            c['total_boxes'] = total_boxes
                    save_customers_to_disk(st.session_state.customers)
                    
                    history_record = {
                        "customer": current_cust['name'],
                        "phone": current_cust.get('phone', ''),
                        "city": current_cust['city'],
                        "salesman": current_cust.get('salesman', 'Admin'),
                        "boxes": total_boxes,
                        "items_count": len(items)
                    }
                    st.session_state.sales_history.append(history_record)
                    st.success("Order Finalized Successfully!")
                    st.session_state.current_nav = "4 Sales Dashboard & History"
                    st.rerun()

# --- 4. SALES DASHBOARD & HISTORY ---
elif st.session_state.current_nav == "4 Sales Dashboard & History":
    st.header("📊 Professional Sales Dashboard & History")
    
    st.session_state.customers = load_customers_from_disk()
    customers_df = pd.DataFrame(st.session_state.customers) if st.session_state.customers else pd.DataFrame(columns=["cid", "name", "phone", "city", "status", "salesman"])
    
    total_new_customers = len(st.session_state.customers)
    total_selected = len(customers_df[customers_df['status'] == 'Selected']) if not customers_df.empty else 0
    total_finalized = len(customers_df[customers_df['status'] == 'Finalized']) if not customers_df.empty else 0
    
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("👥 Total New Customers", total_new_customers)
    kpi2.metric("📋 Tiles Selected", total_selected)
    kpi3.metric("✅ Orders Finalized", total_finalized)
    
    st.markdown("---")
    st.subheader("👨‍💼 Salesman Performance Analysis")
    
    if not customers_df.empty and 'salesman' in customers_df.columns:
        salesman_summary = customers_df.groupby('salesman').agg(
            Total_Attended=('name', 'count'),
            Finalized_Orders=('status', lambda x: (x == 'Finalized').sum())
        ).reset_index()
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.dataframe(salesman_summary, use_container_width=True)
        with col_g2:
            st.markdown("#### 📈 Salesman Performance Chart")
            st.bar_chart(salesman_summary.set_index('salesman')[['Total_Attended', 'Finalized_Orders']])
    else:
        st.info("No salesman activity data available yet.")
        
        st.markdown("---")
    st.subheader("📜 Detailed Customer History")
    if not customers_df.empty:
        st.dataframe(customers_df[['cid', 'name', 'phone', 'city', 'salesman', 'status']], use_container_width=True)
    else:
        st.info("No customer records found.")
