from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from .models import Alumno, Autoescuela, RegistroAlumno


class ReorganizarFechasRegistrosTests(TestCase):
    def setUp(self):
        self.sede = Autoescuela.objects.create(nombre='Sede de prueba')
        self.ajena = Autoescuela.objects.create(nombre='Sede ajena')

    def registro(self, sede, *, fecha_alta, fecha_inicio=None, numero_registro=None):
        alumno = Alumno.objects.create(autoescuela=sede, nombre=f'Alumno {Alumno.objects.count()}')
        return RegistroAlumno.objects.create(
            autoescuela=sede,
            alumno=alumno,
            permiso='B',
            fecha_alta=fecha_alta,
            fecha_inicio=fecha_inicio,
            numero_registro=numero_registro,
        )

    def test_moves_historical_date_to_inicio_and_renumbers_b(self):
        antiguo = self.registro(
            self.sede, fecha_alta=date(2026, 1, 10), fecha_inicio=date(2020, 1, 1), numero_registro=8,
        )
        corte = self.registro(self.sede, fecha_alta=date(2026, 11, 5), numero_registro=12)
        posterior = self.registro(self.sede, fecha_alta=date(2026, 12, 1), numero_registro=3)
        sin_fecha = self.registro(self.sede, fecha_alta=None, numero_registro=4)
        ajeno = self.registro(self.ajena, fecha_alta=date(2026, 1, 1), numero_registro=9)

        salida = StringIO()
        call_command('reorganizar_fechas_registros', '--autoescuela-id', str(self.sede.pk), '--confirmar', stdout=salida)

        antiguo.refresh_from_db()
        corte.refresh_from_db()
        posterior.refresh_from_db()
        sin_fecha.refresh_from_db()
        ajeno.refresh_from_db()
        self.assertEqual((antiguo.fecha_inicio, antiguo.fecha_alta), (date(2026, 1, 10), date(2026, 11, 5)))
        self.assertEqual((corte.fecha_inicio, corte.fecha_alta), (date(2026, 11, 5), date(2026, 11, 5)))
        self.assertEqual((posterior.fecha_inicio, posterior.fecha_alta), (date(2026, 12, 1), date(2026, 12, 1)))
        self.assertIsNone(sin_fecha.fecha_inicio)
        self.assertIsNone(sin_fecha.fecha_alta)
        self.assertEqual((antiguo.numero_registro, corte.numero_registro, posterior.numero_registro, sin_fecha.numero_registro), (1, 2, 3, 4))
        self.assertEqual((ajeno.fecha_inicio, ajeno.fecha_alta, ajeno.numero_registro), (None, date(2026, 1, 1), 9))
        self.assertIn('Registros actualizados: 3', salida.getvalue())
        self.assertIn('Registros sin fecha alta: 1', salida.getvalue())
