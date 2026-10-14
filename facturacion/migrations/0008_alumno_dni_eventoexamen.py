from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('facturacion', '0007_factura_tacografo')]
    operations = [
        migrations.AddField(
            model_name='alumno', name='fecha_caducidad_dni',
            field=models.DateField(blank=True, null=True, verbose_name='Caducidad DNI/NIE'),
        ),
        migrations.CreateModel(
            name='EventoExamen',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('TEORICO', 'Teorico'), ('PRACTICO', 'Practico'), ('RENOVACION', 'Renovacion academica')], max_length=10)),
                ('fecha', models.DateField()),
                ('resultado', models.CharField(blank=True, default='', choices=[('PENDIENTE', 'Pendiente'), ('APROBADO', 'Aprobado'), ('SUSPENDIDO', 'Suspendido')], max_length=10)),
                ('registro', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='eventos', to='facturacion.registroalumno')),
            ],
            options={'ordering': ['fecha', 'pk']},
        ),
        migrations.AddConstraint(
            model_name='eventoexamen',
            constraint=models.CheckConstraint(check=models.Q(tipo='RENOVACION', resultado='') | models.Q(tipo__in=['TEORICO', 'PRACTICO'], resultado__in=['PENDIENTE', 'APROBADO', 'SUSPENDIDO']), name='evento_tipo_resultado_valido'),
        ),
    ]
