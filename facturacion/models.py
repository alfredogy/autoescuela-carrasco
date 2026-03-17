from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


class Autoescuela(models.Model):
    nombre = models.CharField('Nombre', max_length=100, unique=True)

    class Meta:
        verbose_name = 'Autoescuela'
        verbose_name_plural = 'Autoescuelas'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    autoescuelas = models.ManyToManyField(Autoescuela, blank=True, related_name='usuarios')

    class Meta:
        verbose_name = 'Perfil de Usuario'
        verbose_name_plural = 'Perfiles de Usuario'

    def __str__(self):
        return f'Perfil de {self.usuario.username}'


class Configuracion(models.Model):
    """Configuración por autoescuela."""
    autoescuela = models.OneToOneField(
        Autoescuela, on_delete=models.CASCADE,
        related_name='configuracion', null=True, blank=True
    )
    anio_activo = models.PositiveIntegerField('Año activo', default=2025)
    tasa_basica = models.DecimalField('Tasa Básica', max_digits=8, decimal_places=2, default=Decimal('94.05'))
    tasa_a = models.DecimalField('Tasa A', max_digits=8, decimal_places=2, default=Decimal('28.87'))
    traslado = models.DecimalField('Traslado', max_digits=8, decimal_places=2, default=Decimal('8.67'))
    renovacion = models.DecimalField('Renovación', max_digits=8, decimal_places=2, default=Decimal('94.05'))
    iva_rate = models.DecimalField('Tipo IVA', max_digits=4, decimal_places=2, default=Decimal('0.21'))

    emisor_nombre = models.CharField('Nombre emisor', max_length=200, default='DKASA AUTOESCUELA, SL')
    emisor_dni = models.CharField('DNI emisor', max_length=20, default='B25875618')
    emisor_domicilio = models.CharField('Domicilio emisor', max_length=300, default='C/ Beniparrell ,31 - Bajo 9')
    emisor_cp = models.CharField('C.P. emisor', max_length=10, default='46470')
    emisor_municipio = models.CharField('Municipio emisor', max_length=100, default='Albal (Valencia)')

    class Meta:
        verbose_name = 'Configuración'
        verbose_name_plural = 'Configuración'

    def __str__(self):
        sede = self.autoescuela.nombre if self.autoescuela else 'Sin sede'
        return f'Configuración {sede} (Año {self.anio_activo})'

    @classmethod
    def get_instance(cls, autoescuela):
        obj, _ = cls.objects.get_or_create(autoescuela=autoescuela)
        return obj


class Alumno(models.Model):
    autoescuela = models.ForeignKey(
        Autoescuela, on_delete=models.CASCADE,
        related_name='alumnos', null=True, blank=True
    )
    nombre = models.CharField('Nombre y Apellidos', max_length=200)
    dni = models.CharField('DNI/NIE', max_length=20, blank=True, default='')
    direccion = models.CharField('Dirección', max_length=300, blank=True, default='')
    codigo_postal = models.CharField('C.P.', max_length=10, blank=True, default='')
    municipio = models.CharField('Municipio', max_length=100, blank=True, default='')
    provincia = models.CharField('Provincia', max_length=100, blank=True, default='VALENCIA')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Alumno'
        verbose_name_plural = 'Alumnos'

    def __str__(self):
        return f"{self.nombre} ({self.dni or 'Sin DNI'})"

    @property
    def dni_normalizado(self):
        if not self.dni:
            return ''
        return self.dni.upper().replace(' ', '').replace('-', '').strip()


CURSO_CHOICES = [
    ('AM', 'AM'),
    ('A1', 'A1'),
    ('A2', 'A2'),
    ('A', 'A'),
    ('B', 'B'),
    ('C', 'C'),
    ('C+E', 'C+E'),
]

TRIMESTRE_CHOICES = [
    (1, '1er Trimestre'),
    (2, '2º Trimestre'),
    (3, '3er Trimestre'),
    (4, '4º Trimestre'),
]


class Factura(models.Model):
    autoescuela = models.ForeignKey(
        Autoescuela, on_delete=models.CASCADE,
        related_name='facturas', null=True, blank=True
    )
    curso = models.CharField('Curso', max_length=5, choices=CURSO_CHOICES, default='B')
    numero_factura = models.CharField('Nº Factura', max_length=20)
    fecha = models.DateField('Fecha')

    alumno = models.ForeignKey(
        Alumno, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='facturas'
    )

    nombre_factura = models.CharField('Nombre en factura', max_length=200)
    dni_factura = models.CharField('DNI en factura', max_length=20, blank=True, default='')
    direccion_factura = models.CharField('Dirección en factura', max_length=300, blank=True, default='')
    cp_factura = models.CharField('C.P. en factura', max_length=10, blank=True, default='')
    municipio_factura = models.CharField('Municipio en factura', max_length=100, blank=True, default='')
    provincia_factura = models.CharField('Provincia en factura', max_length=100, blank=True, default='')

    base_imponible = models.DecimalField('Base Imponible', max_digits=10, decimal_places=2, default=Decimal('0'))
    iva = models.DecimalField('IVA', max_digits=10, decimal_places=2, default=Decimal('0'))
    tasas = models.DecimalField('Tasas', max_digits=10, decimal_places=2, default=Decimal('0'))
    total = models.DecimalField('Total', max_digits=10, decimal_places=2, default=Decimal('0'))

    tasa_basica_qty = models.PositiveIntegerField('Tasa Básica (cant)', default=0)
    tasa_a_qty = models.PositiveIntegerField('Tasa A (cant)', default=0)
    traslado_qty = models.PositiveIntegerField('Traslado (cant)', default=0)
    renovaciones_qty = models.PositiveIntegerField('Renovaciones (cant)', default=0)

    trimestre = models.PositiveIntegerField('Trimestre', choices=TRIMESTRE_CHOICES)
    anio = models.PositiveIntegerField('Año')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['anio', 'numero_factura']
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'
        unique_together = [['autoescuela', 'numero_factura']]
        indexes = [
            models.Index(fields=['anio', 'trimestre']),
            models.Index(fields=['numero_factura']),
            models.Index(fields=['dni_factura']),
        ]

    def __str__(self):
        return f"Factura {self.numero_factura} - {self.nombre_factura}"

    @property
    def es_exento_iva(self):
        return self.curso in ('C', 'C+E')

    @property
    def numero_corto(self):
        if '/' in self.numero_factura:
            parts = self.numero_factura.split('/')
            if len(parts) == 2:
                try:
                    return str(int(parts[1]))
                except ValueError:
                    pass
        return self.numero_factura

    def save(self, *args, **kwargs):
        if self.fecha:
            self.anio = self.fecha.year
            month = self.fecha.month
            if 1 <= month <= 3:
                self.trimestre = 1
            elif 4 <= month <= 6:
                self.trimestre = 2
            elif 7 <= month <= 9:
                self.trimestre = 3
            else:
                self.trimestre = 4
        super().save(*args, **kwargs)


class ListadoHistorico(models.Model):
    """Datos de los listados históricos con IVA incorrecto."""
    autoescuela = models.ForeignKey(
        Autoescuela, on_delete=models.CASCADE,
        related_name='listados_historicos', null=True, blank=True
    )
    numero_factura = models.CharField('Nº Factura', max_length=20)
    trimestre = models.PositiveIntegerField('Trimestre')
    anio = models.PositiveIntegerField('Año')
    neto = models.DecimalField('Neto (incorrecto)', max_digits=10, decimal_places=2, default=Decimal('0'))
    iva_incorrecto = models.DecimalField('IVA declarado (incorrecto)', max_digits=10, decimal_places=2, default=Decimal('0'))
    total = models.DecimalField('Total', max_digits=10, decimal_places=2, default=Decimal('0'))

    class Meta:
        ordering = ['anio', 'trimestre', 'numero_factura']
        verbose_name = 'Listado Histórico'
        verbose_name_plural = 'Listados Históricos'
        unique_together = [['autoescuela', 'numero_factura', 'trimestre', 'anio']]

    def __str__(self):
        return f"Histórico {self.numero_factura} T{self.trimestre}/{self.anio}"
