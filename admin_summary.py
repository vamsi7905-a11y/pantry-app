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

# === Page Setup ===
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
if df.empty:
    st.warning("⚠️ No data found in Pantry Entries.")
    st.stop()

df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Coupon No"] = df["Coupon No"].astype(str).str.strip()
df["Rate"] = df["Item"].map(dict(rates_ws.get_all_values()[1:]))

# === Apply Filter ===
st.title("📊 Admin Dashboard")
col1, col2 = st.columns(2)
with col1:
    apm_filter = st.text_input("Filter by APM ID")
    name_filter = st.text_input("Filter by Name")
with col2:
    item_filter = st.selectbox("Filter by Item", ["All"] + sorted(df["Item"].unique()))
    action_filter = st.selectbox("Filter by Action", ["All", "Issued", "Returned"])

if apm_filter:
    df = df[df["APM ID"].astype(str).str.contains(apm_filter, case=False)]
if name_filter:
    df = df[df["Name"].astype(str).str.contains(name_filter, case=False)]
if item_filter != "All":
    df = df[df["Item"] == item_filter]
if action_filter != "All":
    df = df[df["Action"] == action_filter]

st.dataframe(df.reset_index(drop=True), use_container_width=True)

# === Bill Format Matching Uploaded Sheet ===
st.markdown("### 📥 Download Monthly Bill in Excel Format")

df["Quantity"] = df["Quantity"].astype(float)
df["Rate"] = df["Item"].map(lambda x: float(dict(rates_ws.get_all_records()).get(x, 0)))
df["Signed Qty"] = df.apply(lambda row: -row["Quantity"] if row["Action"] == "Returned" else row["Quantity"], axis=1)

# Sum signed quantities
grouped = df.groupby(["Date", "APM ID", "Name", "Coupon No", "Item"], as_index=False)["Signed Qty"].sum()

# Add rate and tm
grouped["Rate"] = grouped["Item"].map(dict(rates_ws.get_all_records()))
grouped["Rate"] = grouped["Rate"].astype(float)
grouped["tm"] = grouped["Signed Qty"] * grouped["Rate"]

# Reorder and rename to match your format
final_bill = grouped.rename(columns={
    "Date": "Date",
    "APM ID": "APM ID",
    "Name": "Name",
    "Coupon No": "Coupon Number",
    "Item": "Item",
    "Signed Qty": "Qty",
    "Rate": "Rate",
    "tm": "TM"
})[["Date", "APM ID", "Name", "Coupon Number", "Item", "Qty", "Rate", "TM"]]

# === Export to Excel ===
buffer = BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    final_bill.to_excel(writer, index=False, sheet_name="Monthly Bill")

st.download_button(
    label="📁 Download Monthly Bill Excel",
    data=buffer.getvalue(),
    file_name="Monthly_Bill.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
