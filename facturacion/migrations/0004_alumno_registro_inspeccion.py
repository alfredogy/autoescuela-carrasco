from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0003_alter_factura_curso'),
    ]

    operations = [
        migrations.AddField(
            model_name='alumno',
            name='nombre_pila',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='Nombre'),
        ),
        migrations.AddField(
            model_name='alumno',
            name='apellido1',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='Primer apellido'),
        ),
        migrations.AddField(
            model_name='alumno',
            name='apellido2',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='Segundo apellido'),
        ),
        migrations.AddField(
            model_name='alumno',
            name='causa',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='Causa'),
        ),
        migrations.AddField(
            model_name='alumno',
            name='fecha_alta',
            field=models.DateField(blank=True, null=True, verbose_name='Fecha de alta'),
        ),
        migrations.AddField(
            model_name='alumno',
            name='fecha_apto_teorico',
            field=models.DateField(blank=True, null=True, verbose_name='Fecha apto teórico'),
        ),
        migrations.AddField(
            model_name='alumno',
            name='fecha_fin',
            field=models.DateField(blank=True, null=True, verbose_name='Fecha de fin'),
        ),
        migrations.AddField(
            model_name='alumno',
            name='fecha_inicio',
            field=models.DateField(blank=True, null=True, verbose_name='Fecha de inicio'),
        ),
        migrations.AddField(
            model_name='alumno',
            name='fecha_nacimiento',
            field=models.DateField(blank=True, null=True, verbose_name='Fecha de nacimiento'),
        ),
        migrations.AddField(
            model_name='alumno',
            name='numero_registro',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Nº registro'),
        ),
        migrations.AddField(
            model_name='alumno',
            name='observaciones',
            field=models.TextField(blank=True, default='', verbose_name='Observaciones'),
        ),
        migrations.AddField(
            model_name='alumno',
            name='permiso',
            field=models.CharField(blank=True, choices=[('AM', 'AM'), ('AML', 'AML'), ('A1', 'A1'), ('A2', 'A2'), ('A2 CON B', 'A2 CON B'), ('A', 'A'), ('B', 'B'), ('B96', 'B96'), ('B+E', 'B+E'), ('C', 'C'), ('C1', 'C1'), ('C+E', 'C+E'), ('D', 'D'), ('D1', 'D1')], default='', max_length=20, verbose_name='Permiso'),
        ),
    ]
