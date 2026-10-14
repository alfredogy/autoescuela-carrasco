from calendar import monthrange
from datetime import date


def sumar_meses(fecha, meses):
    mes = fecha.year * 12 + fecha.month - 1 + meses
    anio, mes = divmod(mes, 12)
    return date(anio, mes + 1, min(fecha.day, monthrange(anio, mes + 1)[1]))


def estado_registro(registro, hoy):
    """Replay dated history; renewals reset failures, never contract or theory dates."""
    alertas, periodos = [], []
    if registro.fecha_fin:
        return alertas, periodos
    eventos = sorted((e for e in registro.eventos.all() if e.fecha <= hoy), key=lambda e: (e.fecha, e.pk))
    if any(e.tipo == 'PRACTICO' and e.resultado == 'APROBADO' for e in eventos):
        return alertas, periodos
    suspensos = 0
    ultimo_suspenso = None
    aprobados = [e for e in eventos if e.tipo == 'TEORICO' and e.resultado == 'APROBADO']
    aprobado = aprobados[-1].fecha if aprobados else registro.fecha_apto_teorico
    if aprobado and aprobado > hoy:
        aprobado = None
    clave_aprobado = (aprobado, aprobados[-1].pk if aprobados else 0) if aprobado else None
    for evento in eventos:
        if evento.tipo == 'RENOVACION':
            suspensos = 0
            ultimo_suspenso = None
        elif evento.resultado == 'SUSPENDIDO':
            suspensos += 1
            ultimo_suspenso = evento.fecha

    def fila(tipo, etiqueta, color, inicio, aviso, limite):
        return {'registro': registro, 'alumno': registro.alumno, 'tipo': tipo, 'etiqueta': etiqueta,
                'color': color, 'inicio': inicio, 'aviso': aviso, 'limite': limite,
                'dias': (limite - hoy).days, 'vencido': hoy >= limite}

    alta = registro.fecha_alta
    if alta and hoy >= sumar_meses(alta, 11):
        rojo = hoy >= sumar_meses(alta, 23)
        alertas.append(fila('contrato', 'Contrato: aviso de 24 meses' if rojo else 'Contrato: aviso de 12 meses',
                            'red' if rojo else 'yellow', alta, sumar_meses(alta, 23 if rojo else 11),
                            sumar_meses(alta, 24 if rojo else 12)))
    fallos_teoricos = [e for e in eventos if e.tipo == 'TEORICO' and e.resultado == 'SUSPENDIDO'
                      and (clave_aprobado is None or (e.fecha, e.pk) > clave_aprobado)]
    if fallos_teoricos:
        inicio = fallos_teoricos[0].fecha
        periodo = fila('teoria_pendiente', 'Teorico pendiente: plazo de seis meses', 'orange',
                       inicio, sumar_meses(inicio, 5), sumar_meses(inicio, 6))
        periodos.append(periodo)
        if hoy >= periodo['aviso']:
            alertas.append(periodo)
    if aprobado:
        periodo = fila('teoria_aprobada', 'Teorico aprobado: plazo de 24 meses para practico', 'pink',
                       aprobado, sumar_meses(aprobado, 20), sumar_meses(aprobado, 24))
        periodos.append(periodo)
        if hoy >= periodo['aviso']:
            alertas.append(periodo)
    if suspensos >= 2:
        alerta = fila('renovacion', 'Renovacion academica: dos o mas suspensos', 'orange',
                      ultimo_suspenso, ultimo_suspenso, ultimo_suspenso)
        alerta['suspensos'] = suspensos
        alerta['vencido'] = False
        alertas.append(alerta)
    return alertas, periodos


def calcular_alertas(autoescuela, hoy):
    from ..models import Alumno, RegistroAlumno
    alertas, periodos = [], []
    registros = RegistroAlumno.objects.filter(
        autoescuela=autoescuela, alumno__autoescuela=autoescuela, fecha_fin__isnull=True,
    ).select_related('alumno').prefetch_related('eventos')
    for registro in registros:
        avisos, plazos = estado_registro(registro, hoy)
        alertas.extend(avisos)
        periodos.extend(plazos)
    for alumno in Alumno.objects.filter(autoescuela=autoescuela, fecha_caducidad_dni__lte=hoy):
        alertas.append({'alumno': alumno, 'tipo': 'dni', 'etiqueta': 'DNI/NIE caducado', 'color': 'purple',
                        'inicio': alumno.fecha_caducidad_dni, 'aviso': alumno.fecha_caducidad_dni,
                        'limite': alumno.fecha_caducidad_dni, 'dias': (alumno.fecha_caducidad_dni - hoy).days,
                        'vencido': True})
    periodos.sort(key=lambda p: (p['limite'], p['registro'].pk, p['tipo']))
    return alertas, periodos
