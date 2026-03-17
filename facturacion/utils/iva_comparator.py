from django.db.models import Sum
from decimal import Decimal


def comparar_iva_trimestre(trimestre, anio, autoescuela):
    from facturacion.models import Factura, ListadoHistorico

    correcto = Factura.objects.filter(trimestre=trimestre, anio=anio, autoescuela=autoescuela).aggregate(
        base_total=Sum('base_imponible'),
        iva_total=Sum('iva'),
        tasas_total=Sum('tasas'),
        total_total=Sum('total'),
    )
    correcto['num_facturas'] = Factura.objects.filter(trimestre=trimestre, anio=anio, autoescuela=autoescuela).count()

    incorrecto = ListadoHistorico.objects.filter(trimestre=trimestre, anio=anio, autoescuela=autoescuela).aggregate(
        neto_total=Sum('neto'),
        iva_total=Sum('iva_incorrecto'),
        total_total=Sum('total'),
    )
    incorrecto['num_facturas'] = ListadoHistorico.objects.filter(trimestre=trimestre, anio=anio, autoescuela=autoescuela).count()

    iva_correcto = correcto['iva_total'] or Decimal('0')
    iva_incorrecto = incorrecto['iva_total'] or Decimal('0')

    return {
        'trimestre': trimestre,
        'correcto': {
            'base': correcto['base_total'] or Decimal('0'),
            'iva': iva_correcto,
            'tasas': correcto['tasas_total'] or Decimal('0'),
            'total': correcto['total_total'] or Decimal('0'),
            'num_facturas': correcto['num_facturas'],
        },
        'incorrecto': {
            'neto': incorrecto['neto_total'] or Decimal('0'),
            'iva': iva_incorrecto,
            'total': incorrecto['total_total'] or Decimal('0'),
            'num_facturas': incorrecto['num_facturas'],
        },
        'diferencia_iva': iva_incorrecto - iva_correcto,
    }


def comparar_iva_anual(anio, autoescuela):
    resultados = []
    for tri in range(1, 5):
        resultados.append(comparar_iva_trimestre(tri, anio, autoescuela))

    total_iva_correcto = sum(r['correcto']['iva'] for r in resultados)
    total_iva_incorrecto = sum(r['incorrecto']['iva'] for r in resultados)
    total_tasas = sum(r['correcto']['tasas'] for r in resultados)

    return {
        'resultados': resultados,
        'total_iva_correcto': total_iva_correcto,
        'total_iva_incorrecto': total_iva_incorrecto,
        'total_tasas': total_tasas,
        'diferencia_total': total_iva_incorrecto - total_iva_correcto,
        'porcentaje_exceso': (
            ((total_iva_incorrecto / total_iva_correcto) - 1) * 100
            if total_iva_correcto > 0 else Decimal('0')
        ),
    }
