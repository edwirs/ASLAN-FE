import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, FormView
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from django.conf import settings

from core.pos.forms import *
from core.reports.forms import ReportForm
from core.security.mixins import GroupPermissionMixin
from core.services.factus import create_credit_note, get_numbering_ranges, download_credit_note_pdf
from core.services.services import send_credit_note_electronic_email, generate_qr_base64_from_url

MODULE_NAME = 'Notas Crédito'
logger = logging.getLogger(__name__)

# Motivos DIAN/Factus que implican devolución física de los bienes y, por lo
# tanto, deben reingresar stock. El resto son ajustes puramente financieros.
STOCK_RESTOCK_CONCEPTS = ('1', '2')


class CreditNoteFeListView(GroupPermissionMixin, FormView):
    template_name = 'creditnotefe/admin/list.html'
    form_class = ReportForm
    permission_required = 'view_creditnote'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action', '')
        try:
            if action == 'search':
                data = []
                start_date = request.POST.get('start_date', '')
                end_date = request.POST.get('end_date', '')
                queryset = CreditNote.objects.filter(is_active=True)
                if len(start_date) and len(end_date):
                    queryset = queryset.filter(date_joined__range=[start_date, end_date])
                for i in queryset.order_by('-id'):
                    data.append(i.toJSON())
            elif action == 'search_detail_products':
                data = []
                for i in CreditNoteDetail.objects.filter(credit_note_id=request.POST.get('id')):
                    data.append(i.toJSON())
            elif action == 'get_client_emails':
                credit_note = CreditNote.objects.select_related('client').get(pk=request.POST.get('id'))
                emails = []
                if credit_note.client.email:
                    emails.append({
                        'value': credit_note.client.email,
                        'label': f"Principal — {credit_note.client.email}",
                    })
                for contact in credit_note.client.contacts.exclude(email='').exclude(email__isnull=True):
                    label = contact.names
                    if contact.position:
                        label += f" ({contact.position})"
                    emails.append({'value': contact.email, 'label': f"{label} — {contact.email}"})
                data = {
                    'client_name': credit_note.client.get_full_name(),
                    'emails': emails,
                }
            elif action == 'resend_email':
                credit_note = CreditNote.objects.get(pk=request.POST.get('id'))
                target_email = request.POST.get('email', '').strip()
                if not target_email:
                    data['error'] = 'Debe seleccionar un correo de destino'
                else:
                    result = send_credit_note_electronic_email(credit_note, request=request, target_email=target_email)
                    if result.get('success'):
                        data = {'success': True, 'message': result.get('message')}
                    else:
                        data['error'] = result.get('message')
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Notas Crédito'
        context['list_url'] = reverse_lazy('credit_note_Fe_admin_list')
        context['create_url'] = reverse_lazy('credit_note_Fe_admin_create')
        context['module_name'] = MODULE_NAME
        return context


class CreditNoteFeCreateView(GroupPermissionMixin, CreateView):
    model = CreditNote
    template_name = 'creditnotefe/admin/create.html'
    form_class = CreditNoteForm
    success_url = reverse_lazy('credit_note_Fe_admin_list')
    permission_required = 'add_creditnote'

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', '')
        data = {}
        try:
            if action == 'add':
                with transaction.atomic():
                    company = Company.objects.first()
                    iva = float(company.iva) / 100 if company and company.iva else 0.0

                    credit_note = CreditNote()
                    credit_note.company = company
                    credit_note.employee_id = request.user.id
                    credit_note.iva = iva
                    credit_note.operation_type = request.POST.get('operation_type')
                    credit_note.correction_concept = request.POST.get('correction_concept')
                    credit_note.description = request.POST.get('description', '').strip()
                    credit_note.dscto = 0

                    credit_note.paymentmethod = request.POST.get('paymentmethod')
                    if credit_note.paymentmethod == 'transfer':
                        credit_note.transfermethods = request.POST.get('transfermethods')
                    elif credit_note.paymentmethod == 'mixto':
                        credit_note.nequi_value = float(request.POST.get('nequi_value', 0) or 0)
                        credit_note.daviplata_value = float(request.POST.get('daviplata_value', 0) or 0)
                    else:
                        credit_note.transfermethods = None

                    # La nota crédito no maneja tipo de pago ni vencimiento en
                    # esta vista: siempre se registra de contado.
                    credit_note.typemethods = 'fullpayment'
                    credit_note.expiration_date = None

                    reference_sale = None
                    if credit_note.operation_type == '20':
                        # Nota crédito CON referencia: el cliente y (si aplica) los
                        # ítems provienen de la factura encontrada por su número.
                        bill_number = request.POST.get('reference_bill_number', '').strip()
                        if not bill_number:
                            raise ValidationError('Debe buscar y seleccionar la factura a referenciar')
                        reference_sale = Sale.objects.filter(
                            factus_invoice_id=bill_number, is_electronicinvoice=True
                        ).first()
                        if not reference_sale:
                            raise ValidationError('No se encontró una factura electrónica con ese número')

                        credit_note.reference_sale = reference_sale
                        credit_note.reference_bill_number = reference_sale.factus_invoice_id
                        credit_note.reference_cufe = reference_sale.factus_cufe
                        credit_note.client_id = reference_sale.client_id
                        credit_note.billing_period_start_date = None
                        credit_note.billing_period_end_date = None
                    else:
                        # Nota crédito SIN referencia: cliente elegido manualmente
                        # y periodo de facturación obligatorio.
                        credit_note.client_id = int(request.POST.get('client'))
                        start_date = request.POST.get('billing_period_start_date')
                        end_date = request.POST.get('billing_period_end_date')
                        if not start_date or not end_date:
                            raise ValidationError('Debe indicar el periodo de facturación de la nota crédito')
                        credit_note.billing_period_start_date = start_date
                        credit_note.billing_period_end_date = end_date

                    credit_note.factus_status = 'pending'
                    credit_note.save()

                    # Determinar los ítems a acreditar. La anulación (motivo 2)
                    # siempre debe reflejar EXACTAMENTE lo facturado: se ignora
                    # cualquier edición y se reconstruye desde la factura de
                    # origen, para que el backend nunca dependa de que el
                    # frontend haya bloqueado la tabla correctamente.
                    if credit_note.correction_concept == '2' and reference_sale:
                        source_items = [
                            {
                                'id': sd.product_id,
                                'sale_detail_id': sd.id,
                                'cant': sd.cant,
                                'pvp': float(sd.price),
                                'dscto': float(sd.dscto) * 100,
                            }
                            for sd in reference_sale.saledetail_set.all()
                        ]
                    else:
                        source_items = json.loads(request.POST.get('products', '[]'))

                    if not source_items:
                        raise ValidationError('La nota crédito debe tener al menos 1 producto o servicio')

                    for i in source_items:
                        product = Product.objects.get(pk=i['id'])
                        detail = CreditNoteDetail()
                        detail.credit_note_id = credit_note.id
                        detail.product_id = product.id
                        detail.sale_detail_id = i.get('sale_detail_id')
                        detail.cant = int(i['cant'])
                        detail.price = float(i['pvp'])
                        detail.dscto = float(i.get('dscto', 0)) / 100
                        detail.save()

                        # Reingreso de stock: solo cuando el motivo implica una
                        # devolución física de bienes (1: parcial, 2: anulación
                        # total) y el producto sí maneja inventario. Los ajustes
                        # puramente financieros (3 a 6) nunca mueven stock.
                        if credit_note.correction_concept in STOCK_RESTOCK_CONCEPTS and not product.is_service:
                            product.stock += detail.cant
                            product.save()

                    credit_note.calculate_detail()
                    credit_note.calculate_invoice()

                data = {
                    'print_url': str(reverse_lazy('credit_note_Fe_admin_print', kwargs={'pk': credit_note.id})),
                    'warnings': [],
                }
                target_email = request.POST.get('client_email', '')

                try:
                    numbering_range_id = request.POST.get('numbering_range_id')
                    numbering_range_id = int(numbering_range_id) if numbering_range_id else None
                    factus_response = create_credit_note(
                        credit_note,
                        numbering_range_id=numbering_range_id,
                        target_email=target_email,
                    )
                    if 'error' in factus_response:
                        raise ValidationError(factus_response.get('error'))

                    data_resp = factus_response.get('data', {})
                    # A diferencia de las facturas (cuyos datos vienen anidados en
                    # ``data.bill``), en notas crédito el propio documento va en la
                    # raíz de ``data``; ``data.bill`` es solo un eco de la FACTURA
                    # referenciada, no la nota crédito recién creada.
                    bill_data = data_resp
                    numbering_range = data_resp.get('numbering_range', {})
                    if not bill_data or not bill_data.get('number'):
                        raise ValidationError('Factus no devolvió los datos de la nota crédito creada')
                except Exception:
                    logger.exception('No se pudo generar la nota crédito local %s en Factus', credit_note.id)
                    credit_note.factus_status = 'error'
                    credit_note.save(update_fields=['factus_status'])
                    data['warnings'].append(
                        'La nota crédito se guardó, pero no se pudo enviar a Factus. Revise los registros para reintentarla.'
                    )
                else:
                    try:
                        with transaction.atomic():
                            links_data = bill_data.get('links', {})
                            credit_note.factus_credit_note_number = bill_data.get('number')
                            credit_note.factus_status = bill_data.get('status') or (
                                'validated' if bill_data.get('is_validated') else 'pending'
                            )
                            credit_note.factus_pdf_url = links_data.get('public_url')
                            # DIAN llama "CUDE" (no "CUFE") al código único de las
                            # notas crédito/débito; se conserva el campo factus_cufe
                            # del modelo por reutilizarlo con el mismo propósito.
                            credit_note.factus_cufe = bill_data.get('cude') or bill_data.get('cufe')
                            credit_note.factus_resolution = numbering_range.get('resolution_number')
                            credit_note.factus_prefix = numbering_range.get('prefix')
                            credit_note.factus_range_from = numbering_range.get('from')
                            credit_note.factus_range_to = numbering_range.get('to')
                            credit_note.factus_date_from = numbering_range.get('date_from')
                            credit_note.factus_date_to = numbering_range.get('date_to')
                            credit_note.factus_qr_url = links_data.get('qr')
                            credit_note.save()
                    except Exception:
                        logger.exception(
                            'Factus creó la nota crédito %s, pero no se pudo guardar su respuesta localmente',
                            credit_note.id,
                        )
                        data['warnings'].append(
                            'La nota crédito se guardó y Factus respondió, pero no se pudieron guardar sus datos localmente. Revise los registros.'
                        )
                    else:
                        try:
                            email_result = send_credit_note_electronic_email(credit_note, request=request)
                        except Exception:
                            logger.exception('Error inesperado al enviar el correo de la nota crédito %s', credit_note.id)
                            data['warnings'].append(
                                'La nota crédito electrónica se guardó, pero el correo no pudo enviarse.'
                            )
                        else:
                            if not email_result.get('success'):
                                logger.warning(
                                    'No se pudo enviar el correo de la nota crédito %s: %s',
                                    credit_note.id,
                                    email_result.get('message'),
                                )
                                data['warnings'].append(
                                    'La nota crédito electrónica se guardó, pero el correo no pudo enviarse.'
                                )

            elif action == 'search_invoice':
                bill_number = request.POST.get('bill_number', '').strip()
                if not bill_number:
                    data['error'] = 'Ingrese el número de la factura a buscar'
                else:
                    sale = Sale.objects.filter(
                        factus_invoice_id__iexact=bill_number, is_electronicinvoice=True
                    ).first()
                    if not sale:
                        # Permite encontrarla buscando solo por el consecutivo
                        # (ej. "2519") en vez del número completo con prefijo
                        # (ej. "SETP990002519").
                        sale = Sale.objects.filter(
                            factus_invoice_id__icontains=bill_number, is_electronicinvoice=True
                        ).order_by('-id').first()
                    if not sale:
                        data['error'] = 'No se encontró ninguna factura electrónica con ese número'
                    else:
                        item = sale.toJSON()
                        item['details'] = [d.toJSON() for d in sale.saledetail_set.select_related('product')]
                        data = item

            elif action == 'search_recent_invoices':
                # Alimenta el autocompletado de "Factura Referenciada": al enfocar
                # el campo (sin escribir) muestra las últimas facturas creadas
                # para agilizar la selección sin tener que digitar el número.
                term = request.POST.get('term', '').strip()
                queryset = Sale.objects.filter(is_electronicinvoice=True).exclude(
                    Q(factus_invoice_id__isnull=True) | Q(factus_invoice_id='')
                ).select_related('client')

                if term:
                    queryset = queryset.filter(factus_invoice_id__icontains=term)

                data = []
                for sale in queryset.order_by('-id')[:10]:
                    data.append({
                        'value': sale.factus_invoice_id,
                        'label': f"{sale.factus_invoice_id} — {sale.client.get_full_name()} — $" + f"{float(sale.total):,.2f}",
                        'date_joined': sale.date_joined.strftime('%Y-%m-%d'),
                    })

            elif action == 'search_products':
                ids = json.loads(request.POST.get('ids', '[]'))
                data = []
                term = request.POST.get('term', '')

                queryset = Product.objects.filter(
                    Q(stock__gt=0) | Q(is_service=True)
                ).exclude(id__in=ids)

                if len(term):
                    queryset = queryset.filter(
                        Q(code__icontains=term) | Q(name__icontains=term)
                    )

                queryset = queryset.order_by('code')[:20]

                for i in queryset:
                    item = i.toJSON()
                    item['pvp'] = float(i.pvp)
                    item['value'] = i.get_full_name()
                    item['dscto'] = '0.00'
                    item['total_dscto'] = '0.00'
                    data.append(item)

            elif action == 'search_client':
                data = []
                term = request.POST.get('term', '')
                for i in Client.objects.filter(
                    Q(names__icontains=term) | Q(dni__icontains=term)
                ).order_by('names')[:10]:
                    item = i.toJSON()
                    item['text'] = i.get_full_name()
                    item['email'] = getattr(i, 'email', '') or ''
                    data.append(item)

            elif action == 'create_client':
                form = ClientForm(self.request.POST)
                data = form.save()
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)

        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            response_data = get_numbering_ranges()
            ranges = response_data.get('data', {}).get('data', [])

            active_range = next((r for r in ranges if r.get('document') == 'Nota Crédito' and r.get('is_active')), {})

            prefix = active_range.get('prefix')
            context['factus_range_text'] = str(prefix).strip() if prefix and str(prefix).strip() else ''

            context['factus_current'] = active_range.get('current', 1)
            context['factus_range_id'] = active_range.get('id', '')
        except Exception as e:
            print("ERROR OBTENIENDO RANGOS FACTUS (NOTA CREDITO):", str(e))
            context['factus_range_text'] = ''
            context['factus_current'] = "1"
            context['factus_range_id'] = ''

        context['frmClient'] = ClientForm()
        context['list_url'] = self.success_url
        context['title'] = 'Nuevo registro de una Nota Crédito Electrónica'
        context['action'] = 'add'
        context['company'] = Company.objects.first()
        context['module_name'] = MODULE_NAME
        return context


class CreditNoteFeDeleteView(GroupPermissionMixin, DeleteView):
    model = CreditNote
    template_name = 'delete.html'
    success_url = reverse_lazy('credit_note_Fe_admin_list')
    permission_required = 'delete_creditnote'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.get_object().delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminación de una Nota Crédito'
        context['list_url'] = self.success_url
        context['module_name'] = MODULE_NAME
        return context


@method_decorator(xframe_options_exempt, name='dispatch')
class CreditNoteFePrintView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            credit_note = CreditNote.objects.get(id=self.kwargs['pk'])

            company = None
            if credit_note.company_id:
                company = Company.objects.filter(id=credit_note.company_id).first()

            if not company:
                company = Company.objects.filter(is_active=True).first() or Company.objects.first()

            c_name = company.name if company else "Compañía sin nombre"
            c_ruc = company.ruc if company else "N/A"
            c_email = company.email if company else ""
            c_address = company.address if company else ""
            c_image = company.image.url if (company and company.image and hasattr(company.image, 'url')) else None

            qr_data_to_encode = credit_note.factus_qr_url if credit_note.factus_qr_url else credit_note.factus_cufe
            qr_base64 = generate_qr_base64_from_url(qr_data_to_encode)

            context = {
                'credit_note': credit_note,
                'company': company,
                'company_name': c_name,
                'company_ruc': c_ruc,
                'company_email': c_email,
                'company_address': c_address,
                'company_image_path': c_image,
                'qr_base64': qr_base64,
                'height': 450 + credit_note.creditnotedetail_set.all().count() * 10
            }
            return render(request, 'creditnotefe/format/invoice.html', context)
        except CreditNote.DoesNotExist:
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)


class CreditNoteFeDownloadPdfView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            credit_note = CreditNote.objects.get(id=self.kwargs['pk'])
            if not credit_note.factus_credit_note_number:
                return HttpResponse('Esta nota crédito aún no ha sido validada por Factus', status=400)

            content = download_credit_note_pdf(credit_note.factus_credit_note_number)
            if not content or isinstance(content, dict):
                message = content.get('error') if isinstance(content, dict) else 'No fue posible descargar el PDF'
                return HttpResponse(message, status=502)

            response = HttpResponse(content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="nota_credito_{credit_note.factus_credit_note_number}.pdf"'
            return response
        except CreditNote.DoesNotExist:
            return HttpResponse('La nota crédito no existe', status=404)
