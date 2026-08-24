import json
import os
import math
import urllib.parse
import pandas as pd
import streamlit as st
from calculations import calculate_boxes, calculate_box_sqft
from database import load_stock_from_upload

st.set_page_config(
    page_title="Jay Granite & Tiles Hub", page_icon="🪨", layout="wide"
)

USERS_FILE = "users_db.json"
CUSTOMERS_FILE = "customers_db.json"
SALES_FILE = "sales_db.json"

def load_users_from_disk():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return json.load(f)
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

def load_customers_from_disk():
    if os.path.exists(CUSTOMERS_FILE):
        try:
            with open(CUSTOMERS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return [{"cid": "CUST-001", "name": "Vansh", "phone": "964444419", "city": "Hiriyur"}]

def save_customers_to_disk(cust_list):
    try:
        with open(CUSTOMERS_FILE, "w") as f:
            json.dump(cust_list, f)
    except:
        pass

# Initialize Session State
if "registered_users" not in st.session_state:
    st.session_state.registered_users = load_users_from_disk()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "current_user" not in st.session_state:
    st.session_state.current_user = None

if "customers" not in st.session_state:
    st.session_state.customers = load_customers_from_disk()

if "sales_history" not in st.session_state:
    st.session_state.sales_history = []

if "current_cid" not in st.session_state:
    if st.session_state.customers:
        st.session_state.current_cid = st.session_state.customers[0]["cid"]
    else:
        st.session_state.current_cid = "CUST-001"

if "my_selected_tiles" not in st.session_state:
    st.session_state.my_selected_tiles = []

# --- SIDEBAR ADVANCED LOGIN & NAVIGATION ---
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

# --- MAIN APP SECTIONS ---
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
            cust_options = {f"{c['name']} ({c['phone']} - {c['city']})": c['cid'] for c in st.session_state.customers}
            current_label = next((k for k, v in cust_options.items() if v == st.session_state.current_cid), None)
            selected_label = st.selectbox("Existing Customers", options=list(cust_options.keys()), index=list(cust_options.keys()).index(current_label) if current_label else 0)
            if selected_label:
                st.session_state.current_cid = cust_options[selected_label]
        else:
            st.warning("No customers registered yet.")

elif st.session_state.current_nav == "2 Tiles Selection (Area-Wise)":
    st.title("🪨 Tiles Selection (Area-Wise)")
    uploaded_file = st.file_uploader("Upload Item Master File", type=["csv", "xlsx", "xls"], key="master_uploader")
    df = None
    if uploaded_file is not None:
        df = load_stock_from_upload(uploaded_file)
        if df is not None:
            st.success(f"Successfully loaded {len(df)} items from uploaded file!")
    elif os.path.exists("ITEM MASTER.csv"):
        df = load_stock_from_upload("ITEM MASTER.csv")
        if df is not None:
            st.info(f"Auto-loaded {len(df)} items from default master file!")
    else:
        st.warning("Please upload or ensure 'ITEM MASTER.csv' is present.")

elif st.session_state.current_nav == "3 Measurements, PDF & WhatsApp":
    st.title("📐 Measurements, PDF & WhatsApp Quotation")
    st.info("Your measurement calculation, PDF generation, and WhatsApp sharing tools are active here.")

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
