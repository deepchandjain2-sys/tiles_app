import pandas as pd
import os

CUST_CSV = "customers_saved.csv"
STOCK_CSV = "stock_saved.csv"
ITEMS_CSV = "items_saved.csv"

def save_customers_to_disk(customers_list):
    try:
        if customers_list:
            pd.DataFrame(customers_list).to_csv(CUST_CSV, index=False)
    except Exception as e:
        print(f"Error saving customers: {e}")

def load_customers_from_disk():
    try:
        if os.path.exists(CUST_CSV):
            return pd.read_csv(CUST_CSV).to_dict('records')
    except Exception as e:
        print(f"Error loading customers: {e}")
    return []

def save_stock_to_disk(stock_df):
    try:
        if stock_df is not None and not stock_df.empty:
            stock_df.to_csv(STOCK_CSV, index=False)
    except Exception as e:
        print(f"Error saving stock: {e}")

def load_stock_from_disk():
    try:
        if os.path.exists(STOCK_CSV):
            return pd.read_csv(STOCK_CSV)
    except Exception as e:
        print(f"Error loading stock: {e}")
    return pd.DataFrame()

def save_items_to_disk(items_list):
    try:
        if items_list is not None:
            pd.DataFrame(items_list).to_csv(ITEMS_CSV, index=False)
    except Exception as e:
        print(f"Error saving items: {e}")

def load_items_from_disk():
    try:
        if os.path.exists(ITEMS_CSV):
            return pd.read_csv(ITEMS_CSV).to_dict('records')
    except Exception as e:
        print(f"Error loading items: {e}")
    return []

def load_stock_from_upload(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        return df.dropna(how='all')
    except Exception as e:
        print(f"Error loading file: {e}")
        return None
