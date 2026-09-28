from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0004_alumno_registro_inspeccion'),
    ]

    operations = [
        migrations.AddField(
            model_name='alumno',
            name='estado_apto_teorico',
            field=models.CharField(blank=True, default='', max_length=50, verbose_name='Estado apto teórico'),
        ),
    ]
