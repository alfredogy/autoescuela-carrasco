def autoescuela_context(request):
    if not request.user.is_authenticated:
        return {}
    if request.user.is_superuser:
        return {'es_admin': True, 'autoescuela_activa': None, 'num_autoescuelas': 0}

    autoescuela_id = request.session.get('autoescuela_id')
    autoescuela_activa = None
    num_autoescuelas = 0

    try:
        perfil = request.user.perfil
        num_autoescuelas = perfil.autoescuelas.count()
        if autoescuela_id:
            autoescuela_activa = perfil.autoescuelas.filter(pk=autoescuela_id).first()
    except Exception:
        pass

    return {
        'es_admin': False,
        'autoescuela_activa': autoescuela_activa,
        'num_autoescuelas': num_autoescuelas,
    }
