import pyodbc
import os
from config import DB_CONNECTION_STRING

def init_db():
    print(f"Connecting to database...")
    try:
        conn = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = conn.cursor()
        
        # Read SQL file
        with open('setup_database.sql', 'r', encoding='utf-8') as f:
            sql_script = f.read()
            
        # Split by GO (common in SQL Server scripts, though pyodbc might not handle GO directly, 
        # usually we need to split. Our script uses GO in comments but let's be safe)
        # The provided setup_database.sql uses IF NOT EXISTS blocks which are safe to run as one block usually,
        # but let's split by command if needed. 
        # Actually, the provided script has `GO` commented out. It should be fine to run as batches if we split by valid T-SQL blocks.
        # However, `CREATE TABLE` inside `IF` is fine.
        
        print("Executing setup script...")
        
        # Simple split by semicolon might be too aggressive if text contains semicolons, 
        # but our script is simple. Let's try executing the whole thing or split by specific markers.
        # The script has multiple statements. Pyodbc execute() usually handles one statement or batch.
        # Let's try executing the key parts separately to be robust.
        
        # Part 1: Services Table
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Services' AND xtype='U')
        BEGIN
            CREATE TABLE Services (
                id INT PRIMARY KEY,
                nombre NVARCHAR(255) NOT NULL,
                duracion INT NOT NULL,
                precio DECIMAL(10, 2) NOT NULL,
                description NVARCHAR(MAX)
            );
        END
        """)
        
        # Part 2: Appointments Table
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Appointments' AND xtype='U')
        BEGIN
            CREATE TABLE Appointments (
                id NVARCHAR(50) PRIMARY KEY,
                patient_name NVARCHAR(255) NOT NULL,
                patient_id NVARCHAR(50) NOT NULL,
                patient_phone NVARCHAR(50) NOT NULL,
                service_id INT NOT NULL,
                appointment_date DATE NOT NULL,
                appointment_time TIME NOT NULL,
                status NVARCHAR(20) NOT NULL CHECK (status IN ('confirmed', 'cancelled')),
                reminded BIT DEFAULT 0,
                created_at DATETIME DEFAULT GETDATE(),
                FOREIGN KEY (service_id) REFERENCES Services(id)
            );
        END
        """)
        
        # Part 3: Seed Data (Delete and Insert)
        cursor.execute("DELETE FROM Services")
        
        # Insert services (Batch insert)
        services_sql = """
        INSERT INTO Services (id, nombre, duracion, precio, description) VALUES
        (1, 'Consulta General', 60, 65000, 'Evaluación completa inicial para diagnóstico fisioterapéutico.'),
        (2, 'Valoración por fisioterapia + ecografía especializada', 60, 85000, 'Diagnóstico preciso mediante tecnología de ultrasonido.'),
        (3, 'Sesión de descarga muscular en piernas', 90, 75000, 'Recuperación muscular profunda enfocada en extremidades inferiores.'),
        (4, 'Terapia física avanzada y manejo del dolor', 60, 65000, 'Tratamiento integral para aliviar dolor y recuperar movilidad.'),
        (5, 'Paquete 5 sesiones terapia física y manejo del dolor', 300, 250000, 'Plan completo de recuperación con descuento especial.'),
        (6, 'Sesión de ejercicio personalizado', 60, 50000, 'Rutinas guiadas adaptadas a tus necesidades físicas.'),
        (7, 'Sesión recovery y relajación', 80, 80000, 'Terapia regenerativa para reducir estrés físico.'),
        (8, 'Entrenamiento deportivo', 60, 60000, 'Mejora de rendimiento enfocado en tu disciplina.'),
        (9, 'Acondicionamiento físico en el embarazo', 60, 50000, 'Ejercicios seguros para la salud de la mamá y el bebé.'),
        (10, 'Sesión pilates piso', 60, 50000, 'Fortalecimiento del core y mejora de la postura.'),
        (11, 'Plasma rico en plaquetas', 60, 165000, 'Terapia regenerativa para lesiones articulares o musculares.'),
        (12, '3 sesiones plasma rico en plaquetas', 180, 450000, 'Tratamiento completo regenerativo.'),
        (13, 'Limpieza facial profunda', 90, 90000, 'Higiene facial clínica para renovar tu piel.'),
        (14, 'Limpieza facial profunda con alta hidratación', 120, 120000, 'Tratamiento intensivo de hidratación y limpieza.'),
        (15, 'Plasma rico en hidratación facial + plaquetas', 60, 160000, 'Rejuvenecimiento facial avanzado.'),
        (16, 'Educación continua', 0, 0, 'Talleres y formación especializada.'),
        (17, 'Venta de insumos y suministros médicos', 0, 0, 'Productos especializados para tu recuperación.');
        """
        cursor.execute(services_sql)
        
        conn.commit()
        print("Database initialized successfully!")
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

if __name__ == "__main__":
    init_db()
