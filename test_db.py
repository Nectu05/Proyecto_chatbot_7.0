import database
import sys

try:
    print("Testing connection...")
    conn = database.get_db_connection()
    if conn:
        print("Connection successful.")
        conn.close()
    else:
        print("Connection failed.")
        sys.exit(1)

    print("\nTesting get_services()...")
    services = database.get_services()
    print(f"Found {len(services)} services.")
    for s in services:
        print(f"- {s['nombre']} (ID: {s['id']})")

    if services:
        first_id = services[0]['id']
        print(f"\nTesting get_service_by_id({first_id})...")
        service = database.get_service_by_id(first_id)
        print(f"Service: {service}")
    
    print("\nTesting check_availability...")
    avail = database.check_availability("2024-12-31", "10:00")
    print(f"Available: {avail}")

except Exception as e:
    print(f"An error occurred: {e}")
