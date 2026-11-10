from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from facturacion.models import Alumno, Autoescuela, EventoExamen, Factura, RegistroAlumno


class Command(BaseCommand):
    help = 'Elimina expedientes cerrados y alumnos que no conservan ningun expediente abierto.'

    def add_arguments(self, parser):
        parser.add_argument('--autoescuela-id', type=int, required=True, help='ID de la sede a depurar')
        parser.add_argument('--confirmar', action='store_true', help='Confirma el borrado permanente')

    @transaction.atomic
    def handle(self, *args, **options):
        if not options['confirmar']:
            raise CommandError('Este borrado es permanente. Ejecuta de nuevo con --confirmar.')

        try:
            autoescuela = Autoescuela.objects.get(pk=options['autoescuela_id'])
        except Autoescuela.DoesNotExist as error:
            raise CommandError('No existe una sede con ese ID.') from error

        expedientes = RegistroAlumno.objects.filter(
            autoescuela=autoescuela,
            fecha_fin__isnull=False,
        )
        alumno_ids = list(expedientes.values_list('alumno_id', flat=True).distinct())
        eventos = EventoExamen.objects.filter(registro__in=expedientes).count()
        expedientes_borrados = expedientes.count()
        expedientes.delete()

        alumnos = Alumno.objects.filter(autoescuela=autoescuela, pk__in=alumno_ids, registros__isnull=True)
        alumno_ids_borrados = list(alumnos.values_list('pk', flat=True))
        facturas = Factura.objects.filter(alumno_id__in=alumno_ids_borrados).count()
        alumnos_borrados = alumnos.count()
        alumnos.delete()

        self.stdout.write(self.style.SUCCESS(
            f'Sede: {autoescuela.nombre}. Expedientes borrados: {expedientes_borrados}. '
            f'Eventos eliminados: {eventos}. Alumnos eliminados: {alumnos_borrados}. '
            f'Facturas conservadas y desvinculadas: {facturas}.'
        ))
