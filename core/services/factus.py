import logging
import base64
from datetime import date
from decimal import Decimal

import requests
from django.core.cache import cache
from django.db import connection
from django.utils import timezone

from core.pos import taxes


logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30

# El token de Factus dura 1 hora; se cachea un poco por debajo de eso para
# nunca usar uno que Factus ya haya expirado por un margen de reloj.
TOKEN_CACHE_SECONDS = 55 * 60


class FactusConfigError(Exception):
    """No hay una credencial de Factus activa configurada para este tenant."""
    pass


def _get_active_config():
    """Retorna la credencial de Factus activa del tenant actual.

    ``FactusCredential`` vive en una app de TENANT_APPS, así que esta consulta
    ya queda aislada al esquema del tenant en curso sin necesidad de filtrar
    explícitamente por empresa/cliente.
    """
    from core.pos.models import FactusCredential

    config = FactusCredential.objects.filter(is_active=True).first()
    if not config:
        raise FactusConfigError(
            "No hay credenciales de Factus configuradas para esta empresa. "
            "Configure una en Configuraciones > Credenciales Factus."
        )
    return config


def _as_money(value):
    return f"{value or 0:.2f}"


def _as_quantity(value):
    """Cantidad para Factus: 2 decimales si es entera (como siempre) y hasta 3 si es fraccionaria (0.295)."""
    value = Decimal(str(value or 0))
    return f"{value:.2f}" if value == value.to_integral_value() else f"{value.quantize(Decimal('0.001')):.3f}"


def _nit_dv(nit):
    """Calcula el dígito de verificación DIAN para un NIT sin DV."""
    digits = "".join(char for char in str(nit) if char.isdigit())
    if not digits:
        return ""

    weights = (71, 67, 59, 53, 47, 43, 41, 37, 29, 23, 19, 17, 13, 7, 3)
    total = sum(int(digit) * weight for digit, weight in zip(digits.zfill(15), weights))
    residue = total % 11
    return str(residue if residue < 2 else 11 - residue)


def _error_response(response, body=None, message="Factus rechazó la factura"):
    if body is None:
        try:
            body = response.json()
        except ValueError:
            body = response.text
    logger.warning("Factus rechazó la solicitud (HTTP %s): %s", response.status_code, body)
    return {"error": message, "detail": body}


def get_token(config):
    """Obtiene (y cachea) el token OAuth de la credencial dada.

    La caché se distingue por esquema de tenant + credencial, para que dos
    tenants -o dos credenciales del mismo tenant (sandbox/producción)- nunca
    compartan un token por accidente.
    """
    cache_key = f"factus_token:{connection.schema_name}:{config.id}"
    token = cache.get(cache_key)
    if token:
        return token

    response = requests.post(
        f"{config.api_url}/oauth/token",
        data={
            "grant_type": "password",
            "username": config.username,
            "password": config.password,
            "client_id": config.client_id,
            "client_secret": config.client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    token = response.json()["access_token"]
    cache.set(cache_key, token, TOKEN_CACHE_SECONDS)
    return token


def get_numbering_ranges():
    """Consulta los rangos de numeración activos disponibles en Factus."""
    try:
        config = _get_active_config()
        response = requests.get(
            f"{config.api_url}/v2/numbering-ranges",
            headers={"Authorization": f"Bearer {get_token(config)}", "Accept": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )
        if not response.ok:
            return _error_response(response)
        return response.json()
    except FactusConfigError as exc:
        return {"error": str(exc)}
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.exception("No fue posible consultar los rangos de Factus")
        return {"error": "No fue posible consultar los rangos de Factus", "detail": str(exc)}


def get_acquirer_info(identification_document_code, identification_number):
    """Consulta ante la DIAN el nombre/razón social y correo de un adquiriente
    (``GET /v2/dian/acquirer``), para autocompletar el registro de un cliente."""
    try:
        config = _get_active_config()
        response = requests.get(
            f"{config.api_url}/v2/dian/acquirer",
            params={
                "identification_document_code": identification_document_code,
                "identification_number": identification_number,
            },
            headers={"Authorization": f"Bearer {get_token(config)}", "Accept": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )
        if not response.ok:
            return _error_response(response)
        body = response.json()
        data = body.get("data") or {}
        if not data.get("name") and not data.get("email"):
            return {"error": "La DIAN no tiene datos registrados para esa identificación"}
        return data
    except FactusConfigError as exc:
        return {"error": str(exc)}
    except (requests.RequestException, ValueError) as exc:
        logger.exception(
            "No fue posible consultar el adquiriente %s en la DIAN", identification_number
        )
        return {"error": "No fue posible consultar los datos en la DIAN", "detail": str(exc)}


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
    ``product``, ``dscto``, ``cant``, ``price``, ``iva``, ``tax_key`` y ``retentions``.

    Cada línea lleva su propio impuesto: el que se guardó al vender (IVA ``01`` o INC ``04``, con su tarifa) y sus
    retenciones (``withholding_taxes``: 05 ReteIVA, 06 ReteRenta). Las líneas anteriores a este esquema (sin
    ``tax_key``) siguen usando la tarifa de la venta (``tax_rate``) y ``product.with_tax``.
    """
    items = []
    global_discount_rate = Decimal(str(global_discount_rate or 0))
    for detail in details:
        product = detail.product
        line_discount_rate = Decimal(str(detail.dscto or 0))
        effective_discount_rate = Decimal("1") - (
            (Decimal("1") - line_discount_rate) * (Decimal("1") - global_discount_rate)
        )
        info = taxes.TAX_BY_KEY.get(getattr(detail, "tax_key", "") or "")
        if info:
            line_tax_rate = Decimal(str(detail.iva or 0)) * 100
            tax = {"code": info.code, "rate": _as_money(line_tax_rate)}
            if info.excluded:
                tax.update({"code": "01", "rate": "0.00", "is_excluded": True})
        else:
            line_tax_rate = Decimal(str(tax_rate or 0))
            tax = {"code": "01", "rate": _as_money(line_tax_rate)}
            if not product.with_tax or line_tax_rate == 0:
                tax.update({"rate": "0.00", "is_excluded": True})

        item = {
            "code_reference": product.code,
            "name": product.name,
            "quantity": _as_quantity(detail.cant),
            "discount_rate": _as_money(effective_discount_rate * 100),
            "price": _as_money(detail.price),
            "unit_measure_code": "94",
            "standard_code": "999",
            "taxes": [tax],
        }
        withholdings = []
        for entry in getattr(detail, "retentions", None) or []:
            code, _, rate = str(entry).partition(":")
            if code in taxes.RETENTION_RATES and rate:
                withholdings.append({"code": code, "rate": _as_money(Decimal(rate))})
        if withholdings:
            item["withholding_taxes"] = withholdings
        items.append(item)
    return items


def create_invoice(sale, numbering_range_id, target_email=None):
    """Construye y valida una factura estándar (operación 10) en Factus v2."""
    try:
        config = _get_active_config()
    except FactusConfigError as exc:
        return {"error": str(exc)}

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
            f"{config.api_url}/v2/bills/validate",
            json=payload,
            headers={
                "Authorization": f"Bearer {get_token(config)}",
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
        config = _get_active_config()
        response = requests.get(
            f"{config.api_url}/v2/bills/{bill_number}/download-xml",
            headers={
                "Authorization": f"Bearer {get_token(config)}",
                "Accept": "application/json",
            },
            timeout=REQUEST_TIMEOUT,
        )
        if not response.ok:
            return _error_response(response)
        return response.content
    except FactusConfigError as exc:
        return {"error": str(exc)}
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
        config = _get_active_config()
        response = requests.get(
            f"{config.api_url}/v2/bills/{invoice_number}/download-pdf",
            headers={
                "Authorization": f"Bearer {get_token(config)}",
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
    except FactusConfigError as exc:
        return {"error": str(exc)}
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.exception("No fue posible descargar el PDF de la factura %s desde Factus", invoice_number)
        return {"error": "No fue posible descargar el PDF", "detail": str(exc)}


def create_credit_note(credit_note, numbering_range_id, target_email=None):
    """Construye y valida una nota crédito en Factus v2 (``POST /v2/credit-notes/validate``).

    ``credit_note.operation_type`` define si referencia una factura ('20') o no ('22').
    Ver: https://developers.factus.com.co/notas-credito/descripcion-de-campos/
    """
    try:
        config = _get_active_config()
    except FactusConfigError as exc:
        return {"error": str(exc)}

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
            f"{config.api_url}/v2/credit-notes/validate",
            json=payload,
            headers={
                "Authorization": f"Bearer {get_token(config)}",
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
        config = _get_active_config()
        response = requests.get(
            f"{config.api_url}/v2/credit-notes/{number}",
            headers={"Authorization": f"Bearer {get_token(config)}", "Accept": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )
        if not response.ok:
            return _error_response(response)
        return response.json()
    except FactusConfigError as exc:
        return {"error": str(exc)}
    except (requests.RequestException, ValueError) as exc:
        logger.exception("No fue posible consultar la nota crédito %s en Factus", number)
        return {"error": "No fue posible consultar la nota crédito", "detail": str(exc)}


def download_credit_note_xml(number):
    """Descarga el XML de una nota crédito validada (``GET /v2/credit-notes/:number/download-xml``)."""
    try:
        config = _get_active_config()
        response = requests.get(
            f"{config.api_url}/v2/credit-notes/{number}/download-xml",
            headers={
                "Authorization": f"Bearer {get_token(config)}",
                "Accept": "application/json",
            },
            timeout=REQUEST_TIMEOUT,
        )
        if not response.ok:
            return _error_response(response)
        return response.content
    except FactusConfigError as exc:
        return {"error": str(exc)}
    except (requests.RequestException, ValueError) as exc:
        logger.exception("No fue posible descargar el XML de la nota crédito %s desde Factus", number)
        return {"error": "No fue posible descargar el XML", "detail": str(exc)}


def download_credit_note_pdf(number):
    """
    Descarga el PDF de una nota crédito (``GET /v2/credit-notes/:number/download-pdf``).
    Factus devuelve el binario codificado en Base64 dentro de ``pdf_base_64_encoded``.
    """
    try:
        config = _get_active_config()
        response = requests.get(
            f"{config.api_url}/v2/credit-notes/{number}/download-pdf",
            headers={
                "Authorization": f"Bearer {get_token(config)}",
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
    except FactusConfigError as exc:
        return {"error": str(exc)}
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.exception("No fue posible descargar el PDF de la nota crédito %s desde Factus", number)
        return {"error": "No fue posible descargar el PDF", "detail": str(exc)}


def delete_credit_note(reference_code):
    """
    Elimina una nota crédito NO validada por la DIAN
    (``DELETE /v2/credit-notes/reference/:reference_code``).
    ``reference_code`` es el mismo valor enviado al crearla (``str(credit_note.id)``).
    """
    try:
        config = _get_active_config()
        response = requests.delete(
            f"{config.api_url}/v2/credit-notes/reference/{reference_code}",
            headers={"Authorization": f"Bearer {get_token(config)}", "Accept": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 404:
            # No existe en Factus (p. ej. nunca llegó a crearse allí porque el
            # registro falló antes de validar): no hay nada que borrar del lado
            # de Factus, se puede continuar con la eliminación local.
            return {"success": True, "not_found": True}
        if not response.ok:
            return _error_response(response)
        return {"success": True}
    except FactusConfigError as exc:
        return {"error": str(exc)}
    except requests.RequestException as exc:
        logger.exception("No fue posible eliminar la nota crédito %s en Factus", reference_code)
        return {"error": "No fue posible comunicarse con Factus", "detail": str(exc)}


# ------------------------------------------------------------------------------------------------
# Rango de numeración activo
# ------------------------------------------------------------------------------------------------
def _plain(text):
    import unicodedata

    return unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower().strip()


def get_active_numbering_range(document="Factura de Venta"):
    """Rango de numeración activo y vigente para ese tipo de documento, o ``{"error": ...}``.

    Usa ``GET /v2/numbering-ranges`` (solo consulta: no reserva ni consume ningún consecutivo). Devuelve el rango tal
    como lo entrega Factus: ``id``, ``prefix``, ``from``, ``to``, ``current`` (el PRÓXIMO número a usar),
    ``resolution_number``, ``start_date``/``end_date`` (o ``date_from``/``date_to``), ``is_expired``...
    """
    response = get_numbering_ranges()
    if "error" in response:
        return response
    data = response.get("data")
    ranges = data if isinstance(data, list) else ((data or {}).get("data") or [])
    accepted = {_plain(document), "factura electronica de venta", "factura de venta"}
    candidates = [r for r in ranges if _plain(r.get("document")) in accepted and r.get("is_active") and not r.get("deleted_at")]
    if not candidates:
        return {"error": f"No hay un rango de numeración activo para «{document}» en Factus."}
    valid = [r for r in candidates if not r.get("is_expired")]
    if not valid:
        return {"error": "El rango de numeración activo de Factus está vencido. Renueve la resolución de facturación."}
    return valid[0]


# ------------------------------------------------------------------------------------------------
# RADIAN: eventos de una factura emitida
# ------------------------------------------------------------------------------------------------
# Códigos de la «Tabla de eventos RADIAN» de la documentación de Factus.
RADIAN_EVENTS = {
    "030": "Acuse de recibo de la factura",
    "031": "Reclamo de la factura",
    "032": "Recibo del bien o prestación del servicio",
    "033": "Aceptación expresa",
    "034": "Aceptación tácita",
}
RADIAN_TACIT_ACCEPTANCE = "034"


def _event_list(body):
    """La lista de eventos, venga como arreglo, en ``data`` o en ``data.data``."""
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        data = body.get("data")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            inner = data.get("data")
            if isinstance(inner, list):
                return inner
            if isinstance(data.get("events"), list):
                return data["events"]
        if isinstance(body.get("events"), list):
            return body["events"]
    return []


def get_radian_events(number):
    """Eventos RADIAN de una factura (``GET /v2/bills/:number/radian/events``).

    Devuelve ``{"events": [...]}`` con cada evento normalizado (``code``, ``name``, ``number``, ``cude``,
    ``date``, ``time``) o ``{"error": ...}``.
    """
    try:
        config = _get_active_config()
        response = requests.get(
            f"{config.api_url}/v2/bills/{number}/radian/events",
            headers={"Authorization": f"Bearer {get_token(config)}", "Accept": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )
        try:
            body = response.json()
        except ValueError:
            body = None
        if not response.ok:
            return _error_response(response, body, "Factus no pudo entregar los eventos RADIAN")
    except FactusConfigError as exc:
        return {"error": str(exc)}
    except (requests.RequestException, KeyError) as exc:
        logger.exception("No fue posible consultar los eventos RADIAN de la factura %s", number)
        return {"error": "No fue posible consultar los eventos RADIAN en Factus", "detail": str(exc)}

    events = []
    for raw in _event_list(body):
        if not isinstance(raw, dict):
            continue
        code = str(raw.get("event_code") or raw.get("code") or "").strip().zfill(3) if (raw.get("event_code") or raw.get("code")) else ""
        events.append({
            "code": code,
            "name": raw.get("event_name") or RADIAN_EVENTS.get(code, ""),
            "number": raw.get("number") or "",
            "cude": raw.get("cude") or "",
            "date": raw.get("effective_date") or "",
            "time": raw.get("effective_time") or "",
        })
    return {"events": events}


def radian_summary(events):
    """Estado resumido de una factura según sus eventos RADIAN: ``{"level", "label", "codes"}``.

    ``level``: accepted (033/034), claim (031), received (030/032) o none (sin eventos). El pago de la factura no
    es un evento que Factus exponga, así que no se puede saber si fue pagada.
    """
    codes = {e.get("code") for e in events}
    if "033" in codes:
        label, level = "Aceptada expresamente", "accepted"
    elif "034" in codes:
        label, level = "Aceptada tácitamente", "accepted"
    elif "031" in codes:
        label, level = "Con reclamo", "claim"
    elif "032" in codes:
        label, level = "Bien o servicio recibido", "received"
    elif "030" in codes:
        label, level = "Acuse de recibo", "received"
    else:
        label, level = "Sin eventos del adquirente", "none"
    return {"level": level, "label": label, "codes": sorted(c for c in codes if c)}


def create_tacit_acceptance(number, person):
    """Registra la aceptación tácita (evento 034) de una factura a crédito
    (``POST /v2/bills/:number/radian/events/034``). ``person``: quien registra el evento.

    Campos de ``person``: ``identification_document_code``, ``identification``, ``first_name``, ``last_name`` y,
    opcionales, ``dv``, ``job_title``, ``organization_department``.
    """
    payload = {
        "identification_document_code": str(person.get("identification_document_code", "")).strip(),
        "identification": str(person.get("identification", "")).strip(),
        "dv": str(person.get("dv", "") or "").strip(),
        "first_name": str(person.get("first_name", "")).strip(),
        "last_name": str(person.get("last_name", "")).strip(),
    }
    for optional in ("job_title", "organization_department"):
        value = str(person.get(optional, "") or "").strip()
        if value:
            payload[optional] = value
    try:
        config = _get_active_config()
        response = requests.post(
            f"{config.api_url}/v2/bills/{number}/radian/events/{RADIAN_TACIT_ACCEPTANCE}",
            json=payload,
            headers={
                "Authorization": f"Bearer {get_token(config)}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=REQUEST_TIMEOUT,
        )
        try:
            body = response.json()
        except ValueError:
            body = response.text
        if not response.ok or (isinstance(body, dict) and body.get("status") == "Validation error"):
            return _error_response(response, body, "Factus rechazó el registro de la aceptación tácita")
        return body if isinstance(body, dict) else {"data": body}
    except FactusConfigError as exc:
        return {"error": str(exc)}
    except (requests.RequestException, KeyError) as exc:
        logger.exception("No fue posible registrar la aceptación tácita de la factura %s", number)
        return {"error": "No fue posible comunicarse con Factus", "detail": str(exc)}
