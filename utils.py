from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import calendar
from datetime import datetime, timedelta

def create_calendar(year=None, month=None):
    """
    Creates an inline keyboard with a calendar for the given month and year.
    """
    now = datetime.now()
    if year is None: year = now.year
    if month is None: month = now.month
    
    data_ignore = "ignore"
    keyboard = []
    
    # Month and Year Header
    keyboard.append([
        InlineKeyboardButton(calendar.month_name[month] + " " + str(year), callback_data=data_ignore)
    ])
    
    # Days of Week Header
    days = ["L", "M", "M", "J", "V", "S", "D"]
    keyboard.append([InlineKeyboardButton(day, callback_data=data_ignore) for day in days])
    
    # Days of Month
    month_calendar = calendar.monthcalendar(year, month)
    for week in month_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data=data_ignore))
            else:
                # Check if day is past
                current_date = datetime(year, month, day).date()
                if current_date <= now.date():
                     row.append(InlineKeyboardButton("❌", callback_data=data_ignore)) # Past date or today
                else:
                     row.append(InlineKeyboardButton(str(day), callback_data=f"cal_{year}-{month:02d}-{day:02d}"))
        keyboard.append(row)
    
    # Navigation Buttons (Previous / Next Month)
    # Simple logic: just next month for now to keep it simple, or basic nav
    # For simplicity in this iteration, let's just show current month. 
    # If user needs next month, we can add nav later.
    
    return InlineKeyboardMarkup(keyboard)

def create_time_slots_keyboard(date_text, booked_slots):
    """
    Creates an inline keyboard with time slots.
    Green (✅) for available, Red (🔴) for booked.
    """
    # Define working hours: 9-12 and 14-19
    # Morning: 9, 10, 11
    # Afternoon: 14, 15, 16, 17, 18
    slots = [9, 10, 11, 14, 15, 16, 17, 18]
    
    keyboard = []
    row = []
    
    for hour in slots:
        time_str = f"{hour:02d}:00"
        
        if time_str in booked_slots:
            # Booked
            btn_text = f"{time_str} 🔴"
            callback = "ignore_booked"
        else:
            # Free
            btn_text = f"{time_str} 🟢"
            callback = f"time_{time_str}"
            
        row.append(InlineKeyboardButton(btn_text, callback_data=callback))
        
        if len(row) == 3: # 3 columns
            keyboard.append(row)
            row = []
            
    if row:
        keyboard.append(row)
        
    # Add Back Button
    keyboard.append([InlineKeyboardButton("🔙 Volver al Calendario", callback_data="back_to_calendar")])
    
    return InlineKeyboardMarkup(keyboard)
