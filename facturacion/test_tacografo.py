from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Table
from reportlab.pdfgen.canvas import Canvas

from .forms import FacturaForm
from .models import Autoescuela, Configuracion, Factura, PerfilUsuario
from .utils.calculos import compute_components
from .utils.pdf_generator import generate_invoice_pdf


@override_settings(ALLOWED_HOSTS=['testserver'])
class TacografoTests(TestCase):
    def setUp(self):
        self.sede = Autoescuela.objects.create(nombre='Sede tacografo')
        self.config = Configuracion.get_instance(self.sede)
        user = User.objects.create_user(username='tacografo-test')
        PerfilUsuario.objects.create(usuario=user).autoescuelas.add(self.sede)
        self.client.force_login(user)
        session = self.client.session
        session['autoescuela_id'] = self.sede.pk
        session.save()
        self.data = {
            'curso': 'TACOGRAFO', 'fecha': '2026-10-07', 'total_pagado': '80.00',
            'nombre_factura': 'Nombre correcto en factura', 'dni_factura': '12345678Z',
            'direccion_factura': 'Calle de prueba 12', 'cp_factura': '46470',
            'municipio_factura': 'Albal', 'provincia_factura': 'VALENCIA',
            'tasa_tacografo': '32.47', 'renovaciones': '2',
            'tasa_basica': 'on', 'tasa_a': 'on', 'traslado': 'on',
        }

    def create_invoice(self, **changes):
        response = self.client.post(reverse('facturacion:factura_create'), {**self.data, **changes})
        self.assertEqual(response.status_code, 302)
        return Factura.objects.latest('pk')

    def test_creation_persists_components_and_ignores_driving_fees(self):
        factura = self.create_invoice()
        self.assertEqual(factura.curso, 'TACOGRAFO')
        self.assertEqual((factura.base_imponible, factura.iva, factura.tasas, factura.total),
                         tuple(map(Decimal, ('39.28', '8.25', '32.47', '80.00'))))
        self.assertEqual(factura.tasa_tacografo, Decimal('32.47'))
        self.assertEqual((factura.tasa_basica_qty, factura.tasa_a_qty,
                          factura.traslado_qty, factura.renovaciones_qty), (0, 0, 0, 0))
        for field in ('nombre_factura', 'dni_factura', 'direccion_factura', 'cp_factura',
                      'municipio_factura', 'provincia_factura'):
            self.assertEqual(getattr(factura, field), self.data[field])

    def test_new_form_default_and_edit_retains_stored_fee(self):
        response = self.client.get(reverse('facturacion:factura_create'))
        self.assertEqual(response.context['form']['tasa_tacografo'].value(), Decimal('32.47'))
        self.assertContains(response, 'TACÓGRAFO')
        factura = self.create_invoice(tasa_tacografo='30.00')
        self.config.tasa_basica = Decimal('500')
        self.config.save()
        url = reverse('facturacion:factura_update', args=[factura.pk])
        form = self.client.get(url).context['form']
        self.assertEqual(form['tasa_tacografo'].value(), Decimal('30.00'))
        response = self.client.post(url, {**self.data, 'tasa_tacografo': str(form['tasa_tacografo'].value())})
        self.assertEqual(response.status_code, 302)
        factura.refresh_from_db()
        self.assertEqual(factura.tasa_tacografo, Decimal('30.00'))
        self.assertEqual(factura.tasas, Decimal('30.00'))
        self.client.post(url, {**self.data, 'tasa_tacografo': '34.00'})
        factura.refresh_from_db()
        self.assertEqual(factura.tasas, Decimal('34.00'))

    def test_ajax_preview_matches_saved_invoice(self):
        response = self.client.get(reverse('facturacion:calcular_ajax'), {
            'total_pagado': '80.00', 'curso': 'TACOGRAFO', 'tasa_tacografo': '32.47',
            'tasa_basica': '1', 'tasa_a': '1', 'traslado': '1', 'renovaciones': '2',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'base': '39.28', 'iva': '8.25', 'tasas': '32.47', 'total': '80.00'})

    def test_invalid_fee_rejected_by_form_and_preview(self):
        for fee in ('-1', '80.01', 'invalid', 'NaN', 'Infinity', '32.471', ''):
            with self.subTest(fee=fee):
                form = FacturaForm(data={**self.data, 'tasa_tacografo': fee})
                self.assertFalse(form.is_valid())
                self.assertIn('tasa_tacografo', form.errors)
                response = self.client.get(reverse('facturacion:calcular_ajax'), {
                    'total_pagado': '80.00', 'curso': 'TACOGRAFO', 'tasa_tacografo': fee,
                })
                self.assertEqual(response.status_code, 400)
                self.assertIn('error', response.json())
        response = self.client.post(reverse('facturacion:factura_create'), {**self.data, 'total_pagado': '20'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Factura.objects.exists())
        for total in ('NaN', 'Infinity', 'invalid', '80.001'):
            response = self.client.get(reverse('facturacion:calcular_ajax'), {
                'total_pagado': total, 'curso': 'TACOGRAFO', 'tasa_tacografo': '32.47',
            })
            self.assertEqual(response.status_code, 400)

    def test_other_courses_unchanged_and_switch_clears_fee(self):
        for curso, expected in [('B', ('100.00', '21.00', '94.05', '215.05')),
                                ('C', ('121.00', '0.00', '94.05', '215.05'))]:
            with self.subTest(curso=curso):
                result = compute_components('215.05', 1, 0, 0, 0, curso,
                                            config=self.config, tasa_tacografo='32.47')
                self.assertEqual(result, tuple(map(Decimal, expected)))
                response = self.client.get(reverse('facturacion:calcular_ajax'), {
                    'total_pagado': '215.05', 'curso': curso, 'tasa_basica': '1',
                    'tasa_tacografo': 'invalid',
                })
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['tasas'], '94.05')
        factura = self.create_invoice()
        self.client.post(reverse('facturacion:factura_update', args=[factura.pk]), {
            **self.data, 'curso': 'B', 'total_pagado': '215.05',
            'tasa_a': '', 'traslado': '', 'renovaciones': '0',
        })
        factura.refresh_from_db()
        self.assertEqual(factura.tasa_tacografo, Decimal('0'))
        self.assertEqual(factura.tasa_basica_qty, 1)
        self.assertEqual(factura.tasas, Decimal('94.05'))

    def test_pdf_has_exactly_two_wrapped_concepts_using_stored_amounts(self):
        name = ('Nombre <correcto> & Apellidos ' * 7)[:200].strip()
        factura = self.create_invoice(nombre_factura=name)
        factura.alumno.nombre = 'Nombre incorrecto del alumno'
        factura.alumno.save()
        self.config.tasa_basica = Decimal('1')
        self.config.tasa_a = Decimal('1')
        self.config.traslado = Decimal('1')
        self.config.save()
        table_data = []
        drawn_text = []
        draw_string = Canvas.drawString

        def capture_table(*args, **kwargs):
            table_data.append([row[:] for row in args[0]])
            return Table(*args, **kwargs)

        def capture_text(canvas, x, y, text, *args, **kwargs):
            drawn_text.append(text)
            return draw_string(canvas, x, y, text, *args, **kwargs)

        with patch('facturacion.utils.pdf_generator.Table', side_effect=capture_table), \
                patch.object(Canvas, 'drawString', autospec=True, side_effect=capture_text):
            buffer = generate_invoice_pdf(factura)
        self.assertTrue(buffer.getvalue().startswith(b'%PDF'))
        self.assertIn(f'Cliente: {name}', drawn_text)
        self.assertIn(f'Nombre: {self.config.emisor_nombre}', drawn_text)
        self.assertIn(f'CIF: {self.config.emisor_dni}', drawn_text)
        self.assertIn(f'Dni: {factura.dni_factura}', drawn_text)
        self.assertIn(f'Domicilio: {factura.direccion_factura}', drawn_text)
        rows = [row for row in table_data[0][1:] if row[0]]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(isinstance(row[1], Paragraph) for row in rows))
        self.assertEqual(rows[0][1].getPlainText(), f'TRAMITACION TARJETA TACOGRAFO {name}')
        self.assertEqual(rows[1][1].getPlainText(), 'TASA EXPEDICION TARJETA TACOGRAFO DIGITAL (EXENTA DE IVA)')
        self.assertEqual([row[2] for row in rows], ['39.28', '32.47'])
        for row in rows:
            paragraph = row[1]
            _, height = paragraph.wrap(95 * mm - 12, 1000)
            self.assertGreater(height, paragraph.style.leading)
            unused_widths = [line[0] if paragraph.blPara.kind == 0 else line.extraSpace
                             for line in paragraph.blPara.lines]
            self.assertTrue(all(width >= -0.01 for width in unused_widths))
        self.assertEqual(table_data[1][:3], [
            ['BASE IMPONIBLE', '39.28'], ['IVA 21 %', '8.25'], ['EXENTO', '32.47'],
        ])
        self.assertEqual(self.client.get(reverse('facturacion:factura_pdf', args=[factura.pk])).status_code, 200)

    def test_zero_fee_or_zero_taxable_remainder_still_has_two_concepts(self):
        for fee in ('0.00', '80.00'):
            with self.subTest(fee=fee):
                factura = self.create_invoice(tasa_tacografo=fee)
                with patch('facturacion.utils.pdf_generator.Table', wraps=Table) as table:
                    generate_invoice_pdf(factura)
                rows = [row for row in table.call_args_list[0].args[0][1:] if row[0]]
                self.assertEqual(len(rows), 2)
                self.assertEqual(rows[1][2], fee)
