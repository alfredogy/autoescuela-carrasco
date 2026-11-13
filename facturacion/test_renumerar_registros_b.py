from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from .models import Alumno, Autoescuela, RegistroAlumno


class RenumerarRegistrosBTests(TestCase):
    def setUp(self):
        self.sede = Autoescuela.objects.create(nombre='Sede de prueba')

    def registro(self, *, permiso='B', fecha_alta=None, numero_registro=None):
        alumno = Alumno.objects.create(autoescuela=self.sede, nombre=f'Alumno {Alumno.objects.count()}')
        return RegistroAlumno.objects.create(
            autoescuela=self.sede,
            alumno=alumno,
            permiso=permiso,
            fecha_alta=fecha_alta,
            numero_registro=numero_registro,
        )

    def test_renumbers_only_b_records_by_fecha_inicio_without_gaps(self):
        posterior = self.registro(fecha_alta=date(2026, 1, 1), numero_registro=40)
        posterior.fecha_inicio = date(2026, 3, 1)
        posterior.save()
        sin_fecha = self.registro(fecha_alta=None, numero_registro=12)
        primero = self.registro(fecha_alta=date(2026, 3, 1), numero_registro=8)
        primero.fecha_inicio = date(2026, 1, 1)
        primero.save()
        permiso_a = self.registro(permiso='A', fecha_alta=date(2025, 1, 1), numero_registro=None)

        RegistroAlumno.renumerar_b(self.sede)

        primero.refresh_from_db()
        posterior.refresh_from_db()
        sin_fecha.refresh_from_db()
        permiso_a.refresh_from_db()
        self.assertEqual((primero.numero_registro, posterior.numero_registro, sin_fecha.numero_registro), (1, 2, 3))
        self.assertIsNone(permiso_a.numero_registro)

    def test_command_renumbers_the_selected_school(self):
        primero = self.registro(fecha_alta=date(2026, 1, 1), numero_registro=10)
        segundo = self.registro(fecha_alta=date(2026, 2, 1), numero_registro=30)

        salida = StringIO()
        call_command('renumerar_registros_b', '--autoescuela-id', str(self.sede.pk), '--confirmar', stdout=salida)

        primero.refresh_from_db()
        segundo.refresh_from_db()
        self.assertEqual((primero.numero_registro, segundo.numero_registro), (1, 2))
        self.assertIn('Cambios: 2', salida.getvalue())
