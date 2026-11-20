from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('facturacion', '0011_profesor_fichas_opcional')]

    operations = [
        migrations.AddField(
            model_name='alumno',
            name='telefono',
            field=models.CharField(blank=True, default='', max_length=30, verbose_name='Teléfono'),
        ),
        migrations.AddField(
            model_name='alumno',
            name='correo_electronico',
            field=models.EmailField(blank=True, default='', max_length=254, verbose_name='Correo electrónico'),
        ),
    ]
