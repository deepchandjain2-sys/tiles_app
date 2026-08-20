import streamlit as st
import pandas as pd
import math
from datetime import date

# 1. Page Config
st.set_page_config(
    page_title="Jay Granite & Tiles - Selection & Estimation",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main-title { font-size: 26px; font-weight: 700; color: #1e3a8a; margin-bottom: 0px; }
    .sub-title { font-size: 14px; color: #16a34a; font-weight: 600; margin-bottom: 20px; }
    .tile-card { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-bottom: 10px; }
    .summary-card { background-color: #eff6ff; border-left: 4px solid #2563eb; padding: 10px; border-radius: 4px; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

# 2. Google Sheet (BUSY STOCK) Direct CSV Loader
SHEET_ID = "https://docs.google.com/spreadsheets/d/14fY-SKjwx8sins1gSp6iR1C4_AOWCXb2an8c-UgKaPY/edit?gid=0#gid=0"
GOOGLE_SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

@st.cache_data(ttl=60)
def load_busy_stock():
    try:
        df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
        if df.empty:
            return pd.DataFrame()
            
        # Strip string columns
        df = df.dropna(how='all')
        
        # Identify columns dynamically
        cols = list(df.columns)
        id_col = cols[0]
        name_col = cols[1] if len(cols) > 1 else cols[0]
        con_col = cols[3] if len(cols) > 3 else (cols[2] if len(cols) > 2 else None)
        pack_col = cols[4] if len(cols) > 4 else (cols[3] if len(cols) > 3 else None)
        
        cleaned_data = []
        for _, row in df.iterrows():
            name = str(row[name_col]).strip() if pd.notna(row[name_col]) else ""
            if not name or name.lower() == "nan" or "item name" in name.lower():
                continue
            
            # Conversion factor
            try:
                con_factor = float(row[con_col]) if (con_col and pd.notna(row[con_col])) else 8.0
            except:
                con_factor = 8.0
                
            # Packing unit
            try:
                packing_unit = float(row[pack_col]) if (pack_col and pd.notna(row[pack_col])) else 2.0
            except:
                packing_unit = 2.0
                
            box_sqft = round(con_factor * packing_unit, 2)
            if box_sqft <= 0:
                box_sqft = 16.0
                
            cat = "Floor Tile"
            if "GRAN" in name.upper():
                cat = "Granite"
            elif "WALL" in name.upper() or "HL" in name.upper():
                cat = "Wall Tile"
                
            cleaned_data.append({
                "ITEM_ID": str(row[id_col]).strip() if pd.notna(row[id_col]) else "NA",
                "ITEM_NAME": name,
                "CON_FACTOR": con_factor,
                "PACKING_UNIT": int(packing_unit),
                "BOX_SQFT": box_sqft,
                "CATEGORY": cat
            })
            
        return pd.DataFrame(cleaned_data)
    except Exception as e:
        st.error(f"Google Sheet Fetch Error: {e}")
        return pd.DataFrame()

stock_df = load_busy_stock()

# 3. Session State
if "customer_name" not in st.session_state:
    st.session_state.customer_name = "Deepchand"
if "customer_mobile" not in st.session_state:
    st.session_state.customer_mobile = ""
if "customer_address" not in st.session_state:
    st.session_state.customer_address = ""

if "floors" not in st.session_state:
    st.session_state.floors = [
        {
            "floor_id": 1,
            "floor_name": "Ground Floor",
            "rooms": [
                {"room_id": 101, "name": "Hall", "length": 10.0, "width": 10.0, "skirting": 0.0, "selected_tile": None}
            ]
        }
    ]

# 4. Sidebar
with st.sidebar:
    st.header("👤 Customer Details")
    st.session_state.customer_name = st.text_input("Customer Name", value=st.session_state.customer_name)
    st.session_state.customer_mobile = st.text_input("Mobile Number", value=st.session_state.customer_mobile)
    st.session_state.customer_address = st.text_area("Site / Delivery Address", value=st.session_state.customer_address)
    st.write(f"**Date:** {date.today().strftime('%d-%b-%Y')}")
    
    st.markdown("---")
    if st.button("🔄 Refresh BUSY Stock", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# 5. Header & Tabs
st.markdown("<div class='main-title'>JAY GRANITE & TILES</div>", unsafe_allow_html=True)
st.markdown(f"<div class='sub-title'>● BUSY LIVE ({len(stock_df)} ITEMS AVAILABLE)</div>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📐 1. Rooms & Tile Selection", "📄 2. Estimate Summary & Print"])

# TAB 1: MEASUREMENTS & SELECTION
with tab1:
    col_rooms, col_catalog = st.columns([1.3, 1.2], gap="large")
    
    with col_rooms:
        st.subheader("Room Measurements")
        
        if st.button("➕ Add New Floor", key="add_floor_btn"):
            new_fl_id = len(st.session_state.floors) + 1
            st.session_state.floors.append({
                "floor_id": new_fl_id,
                "floor_name": f"Floor {new_fl_id}",
                "rooms": [{"room_id": int(f"{new_fl_id}01"), "name": "Hall", "length": 12.0, "width": 10.0, "skirting": 4.0, "selected_tile": None}]
            })
            st.rerun()
            
        for f_idx, floor in enumerate(st.session_state.floors):
            with st.expander(f"🏢 {floor['floor_name']}", expanded=True):
                if st.button(f"➕ Add Room to {floor['floor_name']}", key=f"add_room_{floor['floor_id']}"):
                    new_r_id = int(f"{floor['floor_id']}{len(floor['rooms']) + 1}")
                    floor["rooms"].append({"room_id": new_r_id, "name": f"Room {len(floor['rooms']) + 1}", "length": 10.0, "width": 10.0, "skirting": 4.0, "selected_tile": None})
                    st.rerun()
                
                for r_idx, room in enumerate(floor["rooms"]):
                    st.markdown(f"**Room #{r_idx+1}**")
                    c_name, c_len, c_wid, c_skirt, c_del = st.columns([1.5, 1, 1, 1, 0.5])
                    
                    room["name"] = c_name.selectbox(
                        "Type", 
                        ["Hall", "Living Room", "Master Bedroom", "Kitchen", "Bathroom", "Balcony", "Parking", "Custom"],
                        index=["Hall", "Living Room", "Master Bedroom", "Kitchen", "Bathroom", "Balcony", "Parking", "Custom"].index(room["name"]) if room["name"] in ["Hall", "Living Room", "Master Bedroom", "Kitchen", "Bathroom", "Balcony", "Parking"] else 7,
                        key=f"name_{room['room_id']}"
                    )
                    room["length"] = c_len.number_input("Length (ft)", value=float(room["length"]), step=0.5, key=f"len_{room['room_id']}")
                    room["width"] = c_wid.number_input("Width (ft)", value=float(room["width"]), step=0.5, key=f"wid_{room['room_id']}")
                    room["skirting"] = c_skirt.number_input("Skirt (in)", value=float(room["skirting"]), step=1.0, key=f"sk_{room['room_id']}")
                    
                    if c_del.button("❌", key=f"del_{room['room_id']}"):
                        floor["rooms"].pop(r_idx)
                        st.rerun()
                    
                    floor_area = room["length"] * room["width"]
                    skirting_area = 2 * (room["length"] + room["width"]) * (room["skirting"] / 12.0)
                    total_sqft = floor_area + skirting_area
                    
                    if room["selected_tile"]:
                        tile = room["selected_tile"]
                        box_coverage = tile["BOX_SQFT"]
                        exact_boxes = total_sqft / box_coverage
                        req_boxes = math.ceil(exact_boxes)
                        total_covered_sqft = req_boxes * box_coverage
                        
                        st.markdown(f"""
                        <div class='summary-card'>
                            <b>Selected:</b> {tile['ITEM_NAME']}<br>
                            <b>Area:</b> {total_sqft:.1f} SqFt | <b>Required:</b> <span style='color:#2563eb; font-weight:bold;'>{req_boxes} Boxes</span> ({total_covered_sqft:.1f} SqFt) 
                            <small style='color:#64748b;'>[Exact: {exact_boxes:.2f} Boxes]</small>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.caption("👉 Select a tile from the Live Catalog on the right.")
                    
                    st.divider()

    with col_catalog:
        st.subheader("📦 Live Tile Catalog")
        
        if stock_df.empty:
            st.warning("⚠️ No items loaded. Check Google Sheet link or format.")
        else:
            search_query = st.text_input("🔍 Search Tile (e.g. 2X4, Varmora, Grey)", "")
            cat_filter = st.radio("Category", ["All", "Floor Tile", "Wall Tile", "Granite"], horizontal=True)
            
            filtered_df = stock_df.copy()
            if cat_filter != "All":
                filtered_df = filtered_df[filtered_df["CATEGORY"] == cat_filter]
            if search_query:
                filtered_df = filtered_df[filtered_df["ITEM_NAME"].str.contains(search_query, case=False, na=False) | filtered_df["ITEM_ID"].str.contains(search_query, case=False, na=False)]
                
            st.write(f"Showing **{len(filtered_df)}** items")
            
            all_rooms_flat = []
            for f in st.session_state.floors:
                for r in f["rooms"]:
                    all_rooms_flat.append((f"{f['floor_name']} - {r['name']} (ID: {r['room_id']})", r))
                    
            target_room_label = st.selectbox("Assign selected tile to:", [item[0] for item in all_rooms_flat])
            target_room_obj = next((item[1] for item in all_rooms_flat if item[0] == target_room_label), None)
            
            catalog_container = st.container(height=520)
            with catalog_container:
                for _, item in filtered_df.head(100).iterrows():
                    with st.container():
                        st.markdown(f"""
                        <div class='tile-card'>
                            <b>{item['ITEM_NAME']}</b><br>
                            <small style='color:#64748b;'>Code: {item['ITEM_ID']} | Box Coverage: <b>{item['BOX_SQFT']} SqFt</b> ({item['PACKING_UNIT']} Pcs/Box)</small><br>
                            <small style='color:#16a34a; font-weight:600;'>● Available</small>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"Assign to {target_room_obj['name'] if target_room_obj else 'Room'}", key=f"assign_{item['ITEM_ID']}_{target_room_obj['room_id'] if target_room_obj else 0}"):
                            if target_room_obj:
                                target_room_obj["selected_tile"] = item.to_dict()
                                st.rerun()

# TAB 2: SUMMARY & PRINT
with tab2:
    st.subheader("📄 Tile Requirement Estimate Summary")
    
    st.write(f"**Customer:** {st.session_state.customer_name} | **Mobile:** {st.session_state.customer_mobile}")
    if st.session_state.customer_address:
        st.write(f"**Address:** {st.session_state.customer_address}")
    st.write(f"**Date:** {date.today().strftime('%d-%b-%Y')}")
    
    summary_rows = []
    total_estimated_boxes = 0
    total_estimated_sqft = 0.0
    
    for floor in st.session_state.floors:
        for room in floor["rooms"]:
            floor_area = room["length"] * room["width"]
            skirting_area = 2 * (room["length"] + room["width"]) * (room["skirting"] / 12.0)
            req_sqft = floor_area + skirting_area
            
            if room["selected_tile"]:
                tile = room["selected_tile"]
                box_sqft = tile["BOX_SQFT"]
                exact_boxes = req_sqft / box_sqft
                req_boxes = math.ceil(exact_boxes)
                covered_sqft = req_boxes * box_sqft
                
                total_estimated_boxes += req_boxes
                total_estimated_sqft += covered_sqft
                
                summary_rows.append({
                    "Floor / Room": f"{floor['floor_name']} - {room['name']}",
                    "Selected Tile": tile['ITEM_NAME'],
                    "Required Area (SqFt)": round(req_sqft, 1),
                    "Boxes Required": f"{req_boxes} Boxes ({exact_boxes:.2f})",
                    "Total Coverage (SqFt)": round(covered_sqft, 1)
                })
            else:
                summary_rows.append({
                    "Floor / Room": f"{floor['floor_name']} - {room['name']}",
                    "Selected Tile": "Not Selected",
                    "Required Area (SqFt)": round(req_sqft, 1),
                    "Boxes Required": "-",
                    "Total Coverage (SqFt)": "-"
                })
                
    if summary_rows:
        summary_df = pd.DataFrame(summary_rows)
        st.table(summary_df)
        
        st.markdown(f"""
        ### Total Requirement: **{total_estimated_boxes} Boxes** ({total_estimated_sqft:.1f} SqFt)
        """)
        
    st.info("💡 **Print Tip:** ब्राउज़र में `Ctrl + P` दबाकर इसे सीधे PDF या प्रिंटर पर प्रिंट कर सकते हैं।")
