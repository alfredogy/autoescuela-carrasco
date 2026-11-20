from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from facturacion.models import Alumno, Autoescuela, RegistroAlumno


FIELDS = (
    'nombre', 'nombre_pila', 'apellido1', 'apellido2', 'telefono', 'correo_electronico',
    'direccion', 'codigo_postal', 'municipio', 'provincia', 'fecha_nacimiento',
    'fecha_caducidad_dni',
)


def has_value(value):
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


class Command(BaseCommand):
    help = 'Completa campos vacios de alumnos con expediente abierto usando duplicados por DNI.'

    def add_arguments(self, parser):
        parser.add_argument('--autoescuela-id', type=int, required=True, help='ID de la sede a revisar')
        parser.add_argument('--confirmar', action='store_true', help='Aplica los cambios mostrados')

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            autoescuela = Autoescuela.objects.get(pk=options['autoescuela_id'])
        except Autoescuela.DoesNotExist as error:
            raise CommandError('No existe una sede con ese ID.') from error

        alumnos_por_dni = defaultdict(list)
        for alumno in Alumno.objects.filter(autoescuela=autoescuela).order_by('pk'):
            if alumno.dni_normalizado:
                alumnos_por_dni[alumno.dni_normalizado].append(alumno)

        alumnos_abiertos = set(RegistroAlumno.objects.filter(
            autoescuela=autoescuela,
            fecha_fin__isnull=True,
        ).values_list('alumno_id', flat=True))
        cambios = 0
        omitidos = 0

        for dni, alumnos in alumnos_por_dni.items():
            if len(alumnos) < 2:
                continue

            destinos = [alumno for alumno in alumnos if alumno.pk in alumnos_abiertos]
            if len(destinos) != 1:
                omitidos += 1
                self.stdout.write(f'DNI {dni}: omitido ({len(destinos)} expedientes abiertos).')
                continue

            destino = destinos[0]
            origenes = [alumno for alumno in alumnos if alumno.pk != destino.pk]
            actualizaciones = {}
            for field in FIELDS:
                if has_value(getattr(destino, field)):
                    continue
                valores = {getattr(origen, field) for origen in origenes if has_value(getattr(origen, field))}
                if len(valores) == 1:
                    actualizaciones[field] = valores.pop()
                elif len(valores) > 1:
                    omitidos += 1
                    self.stdout.write(f'DNI {dni}: campo {field} omitido (valores distintos).')

            if not actualizaciones:
                continue

            campos = ', '.join(actualizaciones)
            self.stdout.write(f'DNI {dni}: alumno #{destino.pk}, completar {campos}.')
            cambios += 1
            if options['confirmar']:
                for field, value in actualizaciones.items():
                    setattr(destino, field, value)
                destino.save(update_fields=[*actualizaciones, 'updated_at'])

        action = 'actualizados' if options['confirmar'] else 'posibles actualizaciones'
        self.stdout.write(self.style.SUCCESS(
            f'Sede: {autoescuela.nombre}. {action}: {cambios}. Omitidos: {omitidos}.'
        ))
        if not options['confirmar']:
            self.stdout.write('No se ha modificado ningun dato. Ejecuta de nuevo con --confirmar para aplicar los cambios.')
