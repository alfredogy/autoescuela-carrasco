from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from facturacion.models import Autoescuela, RegistroAlumno


FECHA_CORTE = date(2026, 11, 5)


class Command(BaseCommand):
    help = 'Convierte la fecha alta historica en fecha inicio y establece la nueva fecha alta.'

    def add_arguments(self, parser):
        parser.add_argument('--autoescuela-id', type=int, required=True, help='ID de la sede a actualizar')
        parser.add_argument('--confirmar', action='store_true', help='Confirma la actualizacion permanente')

    @transaction.atomic
    def handle(self, *args, **options):
        if not options['confirmar']:
            raise CommandError('Ejecuta de nuevo con --confirmar.')

        try:
            autoescuela = Autoescuela.objects.get(pk=options['autoescuela_id'])
        except Autoescuela.DoesNotExist as error:
            raise CommandError('No existe una sede con ese ID.') from error

        registros = RegistroAlumno.objects.filter(autoescuela=autoescuela)
        sin_fecha = registros.filter(fecha_alta__isnull=True).count()
        actualizados = 0
        for registro in registros.exclude(fecha_alta__isnull=True).only('pk', 'fecha_alta'):
            fecha_inicio = registro.fecha_alta
            nueva_fecha_alta = FECHA_CORTE if fecha_inicio <= FECHA_CORTE else fecha_inicio
            RegistroAlumno.objects.filter(pk=registro.pk).update(
                fecha_inicio=fecha_inicio,
                fecha_alta=nueva_fecha_alta,
            )
            actualizados += 1

        RegistroAlumno.renumerar_b(autoescuela)
        self.stdout.write(self.style.SUCCESS(
            f'Sede: {autoescuela.nombre}. Registros actualizados: {actualizados}. '
            f'Registros sin fecha alta: {sin_fecha}. Fecha de corte: {FECHA_CORTE:%d/%m/%Y}.'
        ))
