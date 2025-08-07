import streamlit as st
import gspread
import pandas as pd
import json
import os
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from io import BytesIO

# === Auth ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

# === Sheets ===
ENTRY_SHEET = "Pantry_Entries"
RATES_SHEET = "Rates"
entries_ws = client.open(ENTRY_SHEET).worksheet("Pantry Entries")
rates_ws = client.open(ENTRY_SHEET).worksheet(RATES_SHEET)

# === Config ===
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

# === Load Data ===
df = pd.DataFrame(entries_ws.get_all_records())
df.columns = df.columns.str.strip()

# === Handle empty sheet safely ===
if df.empty or df.isnull().all().all():
    st.warning("⚠️ No data found.")
    st.stop()

# === Fix Date column safely ===
try:
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
except Exception as e:
    st.warning(f"⚠️ Error parsing Date column: {e}")

df["Coupon No"] = df["Coupon No"].astype(str)

# === Rates ===
rates_df = pd.DataFrame(rates_ws.get_all_records())
rates_df.columns = rates_df.columns.str.strip()
rates_dict = dict(zip(rates_df["Item"], rates_df["Rate"]))

# === Dashboard ===
st.title("📊 Admin Dashboard")

# === Filters ===
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

# === Edit/Delete ===
st.markdown("### ✏️ Edit or Delete Entry")
row_index = st.number_input("Row Index (starts from 0)", min_value=0, max_value=len(df) - 1, step=1)

if st.button("🗑️ Delete Entry"):
    entries_ws.delete_rows(row_index + 2)
    st.success("✅ Entry deleted.")
    st.rerun()

with st.form("edit_form"):
    new_qty = st.number_input("New Quantity", value=int(df.iloc[row_index]["Quantity"]), min_value=1)
    new_action = st.selectbox("New Action", ["Issued", "Returned"],
                              index=["Issued", "Returned"].index(df.iloc[row_index]["Action"]))
    update = st.form_submit_button("✅ Update Entry")
    if update:
        row = df.iloc[row_index].tolist()
        row[4] = new_qty
        row[5] = new_action
        entries_ws.delete_rows(row_index + 2)
        entries_ws.insert_row(row, row_index + 2)
        st.success("✅ Entry updated.")
        st.rerun()

# === Rates ===
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
            st.success(f"✅ Updated rate for {new_item}")
        else:
            rates_ws.append_row([new_item, new_rate])
            st.success(f"✅ Added rate for {new_item}")
        st.rerun()

# === Monthly Bill ===
st.markdown("### 📥 Download Monthly Bill")

today = datetime.today()
selected_year = st.selectbox("Select Year", list(range(2023, today.year + 1)), index=today.year - 2023)
selected_month = st.selectbox("Select Month", list(range(1, 13)), index=today.month - 1)

df_month = df[(pd.to_datetime(df["Date"]).dt.year == selected_year) & (pd.to_datetime(df["Date"]).dt.month == selected_month)]

if df_month.empty:
    st.warning("⚠️ No entries found for selected month.")

if st.button("📁 Generate & Download Bill"):
    issued = df_month[df_month["Action"] == "Issued"].copy()
    returned = df_month[df_month["Action"] == "Returned"].copy()
    returned["Quantity"] = -returned["Quantity"]
    all_entries = pd.concat([issued, returned], ignore_index=True)

    summary = (
        all_entries
        .groupby(["Date", "APM ID", "Coupon No", "Item"], as_index=False)["Quantity"]
        .sum()
    )
    summary = summary[summary["Quantity"] > 0]

    item_names = list(rates_dict.keys())
    bill_rows = []
    for (dt, apm, coup), grp in summary.groupby(["Date", "APM ID", "Coupon No"]):
        row = {"DATE": dt, "APM ID": apm, "COUPON NO": coup}
        total = 0
        for item in item_names:
            qty = grp.loc[grp["Item"] == item, "Quantity"].sum() if item in grp["Item"].values else 0
            rate = rates_dict.get(item, 0)
            tm = qty * rate
            row[item] = qty
            row[f"{item}_TM"] = tm
            total += tm
        row["AMOUNT"] = total
        row["GST 5%"] = round(total * 0.05, 2)
        row["AMOUNT AFTER GST"] = round(total + row["GST 5%"], 2)
        bill_rows.append(row)

    bill_df = pd.DataFrame(bill_rows)
    col_order = ["DATE", "APM ID", "COUPON NO"]
    for item in item_names:
        col_order += [item, f"{item}_TM"]
    col_order += ["AMOUNT", "GST 5%", "AMOUNT AFTER GST"]
    bill_df = bill_df[col_order]

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        bill_df.to_excel(writer, sheet_name="Monthly Bill", index=False)

    st.download_button(
        label="⬇️ Download Monthly Bill",
        data=buffer.getvalue(),
        file_name=f"Monthly_Bill_{selected_year}_{selected_month:02}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
