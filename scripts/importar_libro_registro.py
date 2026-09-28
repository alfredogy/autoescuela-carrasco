"""Importa el registro B desde Excel y lo vincula con los alumnos existentes."""
import argparse
import os
import sys
from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook


BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'autoescuela.settings')

import django

django.setup()

from django.db import transaction

from facturacion.models import Alumno, Autoescuela, Factura


def normalizar_dni(value):
    return str(value or '').upper().replace(' ', '').replace('-', '').strip()


def texto(value):
    return str(value or '').strip()


def fecha(value, avisos=None, fila=None, columna=None):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    for formato in ('%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(str(value).strip(), formato).date()
        except ValueError:
            pass
    if avisos is not None:
        avisos.append(f'Fila {fila}, {columna}: fecha no válida "{value}"')
    return None


def nombre_completo(apellido1, apellido2, nombre):
    return ' '.join(parte for parte in (texto(apellido1), texto(apellido2), texto(nombre)) if parte)


def clave_alumno(dni, nombre, nacimiento):
    dni_normalizado = normalizar_dni(dni)
    if dni_normalizado:
        return f'dni:{dni_normalizado}'
    return f'datos:{nombre.upper()}:{nacimiento or ""}'


def normalizar_nombre(nombre):
    return ' '.join(sorted(texto(nombre).upper().split()))


def estado_apto_teorico(value):
    estado = texto(value).upper()
    if estado == 'EXENTO' or estado.startswith('VIENE DE A'):
        return 'EXENTO'
    return ''


def consolidar_duplicados(alumnos, nombre_excel):
    """Conserva el alumno más antiguo cuando los duplicados son la misma persona."""
    if len(alumnos) <= 1:
        return alumnos[0] if alumnos else None, 0

    if any(normalizar_nombre(alumno.nombre) != normalizar_nombre(nombre_excel) for alumno in alumnos):
        raise ValueError(f'Hay varios alumnos distintos para {nombre_excel}.')

    alumnos = sorted(alumnos, key=lambda alumno: alumno.pk)
    alumno_principal = alumnos[0]
    for alumno_duplicado in alumnos[1:]:
        for campo in ('direccion', 'codigo_postal', 'municipio', 'provincia'):
            if not getattr(alumno_principal, campo) and getattr(alumno_duplicado, campo):
                setattr(alumno_principal, campo, getattr(alumno_duplicado, campo))
        Factura.objects.filter(alumno=alumno_duplicado).update(alumno=alumno_principal)
        alumno_duplicado.delete()
    alumno_principal.save()
    return alumno_principal, len(alumnos) - 1


def importar(path, nombre_autoescuela, dry_run=False):
    autoescuela = Autoescuela.objects.get(nombre=nombre_autoescuela)
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        worksheet = workbook.active
        headers = {
            texto(cell.value).upper(): cell.column
            for cell in worksheet[11]
            if texto(cell.value)
        }
        required = {'F_ALTA', 'APELLIDO1', 'NOMBRE', 'DNI/NIF/NIE', 'PMS'}
        missing = required - headers.keys()
        if missing:
            raise ValueError(f'Faltan columnas requeridas: {", ".join(sorted(missing))}')

        creados = actualizados = omitidos = no_b = duplicados = facturas_enlazadas = alumnos_fusionados = 0
        avisos = []
        alumnos_procesados = set()
        with transaction.atomic():
            for numero_fila, row in enumerate(worksheet.iter_rows(min_row=12, values_only=True), start=12):
                if not any(value not in (None, '') for value in row):
                    continue

                def value(header):
                    return row[headers[header] - 1] if header in headers else None

                def fecha_celda(header):
                    return fecha(value(header), avisos, numero_fila, header)

                if texto(value('PMS')) != 'B':
                    no_b += 1
                    continue

                alumno_nombre = nombre_completo(value('APELLIDO1'), value('APELLIDO2'), value('NOMBRE'))
                dni = texto(value('DNI/NIF/NIE'))
                if not alumno_nombre:
                    omitidos += 1
                    continue

                nacimiento = fecha_celda('F_NTO')
                clave = clave_alumno(dni, alumno_nombre, nacimiento)
                if clave in alumnos_procesados:
                    duplicados += 1
                    continue
                alumnos_procesados.add(clave)

                dni_normalizado = normalizar_dni(dni)
                if dni_normalizado:
                    alumnos = [
                        alumno for alumno in Alumno.objects.filter(autoescuela=autoescuela)
                        if alumno.dni_normalizado == dni_normalizado
                    ]
                else:
                    alumnos = list(Alumno.objects.filter(
                        autoescuela=autoescuela,
                        nombre__iexact=alumno_nombre,
                        fecha_nacimiento=nacimiento,
                    ))

                alumno_existente, fusionados = consolidar_duplicados(alumnos, alumno_nombre)
                alumnos_fusionados += fusionados
                alumnos = [alumno_existente] if alumno_existente else []

                numero_registro = len(alumnos_procesados)
                apto_teorico = value('F.APT.TEOR')
                estado_apto = estado_apto_teorico(apto_teorico)
                defaults = {
                    'nombre': alumno_nombre,
                    'nombre_pila': texto(value('NOMBRE')),
                    'apellido1': texto(value('APELLIDO1')),
                    'apellido2': texto(value('APELLIDO2')),
                    'dni': dni,
                    'permiso': 'B',
                    'numero_registro': numero_registro,
                    'fecha_alta': fecha_celda('F_ALTA'),
                    'fecha_nacimiento': nacimiento,
                    'fecha_inicio': fecha_celda('F.INI'),
                    'fecha_fin': fecha_celda('F.FIN'),
                    'causa': texto(value('CAUSA')),
                    'observaciones': texto(value('OBSERVACIONES')),
                    'fecha_apto_teorico': None if estado_apto else fecha_celda('F.APT.TEOR'),
                    'estado_apto_teorico': estado_apto,
                }
                if alumnos:
                    alumno = alumnos[0]
                    for field, field_value in defaults.items():
                        setattr(alumno, field, field_value)
                    alumno.save()
                    actualizados += 1
                else:
                    alumno = Alumno.objects.create(autoescuela=autoescuela, **defaults)
                    creados += 1

                if dni_normalizado:
                    for factura in Factura.objects.filter(
                        autoescuela=autoescuela, curso='B', alumno__isnull=True
                    ):
                        if normalizar_dni(factura.dni_factura) == dni_normalizado:
                            factura.alumno = alumno
                            factura.save(update_fields=['alumno'])
                            facturas_enlazadas += 1

            if dry_run:
                transaction.set_rollback(True)

        return (
            creados, actualizados, omitidos, no_b, duplicados, facturas_enlazadas,
            alumnos_fusionados, avisos,
        )
    finally:
        workbook.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archivo', type=Path, help='Ruta al LIBRO REGISTRO .xlsx')
    parser.add_argument('--autoescuela', required=True, help='Nombre exacto de la sede')
    parser.add_argument('--dry-run', action='store_true', help='Valida sin guardar cambios')
    args = parser.parse_args()

    creados, actualizados, omitidos, no_b, duplicados, facturas_enlazadas, alumnos_fusionados, avisos = importar(
        args.archivo, args.autoescuela, args.dry_run
    )
    accion = 'Validación terminada' if args.dry_run else 'Importación terminada'
    print(
        f'{accion}: {creados} creados, {actualizados} actualizados, '
        f'{duplicados} duplicados B ignorados, {no_b} filas de otros permisos omitidas, '
        f'{facturas_enlazadas} facturas B enlazadas, {alumnos_fusionados} alumnos duplicados fusionados, '
        f'{omitidos} filas sin nombre.'
    )
    for aviso in avisos:
        print(f'AVISO: {aviso}')


if __name__ == '__main__':
    main()
