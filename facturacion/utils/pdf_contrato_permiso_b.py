from io import BytesIO
from pathlib import Path

from django.conf import settings
from pypdf import PdfReader, PdfWriter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


TEMPLATE_PATH = Path(settings.BASE_DIR) / 'facturacion' / 'assets' / 'Contrato de Ensenanza Permiso B.pdf'


def _date(value):
    return value.strftime('%d/%m/%Y') if value else ''


def _text(pdf, x, y, value, max_width, size=8):
    value = str(value or '')
    while value and stringWidth(value, 'Helvetica', size) > max_width:
        value = value[:-1]
    pdf.setFont('Helvetica', size)
    pdf.drawString(x, y, value)


def generate_permit_b_contract_pdf(registro):
    template = PdfReader(str(TEMPLATE_PATH))
    writer = PdfWriter(clone_from=template)
    page = writer.pages[0]
    width, height = float(page.mediabox.width), float(page.mediabox.height)
    overlay_buffer = BytesIO()
    overlay = canvas.Canvas(overlay_buffer, pagesize=(width, height))
    alumno = registro.alumno

    _text(overlay, 530, 784, registro.numero_registro, 50, 9)
    _text(overlay, 120, 671, alumno.nombre_listado, 220, 8)
    _text(overlay, 410, 671, alumno.dni, 160, 8)
    _text(overlay, 85, 655, alumno.direccion, 250, 8)
    _text(overlay, 420, 655, alumno.municipio, 80, 8)
    _text(overlay, 535, 655, alumno.codigo_postal, 45, 8)
    _text(overlay, 40, 633, _date(alumno.fecha_nacimiento), 100, 7)
    _text(overlay, 210, 638, alumno.telefono, 55, 8)
    _text(overlay, 365, 638, alumno.correo_electronico, 140, 8)
    overlay.save()

    page.merge_page(PdfReader(overlay_buffer).pages[0])
    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output
