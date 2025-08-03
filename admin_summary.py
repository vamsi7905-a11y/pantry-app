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
                st.rerun()
            else:
                st.error("❌ Incorrect password")
    st.stop()

# === Logout ===
st.sidebar.success("✅ Logged in")
if st.sidebar.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.rerun()

# === Load Sheets ===
entries_ws = client.open(ENTRY_SHEET).worksheet("Pantry Entries")
rates_ws = client.open(ENTRY_SHEET).worksheet(RATES_SHEET)
df = pd.DataFrame(entries_ws.get_all_records())
df.columns = df.columns.str.strip()
rates_df = pd.DataFrame(rates_ws.get_all_records())
rates_df.columns = rates_df.columns.str.strip()
rates_dict = dict(zip(rates_df["Item"], rates_df["Rate"]))

if df.empty:
    st.warning("⚠️ No data found in Pantry Entries.")
    st.stop()

df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Coupon No"] = df["Coupon No"].astype(str)

# === View & Filter ===
st.title("📊 Admin Dashboard")
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
row_index = st.number_input("Row Index (starts from 0)", min_value=0, max_value=len(df) - 1, step=1)
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
        row = df.loc[row_index].tolist()
        row[4] = new_qty
        row[5] = new_action
        entries_ws.delete_rows(row_index + 2)
        entries_ws.insert_row(row, row_index + 2)
        st.success("✅ Entry updated.")
        st.rerun()

# === Rates Section ===
st.markdown("### 💰 Item Rates")
st.dataframe(rates_df, use_container_width=True)
with st.form("rates_form"):
    new_item = st.text_input("Item Name")
    new_rate = st.number_input("Rate", step=1, min_value=0)
    submit = st.form_submit_button("➕ Add/Update Rate")
    if submit and new_item:
        items = rates_ws.col_values(1)
        if new_item in items:
            idx = items.index(new_item) + 1
            rates_ws.update_cell(idx, 2, new_rate)
            st.success(f"Updated rate for {new_item}")
        else:
            rates_ws.append_row([new_item, new_rate])
            st.success(f"Added rate for {new_item}")
        st.rerun()

# === Monthly Bill Export ===
st.markdown("---")
st.markdown("### 📥 Download Monthly Bill in Excel Format")

if st.button("Generate Monthly Bill"):
    issued = df[df["Action"] == "Issued"].copy()
    returned = df[df["Action"] == "Returned"].copy()
    returned["Quantity"] = -returned["Quantity"]
    all_entries = pd.concat([issued, returned], ignore_index=True)

    summary = (
        all_entries
        .groupby(["Date", "APM ID", "Coupon No", "Item"], as_index=False)
        ["Quantity"]
        .sum()
    )
    summary = summary[summary["Quantity"] > 0]

    items_list = list(rates_dict.keys())
    bill_rows = []
    for (d, apm, coup), grp in summary.groupby(["Date", "APM ID", "Coupon No"]):
        row = {"DATE": d.date(), "APM ID": apm, "COUPON NO": coup}
        total_amt = 0
        for item in items_list:
            qty = grp.loc[grp["Item"] == item, "Quantity"].sum() if item in grp["Item"].values else 0
            tm = qty * rates_dict.get(item, 0)
            row[item] = qty
            row[f"{item}_TM"] = tm
            total_amt += tm
        row["AMOUNT"] = total_amt
        row["GST 5%"] = round(total_amt * 0.05, 2)
        row["AMOUNT AFTER GST"] = round(total_amt + row["GST 5%"], 2)
        bill_rows.append(row)

    bill_df = pd.DataFrame(bill_rows)
    cols = ["DATE", "APM ID", "COUPON NO"]
    for item in items_list:
        cols += [item, f"{item}_TM"]
    cols += ["AMOUNT", "GST 5%", "AMOUNT AFTER GST"]
    bill_df = bill_df[cols]

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        bill_df.to_excel(writer, index=False, sheet_name="Monthly Bill")
    st.download_button(
        label="📁 Download Monthly Bill Excel",
        data=buffer.getvalue(),
        file_name=f"Monthly_Bill_{datetime.today().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
