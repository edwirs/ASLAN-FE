"""Facturas electrónicas: guardar en local, editar y validar (enviar a Factus / DIAN).

Son tres pasos separados a propósito:

1. **Guardar** (`save_from_request`): registra la factura SOLO en la base local (con su inventario). No toca a Factus.
2. **Editar** (la misma función, con la factura ya existente): solo mientras la factura no haya sido validada.
3. **Validar** (`validate_sale`): ahí sí se envía a Factus; si la DIAN la acepta se guardan su número y CUFE y se
   envía el correo al cliente. Una factura validada ya no se edita ni se elimina: se corrige con una nota crédito.
"""
import json
import logging

from django.db import DatabaseError, transaction

from core.pos.models import Client, Company, CreditNote, Product, ProductAutoAdd, Sale, SaleDetail
from core.pos.sale_deletion import restore_detail_stock
from core.pos.stock_lines import parse_quantity
from core.services import factus
from core.services.services import send_sale_electronic_invoice_email

logger = logging.getLogger(__name__)


class SaleFeError(Exception):
    """No se puede hacer la operación; el mensaje es apto para mostrarse al usuario."""


def get_fe_sale(pk):
    """La factura electrónica con ese id, o ``SaleFeError`` con un mensaje claro."""
    try:
        return Sale.objects.get(pk=int(pk), is_electronicinvoice=True)
    except (Sale.DoesNotExist, TypeError, ValueError):
        raise SaleFeError('La factura no existe.')


def is_validated(sale):
    """¿La factura ya fue aceptada por la DIAN (tiene número o CUFE de Factus)?"""
    return bool(sale.factus_invoice_id or sale.factus_cufe)


def check_can_edit(sale):
    if not sale.is_electronicinvoice:
        raise SaleFeError('Esta venta no es una factura electrónica.')
    if is_validated(sale):
        raise SaleFeError('Esta factura ya fue validada en la DIAN y no se puede editar. '
                          'Para corregirla debe hacerse una nota crédito.')
    if sale.salecreditpayment_set.exists():
        raise SaleFeError('La factura tiene abonos registrados. Elimine primero los abonos para poder editarla.')
    if CreditNote.objects.filter(reference_sale=sale).exists():
        raise SaleFeError('La factura tiene notas crédito asociadas y no se puede editar.')


def save_from_request(request, sale=None):
    """Crea o actualiza la factura electrónica LOCAL a partir del formulario. No la envía a Factus.

    Con ``sale=None`` crea una nueva. Con una factura existente la edita: devuelve al inventario lo que habían
    descontado sus líneas, las reemplaza por las del formulario y recalcula todo, en una sola transacción.
    """
    post = request.POST
    with transaction.atomic():
        if sale is not None:
            sale = Sale.objects.select_for_update().get(pk=sale.pk)
            check_can_edit(sale)
            for detail in sale.saledetail_set.select_related('product'):
                restore_detail_stock(detail)
            sale.saledetail_set.all().delete()
        else:
            sale = Sale()
            sale.employee_id = request.user.id

        company = Company.objects.first()
        sale.company = company
        sale.iva = float(company.iva) / 100 if company and company.iva else 0.0
        sale.client_id = int(post.get('client'))
        sale.dscto = float(post.get('dscto', 0) or 0) / 100
        sale.cash = float(post.get('cash', 0) or 0)
        sale.change = float(post.get('change', 0) or 0)
        sale.paymentmethod = post.get('paymentmethod')
        sale.nequi_value = 0
        sale.daviplata_value = 0
        if sale.paymentmethod == 'transfer':
            sale.transfermethods = post.get('transfermethods')
        elif sale.paymentmethod == 'mixto':
            sale.transfermethods = None
            sale.nequi_value = float(post.get('nequi_value', 0) or 0)
            sale.daviplata_value = float(post.get('daviplata_value', 0) or 0)
        else:
            sale.transfermethods = None

        sale.typemethods = post.get('typemethods')
        sale.expiration_date = post.get('expiration_date') if sale.typemethods == 'credit' else None
        sale.service_type = post.get('service_type')
        sale.propina = float(post.get('propina', 0) or 0)
        sale.description = post.get('description', '').strip()
        sale.is_electronicinvoice = True
        sale.factus_status = 'pending'   # pendiente de validar: todavía no se ha enviado a Factus
        sale.save()

        lines = json.loads(post.get('products', '[]'))
        if not lines:
            raise SaleFeError('La factura debe tener al menos 1 producto o servicio.')
        for i in lines:
            product = Product.objects.get(pk=i['id'])
            detail = SaleDetail()
            detail.sale_id = sale.id
            detail.product_id = product.id
            detail.cost = product.cost_per_sale_unit()
            qty = parse_quantity(i['cant'], product)
            detail.cant = qty
            detail.price = float(i['pvp'])
            detail.dscto = float(i['dscto']) / 100
            detail.save()

            # Descuento de stock
            detail.product.stock -= detail.cant
            detail.product.save()

            # Productos automáticos
            for auto in ProductAutoAdd.objects.filter(trigger_product=product):
                auto_product = auto.auto_product
                auto_product.stock -= auto.quantity * qty
                auto_product.save()

        sale.calculate_detail()
        sale.calculate_invoice()

        files_list = request.FILES.getlist('pdf_files')
        if files_list:
            sale.attachment = files_list[0]
            sale.save(update_fields=['attachment'])
    return sale


def _factus_message(response):
    """Texto del error que devolvió Factus (el mensaje y, si lo trae, el detalle de validación)."""
    message = str(response.get('error'))
    detail = response.get('detail')
    if detail:
        message += ': ' + (detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False))
    return message


def validate_sale(sale_id, request=None, numbering_range_id=None):
    """Envía la factura a Factus y guarda lo que responde. Devuelve ``{'number', 'cufe', 'warnings': [...]}``.

    Lanza ``SaleFeError`` con un mensaje claro si no se pudo validar (la factura queda como pendiente, con estado
    «error», y se puede volver a intentar). El correo al cliente se envía al final y nunca revierte la validación.
    """
    with transaction.atomic():
        try:
            sale = Sale.objects.select_for_update(nowait=True).select_related('client').get(pk=sale_id)
        except Sale.DoesNotExist:
            raise SaleFeError('La factura no existe.')
        except DatabaseError:
            raise SaleFeError('Esta factura ya se está validando. Espere unos segundos y actualice la lista.')
        if not sale.is_electronicinvoice:
            raise SaleFeError('Esta venta no es una factura electrónica.')
        if is_validated(sale):
            raise SaleFeError(f'Esta factura ya fue validada (N° {sale.factus_invoice_id}).')
        if not sale.saledetail_set.exists():
            raise SaleFeError('La factura no tiene productos.')

        if numbering_range_id is None:
            active = factus.get_active_numbering_range()
            if 'error' in active:
                raise SaleFeError(active['error'])
            numbering_range_id = active['id']

        failure = None
        response = factus.create_invoice(sale, numbering_range_id=int(numbering_range_id), target_email=sale.client.email or '')
        if 'error' in response:
            failure = _factus_message(response)
        else:
            data_resp = response.get('data', {})
            # Factus v2 retorna los datos de la factura directamente en ``data``; se conserva el respaldo antiguo.
            bill_data = data_resp.get('bill', data_resp)
            numbering_range = data_resp.get('numbering_range', {})
            if not bill_data or not bill_data.get('number'):
                failure = 'Factus no devolvió los datos de la factura validada.'
        if failure is None:
            links = bill_data.get('links', {})
            sale.factus_invoice_id = bill_data.get('number')
            sale.factus_status = bill_data.get('status') or ('validated' if bill_data.get('is_validated') else 'pending')
            sale.factus_pdf_url = links.get('public_url')
            sale.factus_cufe = bill_data.get('cufe')
            sale.factus_resolution = numbering_range.get('resolution_number')
            sale.factus_prefix = numbering_range.get('prefix')
            sale.factus_range_from = numbering_range.get('from')
            sale.factus_range_to = numbering_range.get('to')
            sale.factus_date_from = numbering_range.get('date_from')
            sale.factus_date_to = numbering_range.get('date_to')
            sale.factus_qr_url = links.get('qr')
            sale.save()

    if failure is not None:
        # Fuera de la transacción: el estado «error» debe quedar guardado aunque se lance la excepción.
        Sale.objects.filter(pk=sale_id).update(factus_status='error')
        raise SaleFeError(failure)

    result = {'number': sale.factus_invoice_id, 'cufe': sale.factus_cufe, 'warnings': []}
    try:
        email = send_sale_electronic_invoice_email(sale, request=request)
        if not email.get('success'):
            logger.warning('No se pudo enviar el correo de la factura %s: %s', sale.id, email.get('message'))
            result['warnings'].append('La factura quedó validada, pero el correo al cliente no pudo enviarse. '
                                      'Puede reenviarlo desde las opciones de la factura.')
    except Exception:
        logger.exception('Error inesperado al enviar el correo de la factura %s', sale.id)
        result['warnings'].append('La factura quedó validada, pero el correo al cliente no pudo enviarse. '
                                  'Puede reenviarlo desde las opciones de la factura.')
    return result


def radian_events(sale):
    """Eventos RADIAN de una factura validada, con su estado resumido. Lanza ``SaleFeError`` si no se pueden leer."""
    if not sale.factus_invoice_id:
        raise SaleFeError('La factura aún no ha sido validada, por eso no tiene eventos RADIAN.')
    response = factus.get_radian_events(sale.factus_invoice_id)
    if 'error' in response:
        raise SaleFeError(response['error'])
    events = response['events']
    codes = {e['code'] for e in events}
    client = sale.client
    return {
        'number': sale.factus_invoice_id,
        'events': events,
        'summary': factus.radian_summary(events),
        'is_credit': sale.typemethods == 'credit',
        'can_tacit': sale.typemethods == 'credit' and not ({'033', '034'} & codes),
        # Una factura electrónica es título valor cuando tiene acuse de recibo, recibo del bien o servicio y aceptación
        'title_value': {'030', '032'} <= codes and bool({'033', '034'} & codes),
        'invoice': {
            'client': client.names,
            'dni': (client.dni or '') + (f'-{client.dv}' if client.dv else ''),
            'date': sale.date_joined.strftime('%d-%m-%Y'),
            'payment_form': 'Crédito' if sale.typemethods == 'credit' else 'Contado',
            'payment_method': sale.get_paymentmethod_display(),
            'due_date': sale.expiration_date.strftime('%d-%m-%Y') if sale.expiration_date and sale.typemethods == 'credit' else '',
            'total': float(sale.total),
            'cufe': sale.factus_cufe or '',
        },
    }


def register_tacit_acceptance(sale, person):
    """Registra la aceptación tácita (solo facturas a crédito, validadas y sin aceptación previa)."""
    if not sale.factus_invoice_id:
        raise SaleFeError('La factura aún no ha sido validada.')
    if sale.typemethods != 'credit':
        raise SaleFeError('La aceptación tácita solo aplica a facturas con forma de pago a crédito.')
    for key, label in (('identification_document_code', 'el tipo de documento'), ('identification', 'el número de documento'),
                       ('first_name', 'los nombres'), ('last_name', 'los apellidos')):
        if not str(person.get(key, '')).strip():
            raise SaleFeError(f'Falta {label} de quien registra el evento.')
    current = radian_events(sale)
    if not current['can_tacit']:
        raise SaleFeError('Esta factura ya tiene una aceptación registrada.')
    response = factus.create_tacit_acceptance(sale.factus_invoice_id, person)
    if 'error' in response:
        raise SaleFeError(_factus_message(response))
    return radian_events(sale)
