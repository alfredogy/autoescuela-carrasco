from io import BytesIO
from pathlib import Path

from django.conf import settings
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

from facturacion.models import ConfiguracionTeorica


TEMPLATE_PATH = Path(settings.BASE_DIR) / 'facturacion' / 'assets' / 'Ficha Alumno Practica en blanco.pdf'


def _date(value):
    return value.strftime('%d/%m/%Y') if value else ''


def _text(pdf, x, y, value, size=8):
    pdf.setFont('Helvetica', size)
    pdf.drawString(x, y, str(value or ''))


def generate_practical_sheet_pdf(registro, ficha):
    config = ConfiguracionTeorica.get_instance(registro.autoescuela)
    template = PdfReader(str(TEMPLATE_PATH))
    writer = PdfWriter(clone_from=template)
    page = writer.pages[0]
    width, height = float(page.mediabox.width), float(page.mediabox.height)
    overlay_buffer = BytesIO()
    overlay = canvas.Canvas(overlay_buffer, pagesize=(width, height))

    _text(overlay, 130 if ficha.tipo == 'DESTREZA' else 430, 758, 'X', 12)
    _text(overlay, 55, 695, config.numero)
    _text(overlay, 195, 695, config.seccion)
    _text(overlay, 338, 695, config.digito_control)
    _text(overlay, 463, 695, config.denominacion)
    _text(overlay, 55, 657, config.direccion)
    _text(overlay, 400, 657, config.codigo_postal)
    _text(overlay, 505, 657, config.poblacion)
    _text(overlay, 55, 620, ficha.profesor.nombre)
    _text(overlay, 450, 620, ficha.profesor.dni)

    alumno = registro.alumno
    _text(overlay, 55, 556, alumno.dni)
    _text(overlay, 195, 556, registro.permiso)
    _text(overlay, 340, 556, alumno.nombre_pila or alumno.nombre)
    _text(overlay, 55, 525, alumno.apellido1)
    _text(overlay, 340, 525, alumno.apellido2)
    _text(overlay, 55, 490, alumno.direccion)
    _text(overlay, 400, 490, alumno.codigo_postal)
    _text(overlay, 505, 490, alumno.municipio)

    for y, clase in zip((437, 415, 393, 371, 349, 327, 305, 283, 261, 239, 217), ficha.clases.all()[:11]):
        _text(overlay, 52, y, _date(clase.fecha), 7)
        _text(overlay, 105, y, clase.hora.strftime('%H:%M') if clase.hora else '', 7)
        _text(overlay, 160, y, clase.ejercicio, 7)
        _text(overlay, 242, y, clase.km_inicial, 7)
        _text(overlay, 282, y, clase.km_final, 7)
        _text(overlay, 323, y, clase.observaciones, 7)

    text = overlay.beginText(55, 145)
    text.setFont('Helvetica', 8)
    for line in ficha.observaciones.splitlines()[:4]:
        text.textLine(line[:170])
    overlay.drawText(text)
    overlay.save()

    overlay_page = PdfReader(overlay_buffer).pages[0]
    page.merge_page(overlay_page)
    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output
