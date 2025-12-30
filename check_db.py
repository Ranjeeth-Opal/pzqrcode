import db
import sys

print("Checking Database Connection...")
try:
    conn = db.get_connection()
    if conn:
        print("Connection Successful!")
        print("Initializing DB...")
        db.init_db()
        print("DB Initialization Complete.")
        conn.close()
    else:
        print("Connection Failed.")
        sys.exit(1)
except Exception as e:
    print(f"Exception: {e}")
    sys.exit(1)
