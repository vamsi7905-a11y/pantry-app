import streamlit as st
import gspread
import pandas as pd
import json
import os
import time
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# === Authenticate Google Sheets ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

# === Load Sheet ===
SHEET_NAME = "Pantry_Entries"
sheet = client.open(SHEET_NAME).worksheet("Pantry Entries")

# === Load existing data ===
try:
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    df.columns = df.columns.astype(str).str.strip()
except Exception as e:
    st.error("❌ Failed to load data from Google Sheets.")
    st.stop()

st.set_page_config(page_title="Pantry Entry", layout="wide")
st.title("🥪 Pantry Coupon Entry System")
st.markdown("---")

# === Setup Persistent State with Timeout ===
defaults = {
    "entry_date": datetime.today().date(),
    "entry_apm": "",
    "entry_name": "",
    "entry_coupon": "",
    "entry_pantry": "",
    "entry_last_time": time.time()
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Auto-clear all after 10 minutes
if time.time() - st.session_state.entry_last_time > 600:
    for key in ["entry_date", "entry_apm", "entry_name", "entry_coupon", "entry_pantry"]:
        st.session_state[key] = "" if key != "entry_date" else datetime.today().date()
    st.session_state.entry_last_time = time.time()

# === Prepare dropdowns from existing data ===
existing_apms = sorted(df["APM ID"].dropna().unique().tolist())
existing_names = sorted(df["Name"].dropna().unique().tolist())

# === Entry Form ===
st.subheader("📥 New Entry")

with st.form("entry_form"):
    col1, col2, col3 = st.columns(3)

    with col1:
        date = st.date_input("Date", value=st.session_state.entry_date)
        apm_id = st.selectbox("APM ID", options=[""] + existing_apms, index=0 if not st.session_state.entry_apm else existing_apms.index(st.session_state.entry_apm)+1)

    with col2:
        name = st.selectbox("Name", options=[""] + existing_names, index=0 if not st.session_state.entry_name else existing_names.index(st.session_state.entry_name)+1)
        coupon_no = st.text_input("Coupon Number", value=st.session_state.entry_coupon)
        if coupon_no and not coupon_no.isdigit():
            st.warning("⚠️ Coupon Number must be numeric")

    with col3:
        item = st.selectbox("Item", [
            "Tea", "Coffee", "Coke", "Veg S/W", "Non S/W", "Biscuit",
            "Juice", "Lays", "Dry Fruits", "Fruit Bowl", "Samosa",
            "Idli/Wada", "EFAAS & LIVIN JUICE", "Mentos"
        ])
        qty = st.number_input("Quantity", min_value=1, value=1)
        action = st.selectbox("Action", ["Issued", "Returned"])

    pantry_boy = st.text_input("Pantry Boy Name", value=st.session_state.entry_pantry)
    submitted = st.form_submit_button("➕ Submit Entry")

# === Submission Handling ===
if submitted:
    if not coupon_no.isdigit():
        st.error("❌ Coupon Number must be numeric")
    elif not apm_id or not name or not pantry_boy:
        st.error("❌ APM ID, Name, and Pantry Boy are required.")
    else:
        sheet.append_row([
            str(date), apm_id, name, item, qty, action, coupon_no, pantry_boy
        ])
        st.success(f"✅ {qty} x {item} ({action}) entry saved for Coupon {coupon_no}.")

        # Retain other values, clear only item & quantity
        st.session_state.entry_date = date
        st.session_state.entry_apm = apm_id
        st.session_state.entry_name = name
        st.session_state.entry_coupon = coupon_no
        st.session_state.entry_pantry = pantry_boy
        st.session_state.entry_last_time = time.time()
        st.experimental_rerun()

st.markdown("---")

# === Optional: Show today's entries (latest first) ===
st.subheader("📋 Today's Entries (Issued Only)")
today = datetime.today().date()
df["Date"] = pd.to_datetime(df["Date"], errors='coerce').dt.date
today_df = df[(df["Date"] == today) & (df["Action"] == "Issued")]

if not today_df.empty:
    st.dataframe(today_df[::-1].reset_index(drop=True), use_container_width=True)
else:
    st.info("No entries recorded for today.")
