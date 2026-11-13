from django.urls import path
from . import views

app_name = 'facturacion'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Facturas CRUD
    path('facturas/', views.FacturaListView.as_view(), name='factura_list'),
    path('facturas/nueva/', views.FacturaCreateView.as_view(), name='factura_create'),
    path('facturas/<int:pk>/', views.FacturaDetailView.as_view(), name='factura_detail'),
    path('facturas/<int:pk>/editar/', views.FacturaUpdateView.as_view(), name='factura_update'),
    path('facturas/<int:pk>/eliminar/', views.FacturaDeleteView.as_view(), name='factura_delete'),

    # API AJAX
    path('api/calcular/', views.calcular_factura_ajax, name='calcular_ajax'),
    path('api/buscar-alumno/', views.buscar_alumno_ajax, name='buscar_alumno'),

    # PDF
    path('facturas/<int:pk>/pdf/', views.generar_pdf_factura, name='factura_pdf'),
    path('facturas/pdf-lote/', views.generar_pdf_lote, name='factura_pdf_lote'),

    # Alumnos
    path('alumnos/', views.AlumnoListView.as_view(), name='alumno_list'),
    path('alumnos/nuevo/', views.AlumnoCreateView.as_view(), name='alumno_create'),
    path('alumnos/<int:pk>/', views.AlumnoDetailView.as_view(), name='alumno_detail'),
    path('alumnos/<int:pk>/editar/', views.AlumnoUpdateView.as_view(), name='alumno_update'),
    path('alumnos/<int:pk>/eliminar/', views.AlumnoDeleteView.as_view(), name='alumno_delete'),
    path('alumnos/<int:alumno_pk>/registros/nuevo/', views.RegistroAlumnoCreateView.as_view(), name='registro_create'),
    path('registros/<int:pk>/editar/', views.RegistroAlumnoUpdateView.as_view(), name='registro_update'),
    path('registros/<int:pk>/eliminar/', views.RegistroAlumnoDeleteView.as_view(), name='registro_delete'),
    path('registros/<int:registro_pk>/ficha-teorica/', views.FichaFormacionTeoricaView.as_view(), name='ficha_teorica'),
    path('registros/<int:registro_pk>/ficha-teorica/pdf/', views.generar_pdf_ficha_teorica, name='ficha_teorica_pdf'),
    path('registros/<int:registro_pk>/ficha-practica/', views.FichaFormacionPracticaView.as_view(), name='ficha_practica'),
    path('registros/<int:registro_pk>/ficha-practica/pdf/', views.generar_pdf_ficha_practica, name='ficha_practica_pdf'),
    path('fichas-practica/<int:ficha_pk>/clases/nueva/', views.ClasePracticaCreateView.as_view(), name='clase_practica_create'),
    path('clases-practica/<int:pk>/editar/', views.ClasePracticaUpdateView.as_view(), name='clase_practica_update'),
    path('clases-practica/<int:pk>/eliminar/', views.ClasePracticaDeleteView.as_view(), name='clase_practica_delete'),
    path('registros/<int:registro_pk>/eventos/nuevo/', views.EventoExamenCreateView.as_view(), name='evento_create'),
    path('eventos/<int:pk>/editar/', views.EventoExamenUpdateView.as_view(), name='evento_update'),
    path('alertas/', views.AlertasView.as_view(), name='alertas'),
    path('caducidad-teorico/', views.AlertasView.as_view(ranking=True), name='caducidad_teorico'),

    # Informes
    path('informes/trimestral/', views.InformeTrimestreView.as_view(), name='informe_trimestral'),
    path('informes/anual/', views.InformeAnualView.as_view(), name='informe_anual'),
    path('informes/comparar-iva/', views.CompararIvaView.as_view(), name='comparar_iva'),
    path('informes/revisar-dnis/', views.RevisarDnisView.as_view(), name='revisar_dnis'),
    path('informes/revisar-tasas/', views.RevisarTasasView.as_view(), name='revisar_tasas'),
    path('informes/facturas-faltantes/', views.FacturasFaltantesView.as_view(), name='facturas_faltantes'),

    # Exportaciones Excel
    path('exportar/trimestre/<int:trimestre>/<int:anio>/', views.exportar_trimestre_excel, name='exportar_trimestre'),
    path('exportar/anual/<int:anio>/', views.exportar_anual_excel, name='exportar_anual'),
    path('exportar/alumnos/', views.exportar_alumnos_excel, name='exportar_alumnos'),
    path('exportar/registro-b/', views.exportar_registro_b_excel, name='exportar_registro_b'),
    path('exportar/informe-iva/', views.exportar_informe_iva, name='exportar_informe_iva'),

    # Importación
    path('importar/', views.ImportarView.as_view(), name='importar'),

    # Configuración
    path('configuracion/', views.ConfiguracionView.as_view(), name='configuracion'),
    path('configuracion/profesores/', views.ProfesorTeoricaListView.as_view(), name='profesor_teorica_list'),
    path('configuracion/profesores/nuevo/', views.ProfesorTeoricaCreateView.as_view(), name='profesor_teorica_create'),
    path('configuracion/profesores/<int:pk>/editar/', views.ProfesorTeoricaUpdateView.as_view(), name='profesor_teorica_update'),
    path('configuracion/profesores/<int:pk>/eliminar/', views.ProfesorTeoricaDeleteView.as_view(), name='profesor_teorica_delete'),
]
