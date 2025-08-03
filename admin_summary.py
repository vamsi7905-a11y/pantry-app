import streamlit as st
import gspread
import pandas as pd
import json
import os
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from io import BytesIO

# === Google Sheets Auth ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

ENTRY_SHEET = "Pantry_Entries"
RATES_SHEET = "Rates"

st.set_page_config(page_title="Admin Panel", layout="wide")

# === Login ===
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Admin Login")
    with st.form("login_form"):
        pwd = st.text_input("Enter Admin Password", type="password")
        login = st.form_submit_button("Login")
        if login:
            if pwd == st.secrets["ADMIN_PASSWORD"]:
                st.session_state.logged_in = True
                st.success("✅ Logged in successfully!")
                st.rerun()
            else:
                st.error("❌ Incorrect password")
    st.stop()

# === Logout ===
st.sidebar.success("✅ Logged in")
if st.sidebar.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.success("✅ Logged out successfully!")
    st.rerun()

# === Load Sheets ===
entries_ws = client.open(ENTRY_SHEET).worksheet("Pantry Entries")
rates_ws = client.open(ENTRY_SHEET).worksheet(RATES_SHEET)

df = pd.DataFrame(entries_ws.get_all_records())
df.columns = df.columns.str.strip()
if df.empty:
    st.warning("⚠️ No data found in Pantry Entries.")
    st.stop()

rates_df = pd.DataFrame(rates_ws.get_all_records())
rates_df.columns = rates_df.columns.str.strip()
rates_dict = dict(zip(rates_df['Item'], rates_df['Rate']))

# === View & Filter ===
st.title("📊 Admin Dashboard")
st.subheader("📋 Pantry Entry Records")

df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

col1, col2 = st.columns(2)
with col1:
    apm_filter = st.text_input("🔎 Filter by APM ID")
    name_filter = st.text_input("🔎 Filter by Name")
with col2:
    item_filter = st.selectbox("🔎 Filter by Item", ["All"] + sorted(df["Item"].unique()))
    action_filter = st.selectbox("🔎 Filter by Action", ["All", "Issued", "Returned"])

if apm_filter:
    df = df[df["APM ID"].astype(str).str.contains(apm_filter, case=False)]
if name_filter:
    df = df[df["Name"].astype(str).str.contains(name_filter, case=False)]
if item_filter != "All":
    df = df[df["Item"] == item_filter]
if action_filter != "All":
    df = df[df["Action"] == action_filter]

st.dataframe(df.reset_index(drop=True), use_container_width=True)

# === Edit/Delete Entries ===
st.markdown("### ✏️ Edit or Delete Entry")

row_index = st.number_input("Row Index (starts at 0)", min_value=0, max_value=len(df)-1, step=1)

if st.button("🗑️ Delete Entry"):
    entries_ws.delete_rows(row_index + 2)
    st.success("✅ Entry deleted.")
    st.rerun()

with st.form("edit_form"):
    new_qty = st.number_input("New Quantity", value=int(df.loc[row_index, "Quantity"]), min_value=1)
    new_action = st.selectbox("New Action", ["Issued", "Returned"],
                              index=["Issued", "Returned"].index(df.loc[row_index, "Action"]))
    update = st.form_submit_button("✅ Update Entry")
    if update:
        updated_row = df.loc[row_index].tolist()
        updated_row[4] = new_qty
        updated_row[5] = new_action
        entries_ws.delete_rows(row_index + 2)
        entries_ws.insert_row(updated_row, row_index + 2)
        st.success("✅ Entry updated.")
        st.rerun()

# === Rates Section ===
st.markdown("### 💰 Manage Item Rates")
st.dataframe(rates_df, use_container_width=True)

with st.form("rates_form"):
    new_item = st.text_input("Item Name")
    new_rate = st.number_input("Rate", step=1, min_value=0)
    submit = st.form_submit_button("➕ Add/Update Rate")
    if submit and new_item:
        existing_items = rates_ws.col_values(1)
        if new_item in existing_items:
            row_num = existing_items.index(new_item) + 1
            rates_ws.update_cell(row_num, 2, new_rate)
            st.success(f"✅ Updated rate for {new_item}")
        else:
            rates_ws.append_row([new_item, new_rate])
            st.success(f"✅ Added {new_item} with rate ₹{new_rate}")
        st.rerun()
