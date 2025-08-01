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

# === Open Sheet ===
SHEET_NAME = "Pantry_Entries"
sheet = client.open(SHEET_NAME).worksheet("Pantry Entries")

# === Load Data ===
data = sheet.get_all_records()
df = pd.DataFrame(data)
df.columns = df.columns.astype(str).str.strip()  # ✅ Clean header names
if df.empty:
    st.warning("⚠️ No data found in the sheet. Please enter at least one record.")
    st.stop()  # Prevent the rest of the app from crashing



st.set_page_config(page_title="Admin Dashboard", layout="wide")
st.title("📊 Pantry Admin Dashboard")

# === Admin Password ===
admin_password = st.text_input("🔐 Enter Admin Password to Edit/Delete", type="password")
stored_password = st.secrets["ADMIN_PASSWORD"]
admin_access = admin_password == stored_password

st.markdown("---")

# === Filter UI ===
with st.expander("🔍 Filters"):
    col1, col2, col3 = st.columns(3)
    with col1:
        apm_filter = st.text_input("APM ID Filter")
    with col2:
        if "Item" in df.columns:
            item_filter = st.selectbox("Item Filter", ["All"] + sorted(df["Item"].dropna().unique()))
        else:
            st.warning("⚠️ 'Item' column not found. Please check your Google Sheet.")
            st.stop()
    with col3:
        action_filter = st.selectbox("Action Filter", ["All", "Issued", "Returned"])

# === Apply Filters ===
filtered_df = df.copy()
if apm_filter:
    filtered_df = filtered_df[filtered_df["APM ID"].astype(str).str.contains(apm_filter, case=False)]
if item_filter != "All":
    filtered_df = filtered_df[filtered_df["Item"] == item_filter]
if action_filter != "All":
    filtered_df = filtered_df[filtered_df["Action"] == action_filter]

st.dataframe(filtered_df, use_container_width=True)

# === Monthly Summary ===
st.markdown("### 📦 Monthly Summary (Issued - Returned)")

if not df.empty:
    summary = (
        df.groupby(["APM ID", "Item", "Action"])["Quantity"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )
    summary["Net Quantity"] = summary.get("Issued", 0) - summary.get("Returned", 0)
    st.dataframe(summary, use_container_width=True)

    # === Download Summary as Excel ===
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        summary.to_excel(writer, index=False, sheet_name="Billing Summary")
    st.download_button(
        label="📥 Download Summary as Excel",
        data=buffer.getvalue(),
        file_name="Monthly_Billing_Summary.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
else:
    st.info("No data available.")

st.markdown("---")

# === Admin Tools: Update / Delete Rows ===
if admin_access:
    st.markdown("### ✏️ Admin Actions (Edit/Delete)")
    row_index = st.number_input("Enter Row Index (starting from 0)", min_value=0, max_value=len(df) - 1)

    if st.button("🗑️ Delete Row"):
        sheet.delete_rows(row_index + 2)  # +2 because of header and 0-index
        st.success("Row deleted. Please refresh the app.")

    with st.form("update_form"):
        new_qty = st.number_input("New Quantity", value=int(df.loc[row_index, "Quantity"]))
        new_action = st.selectbox("New Action", ["Issued", "Returned"])
        update_btn = st.form_submit_button("Update Row")
        if update_btn:
            row_data = df.loc[row_index].tolist()
            row_data[4] = new_qty  # Update Quantity
            row_data[5] = new_action  # Update Action
            sheet.delete_rows(row_index + 2)
            sheet.insert_row(row_data, row_index + 2)
            st.success("Row updated. Please refresh the app.")
else:
    st.warning("🔒 Admin access required to edit or delete entries.")
