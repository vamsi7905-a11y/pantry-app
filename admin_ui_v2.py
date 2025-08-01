# admin_ui_v2.py – Improved Admin Interface with Filters + Inline Edit/Delete

import streamlit as st
import gspread
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials

# === Authenticate Google Sheets ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

# === Setup ===
st.set_page_config(page_title="Admin Entry Manager", layout="wide")

ENTRY_SHEET = "Pantry_Entries"
entries_ws = client.open(ENTRY_SHEET).worksheet("Pantry Entries")
data = entries_ws.get_all_records()
df = pd.DataFrame(data)
df.columns = df.columns.str.strip()

if df.empty:
    st.warning("⚠️ No data found.")
    st.stop()

# === Filters ===
st.title("📋 Pantry Entry Manager")
with st.expander("🔍 Filter Entries"):
    filter_option = st.selectbox("Show Entries For:", ["All", "Today", "This Week", "This Month"])

    today = datetime.today().date()
    if filter_option == "Today":
        df = df[pd.to_datetime(df["Date"]).dt.date == today]
    elif filter_option == "This Week":
        start = today - timedelta(days=today.weekday())
        df = df[(pd.to_datetime(df["Date"]).dt.date >= start)]
    elif filter_option == "This Month":
        df = df[pd.to_datetime(df["Date"]).dt.month == today.month]

# === Display Entries ===
st.markdown("---")
st.subheader("🧾 Entries")

if df.empty:
    st.info("No entries match the selected filter.")
else:
    for i, row in df.iterrows():
        with st.expander(f"{row['Date']} | {row['APM ID']} | {row['Item']} ({row['Quantity']})"):
            st.write(row)
            col1, col2 = st.columns(2)

            if col1.button(f"✏️ Edit", key=f"edit_{i}"):
                st.session_state.edit_row = i
            if col2.button(f"🗑️ Delete", key=f"delete_{i}"):
                entries_ws.delete_rows(i + 2)
                st.success("✅ Entry deleted. Please refresh.")
                st.experimental_rerun()

# === Edit Form ===
if "edit_row" in st.session_state:
    st.markdown("---")
    st.subheader("✏️ Edit Entry")
    row = df.loc[st.session_state.edit_row]

    with st.form("edit_form"):
        new_qty = st.number_input("Quantity", value=int(row["Quantity"]))
        new_action = st.selectbox("Action", ["Issued", "Returned"], index=["Issued", "Returned"].index(row["Action"]))
        submitted = st.form_submit_button("Save Changes")

        if submitted:
            row_data = row.tolist()
            row_data[4] = new_qty
            row_data[5] = new_action
            entries_ws.delete_rows(st.session_state.edit_row + 2)
            entries_ws.insert_row(row_data, st.session_state.edit_row + 2)
            st.success("✅ Entry updated.")
            del st.session_state["edit_row"]
            st.experimental_rerun()

st.markdown("---")
st.caption("UI Version 2 • Inline editing • Week/Month filtering")
