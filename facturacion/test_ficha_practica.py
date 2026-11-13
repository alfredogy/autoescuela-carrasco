from datetime import date, time
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from pypdf import PdfReader

from .models import (Alumno, Autoescuela, ConfiguracionTeorica, ClasePractica,
                     FichaFormacionPractica, PerfilUsuario, ProfesorTeorica, RegistroAlumno)
from .utils.pdf_ficha_practica import generate_practical_sheet_pdf


@override_settings(ALLOWED_HOSTS=['testserver'])
class FichaPracticaTests(TestCase):
    def setUp(self):
        self.sede = Autoescuela.objects.get(nombre='Alfafar')
        self.user = User.objects.create_user(username='ficha-practica')
        PerfilUsuario.objects.create(usuario=self.user).autoescuelas.add(self.sede)
        self.client.force_login(self.user)
        session = self.client.session
        session['autoescuela_id'] = self.sede.pk
        session.save()
        ConfiguracionTeorica.objects.get_or_create(autoescuela=self.sede)
        self.profesor, _ = ProfesorTeorica.objects.get_or_create(
            autoescuela=self.sede, dni='22574957C', defaults={'nombre': 'ANTONIO GARCIA MUÑOZ'},
        )
        self.alumno = Alumno.objects.create(
            autoescuela=self.sede, nombre='LOPEZ DIAZ ANA', nombre_pila='ANA', apellido1='LOPEZ', apellido2='DIAZ',
            dni='12345678Z', direccion='Calle Mayor 1', codigo_postal='46910', municipio='Alfafar',
        )
        self.registro = RegistroAlumno.objects.create(autoescuela=self.sede, alumno=self.alumno, permiso='B')

    def test_practical_sheet_and_classes_export_to_pdf(self):
        url = reverse('facturacion:ficha_practica', args=[self.registro.pk])
        response = self.client.post(url, {
            'profesor': self.profesor.pk,
            'tipo': 'DESTREZA',
            'observaciones': 'Observacion de prueba',
        })
        self.assertRedirects(response, url)
        ficha = FichaFormacionPractica.objects.get(registro=self.registro)
        clase = ClasePractica.objects.create(
            ficha=ficha, fecha=date(2026, 11, 10), hora=time(10, 30), ejercicio='Estacionamiento',
            km_inicial=Decimal('123.40'), km_final=Decimal('130.20'), observaciones='Sin incidencias',
        )

        pdf = PdfReader(generate_practical_sheet_pdf(self.registro, ficha))
        campos = pdf.get_fields()
        texto = pdf.pages[0].extract_text()
        self.assertIn('ANTONIO GARCIA MUÑOZ', texto)
        self.assertEqual(campos['FechaRow1']['/V'], '10/11/2026')
        self.assertEqual(campos['EjercicioRow1']['/V'], 'Estacionamiento')
        self.assertEqual(campos['Km inicioRow1']['/V'], '123.40')
        self.assertNotIn('/Names', pdf.trailer['/Root'])
        self.assertEqual(clase.ficha_id, ficha.pk)

    def test_practical_pdf_can_be_opened_or_downloaded(self):
        ficha = FichaFormacionPractica.objects.create(registro=self.registro, profesor=self.profesor)
        url = reverse('facturacion:ficha_practica_pdf', args=[self.registro.pk])
        self.assertTrue(self.client.get(url)['Content-Disposition'].startswith('inline'))
        self.assertTrue(self.client.get(f'{url}?descargar=1')['Content-Disposition'].startswith('attachment'))

    def test_practical_sheet_can_be_saved_without_professor(self):
        url = reverse('facturacion:ficha_practica', args=[self.registro.pk])
        response = self.client.post(url, {'profesor': '', 'tipo': 'CIRCULACION'})
        self.assertRedirects(response, url)
        ficha = FichaFormacionPractica.objects.get(registro=self.registro)
        self.assertIsNone(ficha.profesor_id)
