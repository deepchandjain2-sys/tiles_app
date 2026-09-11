import streamlit as st

def get_all_customers():
    return st.session_state.get('mock_customers', [])

def save_customer_to_db(cust_data):
    if 'mock_customers' not in st.session_state:
        st.session_state['mock_customers'] = []
    existing = [c for c in st.session_state['mock_customers'] if c.get('mobile') == cust_data.get('mobile')]
    if existing:
        st.session_state['mock_customers'].remove(existing[0])
    st.session_state['mock_customers'].append(cust_data)
    return True

def delete_customer_from_db(mobile):
    if 'mock_customers' in st.session_state:
        st.session_state['mock_customers'] = [c for c in st.session_state['mock_customers'] if c.get('mobile') != mobile]
    return True

def get_all_admin_users():
    return [{"username": "admin", "password": "password", "role": "ADMIN", "branch": "Hiriyur"}]

def add_admin_user(u, p, r, b):
    return True

def delete_admin_user(u):
    return True
