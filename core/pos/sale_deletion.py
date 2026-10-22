"""Eliminación de ventas devolviendo el inventario.

Un crédito es una venta con ``typemethods='credit'``: eliminar el crédito es eliminar la venta. Por eso Ventas,
Facturas Electrónicas y Créditos comparten esta lógica. El stock se devuelve con la operación inversa de
``stock_lines.deduct_line`` (la que se aplicó al vender), usando lo guardado en cada línea de la venta.
"""
from django.db import transaction

from core.pos.models import CreditNote, Product, ProductAutoAdd, ProductPresentation, Sale
from core.pos.stock_lines import QTY_STEP


class SaleDeletionError(Exception):
    """La venta no se puede eliminar; el mensaje es apto para mostrarse al usuario."""


def check_can_delete(sale):
    if sale.salecreditpayment_set.exists():
        raise SaleDeletionError('La venta tiene abonos registrados. Elimine primero los abonos para poder eliminarla.')
    if sale.factus_invoice_id:
        raise SaleDeletionError(
            f'La factura electrónica ya fue enviada a Factus (N° {sale.factus_invoice_id}) y no se puede eliminar. '
            'Debe corregirse con una nota crédito.')
    if CreditNote.objects.filter(reference_sale=sale).exists():
        raise SaleDeletionError('La venta tiene notas crédito asociadas y no se puede eliminar.')


def stock_holder(detail):
    """Dónde se descontó el stock de la línea (misma regla que ``stock_lines.resolve_lines``).

    - Variante con stock propio (``own_stock`` y presentación): el stock de esa variante.
    - Cualquier otro caso, incluida la unidad base de un producto con variantes: el stock del producto.
    - ``None`` si la variante vendida ya no existe (no hay a dónde devolverlo).
    """
    product = detail.product
    if detail.own_stock and detail.presentation_id:
        return ProductPresentation.objects.select_for_update().filter(pk=detail.presentation_id).first()
    if detail.own_stock and detail.presentation_name and detail.presentation_name != product.unit_name:
        return None   # variante borrada: el campo presentation quedó vacío pero guarda su nombre
    return Product.objects.select_for_update().filter(pk=detail.product_id).first()


def restore_detail_stock(detail):
    """Devuelve al inventario lo que descontó una línea de la venta (y sus productos de descuento automático)."""
    base_units = (detail.factor * detail.cant).quantize(QTY_STEP)

    holder = stock_holder(detail)
    if holder is not None:
        holder.stock += base_units
        holder.save(update_fields=['stock'])

    for auto in ProductAutoAdd.objects.filter(trigger_product_id=detail.product_id):
        auto_product = Product.objects.select_for_update().get(pk=auto.auto_product_id)
        auto_product.stock += auto.quantity * base_units
        auto_product.save(update_fields=['stock'])


def delete_sale(sale_id):
    """Elimina la venta y devuelve el stock, todo en una transacción. Lanza ``SaleDeletionError`` si no procede."""
    with transaction.atomic():
        try:
            sale = Sale.objects.select_for_update().get(pk=sale_id)
        except Sale.DoesNotExist:
            raise SaleDeletionError('La venta no existe o ya fue eliminada.')
        check_can_delete(sale)
        for detail in sale.saledetail_set.select_related('product'):
            restore_detail_stock(detail)
        sale.delete()
