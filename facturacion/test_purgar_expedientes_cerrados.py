from datetime import date
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from .models import Alumno, Autoescuela, EventoExamen, Factura, RegistroAlumno


class PurgarExpedientesCerradosTests(TestCase):
    def setUp(self):
        self.sede = Autoescuela.objects.create(nombre='Sede a depurar')
        self.otra_sede = Autoescuela.objects.create(nombre='Sede ajena')

    def registro(self, alumno, *, cerrada=False):
        return RegistroAlumno.objects.create(
            autoescuela=self.sede,
            alumno=alumno,
            permiso='B',
            fecha_fin=date(2026, 1, 1) if cerrada else None,
        )

    def test_deletes_closed_records_and_only_orphaned_students(self):
        solo_cerrado = Alumno.objects.create(autoescuela=self.sede, nombre='Solo cerrado')
        cerrado = self.registro(solo_cerrado, cerrada=True)
        evento = EventoExamen.objects.create(
            registro=cerrado, tipo='TEORICO', resultado='SUSPENDIDO', fecha=date(2025, 1, 1),
        )
        factura = Factura.objects.create(
            autoescuela=self.sede, alumno=solo_cerrado, numero_factura='2026/0001',
            fecha=date(2026, 1, 1), nombre_factura='Solo cerrado',
        )

        reinscrito = Alumno.objects.create(autoescuela=self.sede, nombre='Reinscrito')
        antigua = self.registro(reinscrito, cerrada=True)
        abierta = self.registro(reinscrito)

        ajeno = Alumno.objects.create(autoescuela=self.otra_sede, nombre='Ajeno')
        registro_ajeno = RegistroAlumno.objects.create(
            autoescuela=self.otra_sede, alumno=ajeno, permiso='B', fecha_fin=date(2026, 1, 1),
        )

        salida = StringIO()
        call_command('purgar_expedientes_cerrados', '--autoescuela-id', str(self.sede.pk), '--confirmar', stdout=salida)

        self.assertFalse(RegistroAlumno.objects.filter(pk=cerrado.pk).exists())
        self.assertFalse(EventoExamen.objects.filter(pk=evento.pk).exists())
        self.assertFalse(Alumno.objects.filter(pk=solo_cerrado.pk).exists())
        factura.refresh_from_db()
        self.assertIsNone(factura.alumno_id)
        self.assertFalse(RegistroAlumno.objects.filter(pk=antigua.pk).exists())
        self.assertTrue(Alumno.objects.filter(pk=reinscrito.pk).exists())
        self.assertTrue(RegistroAlumno.objects.filter(pk=abierta.pk).exists())
        self.assertTrue(RegistroAlumno.objects.filter(pk=registro_ajeno.pk).exists())
        self.assertIn('Expedientes borrados: 2', salida.getvalue())

    def test_requires_explicit_confirmation(self):
        alumno = Alumno.objects.create(autoescuela=self.sede, nombre='No borrar')
        registro = self.registro(alumno, cerrada=True)

        with self.assertRaisesMessage(CommandError, '--confirmar'):
            call_command('purgar_expedientes_cerrados', '--autoescuela-id', str(self.sede.pk))

        self.assertTrue(RegistroAlumno.objects.filter(pk=registro.pk).exists())
