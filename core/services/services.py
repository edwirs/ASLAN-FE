
import os
import logging
import requests
import qrcode
import base64
from xhtml2pdf import pisa
from io import BytesIO
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from core.services.factus import download_invoice_xml, download_invoice_pdf
from core.pos.models import Company

logger = logging.getLogger(__name__)

def send_sale_electronic_invoice_email(sale, request=None):
    if sale.email_sent_count >= 4:
        return {
            "success": False, 
            "message": "Esta factura ya alcanzó el límite máximo de 4 envíos de correo."
        }

    client = sale.client
    client_email = client.email if client else None

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

        # 2. Adjuntar PDF obtenido desde el endpoint oficial de Factus
        pdf_content = generate_internal_sale_pdf(sale, request=request)
        if pdf_content:
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
    Renderiza la plantilla HTML de la factura de la venta y la convierte a PDF en memoria.
    """
    try:
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
        c_image = company.image.path if (company and company.image and hasattr(company.image, 'path')) else None

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
        
        # Renderiza tu plantilla HTML existente (reemplaza 'pos/sale/print_invoice.html' 
        # por la ruta real de la plantilla que usa tu iframe de impresión)
        html_string = render_to_string('salefe/format/invoice.html', context, request=request)
        
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html_string.encode("UTF-8")), result)
        
        if pdf.err:
            return None
            
        return result.getvalue()
    except Exception as e:
        logger.exception("Error generando el PDF interno para la venta %s", sale.id)
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