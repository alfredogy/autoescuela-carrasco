from django.db import migrations, models
import django.db.models.deletion


def crear_registros_iniciales(apps, schema_editor):
    Alumno = apps.get_model('facturacion', 'Alumno')
    RegistroAlumno = apps.get_model('facturacion', 'RegistroAlumno')

    for alumno in Alumno.objects.exclude(autoescuela__isnull=True):
        tiene_datos = any([
            alumno.permiso, alumno.numero_registro, alumno.fecha_alta,
            alumno.fecha_inicio, alumno.fecha_fin, alumno.causa,
            alumno.observaciones, alumno.fecha_apto_teorico,
            alumno.estado_apto_teorico,
        ])
        if tiene_datos:
            RegistroAlumno.objects.create(
                autoescuela_id=alumno.autoescuela_id,
                alumno_id=alumno.pk,
                permiso=alumno.permiso or 'B',
                numero_registro=alumno.numero_registro,
                fecha_alta=alumno.fecha_alta,
                fecha_inicio=alumno.fecha_inicio,
                fecha_fin=alumno.fecha_fin,
                causa=alumno.causa,
                observaciones=alumno.observaciones,
                fecha_apto_teorico=alumno.fecha_apto_teorico,
                estado_apto_teorico=alumno.estado_apto_teorico,
            )


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0005_alumno_estado_apto_teorico'),
    ]

    operations = [
        migrations.CreateModel(
            name='RegistroAlumno',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('permiso', models.CharField(choices=[('AM', 'AM'), ('AML', 'AML'), ('A1', 'A1'), ('A2', 'A2'), ('A2 CON B', 'A2 CON B'), ('A', 'A'), ('B', 'B'), ('B96', 'B96'), ('B+E', 'B+E'), ('C', 'C'), ('C1', 'C1'), ('C+E', 'C+E'), ('D', 'D'), ('D1', 'D1')], max_length=20, verbose_name='Permiso')),
                ('numero_registro', models.PositiveIntegerField(blank=True, null=True, verbose_name='Nº registro')),
                ('fecha_alta', models.DateField(blank=True, null=True, verbose_name='Fecha de alta')),
                ('fecha_inicio', models.DateField(blank=True, null=True, verbose_name='Fecha de inicio')),
                ('fecha_fin', models.DateField(blank=True, null=True, verbose_name='Fecha de fin')),
                ('causa', models.CharField(blank=True, default='', max_length=200, verbose_name='Causa')),
                ('observaciones', models.TextField(blank=True, default='', verbose_name='Observaciones')),
                ('fecha_apto_teorico', models.DateField(blank=True, null=True, verbose_name='Fecha apto teórico')),
                ('estado_apto_teorico', models.CharField(blank=True, default='', max_length=50, verbose_name='Estado apto teórico')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('alumno', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='registros', to='facturacion.alumno')),
                ('autoescuela', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='registros_alumnos', to='facturacion.autoescuela')),
            ],
            options={'verbose_name': 'Registro de Alumno', 'verbose_name_plural': 'Registros de Alumnos', 'ordering': ['-fecha_alta', '-pk']},
        ),
        migrations.RunPython(crear_registros_iniciales, migrations.RunPython.noop),
    ]
