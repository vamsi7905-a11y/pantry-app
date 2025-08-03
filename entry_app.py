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
SHEET_NAME = "Pantry_Entries"
sheet = client.open(SHEET_NAME).worksheet("Pantry Entries")

# === Load existing data ===
data = sheet.get_all_records()
df = pd.DataFrame(data)

st.set_page_config(page_title="Pantry Entry", layout="wide")
st.title("🥪 Pantry Coupon Entry System")
st.markdown("---")

# === Initialize persistent state for autofill ===
if "entry_date" not in st.session_state:
    st.session_state.entry_date = datetime.today().date()
if "entry_apm" not in st.session_state:
    st.session_state.entry_apm = ""
if "entry_name" not in st.session_state:
    st.session_state.entry_name = ""
if "entry_coupon" not in st.session_state:
    st.session_state.entry_coupon = ""
if "entry_pantry" not in st.session_state:
    st.session_state.entry_pantry = ""

# === Entry Form ===
st.subheader("📥 New Entry")

with st.form("entry_form"):
    col1, col2, col3 = st.columns(3)

    with col1:
        date = st.date_input("Date", value=st.session_state.entry_date)
        apm_id = st.text_input("APM ID", value=st.session_state.entry_apm)

    with col2:
        name = st.text_input("Name", value=st.session_state.entry_name)
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

    pantry_boy = st.text_input("Pantry Boy Name", value=st.session_state.entry_pantry)

    submitted = st.form_submit_button("➕ Submit Entry")


    if "rerun_flag" not in st.session_state:
    st.session_state.rerun_flag = False

if submitted:
    if not coupon_no.isdigit():
        st.error("❌ Coupon Number must be numeric")
    else:
        sheet.append_row([
            str(date), apm_id, name, item, qty, action, coupon_no, pantry_boy
        ])
        st.success(f"✅ Entry for {item} ({action}) recorded!")

        # Store values for next entry
        st.session_state.entry_date = date
        st.session_state.entry_apm = apm_id
        st.session_state.entry_name = name
        st.session_state.entry_coupon = coupon_no
        st.session_state.entry_pantry = pantry_boy

        # Safe rerun flag
        st.session_state.rerun_flag = True

# Trigger rerun outside form context
if st.session_state.rerun_flag:
    st.session_state.rerun_flag = False
    st.experimental_rerun()

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

