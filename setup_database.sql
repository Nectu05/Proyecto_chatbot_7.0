-- Create Database (Optional, if not already created)
-- CREATE DATABASE FisioterapiaDB;
-- GO

-- USE FisioterapiaDB;
-- GO

-- Drop tables if they exist to ensure correct schema
IF OBJECT_ID('dbo.Appointments', 'U') IS NOT NULL DROP TABLE dbo.Appointments;
IF OBJECT_ID('dbo.Services', 'U') IS NOT NULL DROP TABLE dbo.Services;

-- Create Services Table
CREATE TABLE Services (
        id INT PRIMARY KEY,
        nombre NVARCHAR(255) NOT NULL,
        duracion INT NOT NULL, -- in minutes
        precio DECIMAL(10, 2) NOT NULL,
        description NVARCHAR(MAX)
    );
END

-- Create Appointments Table
CREATE TABLE Appointments (
    id NVARCHAR(50) PRIMARY KEY, -- Using UUID/String ID to match existing logic
    patient_name NVARCHAR(255) NOT NULL,
    patient_id NVARCHAR(50) NOT NULL, -- Cédula
    patient_phone NVARCHAR(50) NOT NULL,
    service_id INT NOT NULL,
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    status NVARCHAR(20) NOT NULL CHECK (status IN ('confirmed', 'cancelled')),
    reminded BIT DEFAULT 0,
    created_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (service_id) REFERENCES Services(id)
);

-- Seed Services Data
-- Clear existing data to ensure consistency with constants.ts
DELETE FROM Services;

INSERT INTO Services (id, nombre, duracion, precio, description) VALUES
(1, 'Consulta', 60, 65000, 'Evaluación completa inicial para diagnóstico fisioterapéutico.'),
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
