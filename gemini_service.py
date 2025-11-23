from google import genai
from google.genai import types
from config import GOOGLE_API_KEY, SYSTEM_INSTRUCTION
import datetime
import json

# Initialize Client
client = genai.Client(api_key=GOOGLE_API_KEY)

# Schema Definition (matching the React one)
response_schema = {
    "type": "OBJECT",
    "properties": {
        "message": {"type": "STRING"},
        "intent": {
            "type": "STRING",
            "enum": ['greeting', 'symptom_analysis', 'show_all_services', 'booking_request', 'cancellation', 'price_inquiry', 'general', 'invoice_analysis', 'check_appointment', 'revenue_report', 'reschedule']
        },
        "suggestedServiceIds": {
            "type": "ARRAY",
            "items": {"type": "INTEGER"}
        },
        "extractedInvoiceData": {
            "type": "OBJECT",
            "properties": {
                "amount": {"type": "NUMBER"},
                "date": {"type": "STRING"}
            }
        }
    },
    "required": ["message", "intent"]
}

def send_message_to_gemini(history, text_message, image_base64=None):
    try:
        model_id = 'gemini-2.5-flash' # User requested specific version

        # Context Injection
        now = datetime.datetime.now()
        day_name = now.strftime("%A") # English day name, might need Spanish translation mapping if strict
        # Simple Spanish mapping for better context
        days_es = {"Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles", "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"}
        day_name_es = days_es.get(day_name, day_name)
        date_string = now.strftime("%Y-%m-%d")

        context_instruction = f"""
        {SYSTEM_INSTRUCTION}
        
        CONTEXTO TEMPORAL OBLIGATORIO:
        - HOY es: {day_name_es.upper()}, {date_string}.
        - Si el usuario dice "mañana", se refiere al día siguiente.
        """

        # Prepare Content
        contents = []
        
        # Add History (simplified for now, usually we pass chat session)
        # In this stateless function, we might just append history if provided in correct format
        # For now, let's assume we send the current message with system instruction
        
        parts = []
        if image_base64:
             parts.append(types.Part.from_bytes(data=image_base64, mime_type="image/jpeg"))
             parts.append(types.Part.from_text(text="Analiza esta imagen. Si es una factura médica, extrae el monto total y la fecha."))

        if text_message:
            parts.append(types.Part.from_text(text=text_message))

        response = client.models.generate_content(
            model=model_id,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                system_instruction=context_instruction,
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=0.2
            )
        )

        if response.text:
            return json.loads(response.text)
        else:
            raise Exception("No response text from Gemini")

    except Exception as e:
        print(f"Gemini API Error: {e}")
        return {
            "message": "Lo siento, tuve un problema técnico momentáneo. ¿Podrías intentarlo de nuevo?",
            "intent": "general"
        }
