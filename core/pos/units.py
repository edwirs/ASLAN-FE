"""Unidades de medida de los productos: lista estándar para el selector del formulario.

Se guardan por su nombre (``Product.unit_name``), así que no hay tablas nuevas y los productos que ya
tenían un nombre libre (p. ej. "Titi" en un producto con variantes) siguen funcionando: su valor se
agrega como opción "Personalizada" al editar y se puede crear otra con "Otra…".
"""
DEFAULT_UNIT = 'Unidad'
OTHER = '__other__'

UNIT_GROUPS = (
    ('Conteo y empaques', (
        'Unidad', 'Docena', 'Par', 'Paquete', 'Caja', 'Bulto', 'Bolsa', 'Botella', 'Lata', 'Frasco', 'Sobre',
        'Tarro', 'Porción', 'Plato',
    )),
    ('Peso', ('Gramo', 'Libra', 'Kilo', 'Arroba', 'Tonelada')),
    ('Volumen', ('Mililitro', 'Litro', 'Galón')),
    ('Longitud', ('Centímetro', 'Metro')),
)

STANDARD_UNITS = tuple(unit for _, units in UNIT_GROUPS for unit in units)

# Unidades que normalmente se venden en fracciones (0,295 kg): al elegirlas, el formulario del producto
# activa solo "¿Permite cantidades decimales?". Gramo, mililitro y centímetro quedan fuera porque ya son
# la unidad más pequeña y se venden en cantidades enteras.
DECIMAL_UNITS = ('Kilo', 'Libra', 'Arroba', 'Tonelada', 'Litro', 'Galón', 'Metro')


def canonical_unit(value, known=()):
    """Normaliza lo escrito y lo alinea con una unidad ya existente (sin importar mayúsculas)."""
    value = ' '.join((value or '').split())
    if not value:
        return ''
    for unit in tuple(STANDARD_UNITS) + tuple(known):
        if unit.lower() == value.lower():
            return unit
    return value[:1].upper() + value[1:]


def unit_choices(current='', custom=()):
    """Opciones agrupadas para el <select>: estándar + personalizadas ya usadas + "Otra…"."""
    extras = sorted({u for u in list(custom) + ([current] if current else []) if u and u not in STANDARD_UNITS},
                    key=str.lower)
    groups = [(label, [(u, u) for u in units]) for label, units in UNIT_GROUPS]
    if extras:
        groups.append(('Personalizadas', [(u, u) for u in extras]))
    groups.append(('', [(OTHER, 'Otra… (escribir)')]))
    return groups
