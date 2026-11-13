from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('facturacion', '0010_ficha_formacion_practica')]

    operations = [
        migrations.AlterField(
            model_name='fichaformacionteorica',
            name='profesor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='fichas_teorica', to='facturacion.profesorteorica'),
        ),
        migrations.AlterField(
            model_name='fichaformacionpractica',
            name='profesor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='fichas_practica', to='facturacion.profesorteorica'),
        ),
    ]
