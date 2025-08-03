# === FINAL entry_app.py ===
import streamlit as st
import gspread
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials

# === Google Sheets Setup ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

# === Open Sheet ===
SHEET_NAME = "Pantry_Entries"
sheet = client.open(SHEET_NAME).worksheet("Pantry Entries")

data = sheet.get_all_records()
df = pd.DataFrame(data)
df.columns = df.columns.astype(str).str.strip()

# === Streamlit Config ===
st.set_page_config(page_title="Pantry Entry", layout="wide")
st.title("🦪 Pantry Coupon Entry System")
st.markdown("---")

# === Session Management ===
if "form_data" not in st.session_state or (
    "last_update" in st.session_state and
    datetime.now() - st.session_state.last_update > timedelta(minutes=10)
):
    st.session_state.form_data = {
        "date": datetime.today().date(),
        "apm_id": "",
        "name": "",
        "coupon_no": "",
        "pantry_boy": "",
        "item": "",
        "qty": 1
    }
    st.session_state.last_update = datetime.now()

existing_apms = sorted(df["APM ID"].dropna().astype(str).unique()) if "APM ID" in df.columns else []
existing_names = sorted(df["Name"].dropna().astype(str).unique()) if "Name" in df.columns else []
existing_pantries = sorted(df["Pantry Boy"].dropna().astype(str).unique()) if "Pantry Boy" in df.columns else []

# === Entry Form ===
st.subheader("📥 New Entry")

with st.form("entry_form"):
    col1, col2, col3 = st.columns(3)

    with col1:
        date = st.date_input("Date", value=st.session_state.form_data["date"])
        apm_id = st.text_input("APM ID", value=st.session_state.form_data["apm_id"], placeholder="Type APM ID")
        if existing_apms:
            st.caption("Suggestions: " + ", ".join(existing_apms[:10]))

    with col2:
        name = st.text_input("Name", value=st.session_state.form_data["name"], placeholder="Type Name")
        if existing_names:
            st.caption("Suggestions: " + ", ".join(existing_names[:10]))

        coupon_no = st.text_input("Coupon Number", value=st.session_state.form_data["coupon_no"])
        if coupon_no and not coupon_no.isdigit():
            st.warning("Coupon Number must be numeric")

    with col3:
        item = st.selectbox("Item", [
            "Tea", "Coffee", "Coke", "Veg S/W", "Non S/W", "Biscuit",
            "Juice", "Lays", "Dry Fruits", "Fruit Bowl", "Samosa",
            "Idli/Wada", "EFAAS & LIVIN JUICE", "Mentos"
        ])
        qty = st.number_input("Quantity", min_value=1, value=1)
        action = st.selectbox("Action", ["Issued", "Returned"])

    pantry_boy = st.text_input("Pantry Boy", value=st.session_state.form_data["pantry_boy"], placeholder="Type Pantry Boy Name")
    if existing_pantries:
        st.caption("Suggestions: " + ", ".join(existing_pantries[:10]))

    submitted = st.form_submit_button("➕ Submit Entry")

if submitted:
    if not coupon_no.isdigit():
        st.error("❌ Coupon Number must be numeric")
    else:
        sheet.append_row([
            str(date),
            apm_id.strip(),
            name.strip(),
            item,
            qty,
            action,
            coupon_no.strip(),
            pantry_boy.strip()
        ])
        st.success(f"✅ Entry for {item} ({action}) recorded!")

        st.session_state.form_data.update({
            "date": date,
            "apm_id": apm_id.strip(),
            "name": name.strip(),
            "coupon_no": coupon_no.strip(),
            "pantry_boy": pantry_boy.strip(),
            "item": "",
            "qty": 1
        })
        st.session_state.last_update = datetime.now()

        st.stop()
