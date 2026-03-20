"""
Management command para importar datos desde Excel.

Uso:
    python manage.py importar_excel /ruta/a/carpeta/
    python manage.py importar_excel /ruta/a/carpeta/ --listados
"""
from django.core.management.base import BaseCommand
from pathlib import Path


class Command(BaseCommand):
    help = 'Importa datos desde archivos Excel de trimestres'

    def add_arguments(self, parser):
        parser.add_argument('carpeta', type=str, help='Carpeta con los archivos Excel')
        parser.add_argument('--listados', action='store_true',
                            help='También importar listados históricos')
        parser.add_argument('--anio', type=int, default=2025,
                            help='Año de los datos (default: 2025)')

    def handle(self, *args, **options):
        carpeta = Path(options['carpeta'])
        anio = options['anio']

        if not carpeta.exists():
            self.stderr.write(self.style.ERROR(f'Carpeta no encontrada: {carpeta}'))
            return

        from facturacion.utils.excel_importer import importar_trimestre, importar_listado

        # Importar trimestres
        self.stdout.write(self.style.WARNING(f'Importando trimestres del año {anio}...'))
        total = 0

        for i in range(1, 5):
            filepath = carpeta / f'Trimestre-{i}.xlsx'
            if filepath.exists():
                with open(filepath, 'rb') as f:
                    count = importar_trimestre(f, i, anio)
                self.stdout.write(f'  Trimestre {i}: {count} facturas importadas')
                total += count
            else:
                self.stdout.write(f'  Trimestre {i}: archivo no encontrado')

        self.stdout.write(self.style.SUCCESS(f'Total facturas importadas: {total}'))

        # Importar listados históricos
        if options['listados']:
            self.stdout.write(self.style.WARNING('\nImportando listados históricos...'))
            nombres = {
                1: 'LISTADO FACT 1 TRI.xlsx',
                2: 'LISTADO FACT 2 TRI.xlsx',
                3: 'LISTADO FACT 3 TRI .xlsx',
                4: 'LISTADO FACT 4 TRI.xlsx',
            }
            total_hist = 0
            for i, nombre in nombres.items():
                filepath = carpeta / nombre
                if filepath.exists():
                    with open(filepath, 'rb') as f:
                        count = importar_listado(f, i, anio)
                    self.stdout.write(f'  Listado T{i}: {count} registros importados')
                    total_hist += count
                else:
                    self.stdout.write(f'  Listado T{i}: archivo no encontrado ({nombre})')

            self.stdout.write(self.style.SUCCESS(f'Total registros históricos: {total_hist}'))
