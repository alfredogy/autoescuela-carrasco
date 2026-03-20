from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from facturacion.models import Autoescuela


class Command(BaseCommand):
    help = 'Crea el superusuario admin y las dos sedes si no existen'

    def handle(self, *args, **options):
        # Crear sedes
        alfafar, created = Autoescuela.objects.get_or_create(nombre='Alfafar')
        if created:
            self.stdout.write(self.style.SUCCESS('Sede "Alfafar" creada'))
        else:
            self.stdout.write('Sede "Alfafar" ya existe')

        albal, created = Autoescuela.objects.get_or_create(nombre='Albal')
        if created:
            self.stdout.write(self.style.SUCCESS('Sede "Albal" creada'))
        else:
            self.stdout.write('Sede "Albal" ya existe')

        # Crear superusuario admin
        if User.objects.filter(username='admin').exists():
            self.stdout.write('El usuario "admin" ya existe')
        else:
            user = User(username='admin', is_staff=True, is_superuser=True)
            user.set_password('password')
            user.save()
            self.stdout.write(self.style.SUCCESS('Superusuario "admin" creado (contraseña: password)'))
