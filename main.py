import streamlit as st
import db
import time

st.set_page_config(page_title="Battery Stock Taking", page_icon="🔋", layout="wide")

# Initialize Session State
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'selected_branch' not in st.session_state:
    st.session_state.selected_branch = None
if 'last_scan_result' not in st.session_state:
    st.session_state.last_scan_result = None

# Initialize DB (Check table existence)
# We do this once or lazily. Let's do it on import/startup to be safe, or behind a cache.
@st.cache_resource
def setup_database():
    db.init_db()

setup_database()

def login_page():
    st.title("🔋 Battery Stock Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if not username or not password:
                st.error("Please enter both username and password.")
            else:
                user_info, error = db.validate_db_user(username, password)
                if error:
                    st.error(f"Login failed: {error}")
                else:
                    st.session_state.logged_in = True
                    st.session_state.user_info = user_info
                    if user_info['branches']:
                        st.session_state.selected_branch = user_info['branches'][0] # Default
                    st.success("Login Successful!")
                    time.sleep(0.5)
                    st.rerun()

import cv2
import numpy as np
import pandas as pd

def main_app():
    user = st.session_state.user_info
    st.sidebar.title(f"User: {user['username']}")
    
    # Initialize Session State (specific to main app)
    if 'scanned_items' not in st.session_state:
        st.session_state.scanned_items = []
    
    # Branch Selection
    st.title("🔋 Battery Stock Scanning")
    
    # Branch Selection in Main Area
    branches = user.get('branches', [])
    if branches:
        col_branch, col_rest = st.columns([1, 3])
        with col_branch:
             selected = st.selectbox("Current Branch", branches, index=branches.index(st.session_state.selected_branch) if st.session_state.selected_branch in branches else 0)
             st.session_state.selected_branch = selected
    else:
        st.error("No branches assigned to this user.")
        return

    # Tabs for different scanning methods
    tab1, tab2 = st.tabs(["📷 Camera Scan", "#️⃣ Manual Entry"])
    
    new_scan = None
    
    with tab1:
        st.write("Take a picture of the QR/Barcode")
        camera_image = st.camera_input("Scan Battery")
        
        if camera_image is not None:
            # Decode image
            bytes_data = camera_image.getvalue()
            cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
            
            # Use pyzbar to decode
            from pyzbar.pyzbar import decode
            decoded_objects = decode(cv2_img)
            
            if decoded_objects:
                # Take the first detected code
                obj = decoded_objects[0]
                data = obj.data.decode("utf-8")
                new_scan = data
                st.success(f"Detected: {data} ({obj.type})")
            else:
                st.warning("No barcode detected.")

    with tab2:
        with st.form("scan_form", clear_on_submit=True):
            barcode = st.text_input("Enter Barcode", key="barcode_input")
            submitted = st.form_submit_button("Add to List")
            if submitted and barcode:
                new_scan = barcode

    # Processing a new scan (from either source)
    if new_scan:
        # Check against local duplicate in current session list
        existing = [item['barcode'] for item in st.session_state.scanned_items]
        if new_scan in existing:
             st.warning(f"Barcode {new_scan} is already in the pending list.")
        else:
            # Check against database
            is_dup, err = db.check_duplicate_barcode(new_scan)
            if is_dup:
                st.error(f"Duplicate: {new_scan} already exists in Database!")
            elif err:
                st.error(f"Error checking DB: {err}")
            else:
                st.session_state.scanned_items.append({
                    'barcode': new_scan,
                    'username': user['username'],
                    'branch': st.session_state.selected_branch,
                    'status': 'Pending'
                })
                st.success(f"Added {new_scan} to list.")
                # We need to rerun to clear camera input if possible or update list
                # Rerun might be annoying for camera flow, but necessary to reset `new_scan` state if we rely on it.
                # Actually, camera input persists until retaken. We might need a "Clear" button or just let it be.

    # Display Scanned Items
    st.divider()
    st.subheader("Pending Scans")
    
    if st.session_state.scanned_items:
        df = pd.DataFrame(st.session_state.scanned_items)
        st.dataframe(df[['barcode', 'branch', 'status']], use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Submit All to Database", type="primary"):
                success, msg = db.insert_scan_batch(st.session_state.scanned_items)
                if success:
                    st.success(msg)
                    st.session_state.scanned_items = [] # Clear list
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Batch Insert Failed: {msg}")
        
        with col2:
            if st.button("Clear List"):
                st.session_state.scanned_items = []
                st.rerun()
    else:
        st.info("No items scanned yet.")

    # Logout
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_info = None
        st.session_state.scanned_items = []
        st.rerun()

if __name__ == "__main__":
    if not st.session_state.logged_in:
        login_page()
    else:
        main_app()

