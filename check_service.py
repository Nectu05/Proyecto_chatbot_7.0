import pyodbc
from config import DB_CONNECTION_STRING

def check_service():
    try:
        conn = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre FROM Services WHERE id = 1")
        row = cursor.fetchone()
        if row:
            print(f"Service 1 Name: {row.nombre}")
        else:
            print("Service 1 not found")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_service()
