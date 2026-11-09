"""Catálogo de impuestos y retenciones de un producto (Colombia).

Es la única fuente de verdad: lo usan el modelo, el formulario, la pantalla (desplegables y ventana de retenciones) y la
importación/exportación de Excel. Los códigos de tributo son los de la DIAN (los mismos que pide Factus):
01 = IVA, 04 = INC (impuesto nacional al consumo), 05 = ReteIVA, 06 = ReteFuente / ReteRenta.

No se incluyen los impuestos que no son un porcentaje sino un valor fijo por unidad (bolsas plásticas, carbono,
combustibles), porque no se pueden expresar como tarifa.
"""
from collections import namedtuple
from decimal import Decimal

Tax = namedtuple('Tax', 'key label rate code excluded')

DEFAULT_TAX = 'iva_19'
LEGACY_NO_TAX = 'iva_excluido'   # los productos que antes tenían «¿se cobra impuesto?» en No

TAXES = (
    Tax('iva_excluido', '0.00-Excluido(IVA)', Decimal('0.00'), '01', True),
    Tax('iva_exento', '0.00-Exento(IVA)', Decimal('0.00'), '01', False),
    Tax('iva_5', '5.00-Bienes/Servicios(IVA)', Decimal('5.00'), '01', False),
    Tax('iva_19', '19.00-Tarifa General(IVA)', Decimal('19.00'), '01', False),
    Tax('inc_4', '4.00-Impoconsumo telefonía(INC)', Decimal('4.00'), '04', False),
    Tax('inc_8', '8.00-Impoconsumo(INC)', Decimal('8.00'), '04', False),
    Tax('inc_16', '16.00-Impoconsumo vehículos(INC)', Decimal('16.00'), '04', False),
)
TAX_BY_KEY = {t.key: t for t in TAXES}
TAX_CHOICES = tuple((t.key, t.label) for t in TAXES)

RETENTION_TYPES = (('05', '05-ReteIVA'), ('06', '06-ReteRenta'))
RETENTION_RATES = {
    '05': ('15.00', '100.00'),
    '06': ('0.10', '0.50', '1.00', '1.50', '2.00', '2.50', '3.00', '3.50', '4.00', '6.00', '7.00', '10.00', '11.00', '20.00'),
}
RETENTION_NAME = dict(RETENTION_TYPES)
RETENTION_BY_RATE = {rate: code for code, rates in RETENTION_RATES.items() for rate in rates}   # 15 y 100 solo existen en ReteIVA


def tax_info(key):
    """El impuesto de ese código, o None si no existe."""
    return TAX_BY_KEY.get(key)


def is_taxed(key):
    """¿Se cobra impuesto? (tarifa mayor que cero). Excluido y Exento no cobran."""
    tax = TAX_BY_KEY.get(key)
    return bool(tax and tax.rate > 0)


def format_rate(value):
    """'2.5' → '2.50'. Lanza ValueError si no es un número."""
    return f'{Decimal(str(value).replace(",", ".").strip()):.2f}'


def retention_key(code, rate):
    return f'{code}:{rate}'


def normalize_retentions(items):
    """Valida y normaliza una lista de retenciones: ['06:0.50', '05:15.00'] → sin repetidas y con tarifas del catálogo.

    Acepta textos «código:tarifa» o diccionarios {'code': '06', 'rate': '0.5'}. Lanza ValueError si alguna no existe.
    """
    result = []
    for item in items or []:
        if isinstance(item, dict):
            code, rate = str(item.get('code', '')).strip(), item.get('rate', '')
        else:
            code, _, rate = str(item).partition(':')
            code = code.strip()
        try:
            rate = format_rate(rate)
        except Exception:
            raise ValueError(f'La retención «{item}» no es válida.')
        if code not in RETENTION_RATES or rate not in RETENTION_RATES[code]:
            raise ValueError(f'La retención {RETENTION_NAME.get(code, code)} al {rate}% no está disponible.')
        key = retention_key(code, rate)
        if key not in result:
            result.append(key)
    return result


def retention_rates_text(items):
    """'0.50, 1.50': solo las tarifas, separadas por coma (así se muestra en el formulario)."""
    return ', '.join(str(i).partition(':')[2] for i in items or [])


def retention_details(items):
    """Para mostrar: [{'code': '06', 'name': '06-ReteRenta', 'rate': '0.50'}, ...]."""
    out = []
    for i in items or []:
        code, _, rate = str(i).partition(':')
        out.append({'code': code, 'name': RETENTION_NAME.get(code, code), 'rate': rate})
    return out


def parse_retention_rates(text):
    """Excel: '0.50, 1.50' (también con ';' o saltos de línea) → lista normalizada. Cada tarifa sola identifica su retención."""
    import re

    items = []
    for part in re.split(r'[,;\n]+', str(text or '')):
        part = part.strip()
        if not part:
            continue
        if ':' in part or '-' in part[:3]:
            code, _, rate = part.replace('-', ':', 1).partition(':')
            items.append({'code': code.strip(), 'rate': rate})
            continue
        try:
            rate = format_rate(part)
        except Exception:
            raise ValueError(f'La retención «{part}» no es un número válido.')
        code = RETENTION_BY_RATE.get(rate)
        if code is None:
            raise ValueError(f'La retención al {rate}% no está disponible. Use una de la hoja «Listas»: '
                             + ', '.join(sorted(RETENTION_BY_RATE, key=Decimal)) + '.')
        items.append({'code': code, 'rate': rate})
    return normalize_retentions(items)


def catalog_for_js():
    """Datos para los desplegables de la pantalla."""
    return {'types': [{'code': c, 'name': n} for c, n in RETENTION_TYPES], 'rates': {c: list(r) for c, r in RETENTION_RATES.items()}}
