import pyodbc
from config import DB_CONNECTION_STRING

def apply_schema_update():
    try:
        conn = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = conn.cursor()
        
        # Read SQL file
        with open('update_schema.sql', 'r') as f:
            sql_script = f.read()
            
        # Execute
        cursor.execute(sql_script)
        conn.commit()
        print("Schema updated successfully.")
        
    except Exception as e:
        print(f"Error updating schema: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    apply_schema_update()
