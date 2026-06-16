import pyodbc
import pandas as pd

# 1. Point directly to your uploaded sample.csv file
csv_file = "sample.csv"  
df = pd.read_csv(csv_file)

# 2. Connection string for SSMS (Using Windows Authentication)
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost\\SQLEXPRESS;"
    "DATABASE=CloudDB;"
    "Trusted_Connection=yes;"
)

try:
    # 3. Establish connection to SQL Server
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    print("Successfully connected to SQL Server")

    # Clear old data from the table before uploading
    cursor.execute("TRUNCATE TABLE server_metrics")

    # 4. Loop through sample.csv rows and insert into SSMS
    insert_query = """
        INSERT INTO server_metrics (server_id, department, cpu_utilization, monthly_cost, status)
        VALUES (?, ?, ?, ?, ?)
    """
    
    for index, row in df.iterrows():
        cursor.execute(insert_query, 
                       row['server_id'], 
                       row['department'], 
                       float(row['cpu_utilization']), 
                       float(row['monthly_cost']), 
                       row['status'])
        
    conn.commit()
    print(f" Success! Imported {len(df)} rows from sample.csv directly into SSMS.")

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    if 'conn' in locals():
        cursor.close()
        conn.close()