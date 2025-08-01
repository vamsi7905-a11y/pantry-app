import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
import os

# === Setup Google Sheets Credentials ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

# === Open Sheet ===
SHEET_NAME = "Pantry_Entries"   # ✅ Exact sheet name from Google Drive
sheet = client.open(SHEET_NAME).worksheet("Pantry Entries")  # ✅ Must match tab name


# === Load existing data ===
data = sheet.get_all_records()
df = pd.DataFrame(data)

st.set_page_config(page_title="Pantry Entry", layout="wide")
st.title("🥪 Pantry Coupon Entry System")

st.markdown("---")

# === Entry Form ===
st.subheader("📥 New Entry")

with st.form("entry_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        date = st.date_input("Date", value=datetime.today())
        apm_id = st.text_input("APM ID", placeholder="e.g. PNA056")

    with col2:
        name = st.text_input("Name", placeholder="e.g. Padma Kumar Nair")
        coupon_no = st.text_input("Coupon Number")

    with col3:
        item = st.selectbox("Item", [
            "Tea", "Coffee", "Coke", "Veg S/W", "Non S/W", "Biscuit",
            "Juice", "Lays", "Dry Fruits", "Fruit Bowl", "Samosa",
            "Idli/Wada", "EFAAS & LIVIN JUICE", "Mentos"
        ])
        qty = st.number_input("Quantity", min_value=1, value=1)
        action = st.selectbox("Action", ["Issued", "Returned"])

    pantry_boy = st.text_input("Pantry Boy Name")

    submitted = st.form_submit_button("➕ Submit Entry")

    if submitted:
        sheet.append_row([
            str(date), apm_id, name, item, qty, action, coupon_no, pantry_boy
        ])
        st.success(f"✅ Entry for {item} ({action}) recorded!")

st.markdown("---")

# === View & Filter Entries ===
st.subheader("📋 View Entries")

if not df.empty:
    with st.expander("🔍 Filter"):
        col1, col2 = st.columns(2)
        with col1:
            filter_apm = st.text_input("Filter by APM ID")
            filter_item = st.selectbox("Filter by Item", ["All"] + sorted(df["Item"].unique()))
        with col2:
            filter_action = st.selectbox("Filter by Action", ["All", "Issued", "Returned"])

    filtered_df = df.copy()

    if filter_apm:
        filtered_df = filtered_df[filtered_df["APM ID"].str.contains(filter_apm, case=False)]
    if filter_item != "All":
        filtered_df = filtered_df[filtered_df["Item"] == filter_item]
    if filter_action != "All":
        filtered_df = filtered_df[filtered_df["Action"] == filter_action]

    st.dataframe(filtered_df.reset_index(drop=True), use_container_width=True)
else:
    st.info("No entries yet.")
