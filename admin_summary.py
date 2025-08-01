# admin_summary.py (Final Version)

import streamlit as st
import gspread
import pandas as pd
import json
import os
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from io import BytesIO

# === Authenticate Google Sheets ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

# === Load Sheets ===
ENTRY_SHEET = "Pantry_Entries"
RATES_SHEET = "Rates"
entries = client.open(ENTRY_SHEET).worksheet("Pantry Entries")
rates_ws = client.open(ENTRY_SHEET).worksheet(RATES_SHEET)

# === Load Entry Data ===
data = entries.get_all_records()
df = pd.DataFrame(data)
df.columns = df.columns.astype(str).str.strip()
if df.empty:
    st.warning("⚠️ No data found in Pantry Entries sheet.")
    st.stop()

# === Load Item Rates ===
rates_data = rates_ws.get_all_records()
rates_df = pd.DataFrame(rates_data)
rates_df.columns = rates_df.columns.str.strip()
rates_dict = dict(zip(rates_df['Item'], rates_df['Rate']))

# === Login System ===
st.set_page_config(page_title="Admin Panel", layout="wide")

# Safe rerun trigger for app refresh
if "refresh_app" in st.session_state:
    del st.session_state["refresh_app"]
    st.experimental_rerun()


if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    with st.form("login_form"):
        st.title("🔐 Admin Login")
        pwd = st.text_input("Enter Admin Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if pwd == st.secrets["ADMIN_PASSWORD"]:
                st.session_state.logged_in = True
                st.success("✅ Logged in successfully.")
                st.experimental_rerun()
            else:
                st.error("❌ Incorrect password.")
    st.stop()

# === Logout ===
st.sidebar.success("✅ Logged in")
if st.sidebar.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.experimental_rerun()

st.title("📊 Admin Billing Dashboard")
st.markdown("---")

# === Billing Summary (Pivoted Format) ===
st.markdown("### 🧾 Final Billing with GST")
df = df[df["Action"] == "Issued"]

pivot = pd.pivot_table(
    df,
    index=["Date", "APM ID", "Coupon No"],
    columns="Item",
    values="Quantity",
    aggfunc="sum",
    fill_value=0
).reset_index()

# Add rate and amount calculations
for item in pivot.columns:
    if item in rates_dict:
        pivot[item] = pivot[item].astype(int)

# Compute total per row
amounts = []
for i, row in pivot.iterrows():
    total = 0
    for item in rates_dict:
        qty = row.get(item, 0)
        rate = rates_dict[item]
        total += qty * rate
    amounts.append(total)

pivot["total amount"] = amounts
pivot["gst 5%"] = pivot["total amount"] * 0.05
pivot["total amount after gst"] = pivot["total amount"] + pivot["gst 5%"]

st.dataframe(pivot, use_container_width=True)

# === Download Final Bill ===
buffer = BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    pivot.to_excel(writer, index=False, sheet_name="Final Billing")

st.download_button(
    label="📥 Download Final Bill (Excel)",
    data=buffer.getvalue(),
    file_name="Pantry_Final_Billing.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

st.markdown("---")

# === Rates Management ===
st.markdown("### 🛠 Item Rates")
st.dataframe(rates_df, use_container_width=True)

with st.form("add_item"):
    new_item = st.text_input("Add New Item")
    new_rate = st.number_input("Rate", min_value=0, step=1)
    add = st.form_submit_button("Add/Update")
    if add and new_item:
    existing_items = rates_ws.col_values(1)
    if new_item in existing_items:
        row_num = existing_items.index(new_item) + 1
        rates_ws.update_cell(row_num, 2, new_rate)
        st.success(f"✅ Updated rate for {new_item}.")
    else:
        rates_ws.append_row([new_item, new_rate])
        st.success(f"✅ Added {new_item} to Rates.")
    st.session_state["refresh_app"] = True  # Safe rerun flag
