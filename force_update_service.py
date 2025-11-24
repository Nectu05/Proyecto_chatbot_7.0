import pyodbc
from config import DB_CONNECTION_STRING

def force_update():
    try:
        conn = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = conn.cursor()
        print("Updating Service 1...")
        cursor.execute("UPDATE Services SET nombre = 'Consulta General' WHERE id = 1")
        conn.commit()
        print("Update committed.")
        
        # Verify
        cursor.execute("SELECT id, nombre FROM Services WHERE id = 1")
        row = cursor.fetchone()
        print(f"New Name: {row.nombre}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    force_update()
