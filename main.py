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
    if 'camera_key' not in st.session_state:
        st.session_state.camera_key = 0
    
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
    scanned_image_data = None
    
    with tab1:
        st.write("Take a picture of the QR/Barcode")
        # Dynamic key to reset camera
        camera_image = st.camera_input("Scan Battery", key=f"camera_{st.session_state.camera_key}")
        
        if camera_image is not None:
            # Decode image
            bytes_data = camera_image.getvalue()
            scanned_image_data = bytes_data # Store for saving later
            cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
            
            # Convert to grayscale (improves detection)
            gray_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2GRAY)
            
            data = None
            debug_info = []

            # Method 1: Pyzbar (best for 1D Barcodes)
            try:
                from pyzbar.pyzbar import decode
                decoded_objects = decode(gray_img) # Use gray image
                if decoded_objects:
                    obj = decoded_objects[0]
                    data = obj.data.decode("utf-8")
                    st.success(f"✅ Barcode Detected: {data} ({obj.type})")
                else:
                    debug_info.append("Pyzbar: No code found")
            except ImportError:
                debug_info.append("Pyzbar: Library not installed")
            except Exception as e:
                debug_info.append(f"Pyzbar Error: {e}")
                
            # Method 2: OpenCV (best for QR Codes) - Fallback
            if not data:
                detector = cv2.QRCodeDetector()
                # OpenCV sometimes likes the color image, sometimes gray. trying original first.
                val, _, _ = detector.detectAndDecode(cv2_img)
                if val:
                    data = val
                    st.success(f"✅ QR Detected: {data}")
                else:
                     debug_info.append("CV2: No QR found")
            
            if data:
                new_scan = data
            else:
                st.warning("❌ No code detected.")
                with st.expander("Debug Info"):
                    for info in debug_info:
                        st.write(info)

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
                # SAVE IMAGE IF EXISTS
                if scanned_image_data:
                    try:
                        import os
                        if not os.path.exists("scanned_images"):
                            os.makedirs("scanned_images")
                        
                        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
                        filename = f"scanned_images/{new_scan}_{timestamp_str}.jpg"
                        with open(filename, "wb") as f:
                            f.write(scanned_image_data)
                        # st.info(f"Image saved: {filename}")
                    except Exception as e:
                        st.error(f"Failed to save image: {e}")

                st.session_state.scanned_items.append({
                    'barcode': new_scan,
                    'username': user['username'],
                    'branch': st.session_state.selected_branch,
                    'status': 'Pending'
                })
                st.success(f"Added {new_scan} to list.")
                
                # RESET CAMERA if source was camera
                if scanned_image_data:
                    st.session_state.camera_key += 1
                    time.sleep(0.5) # Short pause to see success message
                    st.rerun()

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

    # Admin View for devp01
    if user['username'] == 'devp01':
        st.divider()
        st.subheader("🛠 Admin: Manage Scans")
        
        all_scans, err = db.get_all_scans()
        if err:
             st.error(f"Error loading data: {err}")
        elif not all_scans.empty:
             # Add a selection column
             all_scans.insert(0, "Select", False)
             
             # Show data editor
             edited_df = st.data_editor(
                 all_scans,
                 column_config={
                     "Select": st.column_config.CheckboxColumn(required=True),
                     "created_date": st.column_config.TextColumn(disabled=True),
                     "scan_id": st.column_config.NumberColumn(disabled=True),
                     "barcode": st.column_config.TextColumn(disabled=True),
                     "created_by": st.column_config.TextColumn(disabled=True),
                     "branch_code": st.column_config.TextColumn(disabled=True),
                 },
                 use_container_width=True,
                 hide_index=True
             )
             
             # Filter selected
             selected_rows = edited_df[edited_df['Select']]
             
             if not selected_rows.empty:
                 st.warning(f"Selected {len(selected_rows)} record(s) for deletion.")
                 if st.button("🗑 Delete Selected", type="primary"):
                     count = 0
                     for index, row in selected_rows.iterrows():
                         db.delete_scan(row['scan_id'])
                         count += 1
                     st.success(f"Deleted {count} records.")
                     time.sleep(1)
                     st.rerun()
        else:
             st.info("No records found.")

if __name__ == "__main__":
    if not st.session_state.logged_in:
        login_page()
    else:
        main_app()