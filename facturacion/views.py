import zipfile
from functools import wraps
from io import BytesIO
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum, Q, Count
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import (
    TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
)

from .models import Factura, Alumno, Configuracion, ListadoHistorico, Autoescuela, PerfilUsuario, CURSO_CHOICES
from .forms import FacturaForm, AlumnoForm, ConfiguracionForm, ImportarExcelForm, UsuarioForm
from .utils.calculos import compute_components, next_invoice_number, find_missing_invoices
from .utils.dni_validator import validar_dni
from .utils.iva_comparator import comparar_iva_anual


# ============================================================
# Helpers multi-autoescuela
# ============================================================

def get_autoescuela_activa(request):
    autoescuela_id = request.session.get('autoescuela_id')
    if not autoescuela_id:
        return None
    try:
        perfil = request.user.perfil
        return perfil.autoescuelas.get(pk=autoescuela_id)
    except Exception:
        return None


class AutoescuelaActivaMixin(LoginRequiredMixin):
    """Mixin para vistas que requieren autoescuela activa en sesión."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.is_superuser:
            return redirect('panel_admin')
        autoescuela = get_autoescuela_activa(request)
        if autoescuela is None:
            return redirect('seleccionar_sede')
        self.autoescuela_activa = autoescuela
        return super(LoginRequiredMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['autoescuela_activa'] = self.autoescuela_activa
        return ctx


def con_autoescuela(func):
    """Decorador para vistas de función que requieren autoescuela activa."""
    @login_required
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser:
            return redirect('panel_admin')
        autoescuela = get_autoescuela_activa(request)
        if autoescuela is None:
            return redirect('seleccionar_sede')
        return func(request, *args, autoescuela=autoescuela, **kwargs)
    return wrapper


# ============================================================
# Login dispatch y selección de sede
# ============================================================

@login_required
def login_dispatch(request):
    if request.user.is_superuser:
        return redirect('panel_admin')
    try:
        perfil = request.user.perfil
        autoescuelas = perfil.autoescuelas.all()
    except PerfilUsuario.DoesNotExist:
        messages.error(request, 'Tu usuario no tiene autoescuelas asignadas. Contacta con el administrador.')
        return redirect('logout')

    if autoescuelas.count() == 0:
        messages.error(request, 'Tu usuario no tiene autoescuelas asignadas. Contacta con el administrador.')
        return redirect('logout')
    elif autoescuelas.count() == 1:
        request.session['autoescuela_id'] = autoescuelas.first().pk
        return redirect('facturacion:dashboard')
    else:
        return redirect('seleccionar_sede')


@login_required
def seleccionar_sede(request):
    if request.user.is_superuser:
        return redirect('panel_admin')
    try:
        perfil = request.user.perfil
        autoescuelas = perfil.autoescuelas.all()
    except PerfilUsuario.DoesNotExist:
        messages.error(request, 'Tu usuario no tiene autoescuelas asignadas.')
        return redirect('logout')

    if request.method == 'POST':
        autoescuela_id = request.POST.get('autoescuela_id')
        if autoescuelas.filter(pk=autoescuela_id).exists():
            request.session['autoescuela_id'] = int(autoescuela_id)
            return redirect('facturacion:dashboard')
        messages.error(request, 'Sede no válida.')

    return render(request, 'facturacion/seleccionar_sede.html', {'autoescuelas': autoescuelas})


@login_required
def cambiar_sede(request):
    if request.user.is_superuser:
        return redirect('panel_admin')
    request.session.pop('autoescuela_id', None)
    return redirect('seleccionar_sede')


# ============================================================
# Panel de administración
# ============================================================

class AdminRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_superuser:
            return redirect('facturacion:dashboard')
        return super(LoginRequiredMixin, self).dispatch(request, *args, **kwargs)


class PanelAdminView(AdminRequiredMixin, TemplateView):
    template_name = 'panel_admin/panel.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['usuarios'] = User.objects.filter(is_superuser=False).prefetch_related('perfil__autoescuelas')
        ctx['autoescuelas'] = Autoescuela.objects.all()
        return ctx


class CrearUsuarioView(AdminRequiredMixin, TemplateView):
    template_name = 'panel_admin/usuario_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = UsuarioForm()
        ctx['titulo'] = 'Nuevo usuario'
        return ctx

    def post(self, request, *args, **kwargs):
        form = UsuarioForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form, 'titulo': 'Nuevo usuario'})

        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        autoescuelas = form.cleaned_data['autoescuelas']

        if User.objects.filter(username=username).exists():
            form.add_error('username', 'Ya existe un usuario con ese nombre.')
            return render(request, self.template_name, {'form': form, 'titulo': 'Nuevo usuario'})

        if not password:
            form.add_error('password', 'La contraseña es obligatoria para nuevos usuarios.')
            return render(request, self.template_name, {'form': form, 'titulo': 'Nuevo usuario'})

        user = User(username=username)
        user.set_password(password)
        user.save()

        perfil = PerfilUsuario.objects.create(usuario=user)
        perfil.autoescuelas.set(autoescuelas)

        messages.success(request, f'Usuario "{username}" creado correctamente.')
        return redirect('panel_admin')


class EditarUsuarioView(AdminRequiredMixin, TemplateView):
    template_name = 'panel_admin/usuario_form.html'

    def get_object(self):
        return get_object_or_404(User, pk=self.kwargs['pk'], is_superuser=False)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        usuario = self.get_object()
        autoescuelas_actuales = []
        try:
            autoescuelas_actuales = list(usuario.perfil.autoescuelas.values_list('pk', flat=True))
        except PerfilUsuario.DoesNotExist:
            pass
        ctx['form'] = UsuarioForm(initial={
            'username': usuario.username,
            'autoescuelas': autoescuelas_actuales,
        })
        ctx['titulo'] = f'Editar usuario: {usuario.username}'
        ctx['editando'] = True
        ctx['usuario'] = usuario
        return ctx

    def post(self, request, *args, **kwargs):
        usuario = self.get_object()
        form = UsuarioForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {
                'form': form, 'titulo': f'Editar usuario: {usuario.username}',
                'editando': True, 'usuario': usuario
            })

        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        autoescuelas = form.cleaned_data['autoescuelas']

        if User.objects.filter(username=username).exclude(pk=usuario.pk).exists():
            form.add_error('username', 'Ya existe un usuario con ese nombre.')
            return render(request, self.template_name, {
                'form': form, 'titulo': f'Editar usuario: {usuario.username}',
                'editando': True, 'usuario': usuario
            })

        usuario.username = username
        if password:
            usuario.set_password(password)
        usuario.save()

        perfil, _ = PerfilUsuario.objects.get_or_create(usuario=usuario)
        perfil.autoescuelas.set(autoescuelas)

        messages.success(request, f'Usuario "{username}" actualizado correctamente.')
        return redirect('panel_admin')


class EliminarUsuarioView(AdminRequiredMixin, TemplateView):
    template_name = 'panel_admin/usuario_confirm_delete.html'

    def get_object(self):
        return get_object_or_404(User, pk=self.kwargs['pk'], is_superuser=False)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['usuario'] = self.get_object()
        return ctx

    def post(self, request, *args, **kwargs):
        usuario = self.get_object()
        nombre = usuario.username
        usuario.delete()
        messages.success(request, f'Usuario "{nombre}" eliminado.')
        return redirect('panel_admin')


# ============================================================
# Dashboard
# ============================================================

class DashboardView(AutoescuelaActivaMixin, TemplateView):
    template_name = 'facturacion/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        config = Configuracion.get_instance(self.autoescuela_activa)
        anio = config.anio_activo

        ctx['anio'] = anio
        ctx['total_facturas'] = Factura.objects.filter(anio=anio, autoescuela=self.autoescuela_activa).count()

        totales = Factura.objects.filter(anio=anio, autoescuela=self.autoescuela_activa).aggregate(
            total_base=Sum('base_imponible'),
            total_iva=Sum('iva'),
            total_tasas=Sum('tasas'),
            total_total=Sum('total'),
        )
        ctx['totales'] = {k: v or Decimal('0') for k, v in totales.items()}
        ctx['total_alumnos'] = Alumno.objects.filter(autoescuela=self.autoescuela_activa).count()

        trimestres = []
        for t in range(1, 5):
            agg = Factura.objects.filter(anio=anio, trimestre=t, autoescuela=self.autoescuela_activa).aggregate(
                count=Count('id'), total=Sum('total')
            )
            trimestres.append({
                'num': t,
                'facturas': agg['count'],
                'total': agg['total'] or Decimal('0'),
            })
        ctx['trimestres'] = trimestres

        ctx['ultimas_facturas'] = Factura.objects.filter(
            anio=anio, autoescuela=self.autoescuela_activa
        ).order_by('-fecha', '-pk')[:10]
        return ctx


# ============================================================
# Facturas CRUD
# ============================================================

class FacturaListView(AutoescuelaActivaMixin, ListView):
    model = Factura
    template_name = 'facturacion/factura_list.html'
    paginate_by = 50

    def get_queryset(self):
        qs = Factura.objects.filter(autoescuela=self.autoescuela_activa)
        anio = self.request.GET.get('anio')
        trimestre = self.request.GET.get('trimestre')
        curso = self.request.GET.get('curso')
        q = self.request.GET.get('q')

        if anio:
            qs = qs.filter(anio=anio)
        if trimestre:
            qs = qs.filter(trimestre=trimestre)
        if curso:
            qs = qs.filter(curso=curso)
        if q:
            qs = qs.filter(
                Q(nombre_factura__icontains=q) |
                Q(dni_factura__icontains=q) |
                Q(numero_factura__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        config = Configuracion.get_instance(self.autoescuela_activa)
        ctx['anio_activo'] = config.anio_activo
        ctx['anio_filtro'] = self.request.GET.get('anio', '')
        ctx['trimestre_filtro'] = self.request.GET.get('trimestre', '')
        ctx['curso_filtro'] = self.request.GET.get('curso', '')
        ctx['q'] = self.request.GET.get('q', '')
        ctx['cursos'] = CURSO_CHOICES

        qs = self.get_queryset()
        ctx['totales'] = qs.aggregate(
            total_base=Sum('base_imponible'),
            total_iva=Sum('iva'),
            total_tasas=Sum('tasas'),
            total_total=Sum('total'),
        )
        ctx['count'] = qs.count()

        ctx['anios'] = (
            Factura.objects.filter(autoescuela=self.autoescuela_activa)
            .values_list('anio', flat=True).distinct().order_by('-anio')
        )
        return ctx


class FacturaCreateView(AutoescuelaActivaMixin, CreateView):
    model = Factura
    form_class = FacturaForm
    template_name = 'facturacion/factura_form.html'

    def get_initial(self):
        initial = super().get_initial()
        initial['provincia_factura'] = 'VALENCIA'
        initial['renovaciones'] = 0
        return initial

    def form_valid(self, form):
        config = Configuracion.get_instance(self.autoescuela_activa)
        factura = form.save(commit=False)
        factura.autoescuela = self.autoescuela_activa

        total_pagado = form.cleaned_data['total_pagado']
        tb = 1 if form.cleaned_data.get('tasa_basica') else 0
        ta = 1 if form.cleaned_data.get('tasa_a') else 0
        tr = 1 if form.cleaned_data.get('traslado') else 0
        rn = form.cleaned_data.get('renovaciones', 0)

        base, iva, tasas, total = compute_components(
            total_pagado, tb, ta, tr, rn, factura.curso, config=config
        )

        factura.base_imponible = base
        factura.iva = iva
        factura.tasas = tasas
        factura.total = total_pagado
        factura.tasa_basica_qty = tb
        factura.tasa_a_qty = ta
        factura.traslado_qty = tr
        factura.renovaciones_qty = rn

        num_manual = form.cleaned_data.get('numero_factura_manual', '').strip()
        if num_manual:
            if '/' in num_manual:
                factura.numero_factura = num_manual
            elif num_manual.isdigit():
                factura.numero_factura = f"{config.anio_activo}/{int(num_manual):04d}"
            else:
                form.add_error('numero_factura_manual', 'Formato inválido')
                return self.form_invalid(form)
        else:
            n = next_invoice_number(factura.fecha.year if factura.fecha else config.anio_activo, self.autoescuela_activa)
            anio = factura.fecha.year if factura.fecha else config.anio_activo
            factura.numero_factura = f"{anio}/{n:04d}"

        if Factura.objects.filter(numero_factura=factura.numero_factura, autoescuela=self.autoescuela_activa).exists():
            form.add_error('numero_factura_manual', f'La factura {factura.numero_factura} ya existe.')
            return self.form_invalid(form)

        dni = factura.dni_factura.strip()
        if dni:
            alumno, created = Alumno.objects.get_or_create(
                dni=dni,
                autoescuela=self.autoescuela_activa,
                defaults={
                    'nombre': factura.nombre_factura,
                    'direccion': factura.direccion_factura,
                    'codigo_postal': factura.cp_factura,
                    'municipio': factura.municipio_factura,
                    'provincia': factura.provincia_factura,
                }
            )
            if not created and factura.direccion_factura:
                alumno.direccion = factura.direccion_factura
                alumno.codigo_postal = factura.cp_factura
                alumno.municipio = factura.municipio_factura
                alumno.provincia = factura.provincia_factura
                alumno.save()
            factura.alumno = alumno

        factura.save()
        messages.success(self.request, f'Factura {factura.numero_factura} creada correctamente.')

        if '_addanother' in self.request.POST:
            return redirect('facturacion:factura_create')
        return redirect('facturacion:factura_detail', pk=factura.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Nueva Factura'
        return ctx


class FacturaDetailView(AutoescuelaActivaMixin, DetailView):
    model = Factura
    template_name = 'facturacion/factura_detail.html'

    def get_queryset(self):
        return Factura.objects.filter(autoescuela=self.autoescuela_activa)


class FacturaUpdateView(AutoescuelaActivaMixin, UpdateView):
    model = Factura
    form_class = FacturaForm
    template_name = 'facturacion/factura_form.html'

    def get_queryset(self):
        return Factura.objects.filter(autoescuela=self.autoescuela_activa)

    def get_initial(self):
        initial = super().get_initial()
        obj = self.get_object()
        initial['total_pagado'] = obj.total
        initial['tasa_basica'] = obj.tasa_basica_qty > 0
        initial['tasa_a'] = obj.tasa_a_qty > 0
        initial['traslado'] = obj.traslado_qty > 0
        initial['renovaciones'] = obj.renovaciones_qty
        initial['numero_factura_manual'] = obj.numero_factura
        return initial

    def form_valid(self, form):
        config = Configuracion.get_instance(self.autoescuela_activa)
        factura = form.save(commit=False)

        total_pagado = form.cleaned_data['total_pagado']
        tb = 1 if form.cleaned_data.get('tasa_basica') else 0
        ta = 1 if form.cleaned_data.get('tasa_a') else 0
        tr = 1 if form.cleaned_data.get('traslado') else 0
        rn = form.cleaned_data.get('renovaciones', 0)

        base, iva, tasas, total = compute_components(
            total_pagado, tb, ta, tr, rn, factura.curso, config=config
        )

        factura.base_imponible = base
        factura.iva = iva
        factura.tasas = tasas
        factura.total = total_pagado
        factura.tasa_basica_qty = tb
        factura.tasa_a_qty = ta
        factura.traslado_qty = tr
        factura.renovaciones_qty = rn

        num_manual = form.cleaned_data.get('numero_factura_manual', '').strip()
        if num_manual and num_manual != factura.numero_factura:
            if '/' in num_manual:
                factura.numero_factura = num_manual
            elif num_manual.isdigit():
                factura.numero_factura = f"{config.anio_activo}/{int(num_manual):04d}"

        factura.save()
        messages.success(self.request, f'Factura {factura.numero_factura} actualizada.')
        return redirect('facturacion:factura_detail', pk=factura.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = f'Editar Factura {self.object.numero_factura}'
        ctx['editing'] = True
        return ctx


class FacturaDeleteView(AutoescuelaActivaMixin, DeleteView):
    model = Factura
    template_name = 'facturacion/factura_confirm_delete.html'
    success_url = reverse_lazy('facturacion:factura_list')

    def get_queryset(self):
        return Factura.objects.filter(autoescuela=self.autoescuela_activa)

    def form_valid(self, form):
        messages.success(self.request, f'Factura {self.object.numero_factura} eliminada.')
        return super().form_valid(form)


# ============================================================
# API AJAX
# ============================================================

@con_autoescuela
def calcular_factura_ajax(request, autoescuela):
    try:
        total_pagado = float(request.GET.get('total_pagado', 0))
        tb = int(request.GET.get('tasa_basica', 0))
        ta = int(request.GET.get('tasa_a', 0))
        tr = int(request.GET.get('traslado', 0))
        rn = int(request.GET.get('renovaciones', 0))
        curso = request.GET.get('curso', 'B')
        config = Configuracion.get_instance(autoescuela)

        base, iva, tasas, total = compute_components(total_pagado, tb, ta, tr, rn, curso, config=config)

        return JsonResponse({
            'base': str(base),
            'iva': str(iva),
            'tasas': str(tasas),
            'total': str(total),
        })
    except (ValueError, TypeError) as e:
        return JsonResponse({'error': str(e)}, status=400)


@con_autoescuela
def buscar_alumno_ajax(request, autoescuela):
    dni = request.GET.get('dni', '').strip()
    if len(dni) < 3:
        return JsonResponse({'found': False})

    try:
        alumno = Alumno.objects.filter(
            autoescuela=autoescuela
        ).filter(
            Q(dni__icontains=dni) | Q(nombre__icontains=dni)
        ).first()
        if alumno:
            return JsonResponse({
                'found': True,
                'nombre': alumno.nombre,
                'dni': alumno.dni,
                'direccion': alumno.direccion,
                'cp': alumno.codigo_postal,
                'municipio': alumno.municipio,
                'provincia': alumno.provincia,
            })
    except Exception:
        pass
    return JsonResponse({'found': False})


# ============================================================
# PDF
# ============================================================

@con_autoescuela
def generar_pdf_factura(request, pk, autoescuela):
    from .utils.pdf_generator import generate_invoice_pdf
    factura = get_object_or_404(Factura, pk=pk, autoescuela=autoescuela)
    buffer = generate_invoice_pdf(factura)
    response = HttpResponse(buffer, content_type='application/pdf')
    filename = f"fra {factura.numero_corto}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@con_autoescuela
def generar_pdf_lote(request, autoescuela):
    from .utils.pdf_generator import generate_invoice_pdf

    anio = int(request.GET.get('anio', Configuracion.get_instance(autoescuela).anio_activo))
    trimestre = request.GET.get('trimestre')

    qs = Factura.objects.filter(anio=anio, autoescuela=autoescuela)
    if trimestre:
        qs = qs.filter(trimestre=int(trimestre))

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for factura in qs:
            pdf_buffer = generate_invoice_pdf(factura)
            zf.writestr(f"fra {factura.numero_corto}.pdf", pdf_buffer.read())

    zip_buffer.seek(0)
    label = f"T{trimestre}_" if trimestre else ""
    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="facturas_{label}{anio}.zip"'
    return response


# ============================================================
# Alumnos
# ============================================================

class AlumnoListView(AutoescuelaActivaMixin, ListView):
    model = Alumno
    template_name = 'facturacion/alumno_list.html'
    paginate_by = 50

    def get_queryset(self):
        qs = Alumno.objects.filter(autoescuela=self.autoescuela_activa)
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(dni__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['total_alumnos'] = Alumno.objects.filter(autoescuela=self.autoescuela_activa).count()
        return ctx


class AlumnoDetailView(AutoescuelaActivaMixin, DetailView):
    model = Alumno
    template_name = 'facturacion/alumno_detail.html'

    def get_queryset(self):
        return Alumno.objects.filter(autoescuela=self.autoescuela_activa)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['facturas'] = self.object.facturas.all().order_by('-fecha')
        return ctx


class AlumnoUpdateView(AutoescuelaActivaMixin, UpdateView):
    model = Alumno
    form_class = AlumnoForm
    template_name = 'facturacion/alumno_form.html'

    def get_queryset(self):
        return Alumno.objects.filter(autoescuela=self.autoescuela_activa)

    def get_success_url(self):
        return self.object.get_absolute_url() if hasattr(self.object, 'get_absolute_url') else reverse_lazy('facturacion:alumno_list')

    def form_valid(self, form):
        messages.success(self.request, 'Alumno actualizado correctamente.')
        return super().form_valid(form)


# ============================================================
# Informes
# ============================================================

class InformeTrimestreView(AutoescuelaActivaMixin, TemplateView):
    template_name = 'facturacion/informe_trimestral.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        config = Configuracion.get_instance(self.autoescuela_activa)
        anio = int(self.request.GET.get('anio', config.anio_activo))
        trimestre = int(self.request.GET.get('trimestre', 1))

        facturas = Factura.objects.filter(anio=anio, trimestre=trimestre, autoescuela=self.autoescuela_activa)
        ctx['anio'] = anio
        ctx['trimestre'] = trimestre
        ctx['facturas'] = facturas
        ctx['totales'] = facturas.aggregate(
            total_base=Sum('base_imponible'),
            total_iva=Sum('iva'),
            total_tasas=Sum('tasas'),
            total_total=Sum('total'),
        )
        ctx['count'] = facturas.count()
        return ctx


class InformeAnualView(AutoescuelaActivaMixin, TemplateView):
    template_name = 'facturacion/informe_anual.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        config = Configuracion.get_instance(self.autoescuela_activa)
        anio = int(self.request.GET.get('anio', config.anio_activo))

        ctx['anio'] = anio
        trimestres = []
        for t in range(1, 5):
            agg = Factura.objects.filter(anio=anio, trimestre=t, autoescuela=self.autoescuela_activa).aggregate(
                total_base=Sum('base_imponible'),
                total_iva=Sum('iva'),
                total_tasas=Sum('tasas'),
                total_total=Sum('total'),
                count=Count('id'),
            )
            trimestres.append({'num': t, **{k: v or Decimal('0') for k, v in agg.items()}})
        ctx['trimestres'] = trimestres

        total_agg = Factura.objects.filter(anio=anio, autoescuela=self.autoescuela_activa).aggregate(
            total_base=Sum('base_imponible'),
            total_iva=Sum('iva'),
            total_tasas=Sum('tasas'),
            total_total=Sum('total'),
            count=Count('id'),
        )
        ctx['total'] = {k: v or Decimal('0') for k, v in total_agg.items()}
        ctx['faltantes'] = find_missing_invoices(anio, self.autoescuela_activa)
        return ctx


class CompararIvaView(AutoescuelaActivaMixin, TemplateView):
    template_name = 'facturacion/comparar_iva.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        config = Configuracion.get_instance(self.autoescuela_activa)
        anio = int(self.request.GET.get('anio', config.anio_activo))
        ctx['anio'] = anio
        ctx['informe'] = comparar_iva_anual(anio, self.autoescuela_activa)
        return ctx


class RevisarDnisView(AutoescuelaActivaMixin, TemplateView):
    template_name = 'facturacion/revisar_dnis.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        alumnos = Alumno.objects.filter(autoescuela=self.autoescuela_activa).exclude(dni__exact='')
        errores = []
        revisados = set()
        for alumno in alumnos:
            dni_norm = alumno.dni_normalizado
            if dni_norm in revisados:
                continue
            revisados.add(dni_norm)
            resultado = validar_dni(alumno.dni)
            if not resultado['valido']:
                errores.append({'alumno': alumno, 'resultado': resultado})

        ctx['errores'] = errores
        ctx['total_revisados'] = len(revisados)
        ctx['total_errores'] = len(errores)
        return ctx


class RevisarTasasView(AutoescuelaActivaMixin, TemplateView):
    template_name = 'facturacion/revisar_tasas.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        config = Configuracion.get_instance(self.autoescuela_activa)
        anio = int(self.request.GET.get('anio', config.anio_activo))

        personas = []
        alumnos_con_facturas = Alumno.objects.filter(
            facturas__anio=anio, autoescuela=self.autoescuela_activa
        ).distinct()
        for alumno in alumnos_con_facturas:
            facturas = alumno.facturas.filter(anio=anio, autoescuela=self.autoescuela_activa)
            if facturas.exists() and not facturas.exclude(tasas=0).exists():
                personas.append({
                    'alumno': alumno,
                    'trimestres': list(facturas.values_list('trimestre', flat=True).distinct()),
                    'num_facturas': facturas.count(),
                })

        ctx['personas'] = sorted(personas, key=lambda x: x['alumno'].nombre)
        ctx['anio'] = anio
        ctx['total'] = len(personas)
        return ctx


class FacturasFaltantesView(AutoescuelaActivaMixin, TemplateView):
    template_name = 'facturacion/facturas_faltantes.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        config = Configuracion.get_instance(self.autoescuela_activa)
        anio = int(self.request.GET.get('anio', config.anio_activo))
        ctx['anio'] = anio
        ctx['faltantes'] = find_missing_invoices(anio, self.autoescuela_activa)

        nums = []
        for nf in Factura.objects.filter(anio=anio, autoescuela=self.autoescuela_activa).values_list('numero_factura', flat=True):
            if '/' in nf:
                parts = nf.split('/')
                if len(parts) == 2 and parts[1].isdigit():
                    nums.append(int(parts[1]))
        if nums:
            ctx['rango_min'] = min(nums)
            ctx['rango_max'] = max(nums)
            ctx['total_existentes'] = len(set(nums))
        return ctx


# ============================================================
# Exportaciones Excel
# ============================================================

@con_autoescuela
def exportar_trimestre_excel(request, trimestre, anio, autoescuela):
    from .utils.excel_exporter import exportar_facturas_excel
    buffer = exportar_facturas_excel(anio, autoescuela, trimestre=trimestre)
    response = HttpResponse(
        buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="Trimestre-{trimestre}_{anio}.xlsx"'
    return response


@con_autoescuela
def exportar_anual_excel(request, anio, autoescuela):
    from .utils.excel_exporter import exportar_facturas_excel
    buffer = exportar_facturas_excel(anio, autoescuela)
    response = HttpResponse(
        buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="Anual-{anio}.xlsx"'
    return response


@con_autoescuela
def exportar_alumnos_excel(request, autoescuela):
    from .utils.excel_exporter import exportar_alumnos
    buffer = exportar_alumnos(autoescuela)
    response = HttpResponse(
        buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="alumnos.xlsx"'
    return response


@con_autoescuela
def exportar_informe_iva(request, autoescuela):
    from .utils.excel_exporter import exportar_informe_comparacion_iva
    config = Configuracion.get_instance(autoescuela)
    anio = int(request.GET.get('anio', config.anio_activo))
    buffer = exportar_informe_comparacion_iva(anio, autoescuela)
    response = HttpResponse(
        buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="INFORME_COMPARACION_IVA_{anio}.xlsx"'
    return response


# ============================================================
# Importación
# ============================================================

class ImportarView(AutoescuelaActivaMixin, TemplateView):
    template_name = 'facturacion/importar.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        config = Configuracion.get_instance(self.autoescuela_activa)
        ctx['form'] = ImportarExcelForm(initial={'anio': config.anio_activo})
        return ctx

    def post(self, request, *args, **kwargs):
        form = ImportarExcelForm(request.POST, request.FILES)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        archivo = request.FILES['archivo']
        tipo = form.cleaned_data['tipo']
        trimestre = int(form.cleaned_data['trimestre'])
        anio = form.cleaned_data['anio']

        try:
            from .utils.excel_importer import importar_trimestre, importar_listado
            if tipo == 'trimestre':
                count = importar_trimestre(archivo, trimestre, anio, self.autoescuela_activa)
                messages.success(request, f'Importadas {count} facturas del Trimestre {trimestre}.')
            else:
                count = importar_listado(archivo, trimestre, anio, self.autoescuela_activa)
                messages.success(request, f'Importados {count} registros del listado histórico T{trimestre}.')
        except Exception as e:
            messages.error(request, f'Error al importar: {e}')

        return redirect('facturacion:importar')


# ============================================================
# Configuración
# ============================================================

class ConfiguracionView(AutoescuelaActivaMixin, TemplateView):
    template_name = 'facturacion/configuracion.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = ConfiguracionForm(instance=Configuracion.get_instance(self.autoescuela_activa))
        return ctx

    def post(self, request, *args, **kwargs):
        form = ConfiguracionForm(request.POST, instance=Configuracion.get_instance(self.autoescuela_activa))
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuración actualizada.')
            return redirect('facturacion:configuracion')
        return self.render_to_response(self.get_context_data(form=form))
