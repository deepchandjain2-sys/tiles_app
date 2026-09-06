import sqlite3
import os
import base64
import requests
import streamlit as st

GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
REPO_NAME = st.secrets.get("REPO_NAME", "deepchandjain2-sys/tiles_app")
DB_FILE = "jay_granite_master.db"

def fetch_db_from_github():
    if not GITHUB_TOKEN or not REPO_NAME:
        return
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{DB_FILE}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            content_encoded = response.json().get("content", "")
            decoded_bytes = base64.b64decode(content_encoded)
            with open(DB_FILE, "wb") as f:
                f.write(decoded_bytes)
    except Exception:
        pass

def push_db_to_github():
    if not GITHUB_TOKEN or not REPO_NAME:
        return
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{DB_FILE}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        sha = r.json().get("sha") if r.status_code == 200 else None

        if os.path.exists(DB_FILE):
            with open(DB_FILE, "rb") as f:
                content_bytes = f.read()
            content_encoded = base64.b64encode(content_bytes).decode("utf-8")

            payload = {
                "message": "Auto-sync SQLite database [skip ci]",
                "content": content_encoded,
                "branch": "main"
            }
            if sha:
                payload["sha"] = sha

            requests.put(url, headers=headers, json=payload, timeout=10)
    except Exception:
        pass

# Fetch existing DB from GitHub on startup if available
if not os.path.exists(DB_FILE):
    fetch_db_from_github()
