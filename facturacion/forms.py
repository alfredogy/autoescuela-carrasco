from decimal import Decimal

from django import forms
from django.contrib.auth.models import User
from .models import Factura, Alumno, RegistroAlumno, Configuracion, Autoescuela, CURSO_CHOICES


class FacturaForm(forms.ModelForm):
    tasa_tacografo = forms.DecimalField(
        label='Tasa expedición tarjeta tacógrafo digital',
        max_digits=10, decimal_places=2, min_value=0, required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'})
    )
    total_pagado = forms.DecimalField(
        label='Total pagado',
        max_digits=10, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_total_pagado'})
    )
    tasa_basica = forms.BooleanField(
        label='Tasa Básica', required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_tasa_basica'})
    )
    tasa_a = forms.BooleanField(
        label='Tasa A', required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_tasa_a'})
    )
    traslado = forms.BooleanField(
        label='Traslado', required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_traslado'})
    )
    renovaciones = forms.IntegerField(
        label='Renovaciones', min_value=0, initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'style': 'width:80px', 'id': 'id_renovaciones'})
    )
    numero_factura_manual = forms.CharField(
        label='Nº Factura (opcional)', max_length=20, required=False,
        help_text='Dejar vacío para auto-numerar',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Auto'})
    )

    class Meta:
        model = Factura
        fields = ['curso', 'fecha', 'nombre_factura', 'dni_factura',
                  'direccion_factura', 'cp_factura', 'municipio_factura', 'provincia_factura', 'tasa_tacografo']
        widgets = {
            'curso': forms.Select(attrs={'class': 'form-select', 'id': 'id_curso'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'nombre_factura': forms.TextInput(attrs={'class': 'form-control'}),
            'dni_factura': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_dni_factura', 'placeholder': 'Escribe DNI para buscar alumno'}),
            'direccion_factura': forms.TextInput(attrs={'class': 'form-control'}),
            'cp_factura': forms.TextInput(attrs={'class': 'form-control', 'style': 'width:120px'}),
            'municipio_factura': forms.TextInput(attrs={'class': 'form-control'}),
            'provincia_factura': forms.TextInput(attrs={'class': 'form-control', 'value': 'VALENCIA'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.initial.setdefault('tasa_tacografo', Decimal('32.47'))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('curso') == 'TACOGRAFO':
            tasa = cleaned.get('tasa_tacografo')
            total = cleaned.get('total_pagado')
            if tasa is None and 'tasa_tacografo' not in self.errors:
                self.add_error('tasa_tacografo', 'Introduce la tasa de tacógrafo.')
            elif tasa is not None and total is not None and tasa > total:
                self.add_error('tasa_tacografo', 'La tasa no puede superar el total pagado.')
            for field in ('tasa_basica', 'tasa_a', 'traslado', 'renovaciones'):
                cleaned[field] = 0
        else:
            cleaned['tasa_tacografo'] = Decimal('0')
        return cleaned


class AlumnoForm(forms.ModelForm):
    class Meta:
        model = Alumno
        fields = [
            'nombre', 'nombre_pila', 'apellido1', 'apellido2', 'dni', 'direccion', 'codigo_postal', 'municipio', 'provincia',
            'fecha_nacimiento',
        ]
        widgets = {
            'nombre': forms.HiddenInput(),
            'nombre_pila': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido1': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido2': forms.TextInput(attrs={'class': 'form-control'}),
            'dni': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_postal': forms.TextInput(attrs={'class': 'form-control', 'style': 'width:120px'}),
            'municipio': forms.TextInput(attrs={'class': 'form-control'}),
            'provincia': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_alta': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_nacimiento': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nombre'].required = False
        self.fields['nombre_pila'].required = True
        self.fields['fecha_nacimiento'].input_formats = ['%Y-%m-%d']
        if self.instance.pk and not self.instance.nombre_pila:
            self.initial['nombre_pila'] = self.instance.nombre

    def clean(self):
        cleaned_data = super().clean()
        nombre_completo = ' '.join(
            parte for parte in (
                cleaned_data.get('apellido1', ''),
                cleaned_data.get('apellido2', ''),
                cleaned_data.get('nombre_pila', ''),
            ) if parte
        )
        self.instance.nombre = nombre_completo
        cleaned_data['nombre'] = nombre_completo
        return cleaned_data


class RegistroAlumnoForm(forms.ModelForm):
    class Meta:
        model = RegistroAlumno
        fields = [
            'permiso', 'numero_registro', 'fecha_alta', 'fecha_inicio', 'fecha_fin',
            'causa', 'observaciones', 'fecha_apto_teorico', 'estado_apto_teorico',
        ]
        widgets = {
            'permiso': forms.Select(attrs={'class': 'form-select'}),
            'numero_registro': forms.NumberInput(attrs={'class': 'form-control'}),
            'fecha_alta': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_inicio': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'causa': forms.TextInput(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'fecha_apto_teorico': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'estado_apto_teorico': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'EXENTO'}),
        }

    def __init__(self, *args, autoescuela=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.autoescuela = autoescuela
        for field_name in ('fecha_alta', 'fecha_inicio', 'fecha_fin', 'fecha_apto_teorico'):
            self.fields[field_name].input_formats = ['%Y-%m-%d']
        if not self.instance.pk and self.initial.get('permiso', 'B') == 'B' and autoescuela:
            ultimo = RegistroAlumno.objects.filter(autoescuela=autoescuela, permiso='B').order_by(
                '-numero_registro'
            ).values_list('numero_registro', flat=True).first() or 0
            self.initial['numero_registro'] = ultimo + 1

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('permiso') != 'B':
            cleaned_data['numero_registro'] = None
        return cleaned_data


class ConfiguracionForm(forms.ModelForm):
    class Meta:
        model = Configuracion
        fields = ['anio_activo', 'tasa_basica', 'tasa_a', 'traslado', 'renovacion', 'iva_rate',
                  'emisor_nombre', 'emisor_dni', 'emisor_domicilio', 'emisor_cp', 'emisor_municipio']
        widgets = {
            'anio_activo': forms.NumberInput(attrs={'class': 'form-control', 'style': 'width:100px'}),
            'tasa_basica': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'width:120px'}),
            'tasa_a': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'width:120px'}),
            'traslado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'width:120px'}),
            'renovacion': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'width:120px'}),
            'iva_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'width:100px'}),
            'emisor_nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'emisor_dni': forms.TextInput(attrs={'class': 'form-control', 'style': 'width:150px'}),
            'emisor_domicilio': forms.TextInput(attrs={'class': 'form-control'}),
            'emisor_cp': forms.TextInput(attrs={'class': 'form-control', 'style': 'width:100px'}),
            'emisor_municipio': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ImportarExcelForm(forms.Form):
    archivo = forms.FileField(
        label='Archivo Excel (.xlsx)',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx'})
    )
    tipo = forms.ChoiceField(
        label='Tipo de archivo',
        choices=[
            ('trimestre', 'Trimestre (Trimestre-X.xlsx)'),
            ('listado', 'Listado histórico (LISTADO FACT X TRI.xlsx)'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    trimestre = forms.ChoiceField(
        label='Trimestre',
        choices=[(1, 'T1'), (2, 'T2'), (3, 'T3'), (4, 'T4')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    anio = forms.IntegerField(
        label='Año',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'style': 'width:100px'})
    )


class UsuarioForm(forms.Form):
    username = forms.CharField(
        label='Nombre de usuario', max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text='Dejar vacío para no cambiar la contraseña (solo al editar)'
    )
    autoescuelas = forms.ModelMultipleChoiceField(
        queryset=Autoescuela.objects.all(),
        label='Autoescuelas asignadas',
        widget=forms.CheckboxSelectMultiple(),
        required=False,
    )
