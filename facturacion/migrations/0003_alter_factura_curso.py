from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0002_autoescuela_multitenancy'),
    ]

    operations = [
        migrations.AlterField(
            model_name='factura',
            name='curso',
            field=models.CharField(
                choices=[
                    ('AM', 'AM'),
                    ('A1', 'A1'),
                    ('A2', 'A2'),
                    ('A', 'A'),
                    ('B', 'B'),
                    ('B96', 'B96'),
                    ('B+E', 'B+E'),
                    ('C', 'C'),
                    ('C1', 'C1'),
                    ('C+E', 'C+E'),
                    ('D1', 'D1'),
                ],
                default='B',
                max_length=5,
                verbose_name='Curso',
            ),
        ),
    ]
