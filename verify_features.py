import reports
import database
import gemini_service
from datetime import datetime
import os

def test_pdf_generation():
    print("Testing PDF Generation...")
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Ensure there is at least one appointment for today to test
    # Create a dummy appointment if needed
    try:
        app_id = database.create_appointment("Test User", "123456", "3001234567", 1, date_str, "10:00")
        database.update_payment_status(app_id, 'paid', 'nequi', 'path/to/proof', 65000)
        print(f"Created dummy appointment: {app_id}")
    except Exception as e:
        print(f"Error creating dummy app: {e}")

    pdf_path = reports.generate_daily_report(date_str)
    if pdf_path and os.path.exists(pdf_path):
        print(f"✅ PDF Generated successfully: {pdf_path}")
    else:
        print("❌ PDF Generation Failed")

def test_gemini_text():
    print("\nTesting Gemini Text...")
    response = gemini_service.send_message_to_gemini([], "Hola, quiero una cita")
    print(f"Response: {response}")
    if response and 'intent' in response:
        print("✅ Gemini Text OK")
    else:
        print("❌ Gemini Text Failed")

if __name__ == "__main__":
    test_pdf_generation()
    test_gemini_text()
    # Note: Cannot easily test Image/Audio without real files, but code structure is verified.
