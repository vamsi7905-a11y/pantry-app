import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json
import os

# === Setup Google Sheets Credentials ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

# === Open Sheet ===
SHEET_NAME = "Pantry_Entries"
sheet = client.open(SHEET_NAME).worksheet("Pantry Entries")

# === Load existing data ===
data = sheet.get_all_records()
df = pd.DataFrame(data)
df.columns = df.columns.str.strip()

st.set_page_config(page_title="Pantry Entry", layout="wide")
st.title("🥪 Pantry Coupon Entry System")
st.markdown("---")

# === Session State for Autofill and Reset ===
defaults = {
    "entry_date": datetime.today().date(),
    "entry_apm": "",
    "entry_name": "",
    "entry_coupon": "",
    "entry_pantry": "",
    "last_active": datetime.now()
}

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# Auto-clear after 10 mins
if datetime.now() - st.session_state.last_active > timedelta(minutes=10):
    for key in defaults:
        st.session_state[key] = defaults[key]

# === Entry Form ===
st.subheader("📥 New Entry")

with st.form("entry_form"):
    col1, col2, col3 = st.columns(3)

    with col1:
        date = st.date_input("Date", value=st.session_state.entry_date)
        apm_options = sorted(df["APM ID"].dropna().unique())
        apm_id = st.selectbox("APM ID", options=apm_options + ["Enter new..."], index=0)
        if apm_id == "Enter new...":
            apm_id = st.text_input("Enter new APM ID")

    with col2:
        name_options = sorted(df["Name"].dropna().unique())
        name = st.selectbox("Name", options=name_options + ["Enter new..."], index=0)
        if name == "Enter new...":
            name = st.text_input("Enter new Name")

        coupon_no = st.text_input("Coupon Number", value=st.session_state.entry_coupon)
        if coupon_no and not coupon_no.isdigit():
            st.warning("Coupon Number must be numeric")

    with col3:
        item = st.selectbox("Item", [
            "Tea", "Coffee", "Coke", "Veg S/W", "Non S/W", "Biscuit",
            "Juice", "Lays", "Dry Fruits", "Fruit Bowl", "Samosa",
            "Idli/Wada", "EFAAS & LIVIN JUICE", "Mentos"
        ])
        qty = st.number_input("Quantity", min_value=1, value=1)
        action = st.selectbox("Action", ["Issued", "Returned"])

    pantry_options = sorted(df["Pantry Boy Name"].dropna().unique()) if "Pantry Boy Name" in df else []
    pantry_boy = st.selectbox("Pantry Boy Name", options=pantry_options + ["Enter new..."], index=0)
    if pantry_boy == "Enter new...":
        pantry_boy = st.text_input("Enter Pantry Boy Name")

    submitted = st.form_submit_button("➕ Submit Entry")

if submitted:
    if not coupon_no.isdigit():
        st.error("❌ Coupon Number must be numeric")
    else:
        sheet.append_row([
            str(date), apm_id, name, item, qty, action, coupon_no, pantry_boy
        ])
        st.success(f"✅ Entry for {item} ({action}) recorded!")

        # Keep others, reset item & qty
        st.session_state.entry_date = date
        st.session_state.entry_apm = apm_id
        st.session_state.entry_name = name
        st.session_state.entry_coupon = coupon_no
        st.session_state.entry_pantry = pantry_boy
        st.session_state.last_active = datetime.now()
        st.rerun()

st.markdown("---")

# === View & Filter Entries ===
st.subheader("📋 View Entries")

if not df.empty:
    with st.expander("🔍 Filter"):
        col1, col2 = st.columns(2)
        with col1:
            filter_apm = st.text_input("Filter by APM ID")
            filter_name = st.text_input("Filter by Name")
        with col2:
            filter_item = st.selectbox("Filter by Item", ["All"] + sorted(df["Item"].unique()))
            filter_action = st.selectbox("Filter by Action", ["All", "Issued", "Returned"])

    filtered_df = df.copy()

    if filter_apm:
        filtered_df = filtered_df[filtered_df["APM ID"].str.contains(filter_apm, case=False)]
    if filter_name:
        filtered_df = filtered_df[filtered_df["Name"].str.contains(filter_name, case=False)]
    if filter_item != "All":
        filtered_df = filtered_df[filtered_df["Item"] == filter_item]
    if filter_action != "All":
        filtered_df = filtered_df[filtered_df["Action"] == filter_action]

    st.dataframe(filtered_df.reset_index(drop=True), use_container_width=True)
else:
    st.info("No entries yet.")
