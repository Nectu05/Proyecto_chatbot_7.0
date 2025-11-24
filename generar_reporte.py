import reports
from datetime import datetime
import os

def main():
    print("📊 Generando Reporte Diario...")
    
    # Default to today
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Optional: Allow user to input date
    user_input = input(f"Presiona ENTER para generar el reporte de hoy ({date_str}) o escribe una fecha (YYYY-MM-DD): ")
    if user_input.strip():
        date_str = user_input.strip()
        
    pdf_path = reports.generate_daily_report(date_str)
    
    if pdf_path and os.path.exists(pdf_path):
        print(f"\n✅ Reporte generado exitosamente en:\n{pdf_path}")
        # Try to open the folder
        os.startfile(os.path.dirname(pdf_path))
    else:
        print("\n❌ Error al generar el reporte.")
        
    input("\nPresiona ENTER para salir...")

if __name__ == "__main__":
    main()
