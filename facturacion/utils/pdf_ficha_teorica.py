from io import BytesIO
from pathlib import Path

from django.conf import settings
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

from facturacion.models import ConfiguracionTeorica, EventoExamen


TEMPLATE_PATH = Path(settings.BASE_DIR) / 'facturacion' / 'assets' / 'Ficha Alumno Formac Teorica en blanco.pdf'


def _date(value):
    return value.strftime('%d/%m/%Y') if value else ''


def _text(pdf, x, y, value, size=9):
    pdf.setFont('Helvetica', size)
    pdf.drawString(x, y, str(value or ''))


def generate_theoretical_sheet_pdf(registro, ficha):
    config = ConfiguracionTeorica.get_instance(registro.autoescuela)
    template = PdfReader(str(TEMPLATE_PATH))
    writer = PdfWriter(clone_from=template)
    page = writer.pages[0]
    width, height = float(page.mediabox.width), float(page.mediabox.height)
    overlay_buffer = BytesIO()
    overlay = canvas.Canvas(overlay_buffer, pagesize=(width, height))

    _text(overlay, 55, 724, config.numero)
    _text(overlay, 195, 724, config.seccion)
    _text(overlay, 338, 724, config.digito_control)
    _text(overlay, 463, 724, config.denominacion)
    _text(overlay, 55, 665, config.direccion)
    _text(overlay, 400, 665, config.codigo_postal)
    _text(overlay, 505, 665, config.poblacion)
    _text(overlay, 55, 605, ficha.profesor.nombre)
    _text(overlay, 450, 605, ficha.profesor.dni)

    alumno = registro.alumno
    _text(overlay, 55, 538, alumno.dni)
    _text(overlay, 195, 538, registro.permiso)
    _text(overlay, 340, 538, alumno.nombre_pila or alumno.nombre)
    _text(overlay, 55, 507, alumno.apellido1)
    _text(overlay, 340, 507, alumno.apellido2)
    _text(overlay, 55, 476, alumno.direccion)
    _text(overlay, 400, 476, alumno.codigo_postal)
    _text(overlay, 505, 476, alumno.municipio)
    _text(overlay, 55, 416, _date(ficha.fecha_inicio))
    _text(overlay, 220, 416, _date(ficha.fecha_fin))
    _text(overlay, 410, 416, ficha.faltas_asistencia)

    for y, event in zip((347, 316, 285, 254, 223), EventoExamen.objects.filter(
            registro=registro, tipo='TEORICO').order_by('fecha', 'pk')):
        _text(overlay, 150, y, _date(event.fecha))
        _text(overlay, 400, y, event.get_resultado_display())
    text = overlay.beginText(55, 165)
    text.setFont('Helvetica', 9)
    for line in ficha.observaciones.splitlines()[:5]:
        text.textLine(line[:130])
    overlay.drawText(text)
    overlay.save()

    overlay_page = PdfReader(overlay_buffer).pages[0]
    page.merge_page(overlay_page)
    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output
