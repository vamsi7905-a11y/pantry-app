import streamlit as st
import gspread
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials

# === Google Sheets Auth ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

SHEET_NAME = "Pantry_Entries"
sheet = client.open(SHEET_NAME).worksheet("Pantry Entries")

# === Load Data ===
data = sheet.get_all_records()
df = pd.DataFrame(data)
df.columns = df.columns.str.strip()

# === Set Streamlit Page ===
st.set_page_config(page_title="Pantry Entry", layout="wide")
st.title("🥪 Pantry Coupon Entry System")
st.markdown("---")

# === Session State Defaults ===
if "entry_time" not in st.session_state:
    st.session_state.entry_time = datetime.now()

if "entry_date" not in st.session_state or datetime.now() - st.session_state.entry_time > timedelta(minutes=10):
    st.session_state.entry_date = datetime.today().date()
    st.session_state.entry_apm = ""
    st.session_state.entry_name = ""
    st.session_state.entry_coupon = ""
    st.session_state.entry_pantry = ""
    st.session_state.entry_time = datetime.now()

# === Entry Form ===
st.subheader("📥 New Entry")

with st.form("entry_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        date = st.date_input("Date", value=st.session_state.entry_date)
        apm_id = st.text_input("APM ID", value=st.session_state.entry_apm, placeholder="Type or select APM ID")
    with col2:
        name = st.text_input("Name", value=st.session_state.entry_name, placeholder="Type or select Name")
        coupon_no = st.text_input("Coupon Number", value=st.session_state.entry_coupon)
        if coupon_no and not coupon_no.isdigit():
            st.warning("Coupon Number must be numeric")
    with col3:
        item = st.selectbox("Item", [
            "Tea", "Coffee", "Coke", "Veg S/W", "Non S/W", "Biscuit",
            "Juice", "Lays", "Dry Fruits", "Fruit Bowl", "Samosa",
            "Idli/Wada", "EFAAS & LIVIN JUICE", "Mentos"
        ])
        qty = st.number_input("Quantity", min_value=1, value=0)
        action = st.selectbox("Action", ["Issued", "Returned"])

    pantry_boy = st.text_input("Pantry Boy Name", value=st.session_state.entry_pantry, placeholder="Type or select Pantry Boy Name")
    submitted = st.form_submit_button("➕ Submit Entry")

# === Submit Entry Logic ===
if submitted:
    if not coupon_no.isdigit():
        st.error("❌ Coupon Number must be numeric")
    else:
        sheet.append_row([
            str(date), apm_id.strip(), name.strip(), item, qty, action, coupon_no.strip(), pantry_boy.strip()
        ])
        st.success(f"✅ Entry for {item} ({action}) recorded!")

        # Reset only item & qty; keep others
        st.session_state.entry_date = date
        st.session_state.entry_apm = apm_id.strip()
        st.session_state.entry_name = name.strip()
        st.session_state.entry_coupon = coupon_no.strip()
        st.session_state.entry_pantry = pantry_boy.strip()
        st.session_state.entry_time = datetime.now()

        st.rerun()

# === View Entries Section ===
st.markdown("---")
st.subheader("📄 Recent Entries")

if not df.empty:
    st.dataframe(df.tail(20).iloc[::-1].reset_index(drop=True), use_container_width=True)
else:
    st.info("No entries yet.")

