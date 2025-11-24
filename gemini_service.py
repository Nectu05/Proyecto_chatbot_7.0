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
            "enum": ['greeting', 'symptom_analysis', 'show_all_services', 'booking_request', 'cancellation', 'price_inquiry', 'general', 'invoice_analysis', 'check_appointment', 'revenue_report', 'reschedule', 'location_inquiry']
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
        },
        "audioTranscription": {"type": "STRING"}
    },
    "required": ["message", "intent"]
}

def send_message_to_gemini(history, text_message, image_base64=None, audio_base64=None):
    try:
        model_id = 'gemini-2.5-flash' 

        # Context Injection
        now = datetime.datetime.now()
        day_name = now.strftime("%A") 
        days_es = {"Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles", "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"}
        day_name_es = days_es.get(day_name, day_name)
        date_string = now.strftime("%Y-%m-%d")

        context_instruction = f"""
        {SYSTEM_INSTRUCTION}
        
        CONTEXTO TEMPORAL OBLIGATORIO:
        - HOY es: {day_name_es.upper()}, {date_string}.
        - Si el usuario dice "mañana", se refiere al día siguiente.
        
        INSTRUCCIONES DE VISIÓN Y AUDIO:
        - Si recibes una IMAGEN de un comprobante de pago (Nequi, Daviplata, Bancolombia, efectivo), extrae el valor y la fecha.
          - Intent: 'invoice_analysis'
          - extractedInvoiceData: {{ "amount": 50000, "date": "2023-10-27" }}
        - Si recibes un AUDIO, transcríbelo y responde como si fuera texto.
          - audioTranscription: "Texto transcrito del audio"
        """

        # Prepare Content
        parts = []
        
        if image_base64:
             parts.append(types.Part.from_bytes(data=image_base64, mime_type="image/jpeg"))
             parts.append(types.Part.from_text(text="Analiza esta imagen. Si es un comprobante de pago, extrae el monto y fecha."))

        if audio_base64:
             parts.append(types.Part.from_bytes(data=audio_base64, mime_type="audio/ogg")) # Telegram voice notes are usually OGG
             parts.append(types.Part.from_text(text="Transcribe este audio y responde a la intención del usuario."))

        if text_message:
            parts.append(types.Part.from_text(text=text_message))

        if not parts:
            return {"message": "No entendí, por favor envía texto, imagen o audio.", "intent": "general"}

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
