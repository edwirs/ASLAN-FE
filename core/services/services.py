
import os
import logging
import requests
import qrcode
import base64
from mimetypes import guess_type
from io import BytesIO
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from core.services.factus import download_invoice_xml, download_invoice_pdf, download_credit_note_xml
from core.pos.models import Company

logger = logging.getLogger(__name__)


def image_to_data_uri(image_field):
    """Convierte una imagen local a data URI para el PDF de Chromium."""
    if not image_field:
        return None

    try:
        image_field.open('rb')
        try:
            content = image_field.read()
        finally:
            image_field.close()

        if not content:
            return None

        mime_type = guess_type(image_field.name)[0] or 'application/octet-stream'
        encoded_content = base64.b64encode(content).decode('ascii')
        return f'data:{mime_type};base64,{encoded_content}'
    except Exception:
        logger.exception('No se pudo preparar la imagen para el PDF')
        return None

def send_sale_electronic_invoice_email(sale, request=None, target_email=None):
    if sale.email_sent_count >= 4:
        return {
            "success": False,
            "message": "Esta factura ya alcanzó el límite máximo de 4 envíos de correo."
        }

    client = sale.client
    client_email = (target_email or (client.email if client else None) or "").strip() or None

    if not client_email:
        return {
            "success": False, 
            "message": "El cliente no tiene un correo electrónico registrado."
        }

    try:
        subject = f"Factura Electrónica de Venta - {sale.factus_invoice_id}"
        message = (
            f"Estimado/a {client.names},\n\n"
            f"Adjunto encontrará el documento equivalente (PDF), el archivo XML "
            f"correspondiente a su factura electrónica #{sale.factus_invoice_id} "
            f"y los documentos adicionales de su compra.\n\n"
            f"Gracias por su compra."
        )

        email = EmailMessage(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [client_email]
        )

        # 1. Adjuntar XML obtenido desde Factus
        if sale.factus_invoice_id:
            xml_content = download_invoice_xml(sale.factus_invoice_id)
            if xml_content and not isinstance(xml_content, dict):
                email.attach(
                    filename=f"factura_{sale.factus_invoice_id}.xml",
                    content=xml_content,
                    mimetype="application/xml"
                )

        # 2. Generar el PDF de la factura con Chromium. No se envía un correo
        # incompleto si el motor de PDF no está disponible.
        pdf_content = generate_internal_sale_pdf(sale, request=request)
        if not pdf_content:
            return {
                "success": False,
                "message": "No fue posible generar el PDF de la factura para el correo.",
            }
        email.attach(
            filename=f"factura_{sale.factus_invoice_id or sale.id}.pdf",
            content=pdf_content,
            mimetype="application/pdf"
        )

        # 3. Adjuntar múltiples archivos enviados desde el formulario
        if request and hasattr(request, 'FILES') and 'pdf_files' in request.FILES:
            files_list = request.FILES.getlist('pdf_files')
            for file in files_list:
                content_type = getattr(file, 'content_type', 'application/octet-stream')
                # REINICIAR EL PUNTERO POR SEGURIDAD
                file.seek(0)
                file_content = file.read()
                if len(file_content) > 0:
                    email.attach(file.name, file_content, content_type)
                else:
                    print(f"--- [ADVERTENCIA] El archivo {file.name} está vacío o ya fue leído. ---")
        else:
            print("--- [DEBUG SERVICE] ADVERTENCIA: No se encontraron 'pdf_files' en request.FILES o request es None. ---")

        # Enviar correo
        email.send(fail_silently=False)

        # Actualizar contador
        sale.email_sent_count += 1
        sale.save(update_fields=['email_sent_count'])

        return {
            "success": True, 
            "message": f"Correo enviado exitosamente (Envío {sale.email_sent_count} de 4)."
        }

    except Exception as e:
        logger.exception("Error al enviar el correo de la factura %s", sale.id)
        return {
            "success": False, 
            "message": f"Hubo un error al enviar el correo: {str(e)}"
        }

def generate_internal_sale_pdf(sale, request=None):
    """
    Renderiza la factura con Chromium y devuelve el PDF en memoria.
    """
    try:
        from playwright.sync_api import sync_playwright

        # 1. BÚSQUEDA BLINDADA DE LA COMPAÑÍA
        company = None
        
        # Intentar obtener la compañía a través de la relación de la venta
        if sale.company_id:
            company = Company.objects.filter(id=sale.company_id).first()
            
        # Si por alguna razón aún es nula, tomar la primera compañía activa del sistema
        if not company:
            company = Company.objects.filter(is_active=True).first() or Company.objects.first()

        # Extraer las propiedades del objeto de forma segura para pasarlas planas
        c_name = company.name if company else "Compañía sin nombre"
        c_ruc = company.ruc if company else "N/A"
        c_email = company.email if company else ""
        c_address = company.address if company else ""
        c_image = image_to_data_uri(company.image) if company and company.image else None

        # Generar la imagen QR en Base64 usando la URL que guardaste de Factus
        qr_data_to_encode = sale.factus_qr_url if sale.factus_qr_url else sale.factus_cufe
        qr_base64 = generate_qr_base64_from_url(qr_data_to_encode)

        # Contexto que necesite tu plantilla HTML de factura
        context = {
            'sale': sale,
            'details': sale.saledetail_set.select_related('product'),
            'company': company,
            'company_name': c_name,
            'company_ruc': c_ruc,
            'company_email': c_email,
            'company_address': c_address,
            'company_image_path': c_image,
            'qr_base64': qr_base64,
        }
        
        html_string = render_to_string('salefe/format/invoice.html', context, request=request)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.emulate_media(media='print')
                page.set_content(html_string, wait_until='load')
                return page.pdf(
                    print_background=True,
                    prefer_css_page_size=True,
                )
            finally:
                browser.close()
    except Exception:
        logger.exception("Error generando el PDF interno para la venta %s", sale.id)
        return None


def send_credit_note_electronic_email(credit_note, request=None):
    client = credit_note.client
    client_email = client.email if client else None

    if not client_email:
        return {
            "success": False,
            "message": "El cliente no tiene un correo electrónico registrado."
        }

    try:
        subject = f"Nota Crédito Electrónica - {credit_note.factus_credit_note_number}"
        message = (
            f"Estimado/a {client.names},\n\n"
            f"Adjunto encontrará el documento equivalente (PDF) y el archivo XML "
            f"correspondiente a la nota crédito electrónica #{credit_note.factus_credit_note_number}.\n\n"
            f"Gracias por su preferencia."
        )

        email = EmailMessage(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [client_email]
        )

        # 1. Adjuntar XML obtenido desde Factus
        if credit_note.factus_credit_note_number:
            xml_content = download_credit_note_xml(credit_note.factus_credit_note_number)
            if xml_content and not isinstance(xml_content, dict):
                email.attach(
                    filename=f"nota_credito_{credit_note.factus_credit_note_number}.xml",
                    content=xml_content,
                    mimetype="application/xml"
                )

        # 2. Generar el PDF de la nota crédito con Chromium. No se envía un
        # correo incompleto si el motor de PDF no está disponible.
        pdf_content = generate_internal_credit_note_pdf(credit_note, request=request)
        if not pdf_content:
            return {
                "success": False,
                "message": "No fue posible generar el PDF de la nota crédito para el correo.",
            }
        email.attach(
            filename=f"nota_credito_{credit_note.factus_credit_note_number or credit_note.id}.pdf",
            content=pdf_content,
            mimetype="application/pdf"
        )

        email.send(fail_silently=False)

        return {
            "success": True,
            "message": "Correo de la nota crédito enviado exitosamente."
        }

    except Exception as e:
        logger.exception("Error al enviar el correo de la nota crédito %s", credit_note.id)
        return {
            "success": False,
            "message": f"Hubo un error al enviar el correo: {str(e)}"
        }


def generate_internal_credit_note_pdf(credit_note, request=None):
    """
    Renderiza la nota crédito con Chromium y devuelve el PDF en memoria.
    """
    try:
        from playwright.sync_api import sync_playwright

        company = None
        if credit_note.company_id:
            company = Company.objects.filter(id=credit_note.company_id).first()
        if not company:
            company = Company.objects.filter(is_active=True).first() or Company.objects.first()

        c_name = company.name if company else "Compañía sin nombre"
        c_ruc = company.ruc if company else "N/A"
        c_email = company.email if company else ""
        c_address = company.address if company else ""
        c_image = image_to_data_uri(company.image) if company and company.image else None

        qr_data_to_encode = credit_note.factus_qr_url if credit_note.factus_qr_url else credit_note.factus_cufe
        qr_base64 = generate_qr_base64_from_url(qr_data_to_encode)

        context = {
            'credit_note': credit_note,
            'details': credit_note.creditnotedetail_set.select_related('product'),
            'company': company,
            'company_name': c_name,
            'company_ruc': c_ruc,
            'company_email': c_email,
            'company_address': c_address,
            'company_image_path': c_image,
            'qr_base64': qr_base64,
        }

        html_string = render_to_string('creditnotefe/format/invoice.html', context, request=request)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.emulate_media(media='print')
                page.set_content(html_string, wait_until='load')
                return page.pdf(
                    print_background=True,
                    prefer_css_page_size=True,
                )
            finally:
                browser.close()
    except Exception:
        logger.exception("Error generando el PDF interno para la nota crédito %s", credit_note.id)
        return None

def generate_qr_base64_from_url(url):
    """Convierte una URL o texto en una imagen QR codificada en Base64"""
    try:
        if not url:
            return None
        qr = qrcode.QRCode(box_size=3, border=1)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{img_str}"
    except Exception:
        return None
