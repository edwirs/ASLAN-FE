"""Líneas de venta/pedido con presentaciones: resolución de precio, factor y stock, y descuento del inventario.

Compartido por la venta rápida (barra) y los pedidos de mesa.

El stock se descuenta del "holder" de cada línea: el producto (conversión de unidades, donde todas sus
presentaciones comparten stock) o la propia presentación (modo variantes, stock por tamaño).
"""
from decimal import Decimal, InvalidOperation

from core.pos.models import Product, ProductAutoAdd, ProductPresentation


QTY_STEP = Decimal('0.001')


def parse_quantity(raw, product):
    """Cantidad vendida como Decimal de hasta 3 decimales.

    Solo los productos marcados "¿Permite cantidades decimales?" admiten fracciones (0,295 kg);
    los demás se venden en unidades enteras. Lanza ``Exception`` con un mensaje claro si no es válida.
    """
    try:
        qty = Decimal(str(raw).replace(',', '.').strip())
    except (InvalidOperation, ValueError):
        raise Exception(f"Cantidad inválida para '{product.name}'.")
    rounded = qty.quantize(QTY_STEP)
    # tolera el ruido de coma flotante del navegador (0.30000000000000004), pero no más de 3 decimales reales
    if abs(qty - rounded) > Decimal('0.0000001'):
        raise Exception(f"La cantidad de '{product.name}' admite máximo 3 decimales.")
    if rounded <= 0:
        raise Exception(f"La cantidad de '{product.name}' debe ser mayor a cero.")
    if rounded != rounded.to_integral_value() and not product.allow_decimals:
        raise Exception(f"'{product.name}' no permite cantidades decimales. Actívelo en el producto "
                        f"(\"¿Permite cantidades decimales?\") o venda unidades enteras.")
    if rounded >= Decimal('1000000'):
        raise Exception(f"La cantidad de '{product.name}' es demasiado grande.")
    return rounded


def parse_price(raw, product):
    """Precio de venta escrito por el cajero: Decimal >= 0 con máximo 2 decimales."""
    try:
        price = Decimal(str(raw).replace(',', '.').strip())
    except (InvalidOperation, ValueError):
        raise Exception(f"Precio inválido para '{product.name}'.")
    if not price.is_finite() or price < 0 or price >= Decimal('10000000'):
        raise Exception(f"El precio de '{product.name}' debe estar entre 0 y 9.999.999.")
    return price.quantize(Decimal('0.01'))


def resolve_lines(raw_lines, snapshot=False, allow_price_override=False):
    """Valida un carrito contra la BD y devuelve las líneas listas para guardar.

    ``snapshot=False``: carrito del navegador; el precio y el factor SIEMPRE salen del catálogo, salvo que
    ``allow_price_override`` (usuario con permiso de editar precios) y la línea traiga ``custom_price``.
    ``snapshot=True``: líneas de un pedido ya tomado; se respetan el precio, el factor y el tipo de stock
    guardados en el pedido (el precio pudo cambiar en el catálogo después), cada línea trae
    ``price``, ``factor``, ``own_stock`` y ``presentation_name``.
    Lanza ``Exception`` con un mensaje claro si algo no se puede vender (sin stock, presentación inexistente).
    """
    lines, needed, products, holders = [], {}, {}, {}
    for raw in raw_lines:
        # Una sola instancia por producto/presentación: si el carrito trae dos líneas del mismo
        # stock, el descuento de la segunda parte del valor ya descontado.
        pid = int(raw['id'])
        if pid not in products:
            products[pid] = Product.objects.select_for_update().get(pk=pid)
        product = products[pid]
        qty = parse_quantity(raw['cant'], product)

        presentation, factor, price = None, Decimal(1), product.pvp
        if snapshot:
            own = bool(raw.get('own_stock'))
            factor, price = Decimal(str(raw['factor'])), Decimal(str(raw['price']))
            if raw.get('presentation_id'):
                presentation = ProductPresentation.objects.filter(pk=raw['presentation_id'], product=product).first()
                if presentation is None:
                    raise Exception(f"La presentación '{raw.get('presentation_name')}' de '{product.name}' ya no existe.")
            elif own and raw.get('presentation_name') and raw['presentation_name'] != product.unit_name:
                raise Exception(f"La variante '{raw['presentation_name']}' de '{product.name}' ya no existe.")
        else:
            own = product.has_own_stock_variants()
            if raw.get('presentation_id'):
                presentation = ProductPresentation.objects.filter(
                    pk=raw['presentation_id'], product=product, is_active=True,
                    product__uses_presentations=True).first()
                if presentation is None:
                    raise Exception(f"La presentación elegida de '{product.name}' ya no está disponible.")
                price = presentation.pvp
                if not own:
                    factor = presentation.factor
            if allow_price_override and raw.get('custom_price') not in (None, ''):
                price = parse_price(raw['custom_price'], product)

        if own and presentation is not None:
            key = ('presentation', presentation.pk)
            if key not in holders:
                holders[key] = ProductPresentation.objects.select_for_update().get(pk=presentation.pk)
            holder, label = holders[key], f'{product.name} - {presentation.name}'
        else:
            key = ('product', product.pk)
            holder, holders[key] = product, product
            label = f'{product.name} - {product.unit_name}' if own else product.name
        if snapshot:
            name = raw.get('presentation_name') or ''
        else:
            name = presentation.name if presentation else (product.unit_name if own else '')

        base_units = (factor * qty).quantize(QTY_STEP)
        needed[key] = needed.get(key, Decimal(0)) + base_units
        lines.append({'product': product, 'presentation': presentation, 'presentation_name': name, 'holder': holder,
                      'key': key, 'label': label, 'own_stock': own, 'cant': qty, 'factor': factor,
                      'base_units': base_units, 'price': price, 'dscto': raw.get('dscto', 0)})

    for line in lines:
        if not line['product'].is_service and line['holder'].stock < needed[line['key']]:
            unit = line['product'].unit_name if not line['own_stock'] else ''
            raise Exception(
                f"No hay suficiente stock de '{line['label']}'. "
                f"Stock disponible: {line['holder'].stock} {unit}".rstrip() + f", solicitado: {needed[line['key']]}")
    return lines


def deduct_line(line):
    """Descuenta del inventario lo vendido en la línea (y de los productos de descuento automático)."""
    holder = line['holder']
    holder.stock -= line['base_units']
    holder.save(update_fields=['stock'])
    for auto in ProductAutoAdd.objects.filter(trigger_product=line['product']):
        auto_product = Product.objects.select_for_update().get(pk=auto.auto_product_id)
        auto_product.stock -= auto.quantity * line['base_units']
        auto_product.save()
