from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from .models import Alumno, Autoescuela, RegistroAlumno


class CompletarDatosDuplicadosTests(TestCase):
    def setUp(self):
        self.sede = Autoescuela.objects.create(nombre='Sede de prueba')

    def registro(self, alumno, cerrado=False):
        return RegistroAlumno.objects.create(
            autoescuela=self.sede,
            alumno=alumno,
            permiso='B',
            fecha_fin=date(2026, 1, 1) if cerrado else None,
        )

    def test_preview_does_not_modify_and_confirmation_completes_blank_fields(self):
        cerrado = Alumno.objects.create(
            autoescuela=self.sede, nombre='Ana Garcia', dni='1234-5678 z',
            direccion='Calle Mayor 1', codigo_postal='46910', municipio='Alfafar', telefono='600123456',
        )
        abierto = Alumno.objects.create(autoescuela=self.sede, nombre='Ana Garcia', dni='12345678Z')
        self.registro(cerrado, cerrado=True)
        self.registro(abierto)

        salida = StringIO()
        call_command('completar_datos_duplicados', '--autoescuela-id', str(self.sede.pk), stdout=salida)
        abierto.refresh_from_db()
        self.assertEqual(abierto.direccion, '')
        self.assertIn('posibles actualizaciones: 1', salida.getvalue())

        call_command('completar_datos_duplicados', '--autoescuela-id', str(self.sede.pk), '--confirmar')
        abierto.refresh_from_db()
        self.assertEqual(abierto.direccion, 'Calle Mayor 1')
        self.assertEqual(abierto.codigo_postal, '46910')
        self.assertEqual(abierto.municipio, 'Alfafar')
        self.assertEqual(abierto.telefono, '600123456')

    def test_skips_multiple_open_records_and_preserves_existing_data(self):
        cerrado = Alumno.objects.create(
            autoescuela=self.sede, nombre='Ana Garcia', dni='12345678Z', direccion='Calle anterior 1',
        )
        abierto = Alumno.objects.create(
            autoescuela=self.sede, nombre='Ana Garcia', dni='12345678Z', direccion='Calle actual 2',
        )
        otro_abierto = Alumno.objects.create(autoescuela=self.sede, nombre='Ana Garcia', dni='12345678Z')
        self.registro(cerrado, cerrado=True)
        self.registro(abierto)
        self.registro(otro_abierto)

        salida = StringIO()
        call_command('completar_datos_duplicados', '--autoescuela-id', str(self.sede.pk), '--confirmar', stdout=salida)
        abierto.refresh_from_db()
        self.assertEqual(abierto.direccion, 'Calle actual 2')
        self.assertIn('omitido (2 expedientes abiertos)', salida.getvalue())

    def test_skips_a_field_when_closed_duplicates_disagree(self):
        primera = Alumno.objects.create(
            autoescuela=self.sede, nombre='Ana Garcia', dni='12345678Z', telefono='600111111',
        )
        segunda = Alumno.objects.create(
            autoescuela=self.sede, nombre='Ana Garcia', dni='12345678Z', telefono='600222222',
        )
        abierto = Alumno.objects.create(autoescuela=self.sede, nombre='Ana Garcia', dni='12345678Z')
        self.registro(primera, cerrado=True)
        self.registro(segunda, cerrado=True)
        self.registro(abierto)

        salida = StringIO()
        call_command('completar_datos_duplicados', '--autoescuela-id', str(self.sede.pk), '--confirmar', stdout=salida)
        abierto.refresh_from_db()
        self.assertEqual(abierto.telefono, '')
        self.assertIn('campo telefono omitido (valores distintos)', salida.getvalue())
