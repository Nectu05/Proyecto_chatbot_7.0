import pyodbc
import uuid
from datetime import datetime
from config import DB_CONNECTION_STRING

def get_db_connection():
    try:
        conn = pyodbc.connect(DB_CONNECTION_STRING)
        return conn
    except Exception as e:
        print(f"Database Connection Error: {e}")
        return None

def get_services():
    conn = get_db_connection()
    if not conn: return []
    
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, duracion, precio, description FROM Services")
    rows = cursor.fetchall()
    
    services = []
    for row in rows:
        services.append({
            "id": row.id,
            "nombre": row.nombre,
            "duracion": row.duracion,
            "precio": float(row.precio),
            "description": row.description
        })
    
    conn.close()
    return services

def get_service_by_id(service_id):
    conn = get_db_connection()
    if not conn: return None
    
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, duracion, precio, description FROM Services WHERE id = ?", service_id)
    row = cursor.fetchone()
    
    service = None
    if row:
        service = {
            "id": row.id,
            "nombre": row.nombre,
            "duracion": row.duracion,
            "precio": float(row.precio),
            "description": row.description
        }
    
    conn.close()
    return service

def create_appointment(patient_name, patient_id, patient_phone, service_id, date, time):
    conn = get_db_connection()
    if not conn: return None
    
    appointment_id = str(uuid.uuid4())
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Appointments (id, patient_name, patient_id, patient_phone, service_id, appointment_date, appointment_time, status, payment_status, payment_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'confirmed', 'pending', 0)
        """, (appointment_id, patient_name, patient_id, patient_phone, service_id, date, time))
        conn.commit()
        return appointment_id
    except Exception as e:
        print(f"Error creating appointment: {e}")
        return None
    finally:
        conn.close()

def get_appointments_by_patient(patient_id):
    conn = get_db_connection()
    if not conn: return []
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.appointment_date, a.appointment_time, a.status, s.nombre, a.patient_name
        FROM Appointments a
        JOIN Services s ON a.service_id = s.id
        WHERE a.patient_id = ? AND a.status = 'confirmed'
        ORDER BY a.appointment_date, a.appointment_time
    """, patient_id)
    
    rows = cursor.fetchall()
    appointments = []
    for row in rows:
        appointments.append({
            "id": row.id,
            "date": str(row.appointment_date),
            "time": str(row.appointment_time),
            "status": row.status,
            "service_name": row.nombre,
            "patient_name": row.patient_name
        })
        
    conn.close()
    return appointments

def get_appointment_by_id(appointment_id):
    conn = get_db_connection()
    if not conn: return None
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.appointment_date, a.appointment_time, a.status, s.nombre, a.patient_name
        FROM Appointments a
        JOIN Services s ON a.service_id = s.id
        WHERE a.id = ?
    """, appointment_id)
    
    row = cursor.fetchone()
    appointment = None
    if row:
        appointment = {
            "id": row.id,
            "date": str(row.appointment_date),
            "time": str(row.appointment_time),
            "status": row.status,
            "service_name": row.nombre,
            "patient_name": row.patient_name
        }
        
    conn.close()
    return appointment

def cancel_appointment(appointment_id):
    conn = get_db_connection()
    if not conn: return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE Appointments SET status = 'cancelled' WHERE id = ?", appointment_id)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error cancelling appointment: {e}")
        return False
    finally:
        conn.close()

def check_availability(date, time):
    conn = get_db_connection()
    if not conn: return False
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM Appointments 
        WHERE appointment_date = ? AND appointment_time = ? AND status = 'confirmed'
    """, (date, time))
    
    count = cursor.fetchone()[0]
    conn.close()
    
    return count == 0

def get_booked_slots(date):
    conn = get_db_connection()
    if not conn: return []
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT appointment_time FROM Appointments 
        WHERE appointment_date = ? AND status = 'confirmed'
    """, date)
    
    rows = cursor.fetchall()
    booked_slots = []
    for row in rows:
        # row.appointment_time is likely a datetime.time object or string
        t = row.appointment_time
        if isinstance(t, str):
            # Handle string "HH:MM:SS"
            try:
                t_obj = datetime.strptime(t, "%H:%M:%S").time()
                booked_slots.append(t_obj.strftime("%H:%M"))
            except ValueError:
                # Fallback if format is different
                booked_slots.append(t[:5])
        else:
            # Handle datetime.time object
            booked_slots.append(t.strftime("%H:%M"))
            
    conn.close()
    return booked_slots

def update_appointment(appointment_id, new_date, new_time):
    conn = get_db_connection()
    if not conn: return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Appointments 
            SET appointment_date = ?, appointment_time = ? 
            WHERE id = ?
        """, (new_date, new_time, appointment_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating appointment: {e}")
        return False
    finally:
        conn.close()

def update_payment_status(appointment_id, status, method, proof_path, amount):
    conn = get_db_connection()
    if not conn: return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Appointments 
            SET payment_status = ?, payment_method = ?, payment_proof = ?, payment_amount = ?
            WHERE id = ?
        """, (status, method, proof_path, amount, appointment_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating payment: {e}")
        return False
    finally:
        conn.close()

def get_daily_appointments(date):
    conn = get_db_connection()
    if not conn: return []
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.patient_name, a.patient_id, s.nombre as service_name, s.precio, a.appointment_time, a.status, a.payment_status, a.payment_method, a.payment_amount
        FROM Appointments a
        JOIN Services s ON a.service_id = s.id
        WHERE a.appointment_date = ?
        ORDER BY a.appointment_time ASC
    """, (date,))
    
    rows = cursor.fetchall()
    appointments = []
    for row in rows:
        appointments.append({
            "id": row.id,
            "patient_name": row.patient_name,
            "patient_id": row.patient_id,
            "service_name": row.service_name,
            "price": float(row.precio),
            "time": str(row.appointment_time),
            "status": row.status,
            "payment_status": row.payment_status,
            "payment_method": row.payment_method,
            "payment_amount": float(row.payment_amount) if row.payment_amount else 0.0
        })
        
    conn.close()
    return appointments

def get_appointments_by_range(start_date, end_date):
    conn = get_db_connection()
    if not conn: return []
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.patient_name, a.patient_id, s.nombre as service_name, s.precio, a.appointment_date, a.appointment_time, a.status, a.payment_status, a.payment_method, a.payment_amount
        FROM Appointments a
        JOIN Services s ON a.service_id = s.id
        WHERE a.appointment_date >= ? AND a.appointment_date <= ?
        ORDER BY a.appointment_date ASC, a.appointment_time ASC
    """, (start_date, end_date))
    
    rows = cursor.fetchall()
    appointments = []
    for row in rows:
        appointments.append({
            "id": row.id,
            "patient_name": row.patient_name,
            "patient_id": row.patient_id,
            "service_name": row.service_name,
            "price": float(row.precio),
            "date": str(row.appointment_date),
            "time": str(row.appointment_time),
            "status": row.status,
            "payment_status": row.payment_status,
            "payment_method": row.payment_method,
            "payment_amount": float(row.payment_amount) if row.payment_amount else 0.0
        })
        
    conn.close()
    return appointments
