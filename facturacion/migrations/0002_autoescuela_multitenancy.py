from decimal import Decimal
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def crear_autoescuelas_y_asignar(apps, schema_editor):
    Autoescuela = apps.get_model('facturacion', 'Autoescuela')
    Configuracion = apps.get_model('facturacion', 'Configuracion')
    Alumno = apps.get_model('facturacion', 'Alumno')
    Factura = apps.get_model('facturacion', 'Factura')
    ListadoHistorico = apps.get_model('facturacion', 'ListadoHistorico')

    alfafar, _ = Autoescuela.objects.get_or_create(nombre='Alfafar')
    Autoescuela.objects.get_or_create(nombre='Albal')

    Configuracion.objects.filter(autoescuela__isnull=True).update(autoescuela=alfafar)
    Alumno.objects.filter(autoescuela__isnull=True).update(autoescuela=alfafar)
    Factura.objects.filter(autoescuela__isnull=True).update(autoescuela=alfafar)
    ListadoHistorico.objects.filter(autoescuela__isnull=True).update(autoescuela=alfafar)


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Crear modelo Autoescuela
        migrations.CreateModel(
            name='Autoescuela',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, unique=True, verbose_name='Nombre')),
            ],
            options={
                'verbose_name': 'Autoescuela',
                'verbose_name_plural': 'Autoescuelas',
                'ordering': ['nombre'],
            },
        ),

        # 2. Crear modelo PerfilUsuario
        migrations.CreateModel(
            name='PerfilUsuario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('usuario', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='perfil',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('autoescuelas', models.ManyToManyField(
                    blank=True,
                    related_name='usuarios',
                    to='facturacion.autoescuela',
                )),
            ],
            options={
                'verbose_name': 'Perfil de Usuario',
                'verbose_name_plural': 'Perfiles de Usuario',
            },
        ),

        # 3. Añadir FK autoescuela a Configuracion
        migrations.AddField(
            model_name='configuracion',
            name='autoescuela',
            field=models.OneToOneField(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='configuracion',
                to='facturacion.autoescuela',
            ),
        ),

        # 4. Añadir FK autoescuela a Alumno
        migrations.AddField(
            model_name='alumno',
            name='autoescuela',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='alumnos',
                to='facturacion.autoescuela',
            ),
        ),

        # 5. Quitar unique=True de Factura.numero_factura
        migrations.AlterField(
            model_name='factura',
            name='numero_factura',
            field=models.CharField(max_length=20, verbose_name='Nº Factura'),
        ),

        # 6. Añadir FK autoescuela a Factura
        migrations.AddField(
            model_name='factura',
            name='autoescuela',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='facturas',
                to='facturacion.autoescuela',
            ),
        ),

        # 7. Quitar unique_together antiguo de ListadoHistorico
        migrations.AlterUniqueTogether(
            name='listadohistorico',
            unique_together=set(),
        ),

        # 8. Añadir FK autoescuela a ListadoHistorico
        migrations.AddField(
            model_name='listadohistorico',
            name='autoescuela',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='listados_historicos',
                to='facturacion.autoescuela',
            ),
        ),

        # 9. Migración de datos
        migrations.RunPython(crear_autoescuelas_y_asignar, migrations.RunPython.noop),

        # 10. Añadir unique_together a Factura (autoescuela + numero_factura)
        migrations.AlterUniqueTogether(
            name='factura',
            unique_together={('autoescuela', 'numero_factura')},
        ),

        # 11. Añadir nuevo unique_together a ListadoHistorico
        migrations.AlterUniqueTogether(
            name='listadohistorico',
            unique_together={('autoescuela', 'numero_factura', 'trimestre', 'anio')},
        ),
    ]
