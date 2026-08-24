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

# Persistent JSON files for Users and Customers sync across devices/sessions
USERS_FILE = "users_db.json"
CUSJOMERS_FILE = "customers_db.json"


def load_users_from_disk():
  if os.path.exists(USERS_FILE):
    try:
      with open(USERS_FILE, "r") as f:
        return json.load(f)
    except:
      pass
  return [
      {"username": "admin", "pin": "1234", "name": "Deepchand Jain", "role": "Admin"}
  ]


def save_users_to_disk(users_list):
  try:
    with open(USERS_FILE, "w") as f:
      json.dump(users_list, f)
  except:
      pass


def load_customers_from_disk():
  if os.path.exists(CUSJOMERS_FILE):
    try:
      with open(CUSJOMERS_FILE, "r") as f:
        return json.load(f)
    except:
      pass
  return [
      {
          "cid": "CUST-001",
          "name": "Vansh",
          "phone": "964444419",
          "city": "Hiriyur",
      }
  ]


def save_customers_to_disk(cust_list):
  try:
    with open(CUSJOMERS_FILE, "w") as f:
      json.dump(cust_list, f)
  except:
      pass


# Initialize session state safely
if "stock_df" not in st.session_state:
  st.session_state.stock_df = load_stock_from_upload(None)

if "my_selected_tiles" not in st.session_state:
  st.session_state.my_selected_tiles = []

if "registered_users" not in st.session_state:
  st.session_state.registered_users = load_users_from_disk()

if "customers" not in st.session_state:
  st.session_state.customers = load_customers_from_disk()

if "sales_history" not in st.session_state:
  st.session_state.sales_history = []

if "logged_in" not in st.session_state:
  st.session_state.logged_in = False

if "current_user" not in st.session_state:
  st.session_state.current_user = None

if "current_nav" not in st.session_state:
  st.session_state.current_nav = "2 Tiles Selection (Area-Wise)"

if "current_cid" not in st.session_state:
  if st.session_state.customers:
    st.session_state.current_cid = st.session_state.customers[0]["cid"]
  else:
    st.session_state.current_cid = "CUST-001"

# Sidebar Navigation
st.sidebar.title("🪨 Jay Granite & Tiles")

if st.session_state.logged_in:
  user_display = (
      f"{st.session_state.current_user.get('name', 'User')} "
      f"({st.session_state.current_user.get('role', 'Staff')})"
  )
  st.sidebar.markdown(f"👤 **User:** {user_display}")
  st.sidebar.markdown("---")
  st.sidebar.markdown("### Navigation Flow")

  nav_options = [
      "1 Customer Registration",
      "2 Tiles Selection (Area-Wise)",
      "3 Measurements, PDF & WhatsApp",
      "4 Sales Dashboard & History",
  ]

  current_index = 1
  if st.session_state.current_nav in nav_options:
    current_index = nav_options.index(st.session_state.current_nav)

  selected_nav = st.sidebar.radio(
      "Go to section", nav_options, index=current_index, label_visibility="collapsed"
  )
  st.session_state.current_nav = selected_nav

  st.sidebar.markdown("---")
  if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.current_user = None
    st.rerun()

else:
  st.sidebar.markdown("### Login / Access")
  username_input = st.sidebar.text_input("Username")
  pin_input = st.sidebar.text_input("PIN / Password", type="password")

 # Initialize session state safely
if "stock_df" not in st.session_state:
  st.session_state.stock_df = load_stock_from_upload(None)

if "my_selected_tiles" not in st.session_state:
  st.session_state.my_selected_tiles = []

if "registered_users" not in st.session_state:
  st.session_state.registered_users = load_users_from_disk()

if "customers" not in st.session_state:
  st.session_state.customers = load_customers_from_disk()

if "sales_history" not in st.session_state:
  st.session_state.sales_history = []

if "logged_in" not in st.session_state:
  st.session_state.logged_in = False

if "current_user" not in st.session_state:
  st.session_state.current_user = None

if "current_nav" not in st.session_state:
  st.session_state.current_nav = "2 Tiles Selection (Area-Wise)"

if "current_cid" not in st.session_state:
  if st.session_state.customers:
    st.session_state.current_cid = st.session_state.customers[0]["cid"]
  else:
    st.session_state.current_cid = "CUST-001"

# Main Page Routing
if not st.session_state.logged_in:
  st.title("🪨 Jay Granite & Tiles Hub")
  st.info("Please login from the sidebar to access the application.")
  st.stop()


# Section 1: Customer Registration
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
          cust_obj = {
              "cid": new_cid,
              "name": c_name.strip(),
              "phone": c_phone.strip(),
              "city": c_city.strip(),
          }
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
      cust_options = {
          f"{c['name']} ({c['phone']} - {c['city']})": c["cid"]
          for c in st.session_state.customers
      }
      current_label = None
      for label, cid in cust_options.items():
        if cid == st.session_state.current_cid:
          current_label = label
          break

      selected_label = st.selectbox(
          "Existing Customers",
          options=list(cust_options.keys()),
          index=(
              list(cust_options.keys()).index(current_label)
              if current_label
              else 0
          ),
      )
      if selected_label:
        st.session_state.current_cid = cust_options[selected_label]

      active_c = next(
          (
              c
              for c in st.session_state.customers
              if c["cid"] == st.session_state.current_cid
          ),
          None,
      )
      if active_c:
        st.markdown(
            f"**Active Customer Details:**\n- **Name:** {active_c['name']}\n-"
            f" **Phone:** {active_c['phone']}\n- **City:** {active_c['city']}"
        )
    else:
      st.warning("No customers registered yet.")

  st.markdown("---")
  if st.button("Proceed to Tiles Selection ➔"):
    st.session_state.current_nav = "2 Tiles Selection (Area-Wise)"
    st.rerun()


# Section 2: Tiles Selection (Area-Wise)
elif st.session_state.current_nav == "2 Tiles Selection (Area-Wise)":
  cid = st.session_state.get(
      "current_cid",
      st.session_state.customers[0]["cid"] if st.session_state.customers else "",
  )
  current_cust = next(
      (
          c
          for c in st.session_state.customers
          if c["cid"] == cid
      ),
      {"name": "Unknown", "phone": "", "city": "Hiriyur"},
  )

  st.markdown(
      f"### 👤 Active Customer: **{current_cust['name']}** | 📞 Phone:"
      f" **{current_cust.get('phone', 'N/A')}** | 📍 City:"
      f" **{current_cust.get('city', 'Hiriyur')}**"
  )
  st.markdown("---")

  st.subheader("📁 Upload Master (CSV / Excel)")
  uploaded_file = st.file_uploader(
      "Upload Item Master File",
      type=["csv", "xlsx", "xls"],
      key="master_uploader",
  )

  df = None
  default_master_path = "ITEM MASTER.csv"

  if uploaded_file is not None:
    df = load_stock_from_upload(uploaded_file)
    if df is not None:
      st.success(f"Successfully loaded {len(df)} items from uploaded file!")
  elif os.path.exists(default_master_path):
    try:
      df = load_stock_from_upload(default_master_path)
      if df is not None:
        st.info(f"Auto-loaded {len(df)} items from default master file!")
    except Exception as e:
      st.error(f"Error reading default master file: {e}")
  else:
    st.warning("Please upload or ensure 'ITEM MASTER.csv' is present.")

  if df is not None:
    st.markdown("---")
    st.success("Master data ready for tile selection.")
