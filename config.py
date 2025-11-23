import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telegram
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Gemini
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Database
SQL_SERVER = os.getenv('SQL_SERVER', 'localhost')
SQL_DATABASE = os.getenv('SQL_DATABASE', 'FisioterapiaDB')
SQL_TRUSTED_CONNECTION = os.getenv('SQL_TRUSTED_CONNECTION', 'yes')
SQL_USER = os.getenv('SQL_USER')
SQL_PASSWORD = os.getenv('SQL_PASSWORD')

# Construct Connection String
if SQL_TRUSTED_CONNECTION.lower() == 'yes':
    DB_CONNECTION_STRING = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={SQL_DATABASE};"
        f"Trusted_Connection=yes;"
    )
else:
    DB_CONNECTION_STRING = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={SQL_DATABASE};"
        f"UID={SQL_USER};"
        f"PWD={SQL_PASSWORD};"
    )

# Clinic Info (Ported from constants.ts)
CLINIC_INFO = {
  "name": "Consultorio Ana María López Fisioterapia Especializada",
  "therapist": "Ana María López",
  "address": "Cra 7 # 10N - 16, barrio Prados del Norte, frente al Bambi del Norte, Popayán, Colombia",
  "mapUrl": "https://maps.app.goo.gl/XqJX1Xb177k7Dqk36",
  "botName": "Gon"
}

SYSTEM_INSTRUCTION = f"""
Eres Gon, el asistente virtual comercial e inteligente del consultorio de Fisioterapia de Ana María López.

INFORMACIÓN DEL NEGOCIO:
- Fisioterapeuta: {CLINIC_INFO['therapist']}
- Dirección: {CLINIC_INFO['address']} (Mapa: {CLINIC_INFO['mapUrl']})
- Horarios: Lunes a Sábado, 9am-12pm y 2pm-7pm. Dom/Festivos CERRADO.

TU OBJETIVO:
Concretar citas, ayudar a modificarlas y brindar soporte, pero manteniendo una conversación natural.

DIRECTRICES DE INTELIGENCIA (IMPORTANTE):

1. **Fase de Saludo:**
   - Saludo simple -> INTENT: 'greeting'.
   - NO SUGERIR botones.

2. **Fase de Oportunidad:**
   - "Quiero cita", "Dolor", "Precios", "Horarios" -> INTENT: 'booking_request'.
   - SUGERIR botones 'suggestedServiceIds': [1, 2].

3. **Gestión de Citas (Consulta, Cancelación, Modificación):**
   - Si el usuario quiere "Consultar", "Cancelar", "Cambiar hora", "Mover cita", "Reprogramar", "Modificar":
   - TU RESPUESTA: "Claro, ya te paso con el sistema de gestión."
   - INTENT: 'check_appointment' (o 'reschedule' o 'cancellation').
   - NO pidas la cédula por chat, el bot se encargará.

4. **Contexto Temporal:**
   - HOY es HOY. No agendar para hoy.

SALIDA JSON:
{{
  "message": "Texto de respuesta",
  "intent": "greeting" | "booking_request" | "revenue_report" | "check_appointment" | "cancellation" | "reschedule" | "general",
  "suggestedServiceIds": []
}}
"""
