import streamlit as st
import pandas as pd
import math
import os
from database import get_all_customers, save_customer_to_db, delete_customer_from_db, get_all_admin_users

GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR4mWSP3s6r7UIwn-kcX8Ogev4yXWTMpMLvL87PGTR_UwxKjkcbU9NNxy__mbkyYplhDHxvsD2nKFvW/pub?gid=1816720040&single=true&output=csv"

@st.cache_data(ttl=0)
def load_catalog_from_google_sheet():
    try:
        df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
        df.columns = df.columns.str.strip().str.lower()
        
        rename_map = {}
        for col in df.columns:
            if 'name' in col or 'tile' in col:
                rename_map[col] = 'name'
            elif 'cat' in col:
                rename_map[col] = 'category'
            elif 'cov' in col or 'box' in col:
                rename_map[col] = 'box_cov'
            elif 'price' in col or 'rate' in col:
                rename_map[col] = 'price'
                
        df = df.rename(columns=rename_map)
        
        required_cols = ['name', 'category', 'box_cov', 'price']
        for rc in required_cols:
            if rc not in df.columns:
                df[rc] = 'Default' if rc in ['name', 'category'] else 0.0
                
        return df.to_dict(orient="records")
    except Exception as e:
        st.error(f"Google Sheet Error: {e}")
        return [
            {"name": "Glossy Vitrified Tile 600x600mm", "category": "Floor", "box_cov": 15.0, "price": 600.0}
        ]

CATALOG_ITEMS = load_catalog_from_google_sheet()

def calculate_tile_boxes(area_sqft, box_coverage_sqft):
    if box_coverage_sqft <= 0:
        return 0, 0
    boxes = math.ceil(area_sqft / box_coverage_sqft)
    return boxes, area_sqft

st.set_page_config(page_title="Tiles & BOQ Management App", layout="wide")

# App flow placeholder variables for navigation/state context
floor_level = st.selectbox("Select Room / Area", ["Hall", "Bedroom", "Kitchen", "Bathroom", "Balcony"])
app_type = st.selectbox("Category", ["Floor", "Wall"])
specific_area_name = st.text_input("Area Name", "Main Hall")

search_query = st.text_input("Search Tile by Name / Category", "")

filtered_catalog = []
for item in CATALOG_ITEMS:
    if search_query.lower() in str(item.get('name', '')).lower() or search_query.lower() in str(item.get('category', '')).lower():
        filtered_catalog.append(item)

if not filtered_catalog:
    filtered_catalog = CATALOG_ITEMS

tile_names = [item.get('name', 'Unknown') for item in filtered_catalog]
selected_tile_name = st.selectbox("Select Tile Item", tile_names)

chosen_tile = None
for t in filtered_catalog:
    if str(t.get('name', '')) == str(selected_tile_name):
        chosen_tile = t
        break

if not chosen_tile and CATALOG_ITEMS:
    chosen_tile = CATALOG_ITEMS[0]

default_box_cov = float(chosen_tile.get('box_cov', 15.0) if chosen_tile else 15.0)

st.write(f"**Selected Item Specs:** Coverage: {default_box_cov} sq.ft/box")

if st.button("Add Area & Tile to Queue", key="add_to_queue_btn"):
    entry = {
        "floor": floor_level,
        "category": app_type,
        "area": specific_area_name,
        "tile_name": selected_tile_name,
        "box_cov": default_box_cov,
        "sqft": 0.0,
        "boxes": 0,
        "total": 0.0
    }
    
    if "selections" not in st.session_state or st.session_state["selections"] is None:
        st.session_state["selections"] = []
    
    st.session_state["selections"].append(entry)
    st.success("Item added to queue successfully!")

if "selections" in st.session_state and st.session_state["selections"]:
    st.write("### Added Items in Queue:")
    for idx, item in enumerate(st.session_state["selections"]):
        q_num = idx + 1
        q_floor = str(item.get('floor', ''))
        q_area = str(item.get('area', ''))
        q_tile = str(item.get('tile_name', ''))
        q_cov = str(item.get('box_cov', 0.0))
        
        row_text = str(q_num) + ". " + q_floor + " -> " + q_area + " | " + q_tile + " (Coverage: " + q_cov + " sq.ft)"
        st.text(row_text)
