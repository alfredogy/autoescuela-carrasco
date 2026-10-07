from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('facturacion', '0006_registroalumno')]

    operations = [
        migrations.AlterField(
            model_name='factura', name='curso',
            field=models.CharField(
                choices=[('AM', 'AM'), ('A1', 'A1'), ('A2', 'A2'), ('A', 'A'),
                         ('B', 'B'), ('B96', 'B96'), ('B+E', 'B+E'), ('C', 'C'),
                         ('C1', 'C1'), ('C+E', 'C+E'), ('D1', 'D1'), ('TACOGRAFO', 'TACÓGRAFO')],
                default='B', max_length=10, verbose_name='Curso',
            ),
        ),
        migrations.AddField(
            model_name='factura', name='tasa_tacografo',
            field=models.DecimalField(default=Decimal('0'), max_digits=10, decimal_places=2,
                                      verbose_name='Tasa tacógrafo'),
        ),
    ]
