from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from pypdf import PdfReader

from .models import (Alumno, Autoescuela, ConfiguracionTeorica, EventoExamen,
                     FichaFormacionTeorica, PerfilUsuario, ProfesorTeorica, RegistroAlumno)
from .utils.pdf_ficha_teorica import generate_theoretical_sheet_pdf


@override_settings(ALLOWED_HOSTS=['testserver'])
class FichaTeoricaTests(TestCase):
    def setUp(self):
        self.sede = Autoescuela.objects.get(nombre='Alfafar')
        self.ajena = Autoescuela.objects.get(nombre='Albal')
        self.user = User.objects.create_user(username='ficha-teorica')
        PerfilUsuario.objects.create(usuario=self.user).autoescuelas.add(self.sede)
        self.client.force_login(self.user)
        session = self.client.session
        session['autoescuela_id'] = self.sede.pk
        session.save()
        self.configuracion, _ = ConfiguracionTeorica.objects.get_or_create(
            autoescuela=self.sede,
            defaults={
                'numero': 'V1086-02', 'seccion': '2', 'digito_control': '9',
                'denominacion': 'DAKASA AUTOESCUELA S.L.', 'direccion': 'AV. ALBUFERA, 18 PBJ',
                'codigo_postal': '46910', 'poblacion': 'Alfafar',
            },
        )
        self.profesor, _ = ProfesorTeorica.objects.get_or_create(
            autoescuela=self.sede, dni='53880414Q',
            defaults={'nombre': 'AINOA ALAPONT CARRASCO'},
        )
        self.profesor_ajeno = ProfesorTeorica.objects.create(
            autoescuela=self.ajena, nombre='Profesor ajeno', dni='00000000T',
        )
        self.alumno = Alumno.objects.create(
            autoescuela=self.sede, nombre='GARCIA PEREZ ANA', nombre_pila='ANA', apellido1='GARCIA',
            apellido2='PEREZ', dni='12345678Z', direccion='Calle Mayor 1', codigo_postal='46910', municipio='Alfafar',
        )
        self.registro = RegistroAlumno.objects.create(
            autoescuela=self.sede, alumno=self.alumno, permiso='B', fecha_inicio=date(2026, 11, 5),
        )

    def test_ficha_limits_professors_to_active_school_and_exports_theoretical_exams(self):
        url = reverse('facturacion:ficha_teorica', args=[self.registro.pk])
        response = self.client.get(url)
        self.assertContains(response, self.profesor.nombre)
        self.assertNotContains(response, self.profesor_ajeno.nombre)

        response = self.client.post(url, {
            'profesor': self.profesor.pk,
            'fecha_inicio': '2026-11-05',
            'fecha_fin': '2026-12-01',
            'faltas_asistencia': 2,
            'observaciones': 'Observacion de prueba',
        })
        self.assertRedirects(response, url)
        ficha = FichaFormacionTeorica.objects.get(registro=self.registro)
        EventoExamen.objects.create(
            registro=self.registro, tipo='TEORICO', resultado='APROBADO', fecha=date(2026, 12, 2),
        )
        EventoExamen.objects.create(
            registro=self.registro, tipo='PRACTICO', resultado='PENDIENTE', fecha=date(2026, 12, 3),
        )

        pdf = PdfReader(generate_theoretical_sheet_pdf(self.registro, ficha))
        campos = pdf.get_fields()
        texto = pdf.pages[0].extract_text()
        self.assertEqual(campos['Número']['/V'], 'V1086-02')
        self.assertEqual(campos['DNINIE_2']['/V'], '12345678Z')
        self.assertEqual(campos['Fecha del examen ddmmaaaaRow1']['/V'], '02/12/2026')
        self.assertEqual(campos['ResultadoRow1']['/V'], 'Aprobado')
        self.assertIn('AINOA ALAPONT CARRASCO', texto)
        self.assertFalse(campos['Fecha del examen ddmmaaaaRow2'].get('/V'))
        self.assertNotIn('/Names', pdf.trailer['/Root'])

    def test_cannot_assign_professor_from_another_school(self):
        response = self.client.post(reverse('facturacion:ficha_teorica', args=[self.registro.pk]), {
            'profesor': self.profesor_ajeno.pk,
            'faltas_asistencia': 0,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(FichaFormacionTeorica.objects.filter(registro=self.registro).exists())
