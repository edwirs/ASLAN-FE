import logging
import base64
from datetime import date
from decimal import Decimal

import requests
from django.conf import settings
from django.utils import timezone


logger = logging.getLogger(__name__)

# Estas credenciales se deben mover a variables de entorno antes de desplegar a
# producción. Se conservan temporalmente aquí para no interrumpir la integración
# ya configurada en este proyecto.
FACTUS_API_URL = "https://api-sandbox.factus.com.co"
CLIENT_ID = "a2548812-8575-447e-a61d-91dc7bd0e2bd"
CLIENT_SECRET = " GD9Kb7AeydRmdox3DlZMs0Le5WR8ghg84VQhLad0"
USERNAME = "fexequialesescobar@hotmail.com"
PASSWORD = "11426546"

REQUEST_TIMEOUT = 30


def _as_money(value):
    return f"{value or 0:.2f}"


def _nit_dv(nit):
    """Calcula el dígito de verificación DIAN para un NIT sin DV."""
    digits = "".join(char for char in str(nit) if char.isdigit())
    if not digits:
        return ""

    weights = (71, 67, 59, 53, 47, 43, 41, 37, 29, 23, 19, 17, 13, 7, 3)
    total = sum(int(digit) * weight for digit, weight in zip(digits.zfill(15), weights))
    residue = total % 11
    return str(residue if residue < 2 else 11 - residue)


def _error_response(response, body=None):
    if body is None:
        try:
            body = response.json()
        except ValueError:
            body = response.text
    logger.warning("Factus rechazó la solicitud (HTTP %s): %s", response.status_code, body)
    return {"error": "Factus rechazó la factura", "detail": body}


def get_token():
    response = requests.post(
        f"{FACTUS_API_URL}/oauth/token",
        data={
            "grant_type": "password",
            "username": USERNAME,
            "password": PASSWORD,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_numbering_ranges():
    """Consulta los rangos de numeración activos disponibles en Factus."""
    try:
        response = requests.get(
            f"{FACTUS_API_URL}/v2/numbering-ranges",
            headers={"Authorization": f"Bearer {get_token()}", "Accept": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )
        if not response.ok:
            return _error_response(response)
        return response.json()
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.exception("No fue posible consultar los rangos de Factus")
        return {"error": "No fue posible consultar los rangos de Factus", "detail": str(exc)}


def _build_customer_payload(client, target_email=None):
    """Construye el objeto ``customer`` que exige Factus a partir de un Client."""
    document_code = str(getattr(client.document_type, "code", "") or "31")
    is_nit = document_code == "31"
    is_company = client.person_type == "juridica"
    client_email = (target_email or client.email or "").strip()

    customer = {
        "identification_document_code": document_code,
        "identification": str(client.dni).replace("-", "").strip(),
        "address": client.address or "Sin dirección",
        "phone": client.mobile or "3000000000",
        "legal_organization_code": "1" if is_company else "2",
        "tribute_code": "01" if client.tax_responsibility == "responsable" else "ZZ",
        "country_code": "CO",
        "municipality_code": client.municipality.codigo if client.municipality else "11001",
    }
    if client_email:
        customer["email"] = client_email
    if is_company:
        customer["company"] = client.names
        customer["trade_name"] = client.commercial_name or client.names
    else:
        customer["names"] = client.names
        customer["trade_name"] = client.commercial_name or client.names
    if is_nit:
        customer["dv"] = _nit_dv(customer["identification"])
    return customer


def _build_items_payload(details, global_discount_rate, tax_rate):
    """Construye el array ``items`` que exige Factus a partir de un queryset de
    detalles (SaleDetail o CreditNoteDetail), ambos con los mismos campos
    ``product``, ``dscto``, ``cant`` y ``price``."""
    items = []
    global_discount_rate = Decimal(str(global_discount_rate or 0))
    for detail in details:
        product = detail.product
        line_discount_rate = Decimal(str(detail.dscto or 0))
        effective_discount_rate = Decimal("1") - (
            (Decimal("1") - line_discount_rate) * (Decimal("1") - global_discount_rate)
        )
        line_tax_rate = Decimal(str(tax_rate or 0))
        tax = {"code": "01", "rate": _as_money(line_tax_rate)}
        if not product.with_tax or line_tax_rate == 0:
            tax.update({"rate": "0.00", "is_excluded": True})

        items.append({
            "code_reference": product.code,
            "name": product.name,
            "quantity": _as_money(detail.cant),
            "discount_rate": _as_money(effective_discount_rate * 100),
            "price": _as_money(detail.price),
            "unit_measure_code": "94",
            "standard_code": "999",
            "taxes": [tax],
        })
    return items


def create_invoice(sale, numbering_range_id, target_email=None):
    """Construye y valida una factura estándar (operación 10) en Factus v2."""
    client = sale.client
    customer = _build_customer_payload(client, target_email)
    items = _build_items_payload(
        sale.saledetail_set.select_related("product"),
        sale.dscto,
        Decimal(str(sale.iva or 0)) * 100,
    )

    payment_form = "2" if sale.typemethods == "credit" else "1"
    payment_detail = {
        "payment_form": payment_form,
        "payment_method_code": "10" if sale.paymentmethod == "cash" else "42",
        "reference_code": f"pago-{sale.id}",
        "amount": _as_money(sale.total),
    }
    if payment_form == "2":
        due_date = sale.expiration_date
        if isinstance(due_date, str):
            try:
                due_date = date.fromisoformat(due_date)
            except ValueError:
                due_date = None
        today = timezone.localdate()
        if not due_date:
            return {"error": "La venta a crédito requiere fecha de vencimiento"}
        if due_date <= today:
            return {
                "error": "La fecha de vencimiento debe ser posterior a la fecha actual",
                "detail": {"payment_details.0.due_date": ["Seleccione al menos el día siguiente."]},
            }
        payment_detail["due_date"] = due_date.isoformat()

    payload = {
        "reference_code": str(sale.id),
        "document": "01",
        "numbering_range_id": int(numbering_range_id),
        "operation_type": "10",
        "send_email": False,
        "payment_details": [payment_detail],
        "cash_rounding_amount": "0.00",
        "customer": customer,
        "items": items,
    }
    observation = (sale.description or "").strip()
    if observation:
        payload["observation"] = observation

    try:
        response = requests.post(
            f"{FACTUS_API_URL}/v2/bills/validate",
            json=payload,
            headers={
                "Authorization": f"Bearer {get_token()}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=REQUEST_TIMEOUT,
        )
        try:
            body = response.json()
        except ValueError:
            body = response.text

        if not response.ok or not isinstance(body, dict) or body.get("status") == "Validation error":
            return _error_response(response, body)
        return body
    except (requests.RequestException, KeyError) as exc:
        logger.exception("No fue posible enviar la factura %s a Factus", sale.id)
        return {"error": "No fue posible comunicarse con Factus", "detail": str(exc)}


def download_invoice_xml(bill_number):
    """
    Consume el endpoint de Factus para obtener el contenido XML 
    de una factura validada utilizando su número.
    """
    try:
        response = requests.get(
            f"{FACTUS_API_URL}/v2/bills/{bill_number}/download-xml",
            headers={
                "Authorization": f"Bearer {get_token()}",
                "Accept": "application/json",
            },
            timeout=REQUEST_TIMEOUT,
        )
        if not response.ok:
            return _error_response(response)
        return response.content
    except (requests.RequestException, ValueError) as exc:
        logger.exception("No fue posible descargar el XML de la factura %s desde Factus", bill_number)
        return {"error": "No fue posible descargar el XML", "detail": str(exc)}


def download_invoice_pdf(invoice_number):
    """
    Descarga el PDF de una factura (``GET /v2/bills/:number/download-pdf``).
    Al igual que en notas crédito, Factus devuelve el binario codificado en
    Base64 dentro de ``pdf_base_64_encoded``, no el binario directo.
    """
    try:
        response = requests.get(
            f"{FACTUS_API_URL}/v2/bills/{invoice_number}/download-pdf",
            headers={
                "Authorization": f"Bearer {get_token()}",
                "Accept": "application/json",
            },
            timeout=REQUEST_TIMEOUT,
        )
        if not response.ok:
            return _error_response(response)

        body = response.json()
        encoded_pdf = body.get("data", body).get("pdf_base_64_encoded")
        if not encoded_pdf:
            return {"error": "Factus no devolvió el PDF de la factura"}
        return base64.b64decode(encoded_pdf)
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.exception("No fue posible descargar el PDF de la factura %s desde Factus", invoice_number)
        return {"error": "No fue posible descargar el PDF", "detail": str(exc)}


def create_credit_note(credit_note, numbering_range_id, target_email=None):
    """Construye y valida una nota crédito en Factus v2 (``POST /v2/credit-notes/validate``).

    ``credit_note.operation_type`` define si referencia una factura ('20') o no ('22').
    Ver: https://developers.factus.com.co/notas-credito/descripcion-de-campos/
    """
    client = credit_note.client
    customer = _build_customer_payload(client, target_email)
    items = _build_items_payload(
        credit_note.creditnotedetail_set.select_related("product"),
        credit_note.dscto,
        Decimal(str(credit_note.iva or 0)) * 100,
    )

    payment_form = "2" if credit_note.typemethods == "credit" else "1"
    payment_detail = {
        "payment_form": payment_form,
        "payment_method_code": "10" if credit_note.paymentmethod == "cash" else "42",
        "reference_code": f"nc-{credit_note.id}",
        "amount": _as_money(credit_note.total),
    }
    if payment_form == "2":
        due_date = credit_note.expiration_date
        if isinstance(due_date, str):
            try:
                due_date = date.fromisoformat(due_date)
            except ValueError:
                due_date = None
        today = timezone.localdate()
        if not due_date:
            return {"error": "La nota crédito a crédito requiere fecha de vencimiento"}
        if due_date <= today:
            return {
                "error": "La fecha de vencimiento debe ser posterior a la fecha actual",
                "detail": {"payment_details.0.due_date": ["Seleccione al menos el día siguiente."]},
            }
        payment_detail["due_date"] = due_date.isoformat()

    payload = {
        "reference_code": str(credit_note.id),
        "correction_concept_code": str(credit_note.correction_concept),
        "customization_id": str(credit_note.operation_type),
        "payment_details": [payment_detail],
        "customer": customer,
        "items": items,
    }
    if numbering_range_id:
        # Factus solo lo exige cuando hay múltiples rangos activos; si se omite
        # usa el único rango disponible por defecto.
        payload["numbering_range_id"] = int(numbering_range_id)

    if credit_note.operation_type == "20":
        # Nota crédito con referencia: obligatorio el número de la factura.
        if not credit_note.reference_bill_number:
            return {"error": "Debe indicar el número de la factura a referenciar"}
        payload["bill_number"] = credit_note.reference_bill_number
    else:
        # Nota crédito sin referencia: Factus exige el periodo de facturación.
        if not credit_note.billing_period_start_date or not credit_note.billing_period_end_date:
            return {"error": "Debe indicar el periodo de facturación de la nota crédito"}
        payload["billing_period"] = {
            "start_date": credit_note.billing_period_start_date.isoformat(),
            "start_time": "00:00:00",
            "end_date": credit_note.billing_period_end_date.isoformat(),
            "end_time": "23:59:59",
        }

    observation = (credit_note.description or "").strip()
    if observation:
        payload["observation"] = observation

    try:
        response = requests.post(
            f"{FACTUS_API_URL}/v2/credit-notes/validate",
            json=payload,
            headers={
                "Authorization": f"Bearer {get_token()}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=REQUEST_TIMEOUT,
        )
        try:
            body = response.json()
        except ValueError:
            body = response.text

        if not response.ok or not isinstance(body, dict) or body.get("status") == "Validation error":
            return _error_response(response, body)
        return body
    except (requests.RequestException, KeyError) as exc:
        logger.exception("No fue posible enviar la nota crédito %s a Factus", credit_note.id)
        return {"error": "No fue posible comunicarse con Factus", "detail": str(exc)}


def get_credit_note(number):
    """Consulta una nota crédito específica (``GET /v2/credit-notes/:number``)."""
    try:
        response = requests.get(
            f"{FACTUS_API_URL}/v2/credit-notes/{number}",
            headers={"Authorization": f"Bearer {get_token()}", "Accept": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )
        if not response.ok:
            return _error_response(response)
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.exception("No fue posible consultar la nota crédito %s en Factus", number)
        return {"error": "No fue posible consultar la nota crédito", "detail": str(exc)}


def download_credit_note_xml(number):
    """Descarga el XML de una nota crédito validada (``GET /v2/credit-notes/:number/download-xml``)."""
    try:
        response = requests.get(
            f"{FACTUS_API_URL}/v2/credit-notes/{number}/download-xml",
            headers={
                "Authorization": f"Bearer {get_token()}",
                "Accept": "application/json",
            },
            timeout=REQUEST_TIMEOUT,
        )
        if not response.ok:
            return _error_response(response)
        return response.content
    except (requests.RequestException, ValueError) as exc:
        logger.exception("No fue posible descargar el XML de la nota crédito %s desde Factus", number)
        return {"error": "No fue posible descargar el XML", "detail": str(exc)}


def download_credit_note_pdf(number):
    """
    Descarga el PDF de una nota crédito (``GET /v2/credit-notes/:number/download-pdf``).
    Factus devuelve el binario codificado en Base64 dentro de ``pdf_base_64_encoded``.
    """
    try:
        response = requests.get(
            f"{FACTUS_API_URL}/v2/credit-notes/{number}/download-pdf",
            headers={
                "Authorization": f"Bearer {get_token()}",
                "Accept": "application/json",
            },
            timeout=REQUEST_TIMEOUT,
        )
        if not response.ok:
            return _error_response(response)

        body = response.json()
        encoded_pdf = body.get("data", body).get("pdf_base_64_encoded")
        if not encoded_pdf:
            return {"error": "Factus no devolvió el PDF de la nota crédito"}
        return base64.b64decode(encoded_pdf)
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.exception("No fue posible descargar el PDF de la nota crédito %s desde Factus", number)
        return {"error": "No fue posible descargar el PDF", "detail": str(exc)}
