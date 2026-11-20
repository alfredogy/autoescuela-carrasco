from datetime import date
from io import BytesIO
from zipfile import ZipFile

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from pypdf import PdfReader

from .models import Alumno, Autoescuela, PerfilUsuario, RegistroAlumno
from .utils.pdf_contrato_permiso_b import generate_permit_b_contract_pdf


@override_settings(ALLOWED_HOSTS=['testserver'])
class ContratoPermisoBTests(TestCase):
    def setUp(self):
        self.sede = Autoescuela.objects.get(nombre='Alfafar')
        self.user = User.objects.create_user(username='contrato-b')
        PerfilUsuario.objects.create(usuario=self.user).autoescuelas.add(self.sede)
        self.client.force_login(self.user)
        session = self.client.session
        session['autoescuela_id'] = self.sede.pk
        session.save()
        self.alumno = Alumno.objects.create(
            autoescuela=self.sede, nombre='MUÑOZ GARCÍA ANA', nombre_pila='ANA', apellido1='MUÑOZ', apellido2='GARCÍA',
            dni='12345678Z', telefono='600123456', correo_electronico='ana@example.test', direccion='Calle Mayor 1',
            codigo_postal='46910', fecha_nacimiento=date(2000, 1, 2),
        )
        self.registro = RegistroAlumno.objects.create(
            autoescuela=self.sede, alumno=self.alumno, permiso='B', numero_registro=12,
        )

    def test_contract_contains_registration_number_and_available_student_data(self):
        pdf = PdfReader(generate_permit_b_contract_pdf(self.registro))
        texto = pdf.pages[0].extract_text()
        for value in ('12', 'ANA MUÑOZ GARCÍA', '12345678Z', '600123456', 'ana@example.test', '02/01/2000'):
            self.assertIn(value, texto)

    def test_individual_and_bulk_contract_downloads(self):
        individual = self.client.get(reverse('facturacion:contrato_permiso_b_pdf', args=[self.registro.pk]))
        self.assertEqual(individual.status_code, 200)
        self.assertTrue(individual['Content-Disposition'].startswith('inline'))

        lote = self.client.get(reverse('facturacion:contrato_permiso_b_lote'))
        self.assertEqual(lote.status_code, 200)
        with ZipFile(BytesIO(b''.join(lote.streaming_content) if hasattr(lote, 'streaming_content') else lote.content)) as archivo:
            self.assertEqual(archivo.namelist(), ['contrato-B-0012-ANA_MU_OZ_GARC_A.pdf'])
