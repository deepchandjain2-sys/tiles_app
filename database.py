import os
import streamlit as st
import json
import sqlite3

DB_FILE = "jay_granite_master.db"

def get_db():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def get_all_customers_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, mobile, address, engineer, salesman, status, selections_json, total_sqft, total_boxes, created_at FROM customers_master ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    
    clients = []
    for r in rows:
        try:
            sels = json.loads(r[7])
        except Exception:
            sels = []
        clients.append({
            "id": r[0],
            "name": r[1],
            "mobile": r[2],
            "address": r[3],
            "engineer": r[4],
            "salesman": r[5],
            "status": r[6],
            "selections": sels,
            "total_sqft": r[8],
            "total_boxes": r[9],
            "created_at": r[10]
        })
    return clients

# Alias taaki app.py ki import error khatam ho jaye
def get_all_customers():
    return get_all_customers_db()

def save_customer_to_db(cust_dict):
    conn = get_db()
    c = conn.cursor()
    sels_json = json.dumps(cust_dict.get("selections", []), ensure_ascii=False)
    c.execute("""
        UPDATE customers_master 
        SET name = ?, mobile = ?, address = ?, engineer = ?, salesman = ?, status = ?, selections_json = ?, total_sqft = ?, total_boxes = ?
        WHERE id = ?
    """, (
        cust_dict.get("name"),
        cust_dict.get("mobile"),
        cust_dict.get("address"),
        cust_dict.get("engineer"),
        cust_dict.get("salesman"),
        cust_dict.get("status", "SELECTION ONLY"),
        sels_json,
        float(cust_dict.get("total_sqft", 0.0)),
        float(cust_dict.get("total_boxes", 0.0)),
        cust_dict.get("id")
    ))
    conn.commit()
    conn.close()

def delete_customer_db(cust_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM customers_master WHERE id = ?", (cust_id,))
    conn.commit()
    conn.close()
