from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Alumno, Autoescuela, Factura, PerfilUsuario, RegistroAlumno


@override_settings(ALLOWED_HOSTS=['testserver'])
class RegistroDeleteTests(TestCase):
    def setUp(self):
        self.sede = Autoescuela.objects.create(nombre='Sede de prueba')
        self.user = User.objects.create_user(username='registro-test')
        PerfilUsuario.objects.create(usuario=self.user).autoescuelas.add(self.sede)
        self.client.force_login(self.user)
        session = self.client.session
        session['autoescuela_id'] = self.sede.pk
        session.save()
        self.alumno = Alumno.objects.create(autoescuela=self.sede, nombre='Alumno de prueba')
        self.registro = RegistroAlumno.objects.create(
            autoescuela=self.sede, alumno=self.alumno, permiso='B', numero_registro=10,
        )
        self.otro = RegistroAlumno.objects.create(
            autoescuela=self.sede, alumno=self.alumno, permiso='B', numero_registro=11,
        )
        self.factura = Factura.objects.create(
            autoescuela=self.sede, alumno=self.alumno, numero_factura='2026/0001',
            fecha=date(2026, 1, 1), nombre_factura=self.alumno.nombre,
        )
        self.url = reverse('facturacion:registro_delete', args=[self.registro.pk])

    def test_confirmation_does_not_delete(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirmar eliminacion')
        self.assertTrue(RegistroAlumno.objects.filter(pk=self.registro.pk).exists())

    def test_post_deletes_only_selected_registration(self):
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('facturacion:alumno_detail', args=[self.alumno.pk]))
        self.assertFalse(RegistroAlumno.objects.filter(pk=self.registro.pk).exists())
        self.factura.refresh_from_db()
        self.otro.refresh_from_db()
        self.assertEqual(self.factura.alumno_id, self.alumno.pk)
        self.assertEqual(self.otro.numero_registro, 11)
        self.assertEqual(self.alumno.registro_principal.pk, self.otro.pk)

    def test_other_school_is_inaccessible(self):
        sede = Autoescuela.objects.create(nombre='Otra sede de prueba')
        alumno = Alumno.objects.create(autoescuela=sede, nombre='Otro alumno')
        registro = RegistroAlumno.objects.create(autoescuela=sede, alumno=alumno, permiso='A')
        url = reverse('facturacion:registro_delete', args=[registro.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertTrue(RegistroAlumno.objects.filter(pk=registro.pk).exists())

    def test_last_registration_can_be_deleted(self):
        self.otro.delete()
        self.client.post(self.url)
        self.assertTrue(Alumno.objects.filter(pk=self.alumno.pk).exists())
        self.assertIsNone(self.alumno.registro_principal)

    def test_anonymous_user_cannot_delete(self):
        self.client.logout()
        self.assertEqual(self.client.post(self.url).status_code, 302)
        self.assertTrue(RegistroAlumno.objects.filter(pk=self.registro.pk).exists())
