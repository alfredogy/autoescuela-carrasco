from django import forms
from django.contrib.auth.models import User
from .models import Factura, Alumno, Configuracion, Autoescuela, CURSO_CHOICES


class FacturaForm(forms.ModelForm):
    total_pagado = forms.DecimalField(
        label='Total pagado',
        max_digits=10, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_total_pagado'})
    )
    tasa_basica = forms.BooleanField(
        label='Tasa Básica B', required=False,
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
                  'direccion_factura', 'cp_factura', 'municipio_factura', 'provincia_factura']
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


class AlumnoForm(forms.ModelForm):
    class Meta:
        model = Alumno
        fields = ['nombre', 'dni', 'direccion', 'codigo_postal', 'municipio', 'provincia']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'dni': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_postal': forms.TextInput(attrs={'class': 'form-control', 'style': 'width:120px'}),
            'municipio': forms.TextInput(attrs={'class': 'form-control'}),
            'provincia': forms.TextInput(attrs={'class': 'form-control'}),
        }


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
