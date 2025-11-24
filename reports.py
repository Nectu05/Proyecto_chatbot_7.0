from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime
import database
import os

def generate_daily_report(date_str):
    """
    Generates a PDF report for the given date.
    Returns the file path of the generated PDF.
    """
    try:
        # Fetch Data
        appointments = database.get_daily_appointments(date_str)
        
        # Calculate Totals
        total_expected = sum(app['price'] for app in appointments)
        total_collected = sum(app['payment_amount'] for app in appointments if app['payment_status'] == 'paid')
        
        # Breakdown by Method
        methods = {}
        for app in appointments:
            if app['payment_status'] == 'paid':
                method = app['payment_method'] or 'Desconocido'
                methods[method] = methods.get(method, 0) + app['payment_amount']

        # Create 'reportes' directory if not exists
        reports_dir = os.path.join(os.getcwd(), 'reportes')
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)

        # Create PDF
        filename = f"Reporte_Diario_{date_str}.pdf"
        filepath = os.path.join(reports_dir, filename)
        
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = styles['Title']
        elements.append(Paragraph(f"Reporte Diario de Citas - {date_str}", title_style))
        elements.append(Spacer(1, 12))
        
        # Summary Section
        elements.append(Paragraph("<b>Resumen Financiero</b>", styles['Heading2']))
        
        summary_data = [
            ["Concepto", "Valor"],
            ["Total Esperado (Servicios Agendados)", f"${total_expected:,.0f}"],
            ["Total Recaudado (Pagos Confirmados)", f"${total_collected:,.0f}"],
        ]
        
        summary_table = Table(summary_data, colWidths=[300, 150])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 12))
        
        # Payment Methods Breakdown
        if methods:
            elements.append(Paragraph("<b>Desglose por Método de Pago</b>", styles['Heading3']))
            method_data = [["Método", "Total"]]
            for method, amount in methods.items():
                method_data.append([method.capitalize(), f"${amount:,.0f}"])
            
            method_table = Table(method_data, colWidths=[300, 150])
            method_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(method_table)
            elements.append(Spacer(1, 12))

        # Detailed List
        elements.append(Paragraph("<b>Detalle de Citas</b>", styles['Heading2']))
        
        data = [["Paciente", "Servicio", "Precio", "Estado Pago", "Método"]]
        
        for app in appointments:
            status_text = "PAGADO" if app['payment_status'] == 'paid' else "PENDIENTE"
            method_text = app['payment_method'] if app['payment_method'] else "-"
            
            data.append([
                app['patient_name'],
                app['service_name'],
                f"${app['price']:,.0f}",
                status_text,
                method_text
            ])
            
        table = Table(data, colWidths=[120, 150, 80, 80, 80])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.aliceblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(table)
        
        # Build
        doc.build(elements)
        return filepath
        
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return None
