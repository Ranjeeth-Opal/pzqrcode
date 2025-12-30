import cx_Oracle
import pandas as pd
import collections

# Connection details
DB_USER = "opallive"
DB_PASS = "log"
DB_DSN = "192.168.10.245:1521/orcl"

def export_users():
    try:
        print("Connecting to Oracle...")
        conn = cx_Oracle.connect(user=DB_USER, password=DB_PASS, dsn=DB_DSN)
        cursor = conn.cursor()
        
        query = """
        select c.username, c.password, br.branchcode 
        from usercontrol a
        join users b on a.usercontrolid=b.usercontrolid
        join axusers c on b.ausername=c.username
        join divisionmast d on a.DIVISION=d.divisionmastid
        join branchmast br on a.branch=br.branchmastid
        where d.divcode='PTAC'
        and c.ACTIVE='T'
        """
        
        print("Executing query...")
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Process data to group by username
        users = {}
        for row in rows:
            username = row[0]
            password = row[1]
            branch = row[2]
            
            if username not in users:
                users[username] = {'password': password, 'branches': set()}
            
            users[username]['branches'].add(branch)
            
        # Convert to DataFrame
        data = []
        for username, info in users.items():
            branches_str = "|".join(sorted(list(info['branches'])))
            data.append({
                'username': username,
                'password': info['password'].lower(), # Ensure lowercase for consistency
                'branches': branches_str
            })
            
        df = pd.DataFrame(data)
        
        # Save to CSV
        df.to_csv('users.csv', index=False)
        print(f"Successfully exported {len(df)} users to users.csv")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

if __name__ == "__main__":
    export_users()
