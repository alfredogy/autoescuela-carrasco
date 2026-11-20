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
    _text(overlay, 155, 658, alumno.nombre_listado, 290, 8)
    _text(overlay, 485, 658, alumno.dni, 85, 8)
    _text(overlay, 120, 636, alumno.direccion, 370, 8)
    _text(overlay, 535, 636, alumno.codigo_postal, 45, 8)
    _text(overlay, 110, 614, alumno.telefono, 100, 8)
    _text(overlay, 275, 614, _date(alumno.fecha_nacimiento), 105, 8)
    _text(overlay, 420, 614, alumno.correo_electronico, 160, 8)
    overlay.save()

    page.merge_page(PdfReader(overlay_buffer).pages[0])
    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output
