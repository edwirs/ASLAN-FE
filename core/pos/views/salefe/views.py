import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, FormView, TemplateView
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from django.conf import settings

from core.pos.forms import *
from core.pos.utilities import printer
from core.reports.forms import ReportForm
from core.security.mixins import GroupPermissionMixin
from core.pos.choices import PAYMENTMETHODS, TRANSFERMETHODS
from core.services.factus import create_invoice, get_numbering_ranges, download_invoice_xml
from core.services.services import send_sale_electronic_invoice_email, generate_qr_base64_from_url

MODULE_NAME = 'Ventas FE'
logger = logging.getLogger(__name__)


class SaleFeListView(GroupPermissionMixin, FormView):
    template_name = 'salefe/admin/list.html'
    form_class = ReportForm
    permission_required = 'view_sale'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action', '')
        try:
            if action == 'search':
                data = []
                start_date = request.POST.get('start_date', '')
                end_date = request.POST.get('end_date', '')
                queryset = Sale.objects.filter(is_electronicinvoice=True)
                if len(start_date) and len(end_date):
                    queryset = queryset.filter(date_joined__range=[start_date, end_date])
                for i in queryset.order_by('-id'):
                    data.append(i.toJSON())
            elif action == 'search_detail_products':
                data = []
                for i in SaleDetail.objects.filter(sale_id=request.POST.get('id')):
                    data.append(i.toJSON())
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Ventas'
        context['list_url'] = reverse_lazy('sale_Fe_admin_list')
        context['create_url'] = reverse_lazy('sale_Fe_admin_create')
        context['module_name'] = MODULE_NAME
        context['sale_form'] = SaleForm()
        return context


def get_sale_Fe(request, pk):
    try:
        sale = Sale.objects.get(pk=pk)
        data = sale.toJSON()
        return JsonResponse(data, safe=False)
    except Sale.DoesNotExist:
        return JsonResponse({'error': 'La venta no existe'}, status=404)


def update_sale_Fe(request, pk):
    try:
        sale = Sale.objects.get(pk=pk)
        sale.paymentmethod = request.POST.get('paymentmethod')
        if sale.paymentmethod == 'transfer':
            sale.transfermethods = request.POST.get('transfermethods')
        else:
            sale.transfermethods = None
            
        sale.total = float(request.POST.get('total', 0) or 0)
        sale.cash = float(request.POST.get('cash', 0) or 0)
        sale.change = float(request.POST.get('change', 0) or 0)
        sale.propina = float(request.POST.get('propina', 0) or 0)
        sale.save()
        return JsonResponse({"success": True})
    except Sale.DoesNotExist:
        return JsonResponse({"error": "Venta no encontrada"})
    except Exception as e:
        return JsonResponse({"error": str(e)})


class SaleFeCreateView(GroupPermissionMixin, CreateView):
    model = Sale
    template_name = 'salefe/admin/create.html'
    form_class = SaleForm
    success_url = reverse_lazy('sale_Fe_admin_list')
    permission_required = 'add_sale'

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', '')
        data = {}
        try:
            if action == 'add':
                # La venta local debe confirmarse antes de interactuar con servicios
                # externos. Así, una caída de Factus o del correo no la revierte.
                with transaction.atomic():
                    company = Company.objects.first()
                    iva = float(company.iva) / 100 if company and company.iva else 0.0

                    sale = Sale()
                    sale.company = company
                    sale.employee_id = request.user.id
                    sale.client_id = int(request.POST.get('client'))
                    sale.iva = iva
                    sale.dscto = float(request.POST.get('dscto', 0) or 0) / 100
                    sale.cash = float(request.POST.get('cash', 0) or 0)
                    sale.change = float(request.POST.get('change', 0) or 0)
                    sale.paymentmethod = request.POST.get('paymentmethod')

                    if sale.paymentmethod == 'transfer':
                        sale.transfermethods = request.POST.get('transfermethods')
                    elif sale.paymentmethod == 'mixto':
                        sale.nequi_value = float(request.POST.get('nequi_value', 0) or 0)
                        sale.daviplata_value = float(request.POST.get('daviplata_value', 0) or 0)
                    else:
                        sale.transfermethods = None

                    sale.typemethods = request.POST.get('typemethods')
                    if sale.typemethods == 'credit':
                        sale.expiration_date = request.POST.get('expiration_date')
                    else:
                        sale.expiration_date = None

                    sale.service_type = request.POST.get('service_type')
                    sale.propina = float(request.POST.get('propina', 0) or 0)
                    sale.description = request.POST.get('description', '').strip()
                    sale.is_electronicinvoice = True
                    sale.factus_status = 'pending'
                    sale.save()

                    # Guardar detalles de productos
                    for i in json.loads(request.POST.get('products', '[]')):
                        product = Product.objects.get(pk=i['id'])
                        detail = SaleDetail()
                        detail.sale_id = sale.id
                        detail.product_id = product.id
                        detail.cant = int(i['cant'])
                        detail.price = float(i['pvp'])
                        detail.dscto = float(i['dscto']) / 100
                        detail.save()

                        # Descuento de stock
                        detail.product.stock -= detail.cant
                        detail.product.save()

                        # Manejo de productos automáticos
                        auto_products = ProductAutoAdd.objects.filter(trigger_product=product)
                        for auto in auto_products:
                            auto_product = auto.auto_product
                            auto_product.stock -= auto.quantity * detail.cant
                            auto_product.save()

                    # Recalcular totales de factura
                    sale.calculate_detail()
                    sale.calculate_invoice()

                    # Guardar el adjunto junto con la venta local, antes de salir
                    # de la transacción que confirma venta, detalle e inventario.
                    files_list = request.FILES.getlist('pdf_files')
                    if files_list:
                        sale.attachment = files_list[0]
                        sale.save(update_fields=['attachment'])

                # Desde este punto la venta ya está confirmada en la base local.
                data = {
                    'print_url': str(reverse_lazy('sale_Fe_admin_print_invoice', kwargs={'pk': sale.id})),
                    'warnings': [],
                }
                target_email = request.POST.get('client_email', '')

                try:
                    numbering_range_id = request.POST.get('numbering_range_id')
                    numbering_range_id = int(numbering_range_id) if numbering_range_id else 8
                    factus_response = create_invoice(
                        sale,
                        numbering_range_id=numbering_range_id,
                        target_email=target_email,
                    )
                    if 'error' in factus_response:
                        raise ValidationError(factus_response.get('error'))

                    data_resp = factus_response.get('data', {})
                    # Factus v2 retorna los datos de la factura directamente en
                    # ``data``. Se conserva el fallback para respuestas antiguas.
                    bill_data = data_resp.get('bill', data_resp)
                    numbering_range = data_resp.get('numbering_range', {})
                    if not bill_data or not bill_data.get('number'):
                        raise ValidationError('Factus no devolvió los datos de la factura creada')
                except Exception:
                    logger.exception('No se pudo facturar la venta local %s en Factus', sale.id)
                    sale.factus_status = 'error'
                    sale.save(update_fields=['factus_status'])
                    data['warnings'].append(
                        'La venta se guardó, pero no se pudo enviar a Factus. Revise los registros para reintentarla.'
                    )
                else:
                    try:
                        # La actualización de datos de Factus se confirma antes
                        # de intentar el correo, para que este nunca dependa de
                        # Gmail ni deje datos de Factus sin persistir.
                        with transaction.atomic():
                            links_data = bill_data.get('links', {})
                            sale.factus_invoice_id = bill_data.get('number')
                            sale.factus_status = bill_data.get('status') or (
                                'validated' if bill_data.get('is_validated') else 'pending'
                            )
                            sale.factus_pdf_url = links_data.get('public_url')
                            sale.factus_cufe = bill_data.get('cufe')
                            sale.factus_resolution = numbering_range.get('resolution_number')
                            sale.factus_prefix = numbering_range.get('prefix')
                            sale.factus_range_from = numbering_range.get('from')
                            sale.factus_range_to = numbering_range.get('to')
                            sale.factus_date_from = numbering_range.get('date_from')
                            sale.factus_date_to = numbering_range.get('date_to')
                            sale.factus_qr_url = links_data.get('qr')
                            sale.save()
                    except Exception:
                        logger.exception(
                            'Factus creó la factura de la venta %s, pero no se pudo guardar su respuesta localmente',
                            sale.id,
                        )
                        data['warnings'].append(
                            'La venta se guardó y Factus respondió, pero no se pudieron guardar sus datos localmente. Revise los registros.'
                        )
                    else:
                        # El servicio captura sus propios errores, pero se protege
                        # también esta llamada para que Gmail jamás revierta la venta.
                        try:
                            email_result = send_sale_electronic_invoice_email(sale, request=request)
                        except Exception:
                            logger.exception('Error inesperado al enviar el correo de la factura %s', sale.id)
                            data['warnings'].append(
                                'La venta y la factura electrónica se guardaron, pero el correo no pudo enviarse.'
                            )
                        else:
                            if not email_result.get('success'):
                                logger.warning(
                                    'No se pudo enviar el correo de la factura %s: %s',
                                    sale.id,
                                    email_result.get('message'),
                                )
                                data['warnings'].append(
                                    'La venta y la factura electrónica se guardaron, pero el correo no pudo enviarse.'
                                )

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
            elif action == 'test_numbering_ranges':
                ranges_response = get_numbering_ranges()
                data = ranges_response
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)

        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_final_consumer(self):
        queryset = Client.objects.filter(dni='222222222222')
        if queryset.exists():
            client = queryset[0]
            item = client.toJSON()
            item['text'] = client.get_full_name()
            item['email'] = getattr(client, 'email', '') or ''
            return json.dumps(item)
        return {}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            response_data = get_numbering_ranges()
            ranges = response_data.get('data', {}).get('data', [])
            
            active_range = next((r for r in ranges if r.get('document') == 'Factura de Venta' and r.get('is_active')), {})
            
            prefix = active_range.get('prefix')
            from_num = active_range.get('from', 0)
            to_num = active_range.get('to', 0)
            
            if prefix and str(prefix).strip():
                context['factus_range_text'] = f"{prefix} ({from_num} - {to_num})"
            else:
                context['factus_range_text'] = f"({from_num} - {to_num})"
                
            context['factus_current'] = active_range.get('current', 1)
            # Pasamos el ID real obtenido de la API al contexto para asignarlo al campo oculto
            context['factus_range_id'] = active_range.get('id', 8)
            templates_dict = {
                t.code: t.content 
                for t in ObservationTemplate.objects.filter(is_active=True)
            }
            context['observation_templates'] = templates_dict
        except Exception as e:
            print("ERROR OBTENIENDO RANGOS FACTUS:", str(e))
            context['factus_range_text'] = "(0 - 0)"
            context['factus_current'] = "1"
            context['factus_range_id'] = 8

        context['frmClient'] = ClientForm()
        context['list_url'] = self.success_url
        context['title'] = 'Nuevo registro de una Venta Electrónica'
        context['action'] = 'add'
        context['company'] = Company.objects.first()
        context['final_consumer'] = self.get_final_consumer()
        context['module_name'] = MODULE_NAME
        return context


class SaleFeDeliveredUpdateView(View):
    def post(self, request, *args, **kwargs):
        data = {}
        if not request.user.has_perm('app_label.delivered_sale'):
            return JsonResponse({'error': 'No tienes permiso para hacer esto'}, status=403)
        try:
            sale_id = kwargs.get('pk')
            sale = Sale.objects.get(pk=sale_id)
            sale.delivered = not sale.delivered
            sale.save()
            data['success'] = True
            data['delivered'] = sale.delivered
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)


class SaleFeDeleteView(GroupPermissionMixin, DeleteView):
    model = Sale
    template_name = 'delete.html'
    success_url = reverse_lazy('sale_Fe_admin_list')
    permission_required = 'delete_sale'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.get_object().delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminación de una Venta'
        context['list_url'] = self.success_url
        context['module_name'] = MODULE_NAME
        return context


@method_decorator(xframe_options_exempt, name='dispatch')
class SaleFePrintInvoiceView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            sale = Sale.objects.get(id=self.kwargs['pk'])
            
            # 1. Búsqueda blindada de la compañía (igual que en el servicio de PDF)
            company = None
            if sale.company_id:
                company = Company.objects.filter(id=sale.company_id).first()
                
            if not company:
                company = Company.objects.filter(is_active=True).first() or Company.objects.first()

            # 2. Variables planas de respaldo
            c_name = company.name if company else "Compañía sin nombre"
            c_ruc = company.ruc if company else "N/A"
            c_email = company.email if company else ""
            c_address = company.address if company else ""
            c_image = company.image.url if (company and company.image and hasattr(company.image, 'url')) else None

            qr_data_to_encode = sale.factus_qr_url if sale.factus_qr_url else sale.factus_cufe
            qr_base64 = generate_qr_base64_from_url(qr_data_to_encode)

            context = {
                'sale': sale,
                'company': company,
                'company_name': c_name,
                'company_ruc': c_ruc,
                'company_email': c_email,
                'company_address': c_address,
                'company_image_path': c_image, # En HTML web usamos .url en vez de .path
                'qr_base64': qr_base64,
                'height': 450 + sale.saledetail_set.all().count() * 10
            }
            return render(request, 'salefe/format/invoice.html', context)
        except Sale.DoesNotExist:
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
