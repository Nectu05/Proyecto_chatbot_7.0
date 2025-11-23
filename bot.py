import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from config import TELEGRAM_TOKEN, CLINIC_INFO
from gemini_service import send_message_to_gemini
import database
import holidays
from datetime import datetime, timedelta
from cachetools import TTLCache
from utils import create_calendar, create_time_slots_keyboard

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Initialize Holidays (Colombia)
co_holidays = holidays.Colombia()

# In-Memory Slot Lock
slot_locks = TTLCache(maxsize=100, ttl=600)

# Conversation States
(
    CHOOSING_SERVICE,
    CHOOSING_DATE,
    CHOOSING_TIME,
    ENTERING_NAME,
    ENTERING_ID,
    ENTERING_PHONE,
    CONFIRMING,
    ENTERING_ID_CANCEL # New state for cancellation flow
) = range(8)

def is_holiday(date_str):
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        return date_obj in co_holidays or date_obj.weekday() == 6 
    except ValueError:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Hola, soy {CLINIC_INFO['botName']}, asistente virtual del {CLINIC_INFO['name']}. ¿En qué puedo ayudarte hoy?"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    # Send to Gemini
    ai_response = send_message_to_gemini([], user_text)
    
    message_text = ai_response.get('message', '')
    intent = ai_response.get('intent', 'general')
    suggested_ids = ai_response.get('suggestedServiceIds', [])
    
    # Logic for Suggestions
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
    
    # Fallback: If AI mentions "sistema de gestión" but intent missed
    if "sistema de gestión" in message_text.lower() and intent == 'general':
        intent = 'check_appointment'

    # Intent Handling
    if intent == 'booking_request':
        if not suggested_ids:
             # Show main menu of services
             services = database.get_services()
             keyboard = [[InlineKeyboardButton(s['nombre'], callback_data=f"view_service_{s['id']}")] for s in services]
             reply_markup = InlineKeyboardMarkup(keyboard)
             await update.message.reply_text("Selecciona un servicio para ver detalles:", reply_markup=reply_markup)
             return CHOOSING_SERVICE
        return CHOOSING_SERVICE

    elif intent == 'check_appointment' or intent == 'cancellation' or intent == 'reschedule':
        await update.message.reply_text(
            "🆔 **Gestión de Citas**\n\n"
            "Para **modificar tu horario**, cancelar o consultar tus citas, por favor ingresa tu **número de cédula**:\n"
            "_(Solo números, sin puntos ni guiones)_",
            parse_mode='Markdown'
        )
        return ENTERING_ID_CANCEL # Reuse this state for both check and cancel for now
        
    return ConversationHandler.END

# --- BOOKING FLOW ---

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    # 1. Show All Services List
    if data == "show_all_services":
        services = database.get_services()
        keyboard = [[InlineKeyboardButton(s['nombre'], callback_data=f"view_service_{s['id']}")] for s in services]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📂 **Servicios Disponibles**\nSelecciona uno para ver más información:", reply_markup=reply_markup, parse_mode='Markdown')
        return CHOOSING_SERVICE

    # 2. View Service Details (The "Card")
    if data.startswith("view_service_"):
        service_id = int(data.split("_")[-1])
        service = database.get_service_by_id(service_id)
        
        # Store service_id temporarily
        context.user_data['temp_service_id'] = service_id
        
        details = (
            f"🏥 **{service['nombre']}**\n\n"
            f"⏱ Duración: {service['duracion']} min\n"
            f"📝 {service.get('description', 'Sin descripción')}\n"
        )
        
        keyboard = [
            [InlineKeyboardButton("📅 Agendar Cita", callback_data=f"book_{service_id}")],
            [InlineKeyboardButton("🔙 Volver", callback_data="show_all_services")]
        ]
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
             
        context.user_data['date'] = date_text
        
        # Get Booked Slots
        booked = database.get_booked_slots(date_text)
        
        # Show Time Slots
        time_markup = create_time_slots_keyboard(date_text, booked)
        await query.edit_message_text(
            text=f"✅ Fecha: {date_text}\n\n**Selecciona una hora disponible:**\n(🟢 Libre | 🔴 Ocupado)",
            reply_markup=time_markup,
            parse_mode='Markdown'
        )
        return CHOOSING_TIME
        
    # 5. Handle Time Selection -> Confirmation
    if data.startswith("time_"):
        time_text = data.split("_")[1]
        context.user_data['time'] = time_text
        
        # Format Date with Day Name (Spanish)
        date_obj = datetime.strptime(context.user_data['date'], "%Y-%m-%d")
        days_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        day_name = days_es[date_obj.weekday()]
        formatted_date = f"{day_name} {context.user_data['date']}"
        
        # Confirmation Buttons
        keyboard = [
            [InlineKeyboardButton("✅ Confirmar Hora", callback_data="confirm_time_yes")],
            [InlineKeyboardButton("🔙 Elegir otra hora", callback_data=f"cal_{context.user_data['date']}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=f"🗓 **Confirmación de Horario**\n\nFecha: {formatted_date}\nHora: {time_text}\n\n¿Es correcto?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return CHOOSING_TIME # Stay in state until confirmed

    # 6. Handle Confirmation -> Ask Name OR Finalize Reschedule
    if data == "confirm_time_yes":
        date_text = context.user_data['date']
        time_text = context.user_data['time']
        slot_key = f"{date_text}_{time_text}"
        
        # Double Check Availability
        if database.check_availability(date_text, time_text) is False:
            await query.answer("❌ Lo sentimos, alguien acaba de tomar este horario.", show_alert=True)
            booked = database.get_booked_slots(date_text)
            time_markup = create_time_slots_keyboard(date_text, booked)
            await query.edit_message_text("Por favor selecciona otra hora:", reply_markup=time_markup)
            return CHOOSING_TIME

        slot_locks[slot_key] = True
        
        # CHECK IF RESCHEDULING
        if context.user_data.get('is_rescheduling'):
            app_id = context.user_data['manage_app_id']
            
            # Fetch old details for comparison
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
        
        # Normal Booking Flow
        await query.edit_message_text("✅ Horario confirmado.\n\nPor favor escribe tu **Nombre Completo**:")
        return ENTERING_NAME

    if data == "ignore_booked":
        await query.answer("❌ Este horario ya está ocupado.", show_alert=True)
        return CHOOSING_TIME

    # Ignore/Navigation
    if data == "ignore":
        await query.answer()
        return CHOOSING_DATE

async def receive_date_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Fallback for manual entry if they ignore the calendar
    date_text = update.message.text
    if is_holiday(date_text):
         await update.message.reply_text("❌ Es festivo/domingo. Intenta otra fecha:")
         return CHOOSING_DATE
    context.user_data['date'] = date_text
    await update.message.reply_text("Hora (Ej: 14:00):")
    return CHOOSING_TIME

async def receive_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time_text = update.message.text
    date_text = context.user_data['date']
    slot_key = f"{date_text}_{time_text}"
    
    # Availability Checks
    if database.check_availability(date_text, time_text) is False:
        await update.message.reply_text("❌ Horario ocupado. Elige otro:")
        return CHOOSING_TIME

    if slot_key in slot_locks:
        await update.message.reply_text("⏳ Alguien está reservando este horario. Elige otro:")
        return CHOOSING_TIME
    
    slot_locks[slot_key] = True
    context.user_data['time'] = time_text
    
    await update.message.reply_text("✅ Horario disponible.\n\nEscribe tu **Nombre Completo**:")
    return ENTERING_NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text(
        "🆔 **Ingresa tu número de Cédula:**\n\n"
        "_(Solo números, sin puntos ni guiones)_",
        parse_mode='Markdown'
    )
    return ENTERING_ID

async def receive_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['patient_id'] = update.message.text
    await update.message.reply_text(
        "📱 **Ingresa tu número de Celular:**\n\n"
        "_(Para contactarte en caso de cambios)_",
        parse_mode='Markdown'
    )
    return ENTERING_PHONE

async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text
    
    s_id = context.user_data['service_id']
    service = database.get_service_by_id(s_id)
    
    # Format Date with Day Name (Spanish)
    date_obj = datetime.strptime(context.user_data['date'], "%Y-%m-%d")
    days_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    day_name = days_es[date_obj.weekday()]
    formatted_date = f"{day_name} {context.user_data['date']}"
    
    summary = (
        f"📝 **Confirmar Cita**\n\n"
        f"👤 **Paciente:** {context.user_data['name']}\n"
        f"🆔 **Cédula:** {context.user_data['patient_id']}\n"
        f"📱 **Celular:** {context.user_data['phone']}\n"
        f"🏥 **Servicio:** {service['nombre']}\n"
        f"📅 **Fecha:** {formatted_date}\n"
        f"🕒 **Hora:** {context.user_data['time']}\n\n"
        f"¿Todos los datos son correctos?"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ SÍ, Confirmar Cita", callback_data="confirm_booking_yes")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_booking")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(summary, reply_markup=reply_markup, parse_mode='Markdown')
    return CONFIRMING

async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_booking_yes":
        app_id = database.create_appointment(
            context.user_data['name'],
            context.user_data['patient_id'],
            context.user_data['phone'],
            context.user_data['service_id'],
            context.user_data['date'],
            context.user_data['time']
        )
        
        # Get Service Name for Credential
        service = database.get_service_by_id(context.user_data['service_id'])
        
        # Format Date
        date_obj = datetime.strptime(context.user_data['date'], "%Y-%m-%d")
        days_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        day_name = days_es[date_obj.weekday()]
        
        msg = (
            f"✅ **¡Cita Agendada Exitosamente!**\n\n"
            f"🎫 **Credencial de Cita**\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"👤 **Paciente:** {context.user_data['name']}\n"
            f"🏥 **Servicio:** {service['nombre']}\n"
            f"📅 **Fecha:** {day_name} {context.user_data['date']}\n"
            f"🕒 **Hora:** {context.user_data['time']}\n"
            f"━━━━━━━━━━━━━━━━\n\n"
            f"Te esperamos. Si necesitas algo más como la dirección del consultorio o cualquier otra ayuda referente a nuestros servicios no dudes en preguntar, estoy aquí para ayudarte."
        )
        
        await query.edit_message_text(msg, parse_mode='Markdown')
    else:
        await query.edit_message_text("❌ Cita cancelada. Puedes volver a empezar cuando quieras.")
    return ConversationHandler.END

# --- MANAGEMENT FLOW ---

async def receive_id_for_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    patient_id = update.message.text
    
    # Validate Numeric ID
    if not patient_id.isdigit():
        await update.message.reply_text("⚠️ Por favor ingresa un número de cédula válido (solo números).")
        return ENTERING_ID_CANCEL

    apps = database.get_appointments_by_patient(patient_id)
    
    if not apps:
        await update.message.reply_text("No encontré citas con esa cédula. Intenta de nuevo o escribe /cancel para salir.")
        return ENTERING_ID_CANCEL # Stay in state to allow retry
        
    # Show appointments with Cancel buttons
    msg = "📅 **Tus Citas:**\nSelecciona una para cancelar (mínimo 24h antes):"
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
            # Manageable (Cancel or Reschedule)
            btn_text = f"⚙️ {day_name} {app['date']} {app['time']} - {app['service_name']}"
            callback = f"manage_{app['id']}"
        else:
            # Locked
            btn_text = f"🔒 {day_name} {app['date']} {app['time']} (No modificable)"
            callback = "ignore_cancellation"
            
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    return ENTERING_ID_CANCEL

async def manage_appointment_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
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
        return ENTERING_ID_CANCEL # Stay in this state

    elif data == "back_to_list":
        # Re-trigger list (simulated by calling receive_id_for_management logic)
        # For simplicity, we just ask for ID again or better, re-show list if we had context.
        # Since we are in ConversationHandler, we can just re-call the list function if we stored ID.
        # But receive_id_for_management expects update.message.text. 
        # Easier: Ask to re-enter ID or just say "Cancelled".
        # Better: Store patient_id in context and re-run query.
        patient_id = context.user_data.get('manage_patient_id')
        if patient_id:
            # Re-fetch and show list
            apps = database.get_appointments_by_patient(patient_id)
            msg = "📅 **Tus Citas:**\nSelecciona una para gestionar:"
            keyboard = []
            now = datetime.now()
            for app in apps:
                app_dt = datetime.strptime(f"{app['date']} {app['time']}", "%Y-%m-%d %H:%M:%S")
                days_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                day_name = days_es[app_dt.weekday()]
                if app_dt.date() > now.date():
                    btn_text = f"⚙️ {day_name} {app['date']} {app['time']} - {app['service_name']}"
                    callback = f"manage_{app['id']}"
                else:
                    btn_text = f"🔒 {day_name} {app['date']} {app['time']} (No modificable)"
                    callback = "ignore_cancellation"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback)])
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            return ENTERING_ID_CANCEL
        else:
            await query.edit_message_text("Por favor ingresa tu cédula nuevamente.")
            return ENTERING_ID_CANCEL

    elif data == "confirm_cancel_ask":
        keyboard = [
            [InlineKeyboardButton("✅ SÍ, Cancelar Cita", callback_data="do_cancel")],
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
            await query.edit_message_text("❌ Error al cancelar. Intenta más tarde.")
        return ConversationHandler.END

    elif data == "reschedule_start":
        # Start Calendar Flow for Reschedule
        # We need to know we are rescheduling.
        context.user_data['is_rescheduling'] = True
        calendar_markup = create_calendar()
        await query.edit_message_text("📅 Selecciona la nueva fecha:", reply_markup=calendar_markup)
        return CHOOSING_DATE # Jump to Calendar State
        
    return ENTERING_ID_CANCEL # Wait for click

async def handle_cancellation_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("cancel_"):
        app_id = query.data.split("_")[1]
        # In a real app we might ask for confirmation again, but let's cancel for speed/parity
        database.cancel_appointment(app_id) # Need to ensure this function exists in database.py or add it
        msg = (
            "✅ **Cita cancelada exitosamente.**\n\n"
            "Si necesitas algo más como la dirección del consultorio o ayuda para agendar nuevamente otra cita no dudes en preguntar, estoy aquí para ayudarte."
        )
        await query.edit_message_text(msg, parse_mode='Markdown')
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END

if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Booking Conversation
    booking_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(button_click, pattern="^(show_all_services|view_service_|book_|cal_|ignore)"),
            MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
        ],
        states={
            CHOOSING_SERVICE: [CallbackQueryHandler(button_click)],
            CHOOSING_DATE: [
                CallbackQueryHandler(button_click),
                MessageHandler(filters.TEXT & (~filters.COMMAND), receive_date_manual)
            ],
            CHOOSING_TIME: [
                CallbackQueryHandler(button_click), # Handles time_ and confirm_time_
                MessageHandler(filters.TEXT, receive_time) # Keep fallback for now
            ],
            ENTERING_NAME: [MessageHandler(filters.TEXT, receive_name)],
            ENTERING_ID: [MessageHandler(filters.TEXT, receive_id)],
            ENTERING_PHONE: [MessageHandler(filters.TEXT, receive_phone)],
            CONFIRMING: [CallbackQueryHandler(confirm_booking)],
            
            ENTERING_ID_CANCEL: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), receive_id_for_management),
                CallbackQueryHandler(manage_appointment_menu)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(booking_conv)
    application.add_handler(CommandHandler('start', start))
    
    print("Bot is running...")
    application.run_polling()
