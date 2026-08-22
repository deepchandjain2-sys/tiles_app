import io
import requests
import streamlit as st
import pandas as pd

# Direct Google Sheet Export Link
SHEET_URL = "https://docs.google.com/spreadsheets/d/14lY-SKjwd9hins1gSp6lR1C4_AOWOx2an8c-UgKaPY/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=30)
def fetch_busy_inventory():
    try:
        # Load directly via Google Visualization API
        response = requests.get(SHEET_URL, timeout=10)
        if response.status_code == 200:
            df = pd.read_csv(io.StringIO(response.text))
        else:
            # Fallback direct read
            df = pd.read_csv(SHEET_URL)
            
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
            
            try:
                con_val = float(row[con_col]) if (con_col and pd.notna(row[con_col])) else 8.0
            except:
                con_val = 8.0
                
            try:
                pack_val = float(row[pack_col]) if (pack_col and pd.notna(row[pack_col])) else 2.0
            except:
                pack_val = 2.0
                
            box_sqft = round(con_val * pack_val, 2)
            if box_sqft <= 0:
                box_sqft = 16.0
                
            cat = "Floor"
            if "GRAN" in name.upper():
                cat = "Granite"
            elif "WALL" in name.upper() or "HL" in name.upper() or "12X18" in name.upper() or "10X15" in name.upper():
                cat = "Wall"
                
            records.append({
                "ITEM_ID": str(row[id_col]).strip() if pd.notna(row[id_col]) else "NA",
                "ITEM_NAME": name,
                "CON_FACTOR": con_val,
                "PACKING_UNIT": int(pack_val),
                "BOX_SQFT": box_sqft,
                "CATEGORY": cat
            })
            
        return pd.DataFrame(records)
    except Exception as err:
        st.error(f"Google Sheet Fetch Error: {err}")
        return pd.DataFrame()
