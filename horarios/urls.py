"""
URL configuration for horarios project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect
from app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: redirect('login')),
    ##LOGIN##
    path('login/', views.login, name='login'),
    path('logout/', views.logout),
    ##CLIENTES##
    path('detalle_reserva/<int:reserva_id>/', views.detalle_reserva, name='detalle_reserva'),
    path('editar_reserva/<int:reserva_id>/', views.editar_reserva),
    path('eliminar_reserva/<int:reserva_id>/', views.eliminar_reserva),
    path('registro/', views.registro_cliente),
    path('reservas/', views.ver_reservas, name='ver_reservas'),
    path('crear_reserva/', views.crear_reserva),
    path('perfil/', views.perfil_cliente, name='perfil'),
    path('editar_perfil/', views.editar_perfil),
    path('desactivar_perfil/', views.desactivar_cuenta),
    ##PERSONAL##
    path('asignar_reserva/<int:reserva_id>/', views.asignar_reserva),
    path('asignaciones_pendientes/', views.mis_asignaciones_pendientes),
    path('asignaciones_completadas/', views.mis_asignaciones_completadas),
    path('finalizar_tarea/<int:asignacion_id>/', views.finalizar_tarea),
    ##OTRO##
    path('gestionar_usuarios/', views.gestionar_usuarios, name='gestionar_usuarios'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('horario_reservas/', views.horario_reservas, name='horario_reservas'),
    path('reasignar_pendientes/', views.reasignar_pendientes),
    path('asignar_manual/', views.asignar_manual),
    path('cambiar_contraseña/', views.cambiar_contraseña),
    path('mapa_asignaciones/', views.mapa_asignaciones),
    path('ver_historial/', views.ver_historial, name='ver_historial'),

    path('editar_perfil/<int:usuario_id>/', views.editar_perfil, name='editar_usuario'),
    path('inhabilitar_usuario/<int:usuario_id>/', views.inhabilitar_usuario, name='inhabilitar_usuario'),
    path('habilitar_usuario/<int:usuario_id>/', views.habilitar_usuario, name='habilitar_usuario'),
    path('cambiar_contraseña/<int:usuario_id>/', views.cambiar_contraseña, name='cambiar_contraseña_admin'),
    path('terminos/', views.terminos_condiciones, name='terminos'),
]
