import reports
from datetime import datetime, timedelta

def main():
    print("=========================================")
    print("   GENERADOR DE REPORTES FINANCIEROS")
    print("=========================================")
    print("1. Reporte de HOY")
    print("2. Reporte de la SEMANA (Últimos 7 días)")
    print("3. Reporte del MES (Mes actual)")
    print("4. Rango Personalizado")
    print("=========================================")
    
    choice = input("Selecciona una opción (1-4): ")
    
    start_date = None
    end_date = None
    
    if choice == '1':
        start_date = datetime.now().strftime("%Y-%m-%d")
        end_date = start_date
        
    elif choice == '2':
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
    elif choice == '3':
        now = datetime.now()
        start_date = now.replace(day=1).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")
        
    elif choice == '4':
        print("\nFormato de fecha: YYYY-MM-DD (Ej: 2023-10-27)")
        start_date = input("Fecha Inicio: ")
        end_date = input("Fecha Fin: ")
        
    else:
        print("Opción inválida.")
        return

    print(f"\nGenerando reporte desde {start_date} hasta {end_date}...")
    try:
        filepath = reports.generate_financial_report(start_date, end_date)
        print(f"\n✅ ¡Reporte generado con éxito!")
        print(f"📂 Ubicación: {filepath}")
    except Exception as e:
        print(f"\n❌ Error al generar el reporte: {e}")

if __name__ == "__main__":
    main()
