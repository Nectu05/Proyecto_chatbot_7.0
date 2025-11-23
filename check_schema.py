import database
import pyodbc

try:
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    print("Connected to Database:", conn.getinfo(pyodbc.SQL_DATABASE_NAME))
    print("Columns in Appointments table:")
    cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Appointments'")
    for row in cursor.fetchall():
        print(f"- {row.COLUMN_NAME}")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
