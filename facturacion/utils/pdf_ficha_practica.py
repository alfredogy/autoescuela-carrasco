from io import BytesIO
from pathlib import Path

from django.conf import settings
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject
from reportlab.pdfgen import canvas

from facturacion.models import ConfiguracionTeorica


TEMPLATE_PATH = Path(settings.BASE_DIR) / 'facturacion' / 'assets' / 'Ficha Alumno Practica en blanco.pdf'


def _date(value):
    return value.strftime('%d/%m/%Y') if value else ''


def _remove_document_scripts(writer):
    writer._root_object.pop(NameObject('/Names'), None)


def _add_professor_name(writer, profesor):
    page = writer.pages[0]
    width, height = float(page.mediabox.width), float(page.mediabox.height)
    overlay_buffer = BytesIO()
    overlay = canvas.Canvas(overlay_buffer, pagesize=(width, height))
    overlay.setFont('Helvetica', 9)
    overlay.drawString(28, 615, profesor.nombre)
    overlay.save()
    page.merge_page(PdfReader(overlay_buffer).pages[0])


def generate_practical_sheet_pdf(registro, ficha):
    config = ConfiguracionTeorica.get_instance(registro.autoescuela)
    writer = PdfWriter(clone_from=PdfReader(str(TEMPLATE_PATH)))
    fields = {
        'practica': '/destreza' if ficha.tipo == 'DESTREZA' else '/circulacion',
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
        'Observaciones': ficha.observaciones,
    }
    for number, clase in enumerate(ficha.clases.all()[:11], 1):
        hora = 'HH:MM' if number == 1 else f'HoraRow{number}'
        fields.update({
            f'FechaRow{number}': _date(clase.fecha),
            hora: clase.hora.strftime('%H:%M') if clase.hora else '',
            f'EjercicioRow{number}': clase.ejercicio,
            f'Km inicioRow{number}': f'{clase.km_inicial:.2f}' if clase.km_inicial is not None else '',
            f'Km finalRow{number}': f'{clase.km_final:.2f}' if clase.km_final is not None else '',
            f'ObservacionesRow{number}': clase.observaciones,
        })

    writer.update_page_form_field_values(writer.pages[0], fields, auto_regenerate=False)
    _add_professor_name(writer, ficha.profesor)
    _remove_document_scripts(writer)
    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output
