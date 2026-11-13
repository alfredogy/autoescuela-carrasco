from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('facturacion', '0009_ficha_formacion_teorica')]

    operations = [
        migrations.CreateModel(
            name='FichaFormacionPractica',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('DESTREZA', 'Destreza'), ('CIRCULACION', 'Circulación')], default='CIRCULACION', max_length=20, verbose_name='Tipo de formación')),
                ('observaciones', models.TextField(blank=True, default='', verbose_name='Observaciones')),
                ('profesor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='fichas_practica', to='facturacion.profesorteorica')),
                ('registro', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='ficha_practica', to='facturacion.registroalumno')),
            ],
        ),
        migrations.CreateModel(
            name='ClasePractica',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField(verbose_name='Fecha')),
                ('hora', models.TimeField(blank=True, null=True, verbose_name='Hora')),
                ('ejercicio', models.CharField(blank=True, default='', max_length=200, verbose_name='Ejercicio')),
                ('km_inicial', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='KM inicial')),
                ('km_final', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='KM final')),
                ('observaciones', models.CharField(blank=True, default='', max_length=300, verbose_name='Observaciones')),
                ('ficha', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='clases', to='facturacion.fichaformacionpractica')),
            ],
            options={'ordering': ['fecha', 'hora', 'pk']},
        ),
    ]
