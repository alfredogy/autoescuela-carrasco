from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from facturacion import views as fac_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('inicio/', fac_views.login_dispatch, name='login_dispatch'),
    path('seleccionar-sede/', fac_views.seleccionar_sede, name='seleccionar_sede'),
    path('cambiar-sede/', fac_views.cambiar_sede, name='cambiar_sede'),
    path('panel-admin/', fac_views.PanelAdminView.as_view(), name='panel_admin'),
    path('panel-admin/usuario/nuevo/', fac_views.CrearUsuarioView.as_view(), name='crear_usuario'),
    path('panel-admin/usuario/<int:pk>/editar/', fac_views.EditarUsuarioView.as_view(), name='editar_usuario'),
    path('panel-admin/usuario/<int:pk>/eliminar/', fac_views.EliminarUsuarioView.as_view(), name='eliminar_usuario'),
    path('', include('facturacion.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
