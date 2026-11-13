from io import BytesIO
from pathlib import Path

from django.conf import settings
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject
from reportlab.pdfgen import canvas

from facturacion.models import ConfiguracionTeorica, EventoExamen


TEMPLATE_PATH = Path(settings.BASE_DIR) / 'facturacion' / 'assets' / 'Ficha Alumno Formac Teorica en blanco.pdf'


def _date(value):
    return value.strftime('%d/%m/%Y') if value else ''


def _remove_document_scripts(writer):
    # The DGT template embeds JavaScript that tries to load a local data file in PDF.js.
    writer._root_object.pop(NameObject('/Names'), None)


def _add_professor_name(writer, profesor):
    page = writer.pages[0]
    width, height = float(page.mediabox.width), float(page.mediabox.height)
    overlay_buffer = BytesIO()
    overlay = canvas.Canvas(overlay_buffer, pagesize=(width, height))
    overlay.setFont('Helvetica', 9)
    overlay.drawString(28, 657, profesor.nombre)
    overlay.save()
    page.merge_page(PdfReader(overlay_buffer).pages[0])


def generate_theoretical_sheet_pdf(registro, ficha):
    config = ConfiguracionTeorica.get_instance(registro.autoescuela)
    writer = PdfWriter(clone_from=PdfReader(str(TEMPLATE_PATH)))
    fields = {
        'Número': config.numero,
        'Sección': config.seccion,
        'Dígito de control': config.digito_control,
        'Denominación': config.denominacion,
        'Dirección': config.direccion,
        'Código postal': config.codigo_postal,
        'Población': config.poblacion,
        'DNINIE': ficha.profesor.dni,
        'DNINIE_2': registro.alumno.dni,
        'Permiso que solicita': registro.permiso,
        'Nombre': registro.alumno.nombre_pila or registro.alumno.nombre,
        'Apellido 1': registro.alumno.apellido1,
        'Apellido 2': registro.alumno.apellido2,
        'Dirección_2': registro.alumno.direccion,
        'Código postal_2': registro.alumno.codigo_postal,
        'Población_2': registro.alumno.municipio,
        'Fecha de inicio de la enseñanza ddmmaaaa': _date(ficha.fecha_inicio),
        'Fecha de finalización del ciclo de la enseñanza ddmmaaaa': _date(ficha.fecha_fin),
        'Faltas de asistencia': str(ficha.faltas_asistencia),
        'Observaciones': ficha.observaciones,
    }
    for number, event in enumerate(EventoExamen.objects.filter(registro=registro, tipo='TEORICO').order_by('fecha', 'pk')[:5], 1):
        fields[f'Fecha del examen ddmmaaaaRow{number}'] = _date(event.fecha)
        fields[f'ResultadoRow{number}'] = event.get_resultado_display()

    writer.update_page_form_field_values(writer.pages[0], fields, auto_regenerate=False)
    _add_professor_name(writer, ficha.profesor)
    _remove_document_scripts(writer)
    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output
