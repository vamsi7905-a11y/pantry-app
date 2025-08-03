# === FINAL admin_summary.py ===
import streamlit as st
import gspread
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials
from io import BytesIO

# === Authenticate ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

ENTRY_SHEET = "Pantry_Entries"
RATES_SHEET = "Rates"

# === Streamlit Config ===
st.set_page_config(page_title="Admin Panel", layout="wide")

# === Login System ===
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
                st.stop()
            else:
                st.error("❌ Incorrect password")
    st.stop()

# === Logout ===
st.sidebar.success("✅ Logged in")
if st.sidebar.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.success("✅ Logged out successfully!")
    st.stop()

# === Load Fresh Data ===
entries = client.open(ENTRY_SHEET).worksheet("Pantry Entries")
rates_ws = client.open(ENTRY_SHEET).worksheet(RATES_SHEET)

entry_data = entries.get_all_records()
df = pd.DataFrame(entry_data)
df.columns = df.columns.str.strip()
if df.empty:
    st.warning("No data found.")
    st.stop()

rates_data = rates_ws.get_all_records()
rates_df = pd.DataFrame(rates_data)
rates_df.columns = rates_df.columns.str.strip()
rates_dict = dict(zip(rates_df['Item'], rates_df['Rate']))

# === Filter ===
st.title("📊 Admin Billing Dashboard")
st.markdown("---")
st.markdown("### 🔍 Filter Entries")
filter_option = st.selectbox("Show Entries For:", ["Today", "This Week", "This Month", "All"])

df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df = df[df["Action"] == "Issued"]

today = pd.Timestamp.today().normalize()
if filter_option == "Today":
    df = df[df["Date"] == today]
elif filter_option == "This Week":
    start = today - pd.Timedelta(days=today.weekday())
    df = df[(df["Date"] >= start) & (df["Date"] <= today)]
elif filter_option == "This Month":
    start = today.replace(day=1)
    df = df[(df["Date"] >= start) & (df["Date"] <= today)]

# === Pivot & Billing ===
st.markdown("### 🧾 Final Billing with GST")
pivot = pd.pivot_table(
    df,
    index=["Date", "APM ID", "Coupon No"],
    columns="Item",
    values="Quantity",
    aggfunc="sum",
    fill_value=0
).reset_index()

amounts = []
for _, row in pivot.iterrows():
    total = sum(row.get(item, 0) * rates_dict.get(item, 0) for item in rates_dict)
    amounts.append(total)

pivot["total amount"] = amounts
pivot["gst 5%"] = pivot["total amount"] * 0.05
pivot["total amount after gst"] = pivot["total amount"] + pivot["gst 5%"]

st.dataframe(pivot, use_container_width=True)

# === Download ===
buffer = BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    pivot.to_excel(writer, index=False, sheet_name="Final Billing")

st.download_button(
    label="📥 Download Final Bill (Excel)",
    data=buffer.getvalue(),
    file_name="Pantry_Final_Billing.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# === Rates Table ===
st.markdown("---")
st.markdown("### 🛠 Item Rates")
st.dataframe(rates_df, use_container_width=True)

with st.form("add_item"):
    new_item = st.text_input("Add New Item")
    new_rate = st.number_input("Rate", min_value=0, step=1)
    add = st.form_submit_button("Add/Update")

    if add and new_item:
        existing_items = rates_ws.col_values(1)
        if new_item in existing_items:
            row = existing_items.index(new_item) + 1
            rates_ws.update_cell(row, 2, new_rate)
            st.success(f"Updated rate for {new_item}.")
        else:
            rates_ws.append_row([new_item, new_rate])
            st.success(f"Added {new_item} to Rates.")
        st.stop()

# === Edit/Delete Section ===
st.markdown("---")
st.markdown("### ✏️ Edit/Delete Entry")
row_index = st.number_input("Enter Row Index (starts from 0)", min_value=0, max_value=len(df)-1, step=1)

if st.button("🗑️ Delete Entry"):
    entries.delete_rows(row_index + 2)
    st.success("Entry deleted. Please refresh.")

with st.form("update_entry"):
    new_qty = st.number_input("New Quantity", value=int(df.loc[row_index, "Quantity"]), min_value=1)
    new_action = st.selectbox("New Action", ["Issued", "Returned"], index=["Issued", "Returned"].index(df.loc[row_index, "Action"]))
    submit = st.form_submit_button("Update Entry")

    if submit:
        updated_row = df.loc[row_index].tolist()
        updated_row[4] = new_qty
        updated_row[5] = new_action
        entries.delete_rows(row_index + 2)
        entries.insert_row(updated_row, row_index + 2)
        st.success("Entry updated.")
