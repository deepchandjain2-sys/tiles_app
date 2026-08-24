import pandas as pd

def save_customer_to_csv(customers_list, filename="customers_history.csv"):
    """
    कस्टमर्स की लिस्ट को CSV फ़ाइल में सेव करता है।
    """
    if customers_list:
        df = pd.DataFrame(customers_list)
        df.to_csv(filename, index=False)
        return True
    return False

def load_stock_from_upload(uploaded_file):
    """
    अपलोड की गई BUSY आइटम मास्टर फ़ाइल (CSV/Excel) को रीड करके प्रोसेस करता है।
    """
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
