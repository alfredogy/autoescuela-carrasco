from django.contrib import admin
from .models import Alumno, Factura, ListadoHistorico, Configuracion


@admin.register(Configuracion)
class ConfiguracionAdmin(admin.ModelAdmin):
    list_display = ('anio_activo', 'iva_rate', 'tasa_basica', 'emisor_nombre')

    def has_add_permission(self, request):
        return not Configuracion.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'dni', 'municipio', 'provincia')
    search_fields = ('nombre', 'dni')
    list_filter = ('provincia',)


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ('numero_factura', 'fecha', 'nombre_factura', 'curso', 'base_imponible', 'iva', 'tasas', 'total', 'trimestre', 'anio')
    search_fields = ('numero_factura', 'nombre_factura', 'dni_factura')
    list_filter = ('anio', 'trimestre', 'curso')
    date_hierarchy = 'fecha'


@admin.register(ListadoHistorico)
class ListadoHistoricoAdmin(admin.ModelAdmin):
    list_display = ('numero_factura', 'trimestre', 'anio', 'neto', 'iva_incorrecto', 'total')
    list_filter = ('anio', 'trimestre')
