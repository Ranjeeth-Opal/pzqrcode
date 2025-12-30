import pandas as pd
import hashlib
import os
from datetime import datetime

USERS_FILE = 'users.csv'
SCANS_FILE = 'scans.csv'

def init_db():
    # Ensure files exist
    if not os.path.exists(USERS_FILE):
        print(f"Creating {USERS_FILE}...")
        df = pd.DataFrame(columns=['username', 'password', 'branches'])
        # Add default admin (pass: admin)
        df.loc[0] = ['admin', hashlib.md5('admin'.encode()).hexdigest(), 'HeadOffice']
        df.to_csv(USERS_FILE, index=False)
        
    if not os.path.exists(SCANS_FILE):
        print(f"Creating {SCANS_FILE}...")
        df = pd.DataFrame(columns=['scan_id', 'barcode', 'created_by', 'branch_code', 'created_date'])
        df.to_csv(SCANS_FILE, index=False)

def validate_db_user(username, password):
    try:
        if not os.path.exists(USERS_FILE):
            return None, "User DB missing"
            
        df = pd.read_csv(USERS_FILE)
        
        # MD5 hash
        md5_hash = hashlib.md5(password.encode()).hexdigest()
        
        # Check user
        user_row = df[(df['username'] == username) & (df['password'] == md5_hash)]
        
        if user_row.empty:
            return None, "Invalid credentials"
            
        # Get branches
        branches_str = str(user_row.iloc[0]['branches'])
        branches = branches_str.split('|') if branches_str and branches_str != 'nan' else []
        
        return {'username': username, 'branches': branches}, None
        
    except Exception as e:
        return None, f"Login error: {e}"

def check_duplicate_barcode(barcode):
    try:
        if not os.path.exists(SCANS_FILE):
            return False, None
            
        df = pd.read_csv(SCANS_FILE)
        if barcode in df['barcode'].astype(str).values:
             return True, None
        return False, None
    except Exception as e:
        return False, str(e)

def insert_scan(barcode, username, branch):
    try:
        # Check duplicate again
        is_dup, _ = check_duplicate_barcode(barcode)
        if is_dup:
             return False, "Duplicate barcode"

        if os.path.exists(SCANS_FILE):
            df = pd.read_csv(SCANS_FILE)
        else:
            df = pd.DataFrame(columns=['scan_id', 'barcode', 'created_by', 'branch_code', 'created_date'])
            
        if not df.empty and 'scan_id' in df.columns:
            new_id = int(df['scan_id'].max()) + 1
        else:
            new_id = 1
        new_row = {
            'scan_id': new_id,
            'barcode': barcode,
            'created_by': username,
            'branch_code': branch,
            'created_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Append
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(SCANS_FILE, index=False)
        
        return True, "Scanned Successfully"
    except Exception as e:
        return False, str(e)

def insert_scan_batch(scans):
    """
    scans: list of dictionaries {'barcode': b, 'username': u, 'branch': br}
    """
    try:
        if os.path.exists(SCANS_FILE):
            df = pd.read_csv(SCANS_FILE)
        else:
            df = pd.DataFrame(columns=['scan_id', 'barcode', 'created_by', 'branch_code', 'created_date'])
            
        new_rows = []
        if not df.empty and 'scan_id' in df.columns:
            # Safely get max ID, handle bad data with errors='coerce' to be safe, though not critical if we manage file well
            current_id = df['scan_id'].max()
            if pd.isna(current_id): current_id = 0
        else:
            current_id = 0
        
        existing_barcodes = set(df['barcode'].astype(str).values)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        count = 0
        for s in scans:
            if s['barcode'] in existing_barcodes:
                continue # Skip duplicates
                
            current_id += 1
            new_rows.append({
                'scan_id': current_id,
                'barcode': s['barcode'],
                'created_by': s['username'],
                'branch_code': s['branch'],
                'created_date': timestamp
            })
            existing_barcodes.add(s['barcode'])
            count += 1
            
        if new_rows:
            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
            df.to_csv(SCANS_FILE, index=False)
            
        return True, f"Successfully inserted {count} records."
    except Exception as e:
        return False, str(e)

def get_all_scans():
    try:
        if not os.path.exists(SCANS_FILE):
            return pd.DataFrame(), "No scans found"
        df = pd.read_csv(SCANS_FILE)
        # Sort by date desc if possible
        if 'created_date' in df.columns:
            df = df.sort_values(by='created_date', ascending=False)
        return df, None
    except Exception as e:
        return None, str(e)

def delete_scan(scan_id):
    try:
        if not os.path.exists(SCANS_FILE):
             return False, "File not found"
             
        df = pd.read_csv(SCANS_FILE)
        
        # Check if ID exists
        if scan_id not in df['scan_id'].values:
            return False, "ID not found"
            
        # Filter out
        df = df[df['scan_id'] != scan_id]
        df.to_csv(SCANS_FILE, index=False)
        return True, "Deleted successfully"
    except Exception as e:
        return False, str(e)
