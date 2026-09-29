from io import BytesIO
from datetime import date
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side


def exportar_facturas_excel(anio, autoescuela, trimestre=None):
    from facturacion.models import Factura

    qs = Factura.objects.filter(anio=anio, autoescuela=autoescuela)
    if trimestre:
        qs = qs.filter(trimestre=trimestre)
    qs = qs.order_by('numero_factura')

    wb = Workbook()
    ws = wb.active
    ws.title = f'Facturas {anio}' if not trimestre else f'Trimestre {trimestre}'

    headers = ['CURSO', 'Nº FACTURA', 'FECHA', 'NOMBRE Y APELLIDOS', 'DNI',
               'BASE IMPONIBLE', 'IVA', 'TASAS', 'TOTAL',
               'DIRECCION', 'CP', 'MUNICIPIO', 'PROVINCIA']
    ws.append(headers)

    for f in qs:
        ws.append([
            f.curso,
            f.numero_factura,
            f.fecha.strftime('%d/%m/%Y') if f.fecha else '',
            f.nombre_factura,
            f.dni_factura,
            float(f.base_imponible),
            float(f.iva),
            float(f.tasas),
            float(f.total),
            f.direccion_factura,
            f.cp_factura,
            f.municipio_factura,
            f.provincia_factura,
        ])

    for row in range(2, ws.max_row + 1):
        for col in (6, 7, 8, 9):
            cell = ws.cell(row=row, column=col)
            if cell.value is not None:
                cell.number_format = '#,##0.00'

    col_widths = [8, 15, 12, 30, 12, 15, 12, 12, 12, 30, 8, 15, 15]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def exportar_alumnos(autoescuela):
    from facturacion.models import Alumno

    wb = Workbook()
    ws = wb.active
    ws.title = 'Alumnos'

    headers = ['NOMBRE Y APELLIDOS', 'DNI', 'DIRECCION', 'CP', 'MUNICIPIO', 'PROVINCIA']
    ws.append(headers)

    for col in range(1, len(headers) + 1):
        ws.cell(row=1, column=col).font = ws.cell(row=1, column=col).font.copy(bold=True)

    for a in Alumno.objects.filter(autoescuela=autoescuela).order_by('nombre'):
        ws.append([a.nombre, a.dni, a.direccion, a.codigo_postal, a.municipio, a.provincia])

    col_widths = [35, 15, 40, 10, 20, 20]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def exportar_registro_b(autoescuela):
    from facturacion.models import RegistroAlumno

    wb = Workbook()
    ws = wb.active
    ws.title = 'Hoja1'

    texto_legal = (
        'En cumplimiento de lo dispuesto en el artículo 39 del Reglamento regulador de las '
        'Escuelas Particulares de Conductores aprobado por R.D. 1295/2003, de fecha 17 de '
        'octubre, modificado por el R.D. 369/2010, de 26 de marzo, el presente libro de registro '
        'informatizado de alumnos de la Escuela de Conductores V-0281-01, denominada Auto '
        'Escuela La Albufera, S.L., con domicilio en Av. de La Albufera, Nº 18, de la localidad de '
        'Alfafar (46910-Valencia), recoge las inscripciones de aquellos cuya fecha de '
        'matriculación es posterior a fecha 01 de Julio de 2014, conservándose actualizado '
        'diariamente hasta el día de la fecha.'
    )
    texto_resumen = (
        'En cumplimiento de lo dispuesto en el artículo 39 del Reglamento regulador de las '
        'Escuelas Particulares de Conductores aprobado por R.D. 1295/2003, de fecha 17 de octubre, '
        'modificado por el R.D. 369/2010, de 26 de marzo, el presente libro de registro info'
    )
    meses = (
        'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
    )
    hoy = date.today()

    ws.merge_cells('B1:M1')
    ws['B1'] = texto_resumen
    ws['B1'].font = Font(name='Aptos Narrow', size=11, bold=True)
    ws['B1'].alignment = Alignment(vertical='center')

    ws.merge_cells('B4:M4')
    ws['B4'] = 'INFORMATIZADO'
    ws['B4'].font = Font(name='Aptos Narrow', size=11, bold=True)
    ws['B4'].alignment = Alignment(horizontal='center', vertical='center')

    ws.merge_cells('B5:M8')
    ws['B5'] = texto_legal
    ws['B5'].font = Font(name='Arial', size=9, bold=True)
    ws['B5'].alignment = Alignment(wrap_text=True, vertical='top')

    ws.merge_cells('A10:M10')
    ws['A10'] = f'Alfafar, a {hoy.day} de {meses[hoy.month - 1]} de {hoy.year}.'
    ws['A10'].font = Font(name='Aptos Narrow', size=11)
    ws['A10'].alignment = Alignment(vertical='center')

    ws.row_dimensions[1].height = 15
    ws.row_dimensions[4].height = 15
    ws.row_dimensions[5].height = 15
    ws.row_dimensions[6].height = 15
    ws.row_dimensions[7].height = 15
    ws.row_dimensions[8].height = 15
    ws.row_dimensions[10].height = 15
    ws.row_dimensions[11].height = 15.75

    headers = [
        'N_REG', 'F_ALTA', 'APELLIDO1', 'APELLIDO2', 'NOMBRE', 'DNI/NIF/NIE',
        'F_NTO', 'PMS', 'F.INI', 'F.FIN', 'Causa', 'OBSERVACIONES', 'F.APT.TEOR',
    ]
    header_fill = PatternFill('solid', fgColor='D0D0D0')
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin'),
    )
    for column, header in enumerate(headers, 1):
        cell = ws.cell(row=11, column=column, value=header)
        cell.font = Font(name='Arial', size=7.5, bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = thin_border

    registros = RegistroAlumno.objects.filter(autoescuela=autoescuela, permiso='B').select_related('alumno').order_by(
        'numero_registro', 'alumno__nombre'
    )
    row_number = 12
    for registro in registros:
        alumno = registro.alumno
        values = [
            registro.numero_registro,
            registro.fecha_alta,
            alumno.apellido1,
            alumno.apellido2,
            alumno.nombre_pila or alumno.nombre,
            alumno.dni,
            alumno.fecha_nacimiento,
            registro.permiso,
            registro.fecha_inicio,
            registro.fecha_fin,
            registro.causa,
            registro.observaciones,
            registro.fecha_apto_teorico or registro.estado_apto_teorico,
        ]
        for column, value in enumerate(values, 1):
            cell = ws.cell(row=row_number, column=column, value=value)
            cell.font = Font(name='Arial', size=8)
            cell.border = thin_border
            cell.alignment = Alignment(vertical='center', wrap_text=column == 12)
        row_number += 1

    for row in ws.iter_rows(min_row=12, min_col=2, max_col=13):
        for cell in row:
            if cell.column in (2, 7, 9, 10, 13) and cell.value:
                cell.number_format = 'DD/MM/YYYY'

    widths = [10.71, 10.71, 14.14, 15.57, 21.43, 11.71, 11.43, 10.71, 0, 10.71, 10.71, 39.14, 11.14]
    for index, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(index)].width = width
    ws.freeze_panes = 'A12'
    ws.auto_filter.ref = f'A11:M{max(row_number - 1, 11)}'
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def exportar_informe_comparacion_iva(anio, autoescuela):
    from facturacion.utils.iva_comparator import comparar_iva_anual

    informe = comparar_iva_anual(anio, autoescuela)
    wb = Workbook()

    ws = wb.active
    ws.title = 'RESUMEN'
    ws.append(['Trimestre', 'Facturas Correctas', 'IVA Correcto', 'Tasas (exentas)',
               'IVA Declarado (incorrecto)', 'Diferencia IVA'])

    for r in informe['resultados']:
        ws.append([
            f'T{r["trimestre"]}',
            r['correcto']['num_facturas'],
            float(r['correcto']['iva']),
            float(r['correcto']['tasas']),
            float(r['incorrecto']['iva']),
            float(r['diferencia_iva']),
        ])

    ws.append([
        'TOTAL ANUAL',
        sum(r['correcto']['num_facturas'] for r in informe['resultados']),
        float(informe['total_iva_correcto']),
        float(informe['total_tasas']),
        float(informe['total_iva_incorrecto']),
        float(informe['diferencia_total']),
    ])

    for col in range(3, 7):
        for row in range(2, ws.max_row + 1):
            ws.cell(row=row, column=col).number_format = '#,##0.00'

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
