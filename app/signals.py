from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth.hashers import make_password
from app.models import Usuario

@receiver(post_migrate)
def crear_usuarios_iniciales(sender, **kwargs):
    if sender.name == 'app':
        if not Usuario.objects.filter(correo='juan@empresa.cl').exists():
            Usuario.objects.create(
                nombre='Juan Pérez',
                correo='juan@empresa.cl',
                contraseña=make_password('juan1234'),
                rol='personal',
                estado='activo'
            )
        if not Usuario.objects.filter(correo='nico@empresa.cl').exists():
            Usuario.objects.create(
                nombre='Nico Arauz',
                correo='nico@empresa.cl',
                contraseña=make_password('nico'),
                rol='personal',
                estado='activo'
            )
        if not Usuario.objects.filter(correo='hola@empresa.cl').exists():
            Usuario.objects.create(
                nombre='Hola',
                correo='hola@empresa.cl',
                contraseña=make_password('hola'),
                rol='personal',
                estado='inactivo'
            )
        if not Usuario.objects.filter(correo='admin@empresa.cl').exists():
            Usuario.objects.create(
                nombre='admin',
                correo='admin@empresa.cl',
                contraseña=make_password('admin'),
                rol='administrador',
                estado='activo'
            )
            
