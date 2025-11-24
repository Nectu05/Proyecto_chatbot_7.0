import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import database
from datetime import datetime
import matplotlib.pyplot as plt
import io

def generate_financial_report(start_date, end_date=None):
    """
    Generates a PDF financial report for a specific date or date range.
    Includes charts and KPIs.
    """
    if end_date is None:
        end_date = start_date
        report_title = f"Reporte Financiero - {start_date}"
        appointments = database.get_daily_appointments(start_date)
    else:
        report_title = f"Reporte Financiero: {start_date} al {end_date}"
        appointments = database.get_appointments_by_range(start_date, end_date)

    # Directory Setup
    report_dir = "reportes"
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)

    filename = f"Reporte_{start_date}_al_{end_date}.pdf" if start_date != end_date else f"Reporte_{start_date}.pdf"
    filepath = os.path.join(report_dir, filename)

    doc = SimpleDocTemplate(filepath, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # --- 1. Header ---
    elements.append(Paragraph("Consultorio Ana María López", styles['Title']))
    elements.append(Paragraph("Fisioterapia Especializada", styles['Heading2']))
    elements.append(Paragraph(report_title, styles['Heading2']))
    elements.append(Spacer(1, 0.2 * inch))

    if not appointments:
        elements.append(Paragraph("No hay citas registradas para este periodo.", styles['Normal']))
        doc.build(elements)
        print(f"Reporte generado (vacío): {filepath}")
        return filepath

    # --- 2. Financial Summary (KPIs) ---
    # Filter active appointments for expected total
    active_appointments = [app for app in appointments if app['status'] != 'cancelled']
    
    total_expected = sum(app['price'] for app in active_appointments)
    total_collected = sum(app['payment_amount'] for app in appointments) # Keep collected as is (audit trail)
    pending_amount = total_expected - sum(app['payment_amount'] for app in active_appointments) # Pending only for active
    
    # Count only active for "Total Citas" or maybe show both? 
    # Let's show Total Citas Activas
    total_appointments = len(active_appointments)
    cancelled_count = len(appointments) - total_appointments

    summary_data = [
        ["Citas Activas", "Total Esperado", "Total Recaudado", "Pendiente"],
        [str(total_appointments), f"${total_expected:,.0f}", f"${total_collected:,.0f}", f"${pending_amount:,.0f}"]
    ]

    summary_table = Table(summary_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#ecf0f1")),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 14),
    ]))
    elements.append(summary_table)
    
    if cancelled_count > 0:
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(f"⚠️ Hay {cancelled_count} citas canceladas en este periodo.", styles['Normal']))
        
    elements.append(Spacer(1, 0.3 * inch))

    # --- 3. Charts Generation ---
    
    # Data Preparation
    payment_methods = {}
    services_count = {}

    for app in appointments:
        # Payment Methods (Include all money collected)
        method = app['payment_method'] if app['payment_method'] else "Pendiente"
        amount = app['payment_amount']
        if amount > 0:
            payment_methods[method] = payment_methods.get(method, 0) + amount
        
        # Services (Only count active for popularity?)
        # Usually better to count what was demanded, even if cancelled? 
        # Let's count only active for "Services Provided"
        if app['status'] != 'cancelled':
            service = app['service_name']
            services_count[service] = services_count.get(service, 0) + 1

    # Pie Chart: Income by Payment Method
    pie_chart_buffer = io.BytesIO()
    if payment_methods:
        plt.figure(figsize=(4, 3))
        plt.pie(payment_methods.values(), labels=payment_methods.keys(), autopct='%1.1f%%', startangle=140, colors=['#3498db', '#2ecc71', '#e74c3c', '#f1c40f'])
        plt.title('Ingresos por Método de Pago')
        plt.savefig(pie_chart_buffer, format='png')
        plt.close()
        pie_chart_buffer.seek(0)
        pie_img = Image(pie_chart_buffer, width=4*inch, height=3*inch)
    else:
        pie_img = Paragraph("No hay datos de pagos para graficar.", styles['Normal'])

    # Bar Chart: Top Services
    bar_chart_buffer = io.BytesIO()
    if services_count:
        plt.figure(figsize=(5, 3))
        plt.barh(list(services_count.keys()), list(services_count.values()), color='#9b59b6')
        plt.xlabel('Cantidad')
        plt.title('Servicios Realizados (Activos)')
        plt.tight_layout()
        plt.savefig(bar_chart_buffer, format='png')
        plt.close()
        bar_chart_buffer.seek(0)
        bar_img = Image(bar_chart_buffer, width=5*inch, height=3*inch)
    else:
        bar_img = Paragraph("No hay datos de servicios para graficar.", styles['Normal'])

    # Add Charts to PDF
    elements.append(Paragraph("Análisis Gráfico", styles['Heading2']))
    elements.append(pie_img)
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(bar_img)
    elements.append(Spacer(1, 0.3 * inch))

    # --- 4. Detailed Table ---
    elements.append(Paragraph("Detalle de Citas", styles['Heading2']))
    
    table_data = [['Paciente', 'Servicio', 'Fecha/Hora', 'Precio', 'Pago', 'Método']]
    
    for app in appointments:
        dt_str = f"{app.get('date', start_date)} {app['time'][:5]}"
        
        if app['status'] == 'cancelled':
            status_symbol = "🚫"
            payment_status_str = "CANCELADA"
            price_str = f"(${app['price']:,.0f})" # Show price in brackets or strike?
            # Let's just show it but maybe indicate it doesn't count
            row_bg = colors.lightgrey
        else:
            status_symbol = "✅" if app['payment_status'] == 'paid' else "⏳"
            payment_status_str = f"{status_symbol} {app['payment_status']}"
            price_str = f"${app['price']:,.0f}"
            row_bg = colors.beige

        row = [
            app['patient_name'],
            app['service_name'][:20] + "..." if len(app['service_name']) > 20 else app['service_name'],
            dt_str,
            price_str,
            payment_status_str,
            app['payment_method'] if app['payment_method'] else "-"
        ]
        table_data.append(row)

    table = Table(table_data, colWidths=[1.5*inch, 2*inch, 1.2*inch, 0.8*inch, 0.8*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    
    # Apply specific row colors for cancelled?
    # ReportLab TableStyle can take list of tuples for row backgrounds, but simpler to just leave it or add conditional formatting if possible.
    # For now, let's just mark them with text "CANCELADA".
    
    elements.append(table)

    # Build PDF
    doc.build(elements)
    print(f"Reporte generado con éxito: {filepath}")
    return filepath
