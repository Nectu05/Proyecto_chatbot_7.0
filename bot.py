import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from telegram import constants
from config import TELEGRAM_TOKEN, CLINIC_INFO
from gemini_service import send_message_to_gemini
import database
import holidays
from datetime import datetime, timedelta
from cachetools import TTLCache
from utils import create_calendar, create_time_slots_keyboard
import reports
import os

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Initialize Holidays (Colombia)
co_holidays = holidays.Colombia()

# In-Memory Slot Lock
slot_locks = TTLCache(maxsize=100, ttl=600)

# Emoji Mapping
SERVICE_EMOJIS = {
    1: "🩺", 2: "📷", 3: "💆‍♂️", 4: "⚡", 5: "📦", 
    6: "🏋️", 7: "🧖", 8: "🏃", 9: "🤰", 10: "🧘", 
    11: "🩸", 13: "🧖‍♀️"
}

# Conversation States
(
    CHOOSING_SERVICE,
    CHOOSING_DATE,
    CHOOSING_TIME,
    ENTERING_NAME,
    ENTERING_ID,
    ENTERING_PHONE,
    CONFIRMING,
    ENTERING_ID_CANCEL, # New state for cancellation flow
    ENTERING_ID_PAYMENT # New state for payment flow
) = range(9)

def is_holiday(date_str):
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        return date_obj in co_holidays or date_obj.weekday() == 6 
    except ValueError:
        return False

async def get_text_or_transcription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Helper to get text from a text message OR transcription from a voice message.
    """
    if update.message.voice:
        # It's a voice message, process it first
        voice_file = await update.message.voice.get_file()
        voice_bytes = await voice_file.download_as_bytearray()
        
        # Send "Typing..."
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
        
        # Transcribe
        ai_response = send_message_to_gemini([], "", audio_base64=voice_bytes)
        transcription = ai_response.get('audioTranscription', '')
        
        if transcription:
            await update.message.reply_text(f"🎤 *Dijiste:* \"{transcription}\"", parse_mode='Markdown')
            return transcription
        else:
            await update.message.reply_text("⚠️ No pude entender el audio. Intenta escribirlo.")
            return None
    else:
        # It's a text message
        return update.message.text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Hola, soy {CLINIC_INFO['botName']}, asistente virtual del {CLINIC_INFO['name']}. ¿En qué puedo ayudarte hoy?"
    )

async def process_ai_response(update: Update, context: ContextTypes.DEFAULT_TYPE, ai_response: dict):
    """
    Unified logic to handle AI responses (text, buttons, intents)
    Used by handle_message, handle_voice, and handle_photo
    """
    message_text = ai_response.get('message', '')
    intent = ai_response.get('intent', 'general')
    suggested_ids = ai_response.get('suggestedServiceIds', [])
    
    # Fallback: If AI mentions "sistema de gestión" but intent missed
    if "sistema de gestión" in message_text.lower() and intent == 'general':
        intent = 'check_appointment'

    # --- INTENT HANDLING ---

    # 1. Booking Request (Priority)
    if intent == 'booking_request':
        reply_markup = None
        if suggested_ids:
            # Store suggestions for "Back" button navigation
            context.user_data['last_suggested_ids'] = suggested_ids
            context.user_data['from_suggestions'] = True
            
            keyboard = []
            
            for s_id in suggested_ids:
                service = database.get_service_by_id(s_id)
                if service:
                    emoji = SERVICE_EMOJIS.get(s_id, "🏥")
                    btn_text = f"{emoji} {service['nombre']}"
                    keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"view_service_{s_id}")])
            
            keyboard.append([InlineKeyboardButton("📋 Ver todos los servicios", callback_data="show_all_services")])
            reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            # Show all services if none suggested
            services = database.get_services()
            keyboard = []
            for s in services:
                emoji = SERVICE_EMOJIS.get(s['id'], "🏥")
                btn_text = f"{emoji} {s['nombre']}"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"view_service_{s['id']}")])
            reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        return CHOOSING_SERVICE

    # 2. Management / Cancellation
    elif intent == 'check_appointment' or intent == 'cancellation' or intent == 'reschedule':
        await update.message.reply_text(
            "🆔 **Gestión de Citas**\n\n"
            "Para **modificar tu horario**, cancelar o consultar tus citas, por favor ingresa tu **número de cédula**:\n"
            "_(Solo números, sin puntos ni guiones)_",
            parse_mode='Markdown'
        )
        return ENTERING_ID_CANCEL 

    # 3. Invoice / Payment Analysis
    elif intent == 'invoice_analysis':
        data = ai_response.get('extractedInvoiceData', {})
        amount = data.get('amount', 0)
        date = data.get('date', 'Desconocida')
        
        context.user_data['payment_amount'] = amount
        context.user_data['payment_date'] = date
        
        await update.message.reply_text(
            f"💰 **Pago Detectado**\n\nValor: ${amount:,.0f}\nFecha: {date}\n\n"
            f"¿A qué cita corresponde este pago? Por favor escribe el número de cédula del paciente para buscar sus citas:",
            parse_mode='Markdown'
        )
        return ENTERING_ID_PAYMENT

    # 4. Greeting (No Buttons - Just Friendly Response)
    elif intent == 'greeting':
        await update.message.reply_text(message_text, parse_mode='Markdown')
        return ConversationHandler.END

    # 5. Location Inquiry (No Buttons)
    elif intent == 'location_inquiry':
        await update.message.reply_text(message_text, parse_mode='Markdown')
        return ConversationHandler.END

    # 6. General / Other
    else:
        reply_markup = None
        if suggested_ids:
            keyboard = []
            for s_id in suggested_ids:
                service = database.get_service_by_id(s_id)
                if service:
                    keyboard.append([InlineKeyboardButton(service['nombre'], callback_data=f"view_service_{s_id}")])
            keyboard.append([InlineKeyboardButton("📋 Ver todos los servicios", callback_data="show_all_services")])
            reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(message_text, reply_markup=reply_markup)
        return ConversationHandler.END

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    # Send Typing Action
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    
    # Send to Gemini
    ai_response = send_message_to_gemini([], user_text)
    
    # Process Response
    return await process_ai_response(update, context, ai_response)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get the photo file
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    # Send Typing Action
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    
    # Send to Gemini
    ai_response = send_message_to_gemini([], update.message.caption or "", image_base64=photo_bytes)
    
    # Process Response
    return await process_ai_response(update, context, ai_response)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get voice file
    voice_file = await update.message.voice.get_file()
    voice_bytes = await voice_file.download_as_bytearray()
    
    # Send Typing Action (or Record Voice)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    
    # Send to Gemini
    ai_response = send_message_to_gemini([], "", audio_base64=voice_bytes)
    
    transcription = ai_response.get('audioTranscription', '')
    
    # Reply with transcription first (optional, but good for feedback)
    if transcription:
        await update.message.reply_text(f"🎤 *Transkripción:* \"{transcription}\"", parse_mode='Markdown')
    
    # Process Response (Buttons, Intents, etc.)
    return await process_ai_response(update, context, ai_response)

# --- PAYMENT FLOW ---

async def receive_id_for_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    patient_id = await get_text_or_transcription(update, context)
    if not patient_id: return ENTERING_ID_PAYMENT
    
    # Clean input
    patient_id = ''.join(filter(str.isdigit, patient_id))

    if not patient_id:
        await update.message.reply_text("⚠️ Cédula inválida. Intenta de nuevo.")
        return ENTERING_ID_PAYMENT

    apps = database.get_appointments_by_patient(patient_id)
    if not apps:
        await update.message.reply_text("No encontré citas para esta cédula.")
        return ConversationHandler.END
        
    # Show appointments to link payment
    keyboard = []
    for app in apps:
        btn_text = f"{app['date']} {app['time']} - {app['service_name']}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"pay_{app['id']}")])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Selecciona la cita a pagar:", reply_markup=reply_markup)
    return ENTERING_ID_PAYMENT

async def confirm_payment_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("pay_"):
        app_id = query.data.split("_")[1]
        amount = context.user_data.get('payment_amount', 0)
        
        # Update DB
        if database.update_payment_status(app_id, 'paid', 'transfer', 'digital_proof', amount):
            await query.edit_message_text(f"✅ **Pago Registrado**\n\nSe ha abonado ${amount:,.0f} a la cita.")
        else:
            await query.edit_message_text("❌ Error al registrar pago.")
            
    return ConversationHandler.END

async def handle_booking_conversation_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles text input specifically during the CHOOSING_SERVICE state.
    It sends the text to Gemini, replies, and then RE-SENDS the service buttons
    to ensure the user doesn't get lost.
    """
    user_text = update.message.text
    
    # Send to Gemini
    ai_response = send_message_to_gemini([], user_text)
    message_text = ai_response.get('message', '')
    suggested_ids = ai_response.get('suggestedServiceIds', [])
    
    # Construct Reply
    # 1. The AI Answer
    await update.message.reply_text(message_text, parse_mode='Markdown')
    
    # 2. Re-attach Service Buttons (Guidance)
    keyboard = []
    if suggested_ids:
        for s_id in suggested_ids:
            service = database.get_service_by_id(s_id)
            if service:
                emoji = SERVICE_EMOJIS.get(s_id, "🏥")
                btn_text = f"{emoji} {service['nombre']}"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"view_service_{s_id}")])
        keyboard.append([InlineKeyboardButton("📋 Ver todos los servicios", callback_data="show_all_services")])
    else:
        services = database.get_services()
        keyboard = []
        for s in services:
            emoji = SERVICE_EMOJIS.get(s['id'], "🏥")
            btn_text = f"{emoji} {s['nombre']}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"view_service_{s['id']}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send a small nudge message with the buttons
    await update.message.reply_text(
        "👇 **Continúa agendando aquí:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return CHOOSING_SERVICE

# --- BOOKING FLOW ---

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    # 1. Show All Services List
    if data == "show_all_services":
        context.user_data['from_suggestions'] = False  # Reset flag
        services = database.get_services()
        keyboard = []
        for s in services:
            emoji = SERVICE_EMOJIS.get(s['id'], "🏥")
            btn_text = f"{emoji} {s['nombre']}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"view_service_{s['id']}")])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📂 **Servicios Disponibles**\nSelecciona uno para ver más información:", reply_markup=reply_markup, parse_mode='Markdown')
        return CHOOSING_SERVICE

    # 1.5 Back to Suggestions
    if data == "back_to_suggestions":
        suggested_ids = context.user_data.get('last_suggested_ids', [])
        keyboard = []
        for s_id in suggested_ids:
            service = database.get_service_by_id(s_id)
            if service:
                emoji = SERVICE_EMOJIS.get(s_id, "🏥")
                btn_text = f"{emoji} {service['nombre']}"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"view_service_{s_id}")])
        
        keyboard.append([InlineKeyboardButton("📋 Ver todos los servicios", callback_data="show_all_services")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("👇 **Aquí tienes los servicios sugeridos:**", reply_markup=reply_markup, parse_mode='Markdown')
        return CHOOSING_SERVICE

    # 2. View Service Details (The "Card")
    if data.startswith("view_service_"):
        service_id = int(data.split("_")[-1])
        service = database.get_service_by_id(service_id)
        
        # Store service_id temporarily
        context.user_data['temp_service_id'] = service_id
        
        emoji = SERVICE_EMOJIS.get(service_id, "🏥")
        details = (
            f"{emoji} **{service['nombre']}**\n\n"
            f"⏱ Duración: {service['duracion']} min\n"
            f"📝 {service.get('description', 'Sin descripción')}\n"
        )
        
        keyboard = [
            [InlineKeyboardButton("📅 Agendar Cita", callback_data=f"book_{service_id}")],
        ]
        
        # Dynamic Back Button
        if context.user_data.get('from_suggestions'):
            keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data="back_to_suggestions")])
        else:
            keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data="show_all_services")])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(details, reply_markup=reply_markup, parse_mode='Markdown')
        return CHOOSING_SERVICE

    # 3. Show Calendar
    if data.startswith("book_") or data == "back_to_calendar":
        if data.startswith("book_"):
            service_id = int(data.split("_")[1])
            context.user_data['service_id'] = service_id
        else:
            service_id = context.user_data.get('service_id')
        
        # Show Calendar
        calendar_markup = create_calendar()
        new_keyboard = list(calendar_markup.inline_keyboard)
        new_keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data=f"view_service_{service_id}")])
        calendar_markup = InlineKeyboardMarkup(new_keyboard)
        
        await query.edit_message_text(
            text="📅 **Selecciona una fecha:**",
            reply_markup=calendar_markup,
            parse_mode='Markdown'
        )
        return CHOOSING_DATE
    
    # 4. Handle Calendar Date Click -> Show Time Slots
    if data.startswith("cal_"):
        date_text = data.split("_")[1]
        
        # Validate Holiday
        if is_holiday(date_text):
             await query.answer("❌ Domingo/Festivo no disponible", show_alert=True)
             return CHOOSING_DATE 
        
        # Validate 1-day advance notice (Backend Check)
        selected_date = datetime.strptime(date_text, "%Y-%m-%d").date()
        now = datetime.now().date()
        if selected_date <= now:
             await query.answer("❌ Debes agendar con 1 día de anticipación.", show_alert=True)
             return CHOOSING_DATE
             
        # Store Date
        context.user_data['date'] = date_text
        
        # Show Time Slots
        time_keyboard = create_time_slots_keyboard(date_text, database.get_booked_slots(date_text))
        await query.edit_message_text(
            f"📅 Fecha: {date_text}\n⏰ **Selecciona una hora:**",
            reply_markup=time_keyboard,
            parse_mode='Markdown'
        )
        return CHOOSING_TIME

    # 5. Handle Time Slot Click -> Ask Name
    if data.startswith("time_"):
        time_text = data.split("_")[1]
        
        # Double Check Availability (Race Condition)
        date_text = context.user_data['date']
        if not database.check_availability(date_text, time_text):
            await query.answer("⚠️ Esa hora ya fue ocupada. Elige otra.", show_alert=True)
            # Refresh slots
            time_keyboard = create_time_slots_keyboard(date_text, database.get_booked_slots(date_text))
            await query.edit_message_text(
                f"📅 Fecha: {date_text}\n⏰ **Selecciona una hora:**",
                reply_markup=time_keyboard,
                parse_mode='Markdown'
            )
            return CHOOSING_TIME
            
        context.user_data['time'] = time_text
        
        # --- RESCHEDULING FLOW ---
        # --- RESCHEDULING FLOW ---
        if context.user_data.get('is_rescheduling'):
            app_id = context.user_data['manage_app_id']
            old_app = database.get_appointment_by_id(app_id)
            
            # Format Dates for Confirmation
            old_date_obj = datetime.strptime(old_app['date'], "%Y-%m-%d")
            new_date_obj = datetime.strptime(date_text, "%Y-%m-%d")
            
            days_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            old_day = days_es[old_date_obj.weekday()]
            new_day = days_es[new_date_obj.weekday()]
            
            # Show Confirmation Dialog
            msg = (
                f"⚠️ **Confirmar Cambio de Cita**\n\n"
                f"📅 **Anterior:** {old_day} {old_app['date']} - {old_app['time']}\n"
                f"📅 **Nueva:** {new_day} {date_text} - {time_text}\n\n"
                f"¿Estás seguro de realizar este cambio?"
            )
            
            keyboard = [
                [InlineKeyboardButton("✅ Confirmar Cambio", callback_data="confirm_reschedule_final")],
                [InlineKeyboardButton("🔙 Elegir otra hora", callback_data=f"cal_{date_text}")]
            ]
            
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            return CHOOSING_TIME
        
        # --- NORMAL BOOKING: SHOW CONFIRMATION ---
        # Format date with day name
        date_obj = datetime.strptime(date_text, "%Y-%m-%d")
        days_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        day_name = days_es[date_obj.weekday()]
        formatted_date = f"{day_name} {date_text}"
        
        # Confirmation Buttons
        keyboard = [
            [InlineKeyboardButton("✅ Confirmar Hora", callback_data="confirm_time_yes")],
            [InlineKeyboardButton("🔙 Elegir otra hora", callback_data=f"cal_{date_text}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📅 **Fecha:** {formatted_date}\n"
            f"🕒 **Hora:** {time_text}\n\n"
            f"¿Confirmas este horario?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return CHOOSING_TIME  # Stay in state until confirmed
    
    # 6. Handle Confirmation -> Ask Name OR Finalize Reschedule
    if data == "confirm_time_yes":
        date_text = context.user_data['date']
        time_text = context.user_data['time']
        slot_key = f"{date_text}_{time_text}"
        
        # Double Check Availability
        if not database.check_availability(date_text, time_text):
            await query.answer("⚠️ Lo sentimos, alguien acaba de tomar este horario.", show_alert=True)
            booked = database.get_booked_slots(date_text)
            time_markup = create_time_slots_keyboard(date_text, booked)
            await query.edit_message_text("Por favor selecciona otra hora:", reply_markup=time_markup)
            return CHOOSING_TIME
        
        # Lock the slot temporarily
        slot_locks[slot_key] = True
        
        await query.edit_message_text(
            f"✅ Fecha: {date_text}\n✅ Hora: {time_text}\n\n"
            "👤 **Escribe tu Nombre Completo:**\n"
            "_(Por favor escribe solo tu nombre, sin prefijos, puntos ni caracteres especiales)_\n\n"
            "🎙 _(O también puedes enviarme una nota de voz)_",
            parse_mode='Markdown'
        )
        return ENTERING_NAME
        
    # 7. Finish Management (Exit)
    if data == "finish_management":
        await query.edit_message_text(
            "✅ **Gestión finalizada**\n\n"
            "Si necesitas información sobre el consultorio, nuestros servicios, "
            "o cualquier otra consulta, no dudes en preguntar. "
            "Estoy aquí para ayudarte.\n\n"
            "¡Que tengas un excelente día! 😊",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    # 8. Finalize Reschedule (After Confirmation)
    if data == "confirm_reschedule_final":
        app_id = context.user_data['manage_app_id']
        date_text = context.user_data['date']
        time_text = context.user_data['time']
        
        old_app = database.get_appointment_by_id(app_id)
        
        if database.update_appointment(app_id, date_text, time_text):
            # Format Dates
            old_date_obj = datetime.strptime(old_app['date'], "%Y-%m-%d")
            new_date_obj = datetime.strptime(date_text, "%Y-%m-%d")
            
            days_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            old_day = days_es[old_date_obj.weekday()]
            new_day = days_es[new_date_obj.weekday()]
            
            msg = (
                f"✅ **¡Cita Reprogramada Exitosamente!**\n\n"
                f"📅 **Anterior:** {old_day} {old_app['date']} - {old_app['time']}\n"
                f"📅 **Nueva:** {new_day} {date_text} - {time_text}\n\n"
                f"Te esperamos. Si necesitas algo más como agendar otra cita, cancelar, cambiar el horario o info sobre la dirección del consultorio, no dudes en preguntar. Estoy aquí para ayudarte."
            )
            await query.edit_message_text(msg, parse_mode='Markdown')
        else:
            await query.edit_message_text("❌ Error al reprogramar. Intenta más tarde.")
            
        # Clean up
        context.user_data['is_rescheduling'] = False
        context.user_data['manage_app_id'] = None
        return ConversationHandler.END

async def show_confirmation_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Summary
    s_id = context.user_data['service_id']
    service = database.get_service_by_id(s_id)
    
    summary = (
        "📋 **CONFIRMAR CITA**\n\n"
        f"👤 **Paciente:** {context.user_data['name']}\n"
        f"🪪 **Cédula:** {context.user_data['patient_id']}\n"
        f"📱 **Celular:** {context.user_data['phone']}\n"
        f"🏥 **Servicio:** {service['nombre']}\n"
        f"📅 **Fecha:** {context.user_data['date']}\n"
        f"⏰ **Hora:** {context.user_data['time']}\n"
        f"💰 **Valor:** ${service['precio']:,.0f}\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Confirmar Cita", callback_data="confirm_booking")],
        [InlineKeyboardButton("👤 Editar Nombre", callback_data="edit_name")],
        [InlineKeyboardButton("🪪 Editar Cédula", callback_data="edit_id")],
        [InlineKeyboardButton("📱 Editar Celular", callback_data="edit_phone")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_booking")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(summary, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(summary, reply_markup=reply_markup, parse_mode='Markdown')

async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = await get_text_or_transcription(update, context)
    if not name: return ENTERING_NAME
    
    context.user_data['name'] = name
    
    # Check if editing
    if context.user_data.get('is_editing'):
        context.user_data['is_editing'] = False
        await show_confirmation_summary(update, context)
        return CONFIRMING
        
    await update.message.reply_text(
        f"Gusto en saludarte, {name}.\n\n"
        "🪪 **Ahora escribe tu número de Cédula:**\n"
        "_(Solo números, sin puntos, comas ni guiones)_\n\n"
        "🎙 _(O dímelo por nota de voz)_",
        parse_mode='Markdown'
    )
    return ENTERING_ID

async def receive_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    patient_id = await get_text_or_transcription(update, context)
    if not patient_id: return ENTERING_ID
    
    # Basic validation (digits only)
    patient_id = ''.join(filter(str.isdigit, patient_id))
    
    if not patient_id:
        await update.message.reply_text("⚠️ Por favor ingresa un número de cédula válido.")
        return ENTERING_ID
        
    context.user_data['patient_id'] = patient_id
    
    # Check if editing
    if context.user_data.get('is_editing'):
        context.user_data['is_editing'] = False
        await show_confirmation_summary(update, context)
        return CONFIRMING
        
    await update.message.reply_text(
        "📱 **Por último, escribe tu número de Celular:**\n"
        "_(Solo números, sin puntos, comas ni guiones)_\n\n"
        "🎙 _(O dímelo por nota de voz)_",
        parse_mode='Markdown'
    )
    return ENTERING_PHONE

async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = await get_text_or_transcription(update, context)
    if not phone: return ENTERING_PHONE
    
    context.user_data['phone'] = phone
    
    # Check if editing (Logic is same as normal flow here, but good to be explicit)
    if context.user_data.get('is_editing'):
        context.user_data['is_editing'] = False
        
    await show_confirmation_summary(update, context)
    return CONFIRMING

async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    # --- EDIT FLOW ---
    if data == "edit_name":
        context.user_data['is_editing'] = True
        await query.edit_message_text("👤 Escribe el nuevo nombre:")
        return ENTERING_NAME
        
    if data == "edit_id":
        context.user_data['is_editing'] = True
        await query.edit_message_text("🪪 Escribe la nueva cédula:")
        return ENTERING_ID
        
    if data == "edit_phone":
        context.user_data['is_editing'] = True
        await query.edit_message_text("📱 Escribe el nuevo celular:")
        return ENTERING_PHONE

    # --- CONFIRMATION ---
    if data == "confirm_booking":
        # Save to DB
        app_id = database.create_appointment(
            context.user_data['name'],
            context.user_data['patient_id'],
            context.user_data['phone'],
            context.user_data['service_id'],
            context.user_data['date'],
            context.user_data['time']
        )
        
        if app_id:
            # Re-fetch service for the name
            service = database.get_service_by_id(context.user_data['service_id'])
            
            # Format Date with Day Name (e.g., Martes 2025-11-25)
            date_obj = datetime.strptime(context.user_data['date'], "%Y-%m-%d")
            days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            day_name = days[date_obj.weekday()]
            formatted_date = f"{day_name} {context.user_data['date']}"
            
            await query.edit_message_text(
                f"✅ **¡Cita Agendada Exitosamente!**\n\n"
                f"🎫 **Credencial de Cita**\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"👤 **Paciente:** {context.user_data['name']}\n"
                f"🏥 **Servicio:** {service['nombre']}\n"
                f"📅 **Fecha:** {formatted_date}\n"
                f"🕒 **Hora:** {context.user_data['time']}\n"
                f"━━━━━━━━━━━━━━━━\n\n"
                f"Te esperamos. Si necesitas algo más como la dirección del consultorio o cualquier otra ayuda referente a nuestros servicios no dudes en preguntar, estoy aquí para ayudarte.",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Hubo un error al guardar la cita. Intenta de nuevo.")
            
        return ConversationHandler.END
        
    if data == "cancel_booking":
        await query.edit_message_text("❌ Proceso de agendamiento cancelado.")
        return ConversationHandler.END

# --- MANAGEMENT FLOW ---

async def receive_id_for_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    patient_id = await get_text_or_transcription(update, context)
    if not patient_id: return ENTERING_ID_CANCEL
    
    # Check for exit keywords
    exit_keywords = ["gracias", "listo", "salir", "cancelar", "terminar", "ya no", "adios"]
    if any(keyword in patient_id.lower() for keyword in exit_keywords):
        await update.message.reply_text("✅ Entendido. Si necesitas algo más, aquí estaré.")
        return ConversationHandler.END
    
    # Clean input
    patient_id = ''.join(filter(str.isdigit, patient_id))
    
    if not patient_id:
        await update.message.reply_text("⚠️ Cédula inválida. Intenta de nuevo.")
        return ENTERING_ID_CANCEL
        
    apps = database.get_appointments_by_patient(patient_id)
    
    if not apps:
        await update.message.reply_text("No encontré citas activas para esta cédula.")
        return ConversationHandler.END
    
    # Store ID for "Back" functionality
    context.user_data['manage_patient_id'] = patient_id
        
    # Show appointments
    msg = "📅 **Tus Citas Activas:**\nSelecciona una cita de la lista si deseas cancelarla o cambiar el horario.\n_(Recuerda que debes hacerlo con al menos un día de antelación)_"
    keyboard = []
    now = datetime.now()
    
    for app in apps:
        # Parse app date and time
        app_dt = datetime.strptime(f"{app['date']} {app['time']}", "%Y-%m-%d %H:%M:%S")
        
        # Format with Day Name
        days_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        day_name = days_es[app_dt.weekday()]
        
        # Check 1 day notice (Relaxed: Appointment Date > Now Date)
        if app_dt.date() > now.date():
            btn_text = f"❌ {day_name} {app['date']} {app['time']} - {app['service_name']}"
            callback = f"manage_{app['id']}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback)])
        else:
            btn_text = f"🔒 {day_name} {app['date']} {app['time']} (No modificable)"
            callback = "ignore_cancellation"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback)])
        
    keyboard.append([InlineKeyboardButton("✅ Terminar / Listo", callback_data="finish_management")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    
    return ENTERING_ID_CANCEL

async def manage_appointment_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "finish_management":
        await query.edit_message_text(
            "✅ **Gestión finalizada**\n\n"
            "Si necesitas información sobre el consultorio, nuestros servicios, "
            "o cualquier otra consulta, no dudes en preguntar. "
            "Estoy aquí para ayudarte.\n\n"
            "¡Que tengas un excelente día! 😊",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
        
    if data == "ignore_cancellation":
        await query.answer("⚠️ Esta cita ya no se puede modificar (menos de 24h).", show_alert=True)
        return ENTERING_ID_CANCEL

    if data.startswith("manage_"):
        app_id = data.split("_")[1]
        context.user_data['manage_app_id'] = app_id
        
        keyboard = [
            [InlineKeyboardButton("🔄 Cambiar Horario", callback_data="reschedule_start")],
            [InlineKeyboardButton("❌ Cancelar Cita", callback_data="confirm_cancel_ask")],
            [InlineKeyboardButton("🔙 Volver", callback_data="back_to_list")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("¿Qué deseas hacer con esta cita?", reply_markup=reply_markup)
        return ENTERING_ID_CANCEL
        
    elif data == "back_to_list":
        patient_id = context.user_data.get('manage_patient_id')
        if patient_id:
            apps = database.get_appointments_by_patient(patient_id)
            msg = "📅 **Tus Citas Activas:**\nSelecciona una cita de la lista si deseas cancelarla o cambiar el horario.\n_(Recuerda que debes hacerlo con al menos un día de antelación)_"
            keyboard = []
            now = datetime.now()
            
            for app in apps:
                app_dt = datetime.strptime(f"{app['date']} {app['time']}", "%Y-%m-%d %H:%M:%S")
                days_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                day_name = days_es[app_dt.weekday()]
                
                if app_dt.date() > now.date():
                    btn_text = f"❌ {day_name} {app['date']} {app['time']} - {app['service_name']}"
                    callback = f"manage_{app['id']}"
                    keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback)])
                else:
                    btn_text = f"🔒 {day_name} {app['date']} {app['time']} (No modificable)"
                    callback = "ignore_cancellation"
                    keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback)])
            
            keyboard.append([InlineKeyboardButton("✅ Terminar / Listo", callback_data="finish_management")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
            return ENTERING_ID_CANCEL
        else:
            await query.edit_message_text("⚠️ Por favor ingresa tu cédula nuevamente.")
            return ENTERING_ID_CANCEL

    elif data == "confirm_cancel_ask":
        keyboard = [
            [InlineKeyboardButton("✅ Sí, Cancelar Cita", callback_data="do_cancel")],
            [InlineKeyboardButton("🔙 No, Volver", callback_data=f"manage_{context.user_data['manage_app_id']}")]
        ]
        await query.edit_message_text("¿Estás seguro de que deseas cancelar esta cita?", reply_markup=InlineKeyboardMarkup(keyboard))
        return ENTERING_ID_CANCEL
        
    elif data == "do_cancel":
        app_id = context.user_data['manage_app_id']
        if database.cancel_appointment(app_id):
            msg = (
                "✅ **Cita cancelada exitosamente.**\n\n"
                "Si necesitas algo más como la dirección del consultorio o ayuda para agendar nuevamente otra cita no dudes en preguntar, estoy aquí para ayudarte."
            )
            await query.edit_message_text(msg, parse_mode='Markdown')
        else:
            await query.edit_message_text("❌ Error al cancelar la cita.")
            
    elif data == "reschedule_start":
        # Show confirmation before starting reschedule
        app_id = context.user_data.get('manage_app_id')
        keyboard = [
            [InlineKeyboardButton("✅ Sí, Cambiar Horario", callback_data="confirm_reschedule_yes")],
            [InlineKeyboardButton("🔙 No, Volver", callback_data=f"manage_{app_id}")]
        ]
        await query.edit_message_text(
            "¿Estás seguro de que deseas cambiar el horario de esta cita?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ENTERING_ID_CANCEL
    
    elif data == "confirm_reschedule_yes":
        # Start Calendar Flow for Reschedule
        context.user_data['is_rescheduling'] = True
        calendar_markup = create_calendar()
        await query.edit_message_text("📅 Selecciona la nueva fecha:", reply_markup=calendar_markup)
        return CHOOSING_DATE
            
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END

def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    
    # Booking Conversation
    booking_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
            MessageHandler(filters.VOICE, handle_voice),
            MessageHandler(filters.PHOTO, handle_photo),
            CallbackQueryHandler(button_click)
        ],
        states={
            CHOOSING_SERVICE: [
                CallbackQueryHandler(button_click),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_booking_conversation_text) # Handle text during button selection
            ],
            CHOOSING_DATE: [CallbackQueryHandler(button_click)],
            CHOOSING_TIME: [CallbackQueryHandler(button_click)],
            ENTERING_NAME: [
                MessageHandler(filters.TEXT | filters.VOICE, receive_name)
            ],
            ENTERING_ID: [
                MessageHandler(filters.TEXT | filters.VOICE, receive_id)
            ],
            ENTERING_PHONE: [
                MessageHandler(filters.TEXT | filters.VOICE, receive_phone)
            ],
            CONFIRMING: [CallbackQueryHandler(confirm_booking)],
            ENTERING_ID_CANCEL: [
                MessageHandler(filters.TEXT | filters.VOICE, receive_id_for_management),
                CallbackQueryHandler(manage_appointment_menu)
            ],
            ENTERING_ID_PAYMENT: [
                MessageHandler(filters.TEXT | filters.VOICE, receive_id_for_payment),
                CallbackQueryHandler(confirm_payment_selection)
            ]
        },
        fallbacks=[CommandHandler("start", start), CommandHandler("cancel", cancel)]
    )
    
    application.add_handler(booking_conv)
    
    print("🤖 Bot iniciado...")
    application.run_polling()

if __name__ == '__main__':
    main()
