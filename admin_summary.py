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

sheet_list = client.openall()
sheet_titles = [s.title for s in sheet_list]
st.write("📄 Sheets your service account can access:", sheet_titles)

# === Open Sheet ===
SHEET_NAME = "Pantry_Entries"
sheet = client.open(SHEET_NAME).worksheet("Pantry Entries")

# === Load Data ===
data = sheet.get_all_records()
df = pd.DataFrame(data)

st.set_page_config(page_title="Admin Dashboard", layout="wide")
st.title("📊 Pantry Admin Dashboard")

# === Password Gate for Admin-Only Features ==
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
        item_filter = st.selectbox("Item Filter", ["All"] + sorted(df["Item"].unique()))
    with col3:
        action_filter = st.selectbox("Action Filter", ["All", "Issued", "Returned"])

filtered_df = df.copy()

if apm_filter:
    filtered_df = filtered_df[filtered_df["APM ID"].str.contains(apm_filter, case=False)]
if item_filter != "All":
    filtered_df = filtered_df[filtered_df["Item"] == item_filter]
if action_filter != "All":
    filtered_df = filtered_df[filtered_df["Action"] == action_filter]

st.dataframe(filtered_df, use_container_width=True)

# === Net Summary ===
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

    # === Download Summary ===
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
            row_data[4] = new_qty  # Update quantity
            row_data[5] = new_action  # Update action
            sheet.delete_rows(row_index + 2)
            sheet.insert_row(row_data, row_index + 2)
            st.success("Row updated. Please refresh the app.")
else:
    st.warning("🔒 Admin access required to edit or delete entries.")
