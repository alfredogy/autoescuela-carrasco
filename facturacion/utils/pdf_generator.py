"""
Generador de facturas PDF con ReportLab.
Migrado de generar_facturas_pdf.py.
"""
from io import BytesIO
from pathlib import Path
from decimal import Decimal

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

from django.conf import settings


def generate_invoice_pdf(factura, output_buffer=None):
    """Genera un PDF de factura. Retorna un BytesIO."""
    from facturacion.models import Configuracion

    config = Configuracion.get_instance(factura.autoescuela)
    buffer = output_buffer or BytesIO()

    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Márgenes
    margin_left = 20 * mm
    margin_right = width - 20 * mm
    y = height - 20 * mm

    # === CABECERA: Logo + Datos emisor ===
    logo_path = Path(settings.BASE_DIR) / 'static' / 'img' / 'logo.png'
    if logo_path.exists():
        try:
            c.drawImage(str(logo_path), margin_left, y - 45 * mm,
                        width=60 * mm, height=45 * mm, preserveAspectRatio=True)
        except Exception:
            c.setFont("Helvetica-Bold", 14)
            c.drawString(margin_left, y - 5 * mm, "A U T O E S C U E L A")
            c.setFont("Helvetica-Bold", 22)
            c.drawString(margin_left, y - 15 * mm, "CARRASCO")
    else:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin_left, y - 5 * mm, "A U T O E S C U E L A")
        c.setFont("Helvetica-Bold", 22)
        c.drawString(margin_left, y - 15 * mm, "CARRASCO")

    # Recuadro datos emisor (derecha)
    box_x = 105 * mm
    box_y = y - 45 * mm
    box_width = 85 * mm
    box_height = 43 * mm

    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.rect(box_x, box_y, box_width, box_height)

    fecha_str = factura.fecha.strftime('%d/%m/%Y') if factura.fecha else ''
    c.setFont("Helvetica", 9)
    c.drawString(box_x + 3 * mm, box_y + box_height - 6 * mm, f"Fecha: {fecha_str}")
    c.drawString(box_x + 3 * mm, box_y + box_height - 12 * mm, f"Nombre: {config.emisor_nombre}")
    c.drawString(box_x + 3 * mm, box_y + box_height - 18 * mm, f"CIF: {config.emisor_dni}")
    c.drawString(box_x + 3 * mm, box_y + box_height - 24 * mm, f"Domicilio: {config.emisor_domicilio}")
    c.drawString(box_x + 3 * mm, box_y + box_height - 30 * mm, f"C.P: {config.emisor_cp}")
    c.drawString(box_x + 3 * mm, box_y + box_height - 36 * mm, f"Municipio/Provincia: {config.emisor_municipio}")

    y = y - 55 * mm

    # === DATOS CLIENTE ===
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    client_box_height = 40 * mm
    client_box_y = y - client_box_height
    c.rect(margin_left, client_box_y, 120 * mm, client_box_height)

    c.setFont("Helvetica", 9)
    c.drawString(margin_left + 3 * mm, y - 6 * mm, f"Cliente: {factura.nombre_factura}")
    c.drawString(margin_left + 3 * mm, y - 12 * mm, f"Dni: {factura.dni_factura}")
    c.drawString(margin_left + 3 * mm, y - 18 * mm, f"Domicilio: {factura.direccion_factura}")
    c.drawString(margin_left + 3 * mm, y - 24 * mm, f"C.P: {factura.cp_factura}")

    municipio_provincia = ''
    if factura.municipio_factura and factura.provincia_factura:
        municipio_provincia = f"{factura.municipio_factura}, {factura.provincia_factura}"
    else:
        municipio_provincia = factura.municipio_factura or factura.provincia_factura

    c.drawString(margin_left + 3 * mm, y - 30 * mm, f"Municipio/Provincia: {municipio_provincia}")
    c.drawString(margin_left + 3 * mm, y - 38 * mm, f"Nº FACTURA ALB {factura.numero_factura}")

    y = y - 50 * mm

    # === TABLA DE CONCEPTOS ===
    tasas_val = float(factura.tasas)
    conceptos = []
    tipo_curso = factura.curso or ''
    es_curso_exento = tipo_curso in ('C', 'C+E')

    # Concepto principal (curso)
    importe_curso = float(factura.base_imponible) + float(factura.iva) if es_curso_exento else float(factura.base_imponible)
    if importe_curso != 0:
        curso_texto = f"CURSO PERMISO {tipo_curso}".strip()
        if es_curso_exento:
            curso_texto += " (EXENTO DE IVA)"
        concepto_curso = f"{curso_texto}\nALUMNO: {factura.nombre_factura},\n{factura.dni_factura}"
        conceptos.append(['1', concepto_curso, f"{importe_curso:.2f}", ''])

    # Tasas desglosadas
    if tasas_val != 0:
        TASA_BASICA = float(config.tasa_basica)
        TASA_A = float(config.tasa_a)
        TASA_TRASLADO = float(config.traslado)

        tasas_restantes = tasas_val

        while tasas_restantes >= TASA_BASICA - 0.01:
            conceptos.append(['1', 'TASA DE TRAFICO (EXENTA DE IVA)', f"{TASA_BASICA:.2f}", ''])
            tasas_restantes = round(tasas_restantes - TASA_BASICA, 2)

        while tasas_restantes >= TASA_A - 0.01:
            conceptos.append(['1', 'TASA DE CURSO A (EXENTA DE IVA)', f"{TASA_A:.2f}", ''])
            tasas_restantes = round(tasas_restantes - TASA_A, 2)

        while tasas_restantes >= TASA_TRASLADO - 0.01:
            conceptos.append(['1', 'TASA DE TRASLADO (EXENTA DE IVA)', f"{TASA_TRASLADO:.2f}", ''])
            tasas_restantes = round(tasas_restantes - TASA_TRASLADO, 2)

        if tasas_restantes > 0.01:
            conceptos.append(['1', 'OTRAS TASAS (EXENTA DE IVA)', f"{tasas_restantes:.2f}", ''])

    # Crear tabla
    table_data = [['CANTIDAD', 'CONCEPTO', 'PRECIO', 'TOTAL']]
    table_data.extend(conceptos)

    while len(table_data) < 12:
        table_data.append(['', '', '', ''])

    col_widths = [20 * mm, 95 * mm, 25 * mm, 25 * mm]
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9),
        ('FONT', (0, 1), (-1, -1), 'Helvetica', 9),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (3, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.white),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))

    table_width, table_height = table.wrap(0, 0)
    table.drawOn(c, margin_left, y - table_height)

    y = y - table_height - 10 * mm

    # === TOTALES ===
    if es_curso_exento:
        base_imponible = 0.0
        iva_amount = 0.0
        exento = float(factura.base_imponible) + float(factura.iva) + float(factura.tasas)
    else:
        base_imponible = float(factura.base_imponible)
        iva_amount = float(factura.iva)
        exento = float(factura.tasas)

    totals_data = [
        ['BASE IMPONIBLE', f"{base_imponible:.2f}"],
        ['IVA 21 %', f"{iva_amount:.2f}"],
        ['EXENTO', f"{exento:.2f}"],
        ['TOTAL', f"{float(factura.total):.2f}\u20ac"],
    ]

    totals_table = Table(totals_data, colWidths=[35 * mm, 20 * mm])
    totals_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 9),
        ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold', 10),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))

    tw, th = totals_table.wrap(0, 0)
    totals_table.drawOn(c, margin_right - tw, y - th)

    c.save()
    buffer.seek(0)
    return buffer
