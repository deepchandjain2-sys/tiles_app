import json
import math
import os
import urllib.parse
from datetime import datetime
import pandas as pd
import streamlit as st
from database import (
    load_customers_from_disk,
    load_stock_from_disk,
    load_stock_from_upload,
    save_customers_to_disk,
    save_json_file,
)
from fpdf import FPDF

st.set_page_config(
    page_title="Jay Granite & Tiles Hub", page_icon="🧱", layout="wide"
)

# --- CONSTANTS & FILE PATHS ---
STOCK_FILE = "stock_data.json"
CUSTOMERS_FILE = "customers_data.json"
MEASUREMENTS_FILE = "measurements_data.json"
USERS_FILE = "users_data.json"
SELECTIONS_FILE = "selections_data.json"

# --- HELPER FUNCTIONS ---


def load_json_file(filepath, default=None):
  if default is None:
    default = []
  if os.path.exists(filepath):
    try:
      with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
    except:
      return default
  return default


def clean_item_name(name):
  if not name:
    return ""
  return str(name).split(" - Size:")[0].strip()


# Initialize Session States
if "users_db" not in st.session_state:
  loaded_users = load_json_file(USERS_FILE, default={})
  if not loaded_users:
    loaded_users = {
        "admin": {"password": "admin123", "role": "Admin", "location": "All"},
        "deepchand jain": {
            "password": "123",
            "role": "Admin",
            "location": "All",
        },
    }
  st.session_state.users_db = loaded_users

if "logged_in" not in st.session_state:
  st.session_state.logged_in = False
  st.session_state.username = ""
  st.session_state.role = ""

if "measurements_list" not in st.session_state:
  st.session_state.measurements_list = load_json_file(
      MEASUREMENTS_FILE, default=[]
  )


# --- AUTHENTICATION FLOW ---
if not st.session_state.logged_in:
  st.title("🧱 Jay Granite & Tiles Hub")
  st.subheader("🔑 Login / Access Portal")

  with st.form("login_form"):
    u_name = st.text_input("Username").strip().lower()
    u_pass = st.text_input("Password", type="password")
    submit_login = st.form_submit_button("Login")

    if submit_login:
      if (
          u_name in st.session_state.users_db
          and st.session_state.users_db[u_name]["password"] == u_pass
      ):
        st.session_state.logged_in = True
        st.session_state.username = u_name
        st.session_state.role = st.session_state.users_db[u_name]["role"]
        st.success("Login Successful!")
        st.rerun()
      else:
        st.error("Invalid Username or Password")

else:
  # --- MAIN APP INTERFACE ---
  st.sidebar.title("Jay Granite & Tiles")
  st.sidebar.text(
      f"User: {st.session_state.username.title()} ({st.session_state.role})"
  )

  menu = st.sidebar.radio(
      "Navigation Flow",
      [
          "1 Customer Registration",
          "2 Tiles Selection (Area-Wise)",
          "3 Measurements, PDF & WhatsApp",
          "4 Sales Dashboard & History",
          "5 Salesman Progress Report",
      ],
  )

  if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

  # --- SECTION 3: MEASUREMENTS, PDF & WHATSAPP ---
  if menu == "3 Measurements, PDF & WhatsApp":
    st.header("📐 Measurements & Quotation Summary")

    selections = load_json_file(SELECTIONS_FILE, default=[])

    if selections:
      st.write(
          "Aapke selected items yahan hain. Area-wise sq.ft daal kar save"
          " karein:"
      )

      for idx, t_data in enumerate(selections):
        floor_area = t_data.get("area", "General Area")
        item_name = clean_item_name(t_data.get("item_name", "Tile"))
        con_factor = t_data.get("con_factor", 1.0)
        box_coverage = t_data.get("box_coverage", 1.0)
        packing_unit = t_data.get("packing_unit", 1.0)

        with st.expander(
            f"📍 Area: {floor_area} ➔ Item: {item_name}", expanded=(idx == 0)
        ):
          col_i1, col_i2 = st.columns([2, 1])
          with col_i1:
            st.markdown(f"**Item:** {item_name}")
            st.markdown(f"**Design Area:** {floor_area}")
            st.caption(
                f"[Size Config] Con Factor: {con_factor} | Packing Unit:"
                f" {packing_unit}"
            )
          with col_i2:
            customer_sqft = st.number_input(
                "Enter Sq.Ft",
                min_value=0.0,
                value=100.0,
                step=5.0,
                key=f"sqft_{t_data.get('cid', idx)}",
            )

          total_boxes = math.ceil(customer_sqft / box_coverage) if box_coverage > 0 else 0
          st.markdown(
              f"📦 **1 Box Coverage:** {box_coverage:.2f} Sq.Ft | 🔥"
              f" **Required Boxes:** {total_boxes} Boxes | 📐 **Input Sq.Ft:**"
              f" **{customer_sqft} Sq.Ft**"
          )

          if st.button(
              "💾 Save Item Quotation", key=f"save_btn_{t_data.get('cid', idx)}"
          ):
            m_item = {
                "cid": t_data.get("cid", str(idx)),
                "area_design": floor_area,
                "item_name": item_name,
                "sqft": customer_sqft,
                "boxes": total_boxes,
                "total_sqft": customer_sqft,
            }
            if "measurements_list" not in st.session_state:
              st.session_state.measurements_list = []
            
            st.session_state.measurements_list.append(m_item)
            save_json_file(MEASUREMENTS_FILE, st.session_state.measurements_list)

            updated_selections = [
                s for s in selections if s.get("cid") != t_data.get("cid")
            ]
            save_json_file(SELECTIONS_FILE, updated_selections)

            st.success(
                f"Saved: {total_boxes} Boxes for {item_name} ({customer_sqft}"
                " Sq.Ft)"
            )
            st.rerun()

    st.markdown("---")
    st.markdown("### 📋 Final Saved Quotation Summary")

    saved_items = st.session_state.get("measurements_list", [])
    if saved_items:
      total_sqft_sum = sum(item.get("sqft", 0) for item in saved_items)
      total_boxes_sum = sum(item.get("boxes", 0) for item in saved_items)

      col_sum1, col_sum2 = st.columns([3, 1])
      with col_sum1:
        st.markdown(
            f"📐 **Total Area:** `{total_sqft_sum:.1f} Sq.Ft` | 📦 **Total"
            f" Boxes:** `{total_boxes_sum} Boxes`"
        )
      with col_sum2:
        if st.button("🗑️ Reset All Saved Quotations"):
          st.session_state.measurements_list = []
          save_json_file(MEASUREMENTS_FILE, [])
          st.success("Cleared all quotations!")
          st.rerun()

      for m_idx, m_row in enumerate(saved_items):
        col_m1, col_m2, col_m3 = st.columns([4, 2, 1])
        with col_m1:
          st.text(
              f"📍 {m_row.get('area_design')} ➔ {m_row.get('item_name')}"
              f" ({m_row.get('sqft')} Sq.Ft / {m_row.get('boxes')} Boxes)"
          )
        with col_m3:
          if st.button("❌ Remove", key=f"rem_saved_{m_idx}"):
            saved_items.pop(m_idx)
            st.session_state.measurements_list = saved_items
            save_json_file(MEASUREMENTS_FILE, saved_items)
            st.rerun()
    else:
      st.info(
          "Abhi koi quotation save nahi ki gayi hai. Upar measurement daal kar"
          " save karein."
      )

  else:
    st.info(
        "Aap baaki sections (Customer Registration, Tiles Selection, etc.) par"
        " navigation menu se ja sakte hain."
    )
