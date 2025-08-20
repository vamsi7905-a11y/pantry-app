# import streamlit as st
# import gspread
# import pandas as pd
# import json
# import os
# from datetime import datetime, timedelta
# from oauth2client.service_account import ServiceAccountCredentials

# # ================= PIN PROTECTION =================
# ENTRY_APP_PIN = os.environ.get("ENTRY_APP_PIN", "")
# pin_input = st.text_input("🔐 Enter Access PIN", type="password")
# if pin_input != ENTRY_APP_PIN:
#     st.warning("Please enter a valid PIN to access the Entry Form.")
#     st.stop()

# # ================= GOOGLE SHEETS =================
# scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])
# creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
# client = gspread.authorize(creds)

# SHEET_NAME = "Pantry_Entries"
# sheet = client.open(SHEET_NAME).worksheet("Pantry Entries")

# # ================= DATA LOADING =================
# data = sheet.get_all_records()
# df = pd.DataFrame(data)

# expected_columns = ["Date", "APM ID", "Name", "Item", "Quantity", "Action", "Coupon No", "Pantry Boy", "Entry Time"]
# if df.empty:
#     df = pd.DataFrame(columns=expected_columns)
# else:
#     try:
#         df.columns = df.columns.str.strip()
#     except Exception:
#         df.columns = expected_columns

# # ================= PAGE CONFIG =================
# st.set_page_config(page_title="Pantry Entry", layout="wide")
# st.title("🥪 Pantry Coupon Entry System")
# st.markdown("---")

# # ================= SESSION STATE DEFAULTS =================
# if "entry_time" not in st.session_state:
#     st.session_state.entry_time = datetime.now()

# if "reset_fields" not in st.session_state:
#     st.session_state.reset_fields = False

# # --- Auto-reset Item & Qty after successful submission ---
# if st.session_state.reset_fields:
#     st.session_state.entry_item = "-- Select Item --"
#     st.session_state.entry_qty = 0
#     st.session_state.reset_fields = False

# # --- Auto-clear ALL fields after 10 minutes ---
# if "entry_date" not in st.session_state or datetime.now() - st.session_state.entry_time > timedelta(minutes=10):
#     st.session_state.entry_date = datetime.today().date()
#     st.session_state.entry_apm = ""
#     st.session_state.entry_name = ""
#     st.session_state.entry_coupon = ""
#     st.session_state.entry_pantry = ""
#     st.session_state.entry_item = "-- Select Item --"
#     st.session_state.entry_qty = 0
#     st.session_state.entry_time = datetime.now()

# # ================= ITEM LIST =================
# try:
#     items_sheet = client.open(SHEET_NAME).worksheet("Rates")
#     items_data = items_sheet.get_all_records()
#     item_list_from_sheet = [row["Item"] for row in items_data if row.get("Item")]
#     item_list = ["-- Select Item --"] + item_list_from_sheet
# except Exception as e:
#     st.warning(f"⚠️ Failed to load item list from sheet: {e}")
#     item_list = [
#         "-- Select Item --", "Tea", "Coffee", "Coke", "Veg Sandwich", "Chicken Sandwich",
#         "Biscuit", "Juice", "Lays", "Dry Fruits", "Fruit Bowl", "Samosa",
#         "Idli/Wada", "EFAAS & LIVIN JUICE", "Mentos"
#     ]

# # ================= ENTRY FORM =================
# st.subheader("📥 New Entry")

# with st.form("entry_form"):
#     col1, col2, col3 = st.columns(3)

#     with col1:
#         date = st.date_input("Date", key="entry_date")
#         apm_id = st.text_input("APM ID", key="entry_apm")

#     with col2:
#         name = st.text_input("Name", key="entry_name")
#         coupon_no = st.text_input("Coupon Number", key="entry_coupon")
#         if coupon_no and not coupon_no.isdigit():
#             st.warning("Coupon Number must be numeric")

#     with col3:
#         item = st.selectbox(
#             "Item",
#             item_list,
#             index=item_list.index(st.session_state.entry_item) if st.session_state.entry_item in item_list else 0,
#             key="entry_item"
#         )
#         qty = st.number_input("Quantity", min_value=0, key="entry_qty")
#         action = st.selectbox("Action", ["Issued", "Returned"], key="entry_action")

#     pantry_boy = st.text_input("Pantry Boy Name", key="entry_pantry")

#     submitted = st.form_submit_button("➕ Submit Entry")

# # ================= SUBMIT LOGIC =================
# if submitted:
#     if not coupon_no.isdigit():
#         st.error("❌ Coupon Number must be numeric")
#     elif item == "-- Select Item --":
#         st.warning("⚠️ Please select a valid item.")
#     elif qty == 0:
#         st.warning("⚠️ Quantity should be more than 0.")
#     else:
#         try:
#             entry_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#             formatted_date = date.strftime("%d-%m-%Y")
#             sheet.append_row([
#                 formatted_date, apm_id.strip(), name.strip(), item, qty, action,
#                 coupon_no.strip(), pantry_boy.strip(), entry_time
#             ])

#             st.success(f"✅ Entry for {item} ({action}) recorded!")

#             # Reset only Item & Qty → keep the rest persistent
#             st.session_state.reset_fields = True
#             st.rerun()

#         except Exception as e:
#             st.error(f"❌ Failed to record entry: {e}")

# # ================= RECENT ENTRIES =================
# st.markdown("---")
# st.subheader("📄 Recent Entries")

# if not df.empty:
#     st.dataframe(df.tail(20).iloc[::-1].reset_index(drop=True), use_container_width=True)
# else:
#     st.info("No entries yet.")


# entry_app.py
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# -----------------------
# Connect to Google Sheet
# -----------------------
@st.cache_resource
def connect_gsheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scope
    )
    client = gspread.authorize(creds)
    sheet = client.open("Pantry_Entries").sheet1   # <-- change to your sheet name
    return sheet

sheet = connect_gsheet()

# -----------------------
# Streamlit App
# -----------------------
st.set_page_config(page_title="Pantry Entry", page_icon="🍵", layout="centered")

st.markdown("## 📝 New Entry")

with st.form("entry_form", clear_on_submit=False):

    # Date & Time
    entry_date = st.date_input("Date", datetime.now().date())
    entry_time = datetime.now().strftime("%H:%M:%S")

    # Name & APM ID
    name = st.text_input("Name")
    apm_id = st.text_input("APM ID")

    # Coupon Number
    coupon_number = st.text_input("Coupon Number")

    # Pantry Boy
    pantry_boy = st.text_input("Pantry Boy Name")

    # Action
    action = st.selectbox("Action", ["Issued", "Returned"])

    st.markdown("### Items")

    if "items" not in st.session_state:
        st.session_state["items"] = []

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        item = st.text_input("Item", key="item_input")
    with col2:
        qty = st.number_input("Quantity", min_value=1, step=1, key="qty_input")
    with col3:
        st.write("")  # spacer
        if st.button("➕ Add Item"):
            if item and qty > 0:
                st.session_state["items"].append({"item": item, "qty": qty})
                st.session_state["item_input"] = ""
                st.session_state["qty_input"] = 1

    # Show current items
    if st.session_state["items"]:
        st.table(st.session_state["items"])

    submitted = st.form_submit_button("✅ Submit Entry")

    if submitted:
        if not (name and apm_id and coupon_number and pantry_boy and st.session_state["items"]):
            st.error("⚠️ Please fill all fields and add at least one item.")
        else:
            for entry in st.session_state["items"]:
                sheet.append_row([
                    entry_date.strftime("%Y-%m-%d"),
                    entry_time,
                    name,
                    apm_id,
                    coupon_number,
                    entry["item"],
                    entry["qty"],
                    action,
                    pantry_boy
                ])
            st.success("✅ Entry submitted successfully!")
            st.session_state["items"] = []  # clear items after submission
