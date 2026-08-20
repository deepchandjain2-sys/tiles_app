import streamlit as st
import pandas as pd
import math
from datetime import date

# -------------------------------------------------------------
# 1. PAGE CONFIGURATION & STYLING
# -------------------------------------------------------------
st.set_page_config(
    page_title="Jay Granite & Tiles - Smart Selection & Estimation",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main-header { font-size: 26px; font-weight: 800; color: #1e3a8a; margin-bottom: 2px; }
    .sub-header { font-size: 14px; color: #16a34a; font-weight: 600; margin-bottom: 15px; }
    .tile-box { 
        background: #ffffff; 
        border: 1px solid #cbd5e1; 
        border-radius: 8px; 
        padding: 12px; 
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .selection-banner {
        background-color: #f0fdf4;
        border: 1px solid #86efac;
        padding: 10px;
        border-radius: 6px;
        margin-top: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 2. GOOGLE SHEET LIVE CSV CONNECTOR (BUSY STOCK)
# -------------------------------------------------------------
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/14lY-SKjwd9hins1gSp6lR1C4_AOWOx2an8c-UgKaPY/export?format=csv&gid=0"

@st.cache_data(ttl=60)
def fetch_busy_inventory():
    try:
        # Load raw sheet
        df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
        if df.empty:
            return pd.DataFrame()
        
        df = df.dropna(how='all')
        cols = list(df.columns)
        
        id_col = cols[0]
        name_col = cols[1] if len(cols) > 1 else cols[0]
        con_col = cols[3] if len(cols) > 3 else None
        pack_col = cols[4] if len(cols) > 4 else None

        records = []
        for _, row in df.iterrows():
            name = str(row[name_col]).strip() if pd.notna(row[name_col]) else ""
            if not name or name.lower() == "nan" or "item name" in name.lower():
                continue
            
            # Conversion factor
            try:
                con_val = float(row[con_col]) if (con_col and pd.notna(row[con_col])) else 8.0
            except:
                con_val = 8.0
                
            # Packing unit
            try:
                pack_val = float(row[pack_col]) if (pack_col and pd.notna(row[pack_col])) else 2.0
            except:
                pack_val = 2.0
                
            box_sqft = round(con_val * pack_val, 2)
            if box_sqft <= 0:
                box_sqft = 16.0
                
            category = "Floor Tile"
            if "GRAN" in name.upper():
                category = "Granite"
            elif "WALL" in name.upper() or "HL" in name.upper() or "12X18" in name.upper() or "10X15" in name.upper():
                category = "Wall Tile"
            elif "16X16" in name.upper() or "PARKING" in name.upper():
                category = "Parking Tile"
                
            records.append({
                "ITEM_ID": str(row[id_col]).strip() if pd.notna(row[id_col]) else "NA",
                "ITEM_NAME": name,
                "CON_FACTOR": con_val,
                "PACKING_UNIT": int(pack_val),
                "BOX_SQFT": box_sqft,
                "CATEGORY": category
            })
            
        return pd.DataFrame(records)
    except Exception as err:
        st.error(f"Google Sheet Fetch Error: {err}")
        return pd.DataFrame()

# -------------------------------------------------------------
# 3. LOGIN & SECURITY SESSION
# -------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def check_login(pin):
    # Default Quick PIN: 1234 or 2026
    if pin in ["1234", "2026"]:
        st.session_state.authenticated = True
        return True
    return False

if not st.session_state.authenticated:
    st.markdown("<div class='main-header'>🏢 JAY GRANITE & TILES</div>", unsafe_allow_html=True)
    st.caption("Staff & Sales Selection Portal")
    st.markdown("---")
    
    col1, col2, _ = st.columns([1, 1, 2])
    with col1:
        st.subheader("🔐 Staff Login")
        entered_pin = st.text_input("Enter Passcode / PIN", type="password", help="Default PIN: 1234")
        if st.button("Unlock System", type="primary", use_container_width=True):
            if check_login(entered_pin):
                st.success("Login Successful!")
                st.rerun()
            else:
                st.error("Invalid PIN. Please try again.")
    st.stop()

# -------------------------------------------------------------
# 4. INITIALIZE APP SESSION DATA
# -------------------------------------------------------------
stock_data = fetch_busy_inventory()

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
                {"room_id": 101, "name": "Hall", "length": 10.0, "width": 10.0, "skirting": 4.0, "selected_tile": None}
            ]
        }
    ]

# -------------------------------------------------------------
# 5. SIDEBAR
# -------------------------------------------------------------
with st.sidebar:
    st.markdown("### 👤 Customer Profile")
    st.session_state.customer_name = st.text_input("Customer Name", value=st.session_state.customer_name)
    st.session_state.customer_mobile = st.text_input("Mobile Number", value=st.session_state.customer_mobile)
    st.session_state.customer_address = st.text_area("Site / Delivery Address", value=st.session_state.customer_address)
    st.write(f"📅 **Date:** {date.today().strftime('%d-%b-%Y')}")
    
    st.markdown("---")
    if st.button("🔄 Refresh BUSY Live Stock", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    if st.button("🔒 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# -------------------------------------------------------------
# 6. MAIN NAVIGATION TABS
# -------------------------------------------------------------
st.markdown("<div class='main-header'>JAY GRANITE & TILES</div>", unsafe_allow_html=True)
st.markdown(f"<div class='sub-header'>● BUSY LIVE CONNECTED ({len(stock_data)} ITEMS IN STOCK)</div>", unsafe_allow_html=True)

tab_measure, tab_select, tab_summary = st.tabs([
    "📐 1. Room Measurements", 
    "🎨 2. Tiles Selection Catalog", 
    "📄 3. Estimate Summary & Print"
])

# -------------------------------------------------------------
# TAB 1: ROOM MEASUREMENTS
# -------------------------------------------------------------
with tab_measure:
    st.subheader("🏠 Site & Room Measurements")
    st.caption("Add floors, rooms, and enter dimensions in feet. Skirting height in inches.")
    
    if st.button("➕ Add New Floor", key="btn_add_floor"):
        new_fid = len(st.session_state.floors) + 1
        st.session_state.floors.append({
            "floor_id": new_fid,
            "floor_name": f"Floor {new_fid}",
            "rooms": [{"room_id": int(f"{new_fid}01"), "name": "Living Room", "length": 12.0, "width": 10.0, "skirting": 4.0, "selected_tile": None}]
        })
        st.rerun()
        
    for f_idx, fl in enumerate(st.session_state.floors):
        with st.expander(f"🏢 {fl['floor_name']}", expanded=True):
            if st.button(f"➕ Add Room to {fl['floor_name']}", key=f"add_room_btn_{fl['floor_id']}"):
                new_rid = int(f"{fl['floor_id']}{len(fl['rooms']) + 1}")
                fl["rooms"].append({"room_id": new_rid, "name": f"Room {len(fl['rooms']) + 1}", "length": 10.0, "width": 10.0, "skirting": 4.0, "selected_tile": None})
                st.rerun()
                
            for r_idx, rm in enumerate(fl["rooms"]):
                st.markdown(f"**Room #{r_idx+1}**")
                c1, c2, c3, c4, c5 = st.columns([1.5, 1, 1, 1, 0.4])
                
                room_types = ["Hall", "Living Room", "Master Bedroom", "Bedroom 2", "Kitchen", "Bathroom", "Balcony", "Parking", "Pooja Room", "Custom"]
                rm["name"] = c1.selectbox("Room Type", room_types, index=room_types.index(rm["name"]) if rm["name"] in room_types else 0, key=f"rname_{rm['room_id']}")
                rm["length"] = c2.number_input("Length (ft)", value=float(rm["length"]), step=0.5, key=f"rlen_{rm['room_id']}")
                rm["width"] = c3.number_input("Width (ft)", value=float(rm["width"]), step=0.5, key=f"rwid_{rm['room_id']}")
                rm["skirting"] = c4.number_input("Skirting (in)", value=float(rm["skirting"]), step=1.0, key=f"rsk_{rm['room_id']}")
                
                if c5.button("❌", key=f"rdel_{rm['room_id']}"):
                    fl["rooms"].pop(r_idx)
                    st.rerun()
                    
                floor_sqft = rm["length"] * rm["width"]
                skirting_sqft = 2 * (rm["length"] + rm["width"]) * (rm["skirting"] / 12.0)
                net_area = floor_sqft + skirting_sqft
                
                if rm["selected_tile"]:
                    tile_info = rm["selected_tile"]
                    b_sqft = tile_info["BOX_SQFT"]
                    boxes_exact = net_area / b_sqft
                    boxes_req = math.ceil(boxes_exact)
                    st.markdown(f"""
                    <div class='selection-banner'>
                        ✅ <b>Tile Assigned:</b> {tile_info['ITEM_NAME']} | <b>Total Area:</b> {net_area:.1f} SqFt<br>
                        📦 <b>Required:</b> <span style='color:#1e3a8a; font-weight:bold; font-size:15px;'>{boxes_req} Boxes</span> ({boxes_req * b_sqft:.1f} SqFt) 
                        <span style='color:#64748b; font-size:12px;'>[Exact: {boxes_exact:.2f} Boxes]</span>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info(f"ℹ️ Area: **{net_area:.1f} SqFt** | Go to **Tab 2 (Tiles Selection Catalog)** to assign tile.")
                st.divider()

# -------------------------------------------------------------
# TAB 2: TILES SELECTION CATALOG
# -------------------------------------------------------------
with tab_select:
    st.subheader("🎨 Live Tiles & Granite Selection")
    
    if stock_data.empty:
        st.warning("⚠️ No items available. Please check BUSY Google Sheet link.")
    else:
        # Search & Filter Row
        f1, f2, f3 = st.columns([2, 1.5, 1.5])
        with f1:
            search_key = st.text_input("🔍 Search Tile / Design Name / Code", placeholder="e.g. 2X4, Varmora, Sega, Crayon, 12X18")
        with f2:
            cat_choice = st.selectbox("Filter Category", ["All", "Floor Tile", "Wall Tile", "Granite", "Parking Tile"])
        with f3:
            # Flatten room list for assignment
            room_dropdown_options = []
            room_map = {}
            for fl in st.session_state.floors:
                for rm in fl["rooms"]:
                    label = f"{fl['floor_name']} ➔ {rm['name']} (ID: {rm['room_id']})"
                    room_dropdown_options.append(label)
                    room_map[label] = rm
                    
            target_room_label = st.selectbox("🎯 Assign Selected Tile To:", room_dropdown_options)
            chosen_room = room_map.get(target_room_label)

        # Filtered DataFrame
        filtered_df = stock_data.copy()
        if cat_choice != "All":
            filtered_df = filtered_df[filtered_df["CATEGORY"] == cat_choice]
        if search_key:
            filtered_df = filtered_df[
                filtered_df["ITEM_NAME"].str.contains(search_key, case=False, na=False) | 
                filtered_df["ITEM_ID"].str.contains(search_key, case=False, na=False)
            ]

        st.write(f"Showing **{len(filtered_df)}** matching tiles in stock:")
        
        # Display Grid
        grid_cols = st.columns(3)
        for idx, (_, tile_row) in enumerate(filtered_df.head(60).iterrows()):
            col_idx = idx % 3
            with grid_cols[col_idx]:
                with st.container():
                    st.markdown(f"""
                    <div class='tile-box'>
                        <div style='font-size:15px; font-weight:700; color:#0f172a;'>{tile_row['ITEM_NAME']}</div>
                        <div style='font-size:12px; color:#64748b;'>Code: <b>{tile_row['ITEM_ID']}</b> | Category: {tile_row['CATEGORY']}</div>
                        <div style='margin-top:6px; font-size:13px;'>📦 <b>{tile_row['BOX_SQFT']} SqFt / Box</b> ({tile_row['PACKING_UNIT']} Pcs)</div>
                        <div style='color:#16a34a; font-size:12px; font-weight:600; margin-top:2px;'>● Ready in Stock</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    btn_text = f"Select for {chosen_room['name']}" if chosen_room else "Select Tile"
                    if st.button(btn_text, key=f"btn_tile_{tile_row['ITEM_ID']}_{idx}", use_container_width=True):
                        if chosen_room:
                            chosen_room["selected_tile"] = tile_row.to_dict()
                            st.success(f"Assigned '{tile_row['ITEM_NAME']}' to {chosen_room['name']}!")
                            st.rerun()

# -------------------------------------------------------------
# TAB 3: ESTIMATE SUMMARY & PRINT
# -------------------------------------------------------------
with tab_summary:
    st.subheader("📄 Material Requirement & Estimation Sheet")
    
    c_info1, c_info2 = st.columns(2)
    with c_info1:
        st.write(f"**Customer:** {st.session_state.customer_name}")
        st.write(f"**Mobile:** {st.session_state.customer_mobile or 'N/A'}")
    with c_info2:
        st.write(f"**Date:** {date.today().strftime('%d-%b-%Y')}")
        st.write(f"**Site Address:** {st.session_state.customer_address or 'N/A'}")
        
    st.markdown("---")
    
    summary_data = []
    grand_total_boxes = 0
    grand_total_sqft = 0.0
    
    for fl in st.session_state.floors:
        for rm in fl["rooms"]:
            fl_area = rm["length"] * rm["width"]
            sk_area = 2 * (rm["length"] + rm["width"]) * (rm["skirting"] / 12.0)
            room_net_area = fl_area + sk_area
            
            if rm["selected_tile"]:
                tile_selected = rm["selected_tile"]
                b_sqft = tile_selected["BOX_SQFT"]
                exact_b = room_net_area / b_sqft
                req_b = math.ceil(exact_b)
                act_covered = req_b * b_sqft
                
                grand_total_boxes += req_b
                grand_total_sqft += act_covered
                
                summary_data.append({
                    "Floor / Room": f"{fl['floor_name']} - {rm['name']}",
                    "Dimensions": f"{rm['length']} x {rm['width']} ft (Sk: {rm['skirting']}\")",
                    "Tile Selected": tile_selected['ITEM_NAME'],
                    "Room Area (SqFt)": round(room_net_area, 1),
                    "Box Coverage": f"{b_sqft} SqFt",
                    "Required Boxes": f"{req_b} Boxes",
                    "Delivered (SqFt)": round(act_covered, 1)
                })
            else:
                summary_data.append({
                    "Floor / Room": f"{fl['floor_name']} - {rm['name']}",
                    "Dimensions": f"{rm['length']} x {rm['width']} ft",
                    "Tile Selected": "⚠️ Not Selected",
                    "Room Area (SqFt)": round(room_net_area, 1),
                    "Box Coverage": "-",
                    "Required Boxes": "-",
                    "Delivered (SqFt)": "-"
                })
                
    if summary_data:
        summary_table = pd.DataFrame(summary_data)
        st.dataframe(summary_table, use_container_width=True)
        
        st.markdown(f"""
        ### 📊 Total Order Estimate: **{grand_total_boxes} Boxes** ({grand_total_sqft:.1f} SqFt)
        """)
        
    st.info("💡 **Print Tip:** ब्राउज़र में `Ctrl + P` दबाकर ग्राहक के लिए सीधे कोटेशन PDF प्रिंट कर सकते हैं।")
