from decimal import Decimal, ROUND_HALF_UP


def compute_components(total_paid, tasa_basica_qty, tasa_a_qty, traslado_qty, renovaciones_qty, curso='B', config=None):
    if config is None:
        from facturacion.models import Configuracion
        config = Configuracion.objects.first()

    tb = Decimal(str(config.tasa_basica))
    ta = Decimal(str(config.tasa_a))
    tr = Decimal(str(config.traslado))
    rn = Decimal(str(config.renovacion))
    iva_rate = Decimal(str(config.iva_rate))

    sum_tasas = (
        Decimal(str(tasa_basica_qty)) * tb +
        Decimal(str(tasa_a_qty)) * ta +
        Decimal(str(traslado_qty)) * tr +
        Decimal(str(renovaciones_qty)) * rn
    ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    total_paid = Decimal(str(total_paid))
    importe_after = (total_paid - sum_tasas).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    if importe_after <= 0:
        base = Decimal('0.00')
        iva = Decimal('0.00')
    else:
        if curso in ('C', 'C+E'):
            base = importe_after
            iva = Decimal('0.00')
        else:
            base = (importe_after / (1 + iva_rate)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            iva = (base * iva_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    total = base + iva + sum_tasas
    return base, iva, sum_tasas, total


def next_invoice_number(anio, autoescuela):
    """Genera el siguiente número de factura para el año y autoescuela dados."""
    from facturacion.models import Factura

    facturas = Factura.objects.filter(anio=anio, autoescuela=autoescuela)
    max_n = 0
    for f in facturas.values_list('numero_factura', flat=True):
        if '/' in f:
            parts = f.split('/')
            if len(parts) == 2 and parts[1].isdigit():
                n = int(parts[1])
                if n > max_n:
                    max_n = n
    return max_n + 1


def find_missing_invoices(anio, autoescuela):
    """Encuentra los números de factura faltantes en la secuencia."""
    from facturacion.models import Factura

    numeros = []
    for nf in Factura.objects.filter(anio=anio, autoescuela=autoescuela).values_list('numero_factura', flat=True):
        if '/' in nf:
            parts = nf.split('/')
            if len(parts) == 2 and parts[1].isdigit():
                numeros.append(int(parts[1]))

    if not numeros:
        return []

    numeros = sorted(set(numeros))
    all_numbers = set(range(numeros[0], numeros[-1] + 1))
    return sorted(all_numbers - set(numeros))
