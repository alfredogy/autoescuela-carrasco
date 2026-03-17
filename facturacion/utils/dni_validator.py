"""
Validación de DNI/NIE español.
Migrado directamente de revisar_dnis.py.
"""
import re

DNI_LETRAS = "TRWAGMYFPDXBNJZSQVHLCKE"
NIE_PREFIJOS = {'X': '0', 'Y': '1', 'Z': '2'}


def calcular_letra_dni(numero: int) -> str:
    return DNI_LETRAS[numero % 23]


def validar_dni(dni: str) -> dict:
    resultado = {
        'valido': True,
        'tipo': 'DESCONOCIDO',
        'errores': [],
        'sugerencia': None
    }

    if not dni or dni.strip() == '':
        resultado['valido'] = False
        resultado['errores'].append('DNI vacío')
        return resultado

    dni_limpio = dni.upper().strip()
    dni_limpio = dni_limpio.replace(' ', '').replace('-', '').replace('.', '')

    if len(dni_limpio) == 0:
        resultado['valido'] = False
        resultado['errores'].append('DNI vacío')
        return resultado

    primer_caracter = dni_limpio[0]

    if primer_caracter in NIE_PREFIJOS:
        resultado['tipo'] = 'NIE'
        dni_para_calculo = NIE_PREFIJOS[primer_caracter] + dni_limpio[1:]
    elif primer_caracter.isdigit():
        resultado['tipo'] = 'DNI'
        dni_para_calculo = dni_limpio
    else:
        resultado['valido'] = False
        resultado['errores'].append(f'Empieza por letra inválida: {primer_caracter} (solo X, Y, Z para NIE)')
        return resultado

    match = re.match(r'^(\d+)([A-Z])?$', dni_para_calculo)

    if not match:
        resultado['valido'] = False
        resultado['errores'].append('Formato no reconocido')
        return resultado

    numeros = match.group(1)
    letra = match.group(2)

    if len(numeros) < 7:
        resultado['valido'] = False
        resultado['errores'].append(f'Muy pocos dígitos ({len(numeros)}), deberían ser 8')
    elif len(numeros) > 8:
        resultado['valido'] = False
        resultado['errores'].append(f'Demasiados dígitos ({len(numeros)}), deberían ser 8')
    elif len(numeros) == 7:
        resultado['valido'] = False
        resultado['errores'].append(f'Falta 1 dígito ({len(numeros)} en lugar de 8)')
        numeros_sugerido = '0' + numeros
        letra_correcta = calcular_letra_dni(int(numeros_sugerido))
        if resultado['tipo'] == 'NIE':
            resultado['sugerencia'] = f"{primer_caracter}{numeros_sugerido[1:]}{letra_correcta}"
        else:
            resultado['sugerencia'] = f"{numeros_sugerido}{letra_correcta}"

    if letra:
        try:
            numero_int = int(numeros)
            letra_correcta = calcular_letra_dni(numero_int)
            if letra != letra_correcta:
                resultado['valido'] = False
                resultado['errores'].append(f'Letra incorrecta: {letra}, debería ser {letra_correcta}')
                if resultado['tipo'] == 'NIE':
                    resultado['sugerencia'] = f"{primer_caracter}{numeros[1:]}{letra_correcta}"
                else:
                    resultado['sugerencia'] = f"{numeros}{letra_correcta}"
        except ValueError:
            resultado['valido'] = False
            resultado['errores'].append('Números no válidos')
    else:
        resultado['valido'] = False
        resultado['errores'].append('Falta la letra final')
        try:
            numero_int = int(numeros)
            letra_correcta = calcular_letra_dni(numero_int)
            if resultado['tipo'] == 'NIE':
                resultado['sugerencia'] = f"{primer_caracter}{numeros[1:]}{letra_correcta}"
            else:
                resultado['sugerencia'] = f"{numeros}{letra_correcta}"
        except ValueError:
            pass

    return resultado
