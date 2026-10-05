"""Presentaciones de producto: validación y sincronización desde el formulario."""
import json
from decimal import Decimal, InvalidOperation

from core.pos.models import Product, ProductPresentation


def _decimal(value, field):
    try:
        return Decimal(str(value).replace(',', '.').strip() or '0')
    except InvalidOperation:
        raise ValueError(f'{field}: valor numérico inválido.')


def parse_presentations(raw, product=None, mode=Product.MODE_CONVERSION):
    """Convierte el JSON del formulario en filas limpias; lanza ``ValueError`` si algo no es válido.

    En modo variantes cada fila lleva su propio stock y el factor es siempre 1.
    """
    variants = mode == Product.MODE_VARIANTS
    try:
        rows = json.loads(raw or '[]')
    except ValueError:
        raise ValueError('Las presentaciones llegaron en un formato inválido.')

    clean, names, barcodes = [], set(), set()
    base_barcode = (product.barcode or '').strip() if product is not None else ''
    for number, row in enumerate(rows, start=1):
        name = (row.get('name') or '').strip()
        label = f'Presentación {number}' + (f' ({name})' if name else '')
        if not name:
            raise ValueError(f'{label}: ingrese el nombre.')
        if name.lower() in names:
            raise ValueError(f'{label}: el nombre está repetido.')
        names.add(name.lower())

        if variants:
            factor = Decimal(1)
            stock = _decimal(row.get('stock') or '0', label)
            if stock < 0:
                raise ValueError(f'{label}: el stock no puede ser negativo.')
        else:
            factor = _decimal(row.get('factor'), label)
            if factor <= 0:
                raise ValueError(f'{label}: las unidades que contiene deben ser mayores a 0.')
            stock = None
        pvp = _decimal(row.get('pvp'), label)
        if pvp <= 0:
            raise ValueError(f'{label}: el precio de venta debe ser mayor a 0.')
        price = _decimal(row.get('price'), label)
        if price < 0:
            raise ValueError(f'{label}: el precio de compra no puede ser negativo.')

        barcode = (row.get('barcode') or '').strip() or None
        if barcode:
            if barcode in barcodes or barcode == base_barcode:
                raise ValueError(f'{label}: el código de barras está repetido en este producto.')
            barcodes.add(barcode)
            others = ProductPresentation.objects.filter(barcode=barcode)
            if row.get('id'):
                others = others.exclude(pk=row['id'])
            if others.exists() or Product.objects.filter(barcode=barcode).exclude(pk=getattr(product, 'pk', None)).exists():
                raise ValueError(f'{label}: el código de barras {barcode} ya pertenece a otro producto o presentación.')

        clean.append({
            'id': row.get('id') or None, 'name': name, 'factor': factor, 'pvp': pvp, 'price': price,
            'barcode': barcode, 'is_active': bool(row.get('is_active', True)), 'stock': stock,
        })
    return clean


def sync_presentations(product, rows):
    """Deja las presentaciones del producto iguales a ``rows`` (crea, actualiza y elimina)."""
    existing = {p.pk: p for p in product.presentations.all()}
    keep = set()
    for row in rows:
        fields = {k: row[k] for k in ('name', 'factor', 'pvp', 'price', 'barcode', 'is_active')}
        obj = existing.get(row['id'])
        if obj is None:
            obj = ProductPresentation(product=product)
        for key, value in fields.items():
            setattr(obj, key, value)
        # En conversión el stock propio no se usa: se conserva el que tuviera (por si se cambia de modo).
        if row.get('stock') is not None:
            obj.stock = row['stock']
        obj.save()
        keep.add(obj.pk)
    # Las ventas ya hechas conservan su nombre y factor copiados (la FK queda en NULL).
    product.presentations.exclude(pk__in=keep).delete()


def barcode_in_use(barcode, exclude_product=None):
    """¿Ese código de barras ya es de una presentación de otro producto?"""
    if not barcode:
        return False
    qs = ProductPresentation.objects.filter(barcode=barcode)
    if exclude_product is not None:
        qs = qs.exclude(product=exclude_product)
    return qs.exists()
