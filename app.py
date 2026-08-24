import streamlit as st
import pandas as pd
import os
import math
import urllib.parse
from calculations import calculate_boxes, calculate_box_sqft
from database import load_stock_from_upload, save_stock_to_disk, load_items_from_disk, save_items_to_disk

st.set_page_config(page_title="Jay Granite & Tiles Hub", page_icon="🏢", layout="wide")

# Initialize session state
if "stock_df" not in st.session_state:
    st.session_state.stock_df = load_stock_from_upload(None)

if "my_selected_tiles" not in st.session_state:
    st.session_state.my_selected_tiles = load_items_from_disk()

if "customers" not in st.session_state:
    st.session_state.customers = []

st.sidebar.title("🏢 Jay Granite & Tiles")
menu = st.sidebar.radio("Navigation Flow", [
    "1 Customer Registration",
    "2 Tiles Selection (Area-Wise)",
    "3 Measurements, PDF & WhatsApp",
    "4 Sales Dashboard & History"
])

# Role selector
role = st.sidebar.selectbox("Role", ["ADMIN", "STAFF"])
if st.sidebar.button("Logout"):
    st.success("Logged out successfully.")

# --- 1. CUSTOMER REGISTRATION ---
if menu == "1 Customer Registration":
    st.header("👤 Customer Registration")
    
    with st.form("customer_form"):
        col1, col2 = st.columns(2)
        with col1:
            cust_name = st.text_input("Customer Name")
            cust_phone = st.text_input("Phone Number")
        with col2:
            cust_city = st.text_input("City / Location", value="Hiriyur")
            cust_gst = st.text_input("GSTIN (Optional)")
            
        submitted = st.form_submit_button("Register & Proceed")
        if submitted:
            if cust_name.strip():
                new_cid = len(st.session_state.customers) + 1
                cust_data = {
                    "cid": new_cid,
                    "name": cust_name,
                    "phone": cust_phone,
                    "city": cust_city,
                    "gst": cust_gst
                }
                st.session_state.customers.append(cust_data)
                st.session_state.current_cid = new_cid
                st.success(f"Customer {cust_name} registered successfully! Proceed to Tiles Selection.")
            else:
                st.error("Please enter the customer name.")

    if st.session_state.customers:
        st.subheader("Select Existing Customer")
        c_options = {f"{c['cid']} - {c['name']} ({c['city']})": c['cid'] for c in st.session_state.customers}
        selected_c_label = st.selectbox("Registered Customers", list(c_options.keys()))
        if selected_c_label:
            st.session_state.current_cid = c_options[selected_c_label]
            st.info(f"Active Customer: {selected_c_label}")

# --- 2. TILES SELECTION (AREA-WISE) ---
elif menu == "2 Tiles Selection (Area-Wise)":
    st.header("🏠 Tiles Selection (Area-Wise)")
    
    if not st.session_state.customers:
        st.warning("Please register a customer first in step 1.")
    else:
        cid = st.session_state.get("current_cid", st.session_state.customers[0]["cid"])
        
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
                # Update 1: Area Name options + Manual typing support
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
                    st.success(f"Added {selected_tile} for {area_name} successfully!")
                    st.rerun()
                else:
                    st.error("Please enter/select a valid Area Name and Tile.")

            st.markdown("---")
            st.subheader("📋 Selected Items for this Customer")
            
            if "my_selected_tiles" not in st.session_state or not isinstance(st.session_state.my_selected_tiles, list):
                st.session_state.my_selected_tiles = []
                
            customer_items = [i for i in st.session_state.my_selected_tiles if isinstance(i, dict) and i.get("cid"] == cid]
            
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
                    
                if st.button("🗑️ Clear All Selections for Customer"):
                    st.session_state.my_selected_tiles = [i for i in st.session_state.my_selected_tiles if not (isinstance(i, dict) and i.get("cid") == cid)]
                    save_items_to_disk(st.session_state.my_selected_tiles)
                    st.rerun()
            else:
                st.info("No tiles selected yet for this customer.")

# --- 3. MEASUREMENTS, PDF & WHATSAPP ---
elif menu == "3 Measurements, PDF & WhatsApp":
    st.header("📐 Measurements, PDF & WhatsApp")
    
    if not st.session_state.customers:
        st.warning("Please register a customer first.")
    else:
        cid = st.session_state.get("current_cid", st.session_state.customers[0]["cid"])
        current_cust = next((c for c in st.session_state.customers if c['cid'] == cid), {"name": "Customer", "phone": ""})
        items = [i for i in st.session_state.get("my_selected_tiles", []) if isinstance(i, dict) and i.get("cid") == cid]
        
        if not items:
            st.info("No items selected for this customer yet. Go to step 2.")
        else:
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
                
                # Correct Calculation Formula: Area / (Con Factor * Packing Unit)
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
            
            # Update 2 & 3: Generate text/HTML quotation for direct view/download & WhatsApp sharing
            summary_text = f"*JAY GRANITE & TILES - QUOTATION*\n\n" \
                           f"Customer: {current_cust['name']}\n" \
                           f"City: {current_cust['city']}\n\n"
            for it in items:
                summary_text += f"• {it.get('floor')} - {it.get('area')} ({it.get('section')}): {it.get('tile')} | Area: {it.get('sqft')} SqFt | Boxes: {it.get('boxes')}\n"
            summary_text += f"\n*Total Boxes Required: {total_boxes}*"

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                # Update 2: Direct file download / open simulation
                st.download_button(
                    label="📄 Download / Open Quotation (TXT)",
                    data=summary_text,
                    file_name=f"Quotation_{current_cust['name']}.txt",
                    mime="text/plain",
                    type="primary"
                )
            with col_btn2:
                # Update 3: WhatsApp Share Button
                encoded_message = urllib.parse.quote(summary_text)
                whatsapp_url = f"https://wa.me/?text={encoded_message}"
                st.markdown(f'<a href="{whatsapp_url}" target="_blank"><button style="background-color:#25D366; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer; font-weight:bold; width:100%;">💬 Share on WhatsApp</button></a>', unsafe_allow_html=True)

# --- 4. SALES DASHBOARD & HISTORY ---
elif menu == "4 Sales Dashboard & History":
    st.header("📊 Sales Dashboard & History")
    st.info("Dashboard and past customer history records will appear here.")
