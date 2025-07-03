from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from .models import Usuario, Reserva, Asignacion, HistorialTarea
from datetime import date, timedelta, datetime
from django.utils import timezone
from django.core.mail import send_mail

def registro_cliente(request):
    if request.method == 'POST':
        nombre = request.POST['nombre']
        correo = request.POST['correo']
        contraseña = request.POST['contraseña']

        if Usuario.objects.filter(correo=correo).exists():
            messages.error(request, 'Correo ya registrado.')
            return redirect('../registro')

        usuario = Usuario(
            nombre=nombre,
            correo=correo,
            contraseña=make_password(contraseña),
            rol='cliente',
            estado='activo'
        )
        usuario.save()
        messages.success(request, 'Cuenta creada. Ahora puedes iniciar sesión.')
        return redirect('../login')

    return render(request, 'registro.html')

def perfil_cliente(request):
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('usuario_rol')

    if not usuario_id or rol != 'cliente':
        return redirect('../dashboard')

    usuario = get_object_or_404(Usuario, id=usuario_id)

    return render(request, 'perfil_cliente.html', {'usuario': usuario})

def editar_perfil(request, usuario_id):
    usuario = get_object_or_404(Usuario, id=usuario_id)
    origen = request.GET.get('origen') or request.POST.get('origen')

    if request.method == 'POST':
        usuario.nombre = request.POST['nombre']
        usuario.correo = request.POST['correo']
        usuario.save()
        messages.success(request, "Perfil actualizado correctamente.")
        
        if origen == 'gestionar_usuarios':
            return redirect('gestionar_usuarios')
        return redirect('perfil')

    return render(request, 'editar_perfil.html', {
        'usuario': usuario,
        'origen': origen
    })

def desactivar_cuenta(request):
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('usuario_rol')

    if not usuario_id or rol != 'cliente':
        return redirect('../dashboard')

    if request.method == 'POST':
        usuario = get_object_or_404(Usuario, id=usuario_id)
        usuario.estado = 'inactivo'
        usuario.save()
        request.session.flush()
        messages.success(request, "Tu cuenta ha sido desactivada.")
        return redirect('../login')

    return render(request, 'desactivar_cuenta.html')

def inhabilitar_usuario(request, usuario_id):
    if request.session.get('usuario_rol') != 'administrador':
        return redirect('/dashboard/')

    usuario = get_object_or_404(Usuario, id=usuario_id)

    if request.method == 'POST':
        usuario.estado = 'inactivo'
        usuario.save()
        messages.success(request, f"El usuario {usuario.nombre} ha sido inhabilitado.")
        return redirect('/gestionar_usuarios/')

    return render(request, 'confirmar_estado.html', {
        'usuario': usuario,
        'accion': 'inhabilitar'
    })

def habilitar_usuario(request, usuario_id):
    if request.session.get('usuario_rol') != 'administrador':
        return redirect('/dashboard/')

    usuario = get_object_or_404(Usuario, id=usuario_id)

    if request.method == 'POST':
        usuario.estado = 'activo'
        usuario.save()
        messages.success(request, f"El usuario {usuario.nombre} ha sido habilitado.")
        return redirect('/gestionar_usuarios/')

    return render(request, 'confirmar_estado.html', {
        'usuario': usuario,
        'accion': 'habilitar'
    })

def login(request):
    if request.method == 'POST':
        correo = request.POST['correo']
        contraseña = request.POST['contraseña']

        try:
            usuario = Usuario.objects.get(correo=correo)
            if not check_password(contraseña, usuario.contraseña):
                messages.error(request, 'Contraseña incorrecta.')
                return redirect('../login')

            if usuario.estado != 'activo':
                messages.warning(request, 'Tu cuenta se encuentra inactiva. Puedes contactar al administrador para más información.')
                return redirect('../login')

            request.session['usuario_id'] = usuario.id
            request.session['usuario_rol'] = usuario.rol
            request.session['usuario_nombre'] = usuario.nombre
            request.session['usuario_estado'] = usuario.estado
            return redirect('/dashboard/') 

        except Usuario.DoesNotExist:
            messages.error(request, 'Usuario no encontrado.')

    return render(request, 'login.html')

def logout(request):
    request.session.flush()
    return redirect('../login')

def dashboard(request):
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('usuario_rol')
    nombre = request.session.get('usuario_nombre')

    if not usuario_id or not rol:
        return HttpResponseRedirect('/login/')

    contexto = {
        'rol': rol,
        'nombre': nombre,
    }
    return render(request, 'dashboard.html', contexto)

def crear_reserva(request):
    if request.session.get('usuario_rol') != 'cliente':
        return redirect('../dashboard')

    if request.method == 'POST':
        direccion = request.POST['direccion']
        tipo_ubicacion = request.POST['tipo_ubicacion']
        fecha = request.POST['fecha']
        hora = request.POST['hora_reserva']

        usuario = Usuario.objects.get(id=request.session['usuario_id'])

        fecha_reserva = datetime.strptime(fecha, '%Y-%m-%d').date()
        hora_reserva = datetime.strptime(hora, '%H:%M').time()
        inicio_nueva = datetime.combine(fecha_reserva, hora_reserva)
        fin_nueva = inicio_nueva + timedelta(hours=2)

        disponibles = personal_disponible(fecha_reserva, hora_reserva)

        if disponibles:
            reserva = Reserva.objects.create(
                fecha_reserva=fecha_reserva,
                hora_reserva=hora_reserva,
                direccion=direccion,
                tipo_ubicacion=tipo_ubicacion,
                estado='pendiente',
                usuario=usuario
            )

            Asignacion.objects.create(
                fecha_asignacion=date.today(),
                reserva=reserva,
                usuario=disponibles[0]
            )

            reserva.estado = 'asignada'
            reserva.save()
            send_mail(
                'Reserva creada y asignada',
                f'Hola {usuario.nombre}, tu reserva para el {fecha_reserva} a las {hora_reserva} ha sido creada y asignada a {disponibles[0].nombre}.',
                'no-reply@tusitio.com',
                [usuario.correo],
                fail_silently=False,
            )

            messages.success(request, f'Reserva creada y asignada a {disponibles[0].nombre}.')
            return redirect('../reservas')

        if tipo_ubicacion == 'oficina':
            asignaciones = Asignacion.objects.filter(reserva__fecha_reserva=fecha_reserva).select_related('reserva', 'usuario')

            for asign in asignaciones:
                reserva_existente = asign.reserva

                if reserva_existente.tipo_ubicacion != 'residencia':
                    continue
                if reserva_existente.estado == 'completada':
                    continue

                inicio_existente = datetime.combine(reserva_existente.fecha_reserva, reserva_existente.hora_reserva)
                fin_existente = inicio_existente + timedelta(hours=2)

                if inicio_nueva < fin_existente and inicio_existente < fin_nueva:
                    personal_a_reasignar = asign.usuario

                    reserva = Reserva.objects.create(
                        fecha_reserva=fecha_reserva,
                        hora_reserva=hora_reserva,
                        direccion=direccion,
                        tipo_ubicacion=tipo_ubicacion,
                        estado='pendiente',
                        usuario=usuario
                    )

                    asign.delete()
                    reserva_existente.estado = 'pendiente'
                    reserva_existente.save()


                    Asignacion.objects.create(
                        fecha_asignacion=date.today(),
                        reserva=reserva,
                        usuario=personal_a_reasignar
                    )

                    reserva.estado = 'asignada'
                    reserva.save()
                    send_mail(
                        'Reserva de oficina asignada',
                        f'Hola {usuario.nombre}, tu reserva para el {fecha_reserva} a las {hora_reserva} fue asignada a {personal_a_reasignar.nombre}. La reserva anterior fue puesta en espera.',
                        'no-reply@tusitio.com',
                        [usuario.correo],
                        fail_silently=False,
                    )

                    messages.success(request, f'Reserva de oficina asignada a {personal_a_reasignar.nombre}. La residencia fue puesta en espera.')
                    return redirect('../reservas')

        reserva = Reserva.objects.create(
            fecha_reserva=fecha_reserva,
            hora_reserva=hora_reserva,
            direccion=direccion,
            tipo_ubicacion=tipo_ubicacion,
            estado='pendiente',
            usuario=usuario
        )
        send_mail(
            'Reserva creada - pendiente',
            f'Hola {usuario.nombre}, tu reserva para el {fecha_reserva} a las {hora_reserva} ha sido creada pero actualmente no hay personal disponible, por lo que queda pendiente.',
            'no-reply@tusitio.com',
            [usuario.correo],
            fail_silently=False,
        )

        messages.warning(request, 'Reserva creada, pero no hay personal disponible. Queda como pendiente.')
        return redirect('../reservas')

    return render(request, 'crear_reserva.html')

def detalle_reserva(request, reserva_id):
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('usuario_rol')

    reserva = get_object_or_404(Reserva, id=reserva_id)
    origen = request.GET.get('origen')

    if rol == 'cliente' and reserva.usuario.id != usuario_id:
        return redirect('dashboard')

    if rol == 'personal':
        asignado = Asignacion.objects.filter(usuario_id=usuario_id, reserva_id=reserva.id).exists()
        if not asignado and origen != 'horario_reservas':
            return redirect('dashboard')

    if origen == 'horario_reservas':
        volver_url = reverse('horario_reservas')
    else:
        volver_url = reverse('ver_reservas')

    return render(request, 'detalle_reserva.html', {
        'reserva': reserva,
        'volver_url': volver_url
    })

def editar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)

    if request.session.get('usuario_rol') != 'cliente' or reserva.usuario.id != request.session['usuario_id']:
        return redirect('../dashboard')

    if request.method == 'POST':
        direccion = request.POST['direccion']
        tipo_ubicacion = request.POST['tipo_ubicacion']
        fecha = request.POST['fecha']
        hora = request.POST['hora_reserva']

        reserva.direccion = direccion
        reserva.tipo_ubicacion = tipo_ubicacion
        reserva.fecha_reserva = datetime.strptime(fecha, '%Y-%m-%d').date()
        reserva.hora_reserva = datetime.strptime(hora, '%H:%M').time()
        reserva.estado = 'pendiente'  # Resetear estado a pendiente si editan (por si fue asignada)

        reserva.save()

        messages.success(request, 'Reserva actualizada correctamente.')
        return redirect('../../reservas')

    return render(request, 'editar_reserva.html', {'reserva': reserva})

def eliminar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)

    if request.session.get('usuario_rol') != 'cliente' or reserva.usuario.id != request.session['usuario_id']:
        return redirect('../dashboard')

    if request.method == 'POST':
        reserva.delete()
        messages.success(request, 'Reserva eliminada correctamente.')
        return redirect('../../reservas')

    return render(request, 'eliminar_reserva.html', {'reserva': reserva})

from django.db.models import Q

def ver_reservas(request):
    if request.session.get('usuario_rol') != 'cliente':
        return redirect('../dashboard')

    usuario_id = request.session['usuario_id']
    estado = request.GET.get('estado', '')  # filtro estado
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')

    filtros = Q(usuario_id=usuario_id)

    if estado in ['pendiente', 'asignada', 'completada']:
        filtros &= Q(estado=estado)

    if fecha_desde:
        filtros &= Q(fecha_reserva__gte=fecha_desde)

    if fecha_hasta:
        filtros &= Q(fecha_reserva__lte=fecha_hasta)

    reservas = Reserva.objects.filter(filtros).order_by('-fecha_reserva')

    pendientes = reservas.filter(estado__in=['pendiente', 'asignada'])
    completadas = reservas.filter(estado='completada')

    contexto = {
        'pendientes': pendientes,
        'completadas': completadas,
        'filtros': {
            'estado': estado,
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
        }
    }

    return render(request, 'ver_reservas.html', contexto)

def personal_disponible(fecha, hora):
    from datetime import datetime, timedelta

    if isinstance(fecha, str):
        fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
    if isinstance(hora, str):
        hora = datetime.strptime(hora, '%H:%M').time()

    fecha_hora_reserva = datetime.combine(fecha, hora)
    inicio = fecha_hora_reserva - timedelta(hours=2)
    fin = fecha_hora_reserva + timedelta(hours=2)

    personal = Usuario.objects.filter(rol='personal', estado='activo')
    disponibles = []

    for p in personal:
        asignaciones = Asignacion.objects.filter(usuario=p).select_related('reserva')

        conflicto = False
        for a in asignaciones:
            r = a.reserva

            if r.estado == 'completada':
                continue

            dt_r = datetime.combine(r.fecha_reserva, r.hora_reserva)
            inicio_r = dt_r
            fin_r = dt_r + timedelta(hours=2)

            if inicio < fin_r and inicio_r < fin:
                conflicto = True
                break

        if not conflicto:
            disponibles.append(p)

    return disponibles

def asignar_reserva(request, reserva_id):
    if request.session.get('usuario_rol') != 'personal':
        return redirect('../dashboard')

    usuario = Usuario.objects.get(id=request.session['usuario_id'])
    reserva = Reserva.objects.get(id=reserva_id)

    if request.method == 'POST':
        Asignacion.objects.create(
            fecha_asignacion=date.today(),
            reserva=reserva,
            usuario=usuario
        )
        reserva.estado = 'asignada'
        reserva.save()
        return redirect('../../reservas_pendientes')

    return render(request, 'asignar_confirmar.html', {'reserva': reserva})

def mis_asignaciones_pendientes(request):
    if request.session.get('usuario_rol') != 'personal':
        return redirect('../dashboard')

    usuario_id = request.session['usuario_id']
    asignaciones = Asignacion.objects.filter(
        usuario_id=usuario_id
    ).exclude(reserva__estado='completada').select_related('reserva')

    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')

    if fecha_desde:
        asignaciones = asignaciones.filter(reserva__fecha_reserva__gte=fecha_desde)
    if fecha_hasta:
        asignaciones = asignaciones.filter(reserva__fecha_reserva__lte=fecha_hasta)

    context = {
        'asignaciones': asignaciones,
        'filtros': {
            'fecha_desde': fecha_desde or '',
            'fecha_hasta': fecha_hasta or ''
        }
    }
    return render(request, 'mis_asignaciones_pendientes.html', context)

def mis_asignaciones_completadas(request):
    if request.session.get('usuario_rol') != 'personal':
        return redirect('../dashboard')

    usuario_id = request.session['usuario_id']
    asignaciones = Asignacion.objects.filter(
        usuario_id=usuario_id,
        reserva__estado='completada'
    ).select_related('reserva')

    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')

    if fecha_desde:
        asignaciones = asignaciones.filter(reserva__fecha_reserva__gte=fecha_desde)
    if fecha_hasta:
        asignaciones = asignaciones.filter(reserva__fecha_reserva__lte=fecha_hasta)

    context = {
        'asignaciones': asignaciones,
        'filtros': {
            'fecha_desde': fecha_desde or '',
            'fecha_hasta': fecha_hasta or ''
        }
    }
    return render(request, 'mis_asignaciones_completadas.html', context)

def finalizar_tarea(request, asignacion_id):
    if request.session.get('usuario_rol') != 'personal':
        return redirect('../dashboard')

    try:
        asignacion = Asignacion.objects.select_related('reserva', 'usuario').get(
            id=asignacion_id, usuario_id=request.session['usuario_id']
        )
    except Asignacion.DoesNotExist:
        messages.error(request, "Asignación inválida.")
        return redirect('../asignaciones_pendientes')

    if not HistorialTarea.objects.filter(asignacion=asignacion).exists():
        HistorialTarea.objects.create(
            hora_inicio=timezone.now(),
            hora_fin=timezone.now(),
            ubicacion=asignacion.reserva.direccion,
            asignacion=asignacion
        )
        asignacion.reserva.estado = 'completada'
        asignacion.reserva.save()

    return redirect('../../asignaciones_pendientes')

from datetime import datetime

def horario_reservas(request):
    usuario_id = request.session.get('usuario_id')
    rol = request.session.get('usuario_rol')

    if not usuario_id or not rol:
        return redirect('../login')

    filtro_estado = request.GET.get('estado', '')
    filtro_semana_str = request.GET.get('semana', '')
    filtro_personal = request.GET.get('personal', '')

    if filtro_semana_str:
        try:
            filtro_semana_date = datetime.strptime(filtro_semana_str, "%Y-%m-%d").date()
        except ValueError:
            filtro_semana_date = date.today()
    else:
        filtro_semana_date = date.today()

    lunes = filtro_semana_date - timedelta(days=filtro_semana_date.weekday())
    domingo = lunes + timedelta(days=6)

    dias_semana = [
        {'nombre_es': 'Lunes', 'fecha': lunes},
        {'nombre_es': 'Martes', 'fecha': lunes + timedelta(days=1)},
        {'nombre_es': 'Miércoles', 'fecha': lunes + timedelta(days=2)},
        {'nombre_es': 'Jueves', 'fecha': lunes + timedelta(days=3)},
        {'nombre_es': 'Viernes', 'fecha': lunes + timedelta(days=4)},
        {'nombre_es': 'Sábado', 'fecha': lunes + timedelta(days=5)},
        {'nombre_es': 'Domingo', 'fecha': lunes + timedelta(days=6)},
    ]

    lista_personal = []
    if rol == 'administrador':
        from app.models import Usuario  # Ajusta el import si es necesario
        lista_personal = Usuario.objects.filter(rol='personal')

    filtro_reserva_kwargs = {'fecha_reserva__range': (lunes, domingo)}

    if filtro_estado:
        filtro_reserva_kwargs['estado'] = filtro_estado

    if rol == 'cliente':
        filtro_reserva_kwargs['usuario_id'] = usuario_id
        reservas = Reserva.objects.filter(**filtro_reserva_kwargs).select_related('usuario')
    elif rol == 'personal':
        asignaciones = Asignacion.objects.filter(
            usuario_id=usuario_id,
            reserva__fecha_reserva__range=(lunes, domingo)
        ).select_related('reserva', 'reserva__usuario')

        if filtro_estado:
            asignaciones = asignaciones.filter(reserva__estado=filtro_estado)

        reservas = [a.reserva for a in asignaciones if a.reserva.estado != 'completada']
    elif rol == 'administrador':
        reservas = Reserva.objects.filter(**filtro_reserva_kwargs).select_related('usuario')
        if filtro_personal:
            reservas = reservas.filter(asignacion__usuario_id=filtro_personal).distinct()
    else:
        reservas = []

    horas_set = set()
    for r in reservas:
        horas_set.add(r.hora_reserva.strftime("%H:%M"))
    horas = sorted(list(horas_set))

    horario_list = []
    for h in horas:
        fila = {'hora': h, 'reservas_por_dia': []}
        for dia in dias_semana:
            reservas_en_hora = [
                r for r in reservas
                if r.hora_reserva.strftime("%H:%M") == h and r.fecha_reserva == dia['fecha']
                and (not filtro_estado or r.estado == filtro_estado)
            ]
            fila['reservas_por_dia'].append(reservas_en_hora)
        horario_list.append(fila)

    contexto = {
        'dias_semana': dias_semana,
        'horario_list': horario_list,
        'rol': rol,
        'filtro_estado': filtro_estado,
        'filtro_semana': filtro_semana_str,
        'filtro_personal': filtro_personal,
        'lista_personal': lista_personal,
    }
    return render(request, 'horario_reservas.html', contexto)

def asignar_con_prioridad(reserva_nueva):
    fecha = reserva_nueva.fecha_reserva
    hora = reserva_nueva.hora_reserva
    inicio_nueva = datetime.combine(fecha, hora)
    fin_nueva = inicio_nueva + timedelta(hours=2)

    disponibles = personal_disponible(fecha, hora)
    if disponibles:
        Asignacion.objects.create(
            fecha_asignacion=datetime.today(),
            reserva=reserva_nueva,
            usuario=disponibles[0]
        )
        reserva_nueva.estado = 'asignada'
        reserva_nueva.save()
        return True

    if reserva_nueva.tipo_ubicacion == 'oficina':
        asignaciones = Asignacion.objects.filter(reserva__fecha_reserva=fecha).select_related('reserva', 'usuario')

        for asign in asignaciones:
            reserva_existente = asign.reserva

            if reserva_existente.tipo_ubicacion != 'residencia':
                continue

            inicio_existente = datetime.combine(reserva_existente.fecha_reserva, reserva_existente.hora_reserva)
            fin_existente = inicio_existente + timedelta(hours=2)

            if inicio_nueva < fin_existente and inicio_existente < fin_nueva:
                personal_a_reasignar = asign.usuario

                asign.delete()
                reserva_existente.estado = 'pendiente'
                reserva_existente.save()

                Asignacion.objects.create(
                    fecha_asignacion=datetime.today(),
                    reserva=reserva_nueva,
                    usuario=personal_a_reasignar
                )
                reserva_nueva.estado = 'asignada'
                reserva_nueva.save()

                return True

    reserva_nueva.estado = 'espera'
    reserva_nueva.save()
    return False

def reasignar_pendientes(request):
    pendientes = Reserva.objects.filter(estado='pendiente')
    asignadas = 0

    for reserva in pendientes:
        disponibles = personal_disponible(reserva.fecha_reserva, reserva.hora_reserva)
        if disponibles:
            Asignacion.objects.create(
                fecha_asignacion=date.today(),
                reserva=reserva,
                usuario=disponibles[0]
            )
            reserva.estado = 'asignada'
            reserva.save()
            asignadas += 1

    return HttpResponse(f"{asignadas} reserva(s) pendientes fueron asignadas.")

def asignar_manual(request):
    if request.session.get('usuario_rol') != 'administrador':
        return redirect('../dashboard')

    reservas_pendientes = Reserva.objects.filter(estado='pendiente')
    personal_disponible = Usuario.objects.filter(rol='personal', estado='activo')

    if request.method == 'POST':
        reserva_id = int(request.POST.get('reserva_id'))
        personal_id = int(request.POST.get('personal_id'))

        reserva = get_object_or_404(Reserva, id=reserva_id)
        personal = get_object_or_404(Usuario, id=personal_id)

        fecha_hora_reserva = datetime.combine(reserva.fecha_reserva, reserva.hora_reserva)
        inicio = fecha_hora_reserva - timedelta(hours=2)
        fin = fecha_hora_reserva + timedelta(hours=2)

        asignaciones = Asignacion.objects.filter(usuario=personal).select_related('reserva')
        for asignacion in asignaciones:
            otra = asignacion.reserva
            dt_otra = datetime.combine(otra.fecha_reserva, otra.hora_reserva)
            if inicio <= dt_otra <= fin:
                otra.estado = 'pendiente'
                otra.save()
                asignacion.delete()

        Asignacion.objects.create(
            fecha_asignacion=date.today(),
            reserva=reserva,
            usuario=personal
        )
        reserva.estado = 'asignada'
        reserva.save()

        messages.success(request, f'Reserva {reserva.id} asignada a {personal.nombre}. Se reemplazaron conflictos previos si existían.')
        return redirect('../asignar_manual')

    return render(request, 'asignar_manual.html', {
        'reservas': reservas_pendientes,
        'personal': personal_disponible
    })

def gestionar_usuarios(request):
    if request.session.get('usuario_rol') != 'administrador':
        return redirect('../dashboard')

    usuarios = Usuario.objects.all().order_by('rol', 'estado', 'nombre')
    return render(request, 'gestionar_usuarios.html', {'usuarios': usuarios})

def cambiar_contraseña(request, usuario_id=None):
    if usuario_id is None:
        usuario_id = request.session.get('usuario_id')

    if not usuario_id:
        return redirect('login')

    usuario = get_object_or_404(Usuario, id=usuario_id)

    if request.method == 'POST':
        nueva = request.POST.get('nueva')
        confirmar = request.POST.get('confirmar')
        origen = request.POST.get('origen', '')

        if not nueva or not confirmar:
            messages.error(request, "Por favor completa todos los campos.")
            return render(request, 'cambiar_contraseña.html', {'origen': origen})

        if nueva != confirmar:
            messages.error(request, "Las contraseñas no coinciden.")
            return render(request, 'cambiar_contraseña.html', {'origen': origen})

        usuario.contraseña = make_password(nueva)
        usuario.save()
        messages.success(request, "Contraseña actualizada correctamente.")

        if origen == 'gestionar_usuarios':
            return redirect('gestionar_usuarios')
        elif origen == 'perfil':
            return redirect('perfil')
        else:
            return redirect('dashboard')

    else:
        origen = request.GET.get('origen', '')
        return render(request, 'cambiar_contraseña.html', {'origen': origen})