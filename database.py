import pandas as pd
import os

CUST_CSV = "customers_saved.csv"
STOCK_CSV = "stock_saved.csv"

def save_customers_to_disk(customers_list):
    try:
        if customers_list:
            df = pd.DataFrame(customers_list)
            df.to_csv(CUST_CSV, index=False)
    except Exception as e:
        print(f"Error saving customers: {e}")

def load_customers_from_disk():
    try:
        if os.path.exists(CUST_CSV):
            df = pd.read_csv(CUST_CSV)
            return df.to_dict('records')
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

def load_stock_from_upload(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        df = df.dropna(how='all')
        return df
    except Exception as e:
        print(f"Error loading file: {e}")
        return None
