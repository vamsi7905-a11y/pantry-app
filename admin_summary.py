import streamlit as st
import gspread
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials
from io import BytesIO

# === Authenticate Google Sheets ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

# === Load Sheets ===
SHEET_NAME = "Pantry_Entries"
entries_ws = client.open(SHEET_NAME).worksheet("Pantry Entries")
rates_ws = client.open(SHEET_NAME).worksheet("Rates")

# === Load Entry Data ===
data = entries_ws.get_all_records()
df = pd.DataFrame(data)
df.columns = df.columns.str.strip()
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
                st.stop()
            else:
                st.error("❌ Incorrect password.")
    st.stop()

# === Safe rerun flag ===
if st.session_state.get("refresh_app"):
    st.session_state["refresh_app"] = False
    st.stop()

# === Sidebar ===
st.sidebar.success("✅ Logged in")
if st.sidebar.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.stop()

# === Filter Panel ===
st.title("📊 Admin Billing Dashboard")
st.markdown("### 🔍 Filter Entries")
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df = df[df["Action"] == "Issued"]

filter_option = st.selectbox("Show Entries For:", ["Today", "This Week", "This Month", "All"])
today = pd.Timestamp.today().normalize()

if filter_option == "Today":
    df = df[df["Date"] == today]
elif filter_option == "This Week":
    start_of_week = today - pd.Timedelta(days=today.weekday())
    df = df[(df["Date"] >= start_of_week) & (df["Date"] <= today)]
elif filter_option == "This Month":
    start_of_month = today.replace(day=1)
    df = df[(df["Date"] >= start_of_month) & (df["Date"] <= today)]

# === Pivot Billing Table ===
st.markdown("### 🧾 Final Billing with GST")
pivot = pd.pivot_table(
    df,
    index=["Date", "APM ID", "Coupon No"],
    columns="Item",
    values="Quantity",
    aggfunc="sum",
    fill_value=0
).reset_index()

# Ensure all items exist
for item in rates_dict:
    if item not in pivot.columns:
        pivot[item] = 0

# Calculate totals
amounts = []
for _, row in pivot.iterrows():
    total = sum(row[item] * rates_dict[item] for item in rates_dict)
    amounts.append(total)

pivot["Total Amount"] = amounts
pivot["GST 5%"] = pivot["Total Amount"] * 0.05
pivot["Total After GST"] = pivot["Total Amount"] + pivot["GST 5%"]

# === Add summary row safely ===
summary_row = pivot.select_dtypes(include='number').sum().to_frame().T
for col, val in [("Date", "Total"), ("APM ID", ""), ("Coupon No", "")]:
    if col not in summary_row.columns:
        summary_row.insert(0, col, val)
    else:
        summary_row[col] = val

final_df = pd.concat([pivot, summary_row], ignore_index=True)
st.dataframe(final_df, use_container_width=True)

# === Download Excel ===
buffer = BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    final_df.to_excel(writer, index=False, sheet_name="Billing")

st.download_button(
    label="📥 Download Final Bill (Excel)",
    data=buffer.getvalue(),
    file_name="Pantry_Billing.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

st.markdown("---")

# === Rates Management ===
st.markdown("### 🛠 Manage Item Rates")
st.dataframe(rates_df, use_container_width=True)

with st.form("add_item_form"):
    new_item = st.text_input("Item Name")
    new_rate = st.number_input("Rate", min_value=0, step=1)
    add = st.form_submit_button("Add/Update")
    if add and new_item:
        existing_items = rates_ws.col_values(1)
        if new_item in existing_items:
            row_num = existing_items.index(new_item) + 1
            rates_ws.update_cell(row_num, 2, new_rate)
            st.success(f"✅ Updated rate for '{new_item}'.")
        else:
            rates_ws.append_row([new_item, new_rate])
            st.success(f"✅ Added new item '{new_item}'.")
        st.session_state["refresh_app"] = True
        st.stop()

st.markdown("---")

# === Edit/Delete Entry ===
st.markdown("### ✏️ Edit or Delete Pantry Entry")

if df.empty:
    st.info("No data available.")
    st.stop()

row_index = st.number_input("Enter Row Index to Edit/Delete", min_value=0, max_value=len(df) - 1, step=1)

# Delete
if st.button("🗑️ Delete Entry"):
    entries_ws.delete_rows(row_index + 2)  # +2 for 0-index and header
    st.success("✅ Entry deleted.")
    st.session_state["refresh_app"] = True
    st.stop()

# Update
with st.form("update_form"):
    new_qty = st.number_input("New Quantity", value=int(df.loc[row_index, "Quantity"]), min_value=1)
    new_action = st.selectbox("New Action", ["Issued", "Returned"], index=["Issued", "Returned"].index(df.loc[row_index, "Action"]))
    update_btn = st.form_submit_button("Update Entry")
    if update_btn:
        row_data = df.loc[row_index].to_dict()
        row_data["Quantity"] = new_qty
        row_data["Action"] = new_action
        col_order = df.columns.tolist()
        ordered_data = [row_data[col] for col in col_order]
        entries_ws.delete_rows(row_index + 2)
        entries_ws.insert_row(ordered_data, row_index + 2)
        st.success("✅ Entry updated.")
        st.session_state["refresh_app"] = True
        st.stop()
