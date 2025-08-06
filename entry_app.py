import streamlit as st
import gspread
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials

# === Auto-clear Item & Quantity after rerun ===
if "entry_success" in st.session_state and st.session_state.entry_success:
    st.session_state.entry_item = "-- Select Item --"
    st.session_state.entry_qty = 0
    st.session_state.entry_success = False
    st.rerun()

# === Google Sheets Auth ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

# === Spreadsheet ===
SHEET_NAME = "Pantry_Entries"
sheet = client.open(SHEET_NAME).worksheet("Pantry Entries")

# === Load Data ===
data = sheet.get_all_records()
df = pd.DataFrame(data)

# Safe column assignment if data is empty
expected_columns = ["Date", "APM ID", "Name", "Item", "Quantity", "Action", "Coupon No", "Pantry Boy", "Entry Time"]
if df.empty:
    df = pd.DataFrame(columns=expected_columns)
else:
    try:
        df.columns = df.columns.str.strip()
    except Exception:
        df.columns = expected_columns

# === Streamlit Page ===
st.set_page_config(page_title="Pantry Entry", layout="wide")
st.title("🥪 Pantry Coupon Entry System")
st.markdown("---")

# === Session State Defaults ===
if "entry_time" not in st.session_state:
    st.session_state.entry_time = datetime.now()

# Auto-clear all fields after 10 minutes
if "entry_date" not in st.session_state or datetime.now() - st.session_state.entry_time > timedelta(minutes=10):
    st.session_state.entry_date = datetime.today().date()
    st.session_state.entry_apm = ""
    st.session_state.entry_name = ""
    st.session_state.entry_coupon = ""
    st.session_state.entry_pantry = ""
    st.session_state.entry_item = "-- Select Item --"
    st.session_state.entry_qty = 0
    st.session_state.entry_time = datetime.now()

# === Item List ===
item_list = ["-- Select Item --", "Tea", "Coffee", "Coke", "Veg S/W", "Non S/W", "Biscuit",
             "Juice", "Lays", "Dry Fruits", "Fruit Bowl", "Samosa",
             "Idli/Wada", "EFAAS & LIVIN JUICE", "Mentos"]

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
        item = st.selectbox("Item", item_list, index=item_list.index(st.session_state.entry_item), key="entry_item")
        qty = st.number_input("Quantity", min_value=0, value=st.session_state.entry_qty, key="entry_qty")
        action = st.selectbox("Action", ["Issued", "Returned"])

    pantry_boy = st.text_input("Pantry Boy Name", value=st.session_state.entry_pantry)
    submitted = st.form_submit_button("➕ Submit Entry")

# === Submit Entry Logic ===
if submitted:
    if not coupon_no.isdigit():
        st.error("❌ Coupon Number must be numeric")
    elif item == "-- Select Item --":
        st.warning("⚠️ Please select a valid item.")
    elif qty == 0:
        st.warning("⚠️ Quantity should be more than 0.")
    else:
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([
                date.strftime("%Y-%m-%d"), apm_id.strip(), name.strip(), item, qty, action,
                coupon_no.strip(), pantry_boy.strip(), now  # 'Entry Time'
            ])
            st.success(f"✅ Entry for {item} ({action}) recorded!")

            # Preserve other fields
            st.session_state.entry_date = date
            st.session_state.entry_apm = apm_id.strip()
            st.session_state.entry_name = name.strip()
            st.session_state.entry_coupon = coupon_no.strip()
            st.session_state.entry_pantry = pantry_boy.strip()
            st.session_state.entry_time = datetime.now()
            st.session_state.entry_success = True

        except Exception as e:
            st.error(f"❌ Failed to record entry: {e}")

# === View Entries Section ===
st.markdown("---")
st.subheader("📄 Recent Entries")

if not df.empty:
    st.dataframe(df.tail(20).iloc[::-1].reset_index(drop=True), use_container_width=True)
else:
    st.info("No entries yet.")
