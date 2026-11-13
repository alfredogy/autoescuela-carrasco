from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from facturacion.models import Autoescuela, RegistroAlumno


class Command(BaseCommand):
    help = 'Renumerar los expedientes B por fecha de alta, sin saltos.'

    def add_arguments(self, parser):
        parser.add_argument('--autoescuela-id', type=int, required=True, help='ID de la sede a renumerar')
        parser.add_argument('--confirmar', action='store_true', help='Confirma la renumeracion')

    @transaction.atomic
    def handle(self, *args, **options):
        if not options['confirmar']:
            raise CommandError('Ejecuta de nuevo con --confirmar.')

        try:
            autoescuela = Autoescuela.objects.get(pk=options['autoescuela_id'])
        except Autoescuela.DoesNotExist as error:
            raise CommandError('No existe una sede con ese ID.') from error

        registros = RegistroAlumno.objects.filter(autoescuela=autoescuela, permiso='B')
        total = registros.count()
        antes = dict(registros.values_list('pk', 'numero_registro'))
        RegistroAlumno.renumerar_b(autoescuela)
        modificados = sum(
            antes[registro.pk] != registro.numero_registro
            for registro in registros.only('pk', 'numero_registro')
        )
        self.stdout.write(self.style.SUCCESS(
            f'Sede: {autoescuela.nombre}. Registros B renumerados: {total}. Cambios: {modificados}.'
        ))
