from django.db import models

# Create your models here.
class Usuario(models.Model):
    nombre = models.CharField(max_length=60)
    correo = models.EmailField(unique=True)
    contraseña = models.CharField(max_length=100)
    rol = models.CharField(max_length=20)
    estado = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.nombre} ({self.rol})"

class Reserva(models.Model):
    TIPO_UBICACION_CHOICES = [
        ('oficina', 'Oficina'),
        ('residencia', 'Residencia'),
    ]
    fecha_reserva = models.DateField()
    hora_reserva = models.TimeField(default="08:00")
    direccion = models.CharField(max_length=100)
    tipo_ubicacion = models.CharField(
        max_length=20,
        choices=TIPO_UBICACION_CHOICES,
        default='residencia'
    )
    estado = models.CharField(max_length=10)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)

    def __str__(self):
        return f"Reserva {self.id} - {self.usuario.nombre}"

class Asignacion(models.Model):
    fecha_asignacion = models.DateField()
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)

    def __str__(self):
        return f"Asignación {self.id} - {self.usuario.nombre}"


class HistorialTarea(models.Model):
    hora_inicio = models.DateTimeField()
    hora_fin = models.DateTimeField()
    ubicacion = models.CharField(max_length=200)
    asignacion = models.ForeignKey(Asignacion, on_delete=models.CASCADE)

    def __str__(self):
        return f"Tarea en {self.ubicacion} - {self.hora_inicio.strftime('%Y-%m-%d %H:%M')}"