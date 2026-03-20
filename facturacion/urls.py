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
    path('alumnos/<int:pk>/', views.AlumnoDetailView.as_view(), name='alumno_detail'),
    path('alumnos/<int:pk>/editar/', views.AlumnoUpdateView.as_view(), name='alumno_update'),

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
    path('exportar/informe-iva/', views.exportar_informe_iva, name='exportar_informe_iva'),

    # Importación
    path('importar/', views.ImportarView.as_view(), name='importar'),

    # Configuración
    path('configuracion/', views.ConfiguracionView.as_view(), name='configuracion'),
]
