from django.db import migrations, models
import django.db.models.deletion


def seed_alfafar_theoretical_data(apps, schema_editor):
    Autoescuela = apps.get_model('facturacion', 'Autoescuela')
    ConfiguracionTeorica = apps.get_model('facturacion', 'ConfiguracionTeorica')
    ProfesorTeorica = apps.get_model('facturacion', 'ProfesorTeorica')
    alfafar = Autoescuela.objects.filter(nombre='Alfafar').first()
    if not alfafar:
        return
    ConfiguracionTeorica.objects.update_or_create(autoescuela=alfafar, defaults={
        'numero': 'V1086-02', 'seccion': '2', 'digito_control': '9',
        'denominacion': 'DAKASA AUTOESCUELA S.L.', 'direccion': 'AV. ALBUFERA, 18 PBJ',
        'codigo_postal': '46910', 'poblacion': 'Alfafar',
    })
    for nombre, dni in [('AINOA ALAPONT CARRASCO', '53880414Q'), ('ANTONIO GARCIA MUÑOZ', '22574957C')]:
        ProfesorTeorica.objects.get_or_create(autoescuela=alfafar, dni=dni, defaults={'nombre': nombre})


class Migration(migrations.Migration):
    dependencies = [('facturacion', '0008_alumno_dni_eventoexamen')]

    operations = [
        migrations.CreateModel(
            name='ConfiguracionTeorica',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero', models.CharField(blank=True, default='', max_length=20, verbose_name='Número')),
                ('seccion', models.CharField(blank=True, default='', max_length=20, verbose_name='Sección')),
                ('digito_control', models.CharField(blank=True, default='', max_length=20, verbose_name='Dígito de control')),
                ('denominacion', models.CharField(blank=True, default='', max_length=200, verbose_name='Denominación')),
                ('direccion', models.CharField(blank=True, default='', max_length=300, verbose_name='Dirección')),
                ('codigo_postal', models.CharField(blank=True, default='', max_length=10, verbose_name='Código postal')),
                ('poblacion', models.CharField(blank=True, default='', max_length=100, verbose_name='Población')),
                ('autoescuela', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='configuracion_teorica', to='facturacion.autoescuela')),
            ],
        ),
        migrations.CreateModel(
            name='ProfesorTeorica',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=200, verbose_name='Nombre y apellidos')),
                ('dni', models.CharField(max_length=20, verbose_name='DNI/NIE')),
                ('autoescuela', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='profesores_teorica', to='facturacion.autoescuela')),
            ],
            options={'ordering': ['nombre']},
        ),
        migrations.CreateModel(
            name='FichaFormacionTeorica',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_inicio', models.DateField(blank=True, null=True, verbose_name='Fecha de inicio')),
                ('fecha_fin', models.DateField(blank=True, null=True, verbose_name='Fecha de finalización')),
                ('faltas_asistencia', models.PositiveIntegerField(default=0, verbose_name='Faltas de asistencia')),
                ('observaciones', models.TextField(blank=True, default='', verbose_name='Observaciones')),
                ('profesor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='fichas_teorica', to='facturacion.profesorteorica')),
                ('registro', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='ficha_teorica', to='facturacion.registroalumno')),
            ],
        ),
        migrations.AddConstraint(
            model_name='profesorteorica',
            constraint=models.UniqueConstraint(fields=('autoescuela', 'dni'), name='profesor_teorica_dni_por_sede'),
        ),
        migrations.RunPython(seed_alfafar_theoretical_data, migrations.RunPython.noop),
    ]
