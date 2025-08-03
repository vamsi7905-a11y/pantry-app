# entry_summary.py - Pantry Staff Entry Summary Dashboard

import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, timedelta
import json
import os
from oauth2client.service_account import ServiceAccountCredentials

# === Authenticate Google Sheets ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

# === Open the correct sheet ===
SHEET_NAME = "Pantry_Entries"
sheet = client.open(SHEET_NAME).worksheet("Pantry Entries")

# === Load data ===
data = sheet.get_all_records()
df = pd.DataFrame(data)
df.columns = df.columns.str.strip()

st.set_page_config(page_title="Pantry Staff Summary", layout="wide")
st.title("🥪 Pantry Coupon Entry Summary")
st.markdown("---")

if df.empty:
    st.warning("No entries yet.")
    st.stop()

# === Preprocess ===
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

# === Filter Section ===
st.subheader("🔍 Filter Entries")
col1, col2, col3, col4 = st.columns(4)

with col1:
    date_filter = st.selectbox("Show for", ["Today", "This Week", "This Month", "All"])

with col2:
    apm_filter = st.text_input("APM ID")

with col3:
    item_filter = st.selectbox("Item", ["All"] + sorted(df["Item"].unique()))

with col4:
    action_filter = st.selectbox("Action", ["All", "Issued", "Returned"])

# === Apply Filters ===
today = pd.Timestamp.today().normalize()

if date_filter == "Today":
    df = df[df["Date"] == today]
elif date_filter == "This Week":
    start = today - pd.Timedelta(days=today.weekday())
    df = df[(df["Date"] >= start) & (df["Date"] <= today)]
elif date_filter == "This Month":
    start = today.replace(day=1)
    df = df[(df["Date"] >= start) & (df["Date"] <= today)]

if apm_filter:
    df = df[df["APM ID"].str.contains(apm_filter, case=False)]

if item_filter != "All":
    df = df[df["Item"] == item_filter]

if action_filter != "All":
    df = df[df["Action"] == action_filter]

# === Show Filtered Table ===
st.markdown("### 📋 Filtered Entries")
st.dataframe(df.reset_index(drop=True), use_container_width=True)

# === Net Summary ===
st.markdown("### 📦 Summary (Issued - Returned)")

summary = (
    df.groupby(["APM ID", "Item", "Action"])["Quantity"]
    .sum()
    .unstack(fill_value=0)
    .reset_index()
)

summary["Net"] = summary.get("Issued", 0) - summary.get("Returned", 0)
st.dataframe(summary, use_container_width=True)
