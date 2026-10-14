from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import AlumnoForm, EventoExamenForm
from .models import Alumno, Autoescuela, EventoExamen, Factura, PerfilUsuario, RegistroAlumno
from .utils.alertas import calcular_alertas, estado_registro, sumar_meses


@override_settings(ALLOWED_HOSTS=['testserver'])
class SedeTestCase(TestCase):
    def setUp(self):
        self.sede = Autoescuela.objects.create(nombre='Sede activa')
        self.otra_sede = Autoescuela.objects.create(nombre='Sede ajena')
        self.user = User.objects.create_user(username='operador')
        PerfilUsuario.objects.create(usuario=self.user).autoescuelas.add(self.sede)
        self.client.force_login(self.user)
        session = self.client.session
        session['autoescuela_id'] = self.sede.pk
        session.save()
        self.alumno = Alumno.objects.create(
            autoescuela=self.sede, nombre='GAO ALFREDO', nombre_pila='ALFREDO', apellido1='GAO',
            direccion='Calle original', codigo_postal='46470', municipio='Albal', provincia='VALENCIA',
        )
        self.ajeno = Alumno.objects.create(autoescuela=self.otra_sede, nombre='ALFREDO GAO')

    def registro(self, alumno=None, **kwargs):
        alumno = alumno or self.alumno
        return RegistroAlumno.objects.create(alumno=alumno, autoescuela=alumno.autoescuela,
                                             **{'permiso': 'B', 'fecha_alta': date(2024, 1, 31), **kwargs})

    def evento(self, registro, tipo='TEORICO', resultado='SUSPENDIDO', fecha=date(2025, 1, 31)):
        return EventoExamen.objects.create(registro=registro, tipo=tipo, resultado=resultado, fecha=fecha)


class FacturaAlumnoTests(SedeTestCase):
    def setUp(self):
        super().setUp()
        self.data = {'curso': 'B', 'fecha': '2026-10-14', 'total_pagado': '100', 'renovaciones': '0',
                     'nombre_factura': 'Snapshot personalizado', 'dni_factura': '',
                     'direccion_factura': 'Direccion de facturacion'}
        self.url = reverse('facturacion:factura_create')

    def crear(self, **changes):
        response = self.client.post(self.url, {**self.data, **changes})
        self.assertEqual(response.status_code, 302)
        return Factura.objects.latest('pk')

    def test_prefill_by_id_without_dni_and_link_keeps_snapshots(self):
        response = self.client.get(self.url, {'alumno': self.alumno.pk})
        form = response.context['form']
        self.assertEqual(form['alumno_id'].value(), self.alumno.pk)
        for field, expected in [('nombre_factura', 'ALFREDO GAO'), ('dni_factura', ''),
                                ('direccion_factura', 'Calle original'), ('cp_factura', '46470'),
                                ('municipio_factura', 'Albal'), ('provincia_factura', 'VALENCIA')]:
            self.assertEqual(form[field].value(), expected)
        factura = self.crear(alumno_id=self.alumno.pk)
        self.assertEqual(factura.alumno_id, self.alumno.pk)
        self.assertEqual(factura.nombre_factura, self.data['nombre_factura'])
        self.alumno.refresh_from_db()
        self.assertEqual(self.alumno.direccion, 'Calle original')
        response = self.client.get(reverse('facturacion:alumno_detail', args=[self.alumno.pk]))
        self.assertContains(response, self.url + '?alumno=' + str(self.alumno.pk))

    def test_cross_school_prefill_and_invalid_id_rejected(self):
        for alumno_id in (self.ajeno.pk, 999999):
            self.assertEqual(self.client.get(self.url, {'alumno': alumno_id}).status_code, 404)
            response = self.client.post(self.url, {**self.data, 'alumno_id': alumno_id})
            self.assertEqual(response.status_code, 200)
            self.assertIn('alumno_id', response.context['form'].errors)
        self.assertFalse(Factura.objects.exists())
        self.assertEqual(self.client.get(self.url, {'alumno': 'invalido'}).status_code, 404)

    def test_update_rejects_cross_school_selected_id(self):
        factura = self.crear(alumno_id=self.alumno.pk)
        response = self.client.post(reverse('facturacion:factura_update', args=[factura.pk]),
                                    {**self.data, 'alumno_id': self.ajeno.pk})
        self.assertIn('alumno_id', response.context['form'].errors)
        factura.refresh_from_db()
        self.assertEqual(factura.alumno_id, self.alumno.pk)

    def test_normalized_dni_fallback_does_not_mutate_student(self):
        self.alumno.dni = '1234-5678 z'
        self.alumno.save()
        factura = self.crear(dni_factura='12345678Z')
        self.assertEqual(factura.alumno_id, self.alumno.pk)
        self.assertEqual(Alumno.objects.filter(autoescuela=self.sede).count(), 1)
        self.alumno.refresh_from_db()
        self.assertEqual(self.alumno.direccion, 'Calle original')

    def test_dni_fallback_never_links_student_from_another_school(self):
        self.ajeno.dni = '12345678Z'
        self.ajeno.save()
        factura = self.crear(dni_factura='12345678Z')
        self.assertNotEqual(factura.alumno_id, self.ajeno.pk)
        self.assertEqual(factura.alumno.autoescuela_id, self.sede.pk)

    def test_ambiguous_legacy_dni_errors_in_create_and_update(self):
        self.alumno.dni = '1234-5678z'
        self.alumno.save()
        duplicado = Alumno.objects.create(autoescuela=self.sede, nombre='Duplicado', dni='12345678Z')
        response = self.client.post(self.url, {**self.data, 'dni_factura': '12345678Z'})
        self.assertIn('dni_factura', response.context['form'].errors)
        self.assertFalse(Factura.objects.exists())
        factura = self.crear(dni_factura='12345678Z', alumno_id=duplicado.pk)
        response = self.client.post(reverse('facturacion:factura_update', args=[factura.pk]),
                                    {**self.data, 'dni_factura': '12345678Z'})
        self.assertIn('dni_factura', response.context['form'].errors)
        factura.refresh_from_db()
        self.assertEqual(factura.alumno_id, duplicado.pk)

    def test_legacy_new_dni_creates_student_but_blank_dni_does_not(self):
        factura = self.crear(dni_factura='99999999X')
        self.assertEqual(factura.alumno.dni, '99999999X')
        factura = self.crear()
        self.assertIsNone(factura.alumno_id)

    def test_invoice_edit_get_iso_and_post_retains_date(self):
        factura = self.crear(alumno_id=self.alumno.pk)
        url = reverse('facturacion:factura_update', args=[factura.pk])
        response = self.client.get(url)
        self.assertContains(response, 'value="2026-10-14"')
        self.assertEqual(response.context['form']['alumno_id'].value(), self.alumno.pk)
        self.assertEqual(self.client.post(url, {**self.data, 'alumno_id': self.alumno.pk}).status_code, 302)
        factura.refresh_from_db()
        self.assertEqual(factura.fecha, date(2026, 10, 14))

    def test_invoice_blank_date_rejected_and_invoice_not_deleted(self):
        factura = self.crear()
        response = self.client.post(reverse('facturacion:factura_update', args=[factura.pk]),
                                    {**self.data, 'fecha': ''})
        self.assertIn('fecha', response.context['form'].errors)
        factura.refresh_from_db()
        self.assertEqual(factura.fecha, date(2026, 10, 14))
        self.assertEqual(Factura.objects.count(), 1)

    def test_search_name_surname_tokens_legacy_and_dni_selectable_results(self):
        legacy = Alumno.objects.create(autoescuela=self.sede, nombre='GAO ALFREDO LEGACY', dni='XYZ123')
        Alumno.objects.create(autoescuela=self.sede, nombre='ALFREDO OTRO', nombre_pila='ALFREDO', apellido1='OTRO')
        url = reverse('facturacion:buscar_alumno')
        for term in ('ALFREDO GAO', 'GAO ALFREDO', 'GAO'):
            response = self.client.get(url, {'q': term})
            self.assertEqual({a['id'] for a in response.json()['results']}, {self.alumno.pk, legacy.pk})
        self.assertEqual(len(self.client.get(url, {'q': 'ALFREDO'}).json()['results']), 3)
        self.assertEqual(self.client.get(url, {'dni': 'XYZ'}).json()['results'][0]['id'], legacy.pk)
        self.assertEqual(self.client.get(url, {'q': ''}).json()['results'], [])
        self.assertEqual(self.client.get(url, {'q': 'ALFREDO IMPOSIBLE'}).json()['results'], [])

    def test_search_is_bounded_and_school_isolated(self):
        Alumno.objects.bulk_create([Alumno(autoescuela=self.sede, nombre='SEARCH') for _ in range(30)])
        results = self.client.get(reverse('facturacion:buscar_alumno'), {'q': 'SEARCH'}).json()['results']
        self.assertEqual(len(results), 20)
        self.assertTrue(all('id' in item for item in results))
        results = self.client.get(reverse('facturacion:buscar_alumno'), {'q': 'ALFREDO'}).json()['results']
        self.assertEqual([item['id'] for item in results], [self.alumno.pk])

    def test_javascript_cache_busting_and_search_markup(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'js/factura_form.js?v=20261014-alumnos-2')
        self.assertContains(response, 'id="alumno-results"')
        self.assertContains(response, 'name="alumno_id"')


class AlumnoListadoTests(SedeTestCase):
    def test_pagination_51_students_multirecords_no_duplicates_or_missing_last(self):
        Alumno.objects.bulk_create([Alumno(autoescuela=self.sede, nombre=f'Alumno {i}', nombre_pila=f'A{i:03}')
                                   for i in range(50)])
        self.registro(numero_registro=634, fecha_fin=date(2025, 1, 1))
        actual = self.registro(numero_registro=2, fecha_alta=date(2025, 1, 1))
        self.registro(numero_registro=3, fecha_alta=date(2024, 12, 1))
        url = reverse('facturacion:alumno_list')
        for orden in ('nombre', 'registro', 'alta'):
            with self.subTest(orden=orden):
                first = self.client.get(url, {'orden': orden})
                last = self.client.get(url, {'orden': orden, 'page': 2})
                self.assertEqual(first.context['paginator'].count, 51)
                self.assertEqual(len(first.context['object_list']), 50)
                self.assertEqual(len(last.context['object_list']), 1)
                rows = list(first.context['object_list']) + list(last.context['object_list'])
                self.assertEqual(len({a.pk for a in rows}), 51)
                alumno = next(a for a in rows if a.pk == self.alumno.pk)
                self.assertEqual(alumno.registro_principal.pk, actual.pk)
                self.assertEqual(alumno.principal_numero, 2)
        self.assertContains(first, 'pagina-directa')
        self.assertContains(first, 'page=2&amp;orden=alta')
        self.assertContains(last, 'Primera')
        detail = self.client.get(reverse('facturacion:alumno_detail', args=[self.alumno.pk]))
        self.assertContains(detail, '634')

    def test_filters_match_one_historical_record_not_separate_joins(self):
        self.registro(numero_registro=634, fecha_alta=date(2024, 1, 31), fecha_fin=date(2025, 1, 1))
        self.registro(permiso='A', fecha_alta=date(2026, 1, 1))
        url = reverse('facturacion:alumno_list')
        response = self.client.get(url, {'permiso': 'A', 'numero_registro': 634})
        self.assertEqual(response.context['paginator'].count, 0)
        response = self.client.get(url, {'permiso': 'B', 'numero_registro': 634, 'fecha_alta': '2024-01-31'})
        self.assertEqual(response.context['paginator'].count, 1)
        self.assertEqual(response.context['object_list'][0].registro_principal.permiso, 'A')
        self.assertEqual(self.client.get(url, {'numero_registro': 'oops'}).status_code, 200)
        self.assertEqual(self.client.get(url, {'fecha_alta': '2026-99-99'}).status_code, 200)

    def test_principal_closed_fallback_latest_date_and_pk_tie(self):
        self.registro(fecha_fin=date(2025, 1, 1), numero_registro=634)
        newest = self.registro(fecha_fin=date(2025, 1, 1), numero_registro=5)
        response = self.client.get(reverse('facturacion:alumno_list'))
        a = response.context['object_list'][0]
        self.assertEqual(a.principal_id, newest.pk)
        self.assertEqual(a.registro_principal.pk, newest.pk)

    def test_number_and_date_order_follow_displayed_principal(self):
        self.registro(numero_registro=634, fecha_alta=date(2026, 1, 1), fecha_fin=date(2026, 2, 1))
        self.registro(numero_registro=2, fecha_alta=date(2024, 1, 1))
        otro = Alumno.objects.create(autoescuela=self.sede, nombre='Otro')
        self.registro(alumno=otro, numero_registro=4, fecha_alta=date(2025, 1, 1))
        url = reverse('facturacion:alumno_list')
        self.assertEqual([a.pk for a in self.client.get(url, {'orden': 'registro'}).context['object_list']],
                         [self.alumno.pk, otro.pk])
        self.assertEqual([a.pk for a in self.client.get(url, {'orden': 'alta'}).context['object_list']],
                         [otro.pk, self.alumno.pk])

    def test_pagination_queries_encoded_and_direct_jump_preserves_filters(self):
        self.alumno.nombre = 'A&B / test'
        self.alumno.save()
        Alumno.objects.bulk_create([Alumno(autoescuela=self.sede, nombre='A&B / test') for _ in range(50)])
        response = self.client.get(reverse('facturacion:alumno_list'), {'q': 'A&B /', 'orden': 'registro'})
        self.assertEqual(response.context['pagination_query'], 'q=A%26B+%2F&orden=registro')
        self.assertEqual(dict(response.context['pagination_fields']), {'q': 'A&B /', 'orden': 'registro'})
        self.assertContains(response, '?page=2&amp;q=A%26B+%2F&amp;orden=registro')
        self.assertContains(response, 'name="q" value="A&amp;B /"')
        response = self.client.get(reverse('facturacion:alumno_list'), {'q': 'A&B /', 'orden': 'registro', 'page': 2})
        self.assertEqual(len(response.context['object_list']), 1)

    def test_list_principal_is_prefetched_and_names_in_display_order(self):
        self.registro()
        response = self.client.get(reverse('facturacion:alumno_list'))
        alumno = response.context['object_list'][0]
        with self.assertNumQueries(0):
            self.assertIsNotNone(alumno.registro_principal)
            self.assertIsNotNone(alumno.registro_principal)
        self.assertContains(response, 'ALFREDO GAO')

    def test_dni_expiry_optional_iso_form_and_detail(self):
        url = reverse('facturacion:alumno_update', args=[self.alumno.pk])
        response = self.client.post(url, {'nombre_pila': 'ALFREDO', 'apellido1': 'GAO', 'fecha_caducidad_dni': '2028-02-29'})
        self.assertEqual(response.status_code, 302)
        self.alumno.refresh_from_db()
        self.assertEqual(self.alumno.fecha_caducidad_dni, date(2028, 2, 29))
        self.assertContains(self.client.get(url), 'value="2028-02-29"')
        self.assertContains(self.client.get(reverse('facturacion:alumno_detail', args=[self.alumno.pk])), '29/02/2028')
        form = AlumnoForm({'nombre_pila': 'ALFREDO', 'fecha_caducidad_dni': ''}, instance=self.alumno)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertIsNone(self.alumno.fecha_caducidad_dni)


class EventoTests(SedeTestCase):
    def test_pending_exam_then_edit_result_type_and_date_keeps_registration(self):
        registro = self.registro()
        url = reverse('facturacion:evento_create', args=[registro.pk])
        response = self.client.get(url)
        self.assertEqual(response.context['form']['resultado'].value(), 'PENDIENTE')
        self.assertEqual(self.client.post(url, {'tipo': 'TEORICO', 'fecha': '2026-10-14', 'resultado': 'PENDIENTE'}).status_code, 302)
        evento = registro.eventos.get()
        url = reverse('facturacion:evento_update', args=[evento.pk])
        self.assertContains(self.client.get(url), 'value="2026-10-14"')
        self.assertEqual(self.client.post(url, {'tipo': 'PRACTICO', 'fecha': '2026-10-15', 'resultado': 'SUSPENDIDO',
                                               'registro': 99999}).status_code, 302)
        evento.refresh_from_db()
        self.assertEqual((evento.tipo, evento.resultado, evento.fecha, evento.registro_id),
                         ('PRACTICO', 'SUSPENDIDO', date(2026, 10, 15), registro.pk))
        self.assertContains(self.client.get(reverse('facturacion:alumno_detail', args=[self.alumno.pk])),
                            reverse('facturacion:evento_update', args=[evento.pk]))

    def test_renewal_event_dated_and_no_result(self):
        registro = self.registro()
        url = reverse('facturacion:evento_create', args=[registro.pk])
        response = self.client.get(url, {'tipo': 'RENOVACION'})
        self.assertEqual(response.context['form']['resultado'].value(), '')
        self.assertEqual(self.client.post(url, {'tipo': 'RENOVACION', 'fecha': '2026-10-14', 'resultado': ''}).status_code, 302)
        self.assertEqual(registro.eventos.get().resultado, '')

    def test_invalid_event_date_type_result_rejected(self):
        for changes in ({'fecha': ''}, {'fecha': '2026-02-30'}, {'tipo': 'INVALID'},
                        {'resultado': 'INVALID'}, {'resultado': ''}, {'tipo': 'RENOVACION', 'resultado': 'APROBADO'}):
            form = EventoExamenForm({'tipo': 'TEORICO', 'fecha': '2026-10-14', 'resultado': 'PENDIENTE', **changes})
            self.assertFalse(form.is_valid(), (changes, form.errors))

    def test_event_cross_school_and_mismatched_registration_scoped_both_ways(self):
        registro = self.registro(alumno=self.ajeno)
        evento = self.evento(registro)
        for url in (reverse('facturacion:evento_create', args=[registro.pk]),
                    reverse('facturacion:evento_update', args=[evento.pk])):
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.post(url, {'tipo': 'TEORICO', 'fecha': '2026-10-14', 'resultado': 'APROBADO'}).status_code, 404)
        registro.autoescuela = self.sede
        registro.save()
        self.assertEqual(self.client.get(reverse('facturacion:evento_create', args=[registro.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('facturacion:evento_update', args=[evento.pk])).status_code, 404)
        with self.assertRaises(ValidationError):
            evento.full_clean()

    def test_history_is_separate_per_registration_and_cascades(self):
        r1, r2 = self.registro(), self.registro()
        self.evento(r1)
        self.evento(r2, tipo='PRACTICO')
        self.assertEqual(r1.eventos.count(), 1)
        self.assertEqual(r2.eventos.count(), 1)
        r1.delete()
        self.assertEqual(EventoExamen.objects.count(), 1)


class AlertasTests(SedeTestCase):
    def tipos(self, registro, hoy):
        return {a['tipo']: a for a in estado_registro(registro, hoy)[0]}

    def test_calendar_months_end_of_month_and_leap_year(self):
        for inicio, meses, esperado in [(date(2024, 1, 31), 1, date(2024, 2, 29)),
                                        (date(2023, 1, 31), 1, date(2023, 2, 28)),
                                        (date(2024, 2, 29), 12, date(2025, 2, 28)),
                                        (date(2024, 2, 29), 24, date(2026, 2, 28)),
                                        (date(2024, 8, 31), 6, date(2025, 2, 28))]:
            self.assertEqual(sumar_meses(inicio, meses), esperado)

    def test_contract_11_23_month_edges_and_expired_not_dropped(self):
        registro = self.registro()
        self.assertNotIn('contrato', self.tipos(registro, date(2024, 12, 30)))
        alerta = self.tipos(registro, date(2024, 12, 31))['contrato']
        self.assertEqual((alerta['color'], alerta['limite']), ('yellow', date(2025, 1, 31)))
        self.assertEqual(self.tipos(registro, date(2025, 12, 30))['contrato']['color'], 'yellow')
        alerta = self.tipos(registro, date(2025, 12, 31))['contrato']
        self.assertEqual((alerta['color'], alerta['limite']), ('red', date(2026, 1, 31)))
        self.assertTrue(self.tipos(registro, date(2027, 1, 1))['contrato']['vencido'])

    def test_contract_leap_anniversary(self):
        registro = self.registro(fecha_alta=date(2024, 2, 29))
        self.assertEqual(self.tipos(registro, date(2026, 1, 29))['contrato']['limite'], date(2026, 2, 28))
        self.assertTrue(self.tipos(registro, date(2026, 2, 28))['contrato']['vencido'])

    def test_two_failures_all_combinations_and_renewal_resets_only_counter(self):
        for tipos in [('TEORICO', 'PRACTICO'), ('TEORICO', 'TEORICO'), ('PRACTICO', 'PRACTICO')]:
            with self.subTest(tipos=tipos):
                registro = self.registro()
                self.evento(registro, tipo=tipos[0])
                self.evento(registro, tipo=tipos[1], fecha=date(2025, 2, 1))
                antes = self.tipos(registro, date(2025, 7, 31))
                self.assertEqual(antes['renovacion']['suspensos'], 2)
                self.evento(registro, tipo='RENOVACION', resultado='', fecha=date(2025, 3, 1))
                despues = self.tipos(registro, date(2025, 7, 31))
                self.assertNotIn('renovacion', despues)
                self.assertEqual(antes['contrato'], despues['contrato'])
                if 'teoria_pendiente' in antes:
                    self.assertEqual(antes['teoria_pendiente'], despues['teoria_pendiente'])
                self.assertEqual(registro.eventos.count(), 3)
                self.evento(registro, fecha=date(2025, 4, 1))
                self.assertNotIn('renovacion', self.tipos(registro, date(2025, 7, 31)))
                self.evento(registro, tipo='PRACTICO', fecha=date(2025, 4, 2))
                self.assertEqual(self.tipos(registro, date(2025, 7, 31))['renovacion']['suspensos'], 2)

    def test_theory_pass_does_not_reset_mixed_failure_counter(self):
        registro = self.registro()
        self.evento(registro)
        self.evento(registro, resultado='APROBADO', fecha=date(2025, 2, 1))
        self.evento(registro, tipo='PRACTICO', fecha=date(2025, 3, 1))
        self.assertIn('renovacion', self.tipos(registro, date(2025, 3, 1)))

    def test_renewal_preserves_approved_theory_deadline_and_other_registration(self):
        registro = self.registro(fecha_apto_teorico=date(2024, 1, 31))
        otro = self.registro()
        for r in (registro, otro):
            self.evento(r, tipo='PRACTICO', fecha=date(2025, 1, 1))
            self.evento(r, tipo='PRACTICO', fecha=date(2025, 1, 2))
        antes = self.tipos(registro, date(2026, 1, 1))['teoria_aprobada']
        self.evento(registro, tipo='RENOVACION', resultado='', fecha=date(2025, 2, 1))
        self.assertEqual(self.tipos(registro, date(2026, 1, 1))['teoria_aprobada'], antes)
        self.assertNotIn('renovacion', self.tipos(registro, date(2026, 1, 1)))
        self.assertIn('renovacion', self.tipos(otro, date(2026, 1, 1)))

    def test_pending_future_exams_and_future_renewal_do_not_change_state(self):
        registro = self.registro()
        self.evento(registro, resultado='PENDIENTE')
        self.evento(registro, fecha=date(2027, 1, 1))
        self.evento(registro, tipo='PRACTICO', resultado='APROBADO', fecha=date(2027, 1, 1))
        self.assertNotIn('renovacion', self.tipos(registro, date(2026, 1, 1)))
        self.assertIn('contrato', self.tipos(registro, date(2026, 1, 1)))
        self.evento(registro)
        self.evento(registro, tipo='PRACTICO')
        self.evento(registro, tipo='RENOVACION', resultado='', fecha=date(2027, 2, 1))
        self.assertIn('renovacion', self.tipos(registro, date(2026, 1, 1)))

    def test_first_failed_theory_5_6_month_edges_and_overdue(self):
        registro = self.registro()
        self.evento(registro)
        self.evento(registro, fecha=date(2025, 2, 10))
        self.assertNotIn('teoria_pendiente', self.tipos(registro, date(2025, 6, 29)))
        alerta = self.tipos(registro, date(2025, 6, 30))['teoria_pendiente']
        self.assertEqual((alerta['inicio'], alerta['limite']), (date(2025, 1, 31), date(2025, 7, 31)))
        self.assertTrue(self.tipos(registro, date(2025, 7, 31))['teoria_pendiente']['vencido'])
        self.assertLess(self.tipos(registro, date(2026, 1, 1))['teoria_pendiente']['dias'], 0)

    def test_latest_theory_pass_clears_prior_first_fail_with_stable_same_day_pk(self):
        registro = self.registro()
        self.evento(registro)
        self.evento(registro, resultado='APROBADO')
        self.assertNotIn('teoria_pendiente', self.tipos(registro, date(2025, 8, 1)))
        self.evento(registro, fecha=date(2025, 1, 31))
        self.assertEqual(self.tipos(registro, date(2025, 8, 1))['teoria_pendiente']['inicio'], date(2025, 1, 31))
        self.evento(registro, resultado='APROBADO', fecha=date(2025, 2, 1))
        self.assertNotIn('teoria_pendiente', self.tipos(registro, date(2025, 8, 1)))

    def test_theory_approved_20_24_month_edges_latest_pass_and_fallback(self):
        registro = self.registro(fecha_apto_teorico=date(2023, 1, 1))
        self.evento(registro, resultado='APROBADO', fecha=date(2024, 2, 29))
        self.assertNotIn('teoria_aprobada', self.tipos(registro, date(2025, 10, 28)))
        alerta = self.tipos(registro, date(2025, 10, 29))['teoria_aprobada']
        self.assertEqual((alerta['color'], alerta['limite']), ('pink', date(2026, 2, 28)))
        self.assertTrue(self.tipos(registro, date(2026, 2, 28))['teoria_aprobada']['vencido'])
        registro.eventos.all().delete()
        self.assertEqual(self.tipos(registro, date(2025, 1, 1))['teoria_aprobada']['inicio'], date(2023, 1, 1))

    def test_exento_no_inferred_date_and_future_historical_pass_ignored(self):
        registro = self.registro(estado_apto_teorico='EXENTO')
        self.assertEqual(estado_registro(registro, date(2026, 1, 1))[1], [])
        registro.fecha_apto_teorico = date(2027, 1, 1)
        self.assertEqual(estado_registro(registro, date(2026, 1, 1))[1], [])

    def test_recorded_pass_overrides_legacy_pass_even_if_legacy_is_later(self):
        registro = self.registro(fecha_apto_teorico=date(2025, 1, 1))
        self.evento(registro, resultado='APROBADO', fecha=date(2024, 1, 1))
        self.assertEqual(self.tipos(registro, date(2026, 1, 1))['teoria_aprobada']['inicio'], date(2024, 1, 1))

    def test_closed_or_practical_passed_stop_all_registration_alerts_and_ranking(self):
        registro = self.registro(fecha_apto_teorico=date(2024, 1, 1))
        self.evento(registro)
        self.evento(registro, tipo='PRACTICO')
        registro.fecha_fin = date(2025, 2, 1)
        self.assertEqual(estado_registro(registro, date(2026, 1, 1)), ([], []))
        registro.fecha_fin = None
        self.evento(registro, tipo='PRACTICO', resultado='APROBADO', fecha=date(2025, 3, 1))
        self.assertEqual(estado_registro(registro, date(2026, 1, 1)), ([], []))

    def test_dni_one_per_student_includes_closed_and_no_registration(self):
        self.alumno.fecha_caducidad_dni = date(2026, 1, 1)
        self.alumno.save()
        self.registro(fecha_fin=date(2025, 1, 1))
        self.registro(fecha_fin=date(2025, 1, 1))
        sin_registro = Alumno.objects.create(autoescuela=self.sede, nombre='Sin registro', fecha_caducidad_dni=date(2025, 1, 1))
        Alumno.objects.create(autoescuela=self.sede, nombre='No caducado', fecha_caducidad_dni=date(2026, 1, 2))
        self.ajeno.fecha_caducidad_dni = date(2020, 1, 1)
        self.ajeno.save()
        alertas, _ = calcular_alertas(self.sede, date(2026, 1, 1))
        self.assertEqual({a['alumno'].pk for a in alertas}, {self.alumno.pk, sin_registro.pk})
        self.assertEqual(len(alertas), 2)
        self.assertTrue(all(a['color'] == 'purple' for a in alertas))

    def test_ranking_both_stages_deadline_ascending_overdue_first(self):
        r1 = self.registro(fecha_apto_teorico=date(2024, 1, 31))
        r2 = self.registro()
        r3 = self.registro(fecha_apto_teorico=date(2025, 1, 31))
        self.evento(r2, fecha=date(2025, 1, 31))
        self.evento(self.registro(alumno=self.ajeno))
        _, ranking = calcular_alertas(self.sede, date(2026, 1, 1))
        self.assertEqual([p['registro'].pk for p in ranking], [r2.pk, r1.pk, r3.pk])
        self.assertEqual([p['tipo'] for p in ranking], ['teoria_pendiente', 'teoria_aprobada', 'teoria_aprobada'])
        self.assertTrue(ranking[0]['vencido'])
        self.assertGreater(ranking[-1]['dias'], 0)

    def test_concurrent_alerts_and_views_render_labels_dates_and_links(self):
        registro = self.registro(fecha_apto_teorico=date(2024, 1, 1))
        self.evento(registro, fecha=date(2025, 1, 1))
        self.evento(registro, tipo='PRACTICO', fecha=date(2025, 1, 2))
        self.alumno.fecha_caducidad_dni = date(2025, 1, 1)
        self.alumno.save()
        with patch('facturacion.views.timezone.localdate', return_value=date(2026, 1, 1)):
            response = self.client.get(reverse('facturacion:alertas'))
            self.assertEqual(len(response.context['filas']), 5)
            for label in ('aviso-red', 'aviso-purple', 'aviso-orange', 'aviso-pink', 'Vencido', 'Renovacion academica'):
                self.assertContains(response, label)
            response = self.client.get(reverse('facturacion:caducidad_teorico'))
            self.assertEqual(len(response.context['filas']), 2)
            self.assertContains(response, reverse('facturacion:registro_update', args=[registro.pk]))
            self.assertContains(response, '31/01/2024')

    def test_alert_views_require_authenticated_active_authorized_school(self):
        for name in ('alertas', 'caducidad_teorico'):
            url = reverse('facturacion:' + name)
            session = self.client.session
            session['autoescuela_id'] = self.otra_sede.pk
            session.save()
            self.assertRedirects(self.client.get(url), reverse('seleccionar_sede'), fetch_redirect_response=False)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('facturacion:alertas')).status_code, 302)
