import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, FormView, TemplateView
from django.shortcuts import get_object_or_404, render
from django.db.models import Count
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from django.conf import settings

from core.pos import salefe_service
from core.pos.forms import *
from core.pos.sale_deletion import delete_sale
from core.pos.utilities import printer
from core.reports.forms import ReportForm
from core.pos.stock_lines import parse_quantity
from core.security.mixins import GroupPermissionMixin
from core.pos.choices import PAYMENTMETHODS, TRANSFERMETHODS
from core.services.factus import (create_invoice, get_active_numbering_range, get_numbering_ranges, download_invoice_xml,
                                  download_invoice_pdf)
from core.services.services import send_sale_electronic_invoice_email, generate_qr_base64_from_url

MODULE_NAME = 'Ventas FE'
logger = logging.getLogger(__name__)


class SaleFeListView(GroupPermissionMixin, FormView):
    template_name = 'salefe/admin/list.html'
    form_class = ReportForm
    permission_required = 'pos.view_electronic_invoice'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action', '')
        try:
            if action == 'search':
                data = []
                start_date = request.POST.get('start_date', '')
                end_date = request.POST.get('end_date', '')
                queryset = Sale.objects.filter(is_electronicinvoice=True).annotate(n_payments=Count('salecreditpayment'))
                if len(start_date) and len(end_date):
                    queryset = queryset.filter(date_joined__range=[start_date, end_date])
                for i in queryset.order_by('-id'):
                    item = i.toJSON()
                    item['validated'] = salefe_service.is_validated(i)
                    # Se edita solo mientras no esté validada ni tenga abonos
                    item['editable'] = not item['validated'] and not i.n_payments
                    data.append(item)
            elif action == 'validate':
                if not request.user.has_perm('pos.validate_electronic_invoice'):
                    return JsonResponse({'error': 'No tiene permiso para validar facturas electrónicas.'}, status=403)
                result = salefe_service.validate_sale(request.POST.get('id'), request=request)
                data = {'success': True, 'number': result['number'], 'warnings': result['warnings'],
                        'message': f'Factura validada por la DIAN: N° {result["number"]}'}
            elif action == 'radian_events':
                if not request.user.has_perm('pos.radian_electronic_invoice'):
                    return JsonResponse({'error': 'No tiene permiso para consultar eventos RADIAN.'}, status=403)
                data = salefe_service.radian_events(salefe_service.get_fe_sale(request.POST.get('id')))
            elif action == 'radian_tacit':
                if not request.user.has_perm('pos.radian_electronic_invoice'):
                    return JsonResponse({'error': 'No tiene permiso para registrar eventos RADIAN.'}, status=403)
                person = {key: request.POST.get(key, '') for key in (
                    'identification_document_code', 'identification', 'dv', 'first_name', 'last_name', 'job_title',
                    'organization_department')}
                data = salefe_service.register_tacit_acceptance(salefe_service.get_fe_sale(request.POST.get('id')), person)
                data['message'] = 'La aceptación tácita quedó registrada.'
            elif action == 'search_detail_products':
                data = []
                for i in SaleDetail.objects.filter(sale_id=request.POST.get('id')):
                    data.append(i.toJSON())
            elif action == 'get_client_emails':
                sale = Sale.objects.select_related('client').get(pk=request.POST.get('id'))
                emails = []
                if sale.client.email:
                    emails.append({
                        'value': sale.client.email,
                        'label': f"Principal — {sale.client.email}",
                    })
                for contact in sale.client.contacts.exclude(email='').exclude(email__isnull=True):
                    label = contact.names
                    if contact.position:
                        label += f" ({contact.position})"
                    emails.append({'value': contact.email, 'label': f"{label} — {contact.email}"})
                data = {
                    'client_name': sale.client.get_full_name(),
                    'emails': emails,
                }
            elif action == 'resend_email':
                sale = Sale.objects.get(pk=request.POST.get('id'))
                target_email = request.POST.get('email', '').strip()
                if not target_email:
                    data['error'] = 'Debe seleccionar un correo de destino'
                else:
                    result = send_sale_electronic_invoice_email(sale, request=request, target_email=target_email)
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
        context['title'] = 'Listado de Ventas'
        context['list_url'] = reverse_lazy('sale_Fe_admin_list')
        context['create_url'] = reverse_lazy('sale_Fe_admin_create')
        context['module_name'] = MODULE_NAME
        context['sale_form'] = SaleForm()
        user = self.request.user
        context['can'] = {
            'edit': user.has_perm('pos.change_electronic_invoice'),
            'validate': user.has_perm('pos.validate_electronic_invoice'),
            'radian': user.has_perm('pos.radian_electronic_invoice'),
        }
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
    permission_required = 'pos.add_electronic_invoice'

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', '')
        data = {}
        try:
            if action == 'add':
                # «Guardar» registra la factura SOLO en la base local. Se envía a Factus después, con «Validar».
                sale = salefe_service.save_from_request(request)
                data = {'print_url': str(reverse_lazy('sale_Fe_admin_print_invoice', kwargs={'pk': sale.id})), 'id': sale.id,
                        'warnings': []}
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
            elif action == 'numbering_preview':
                # Resolución, rango y consecutivo que sigue, solo para mostrarlos (no reserva ni consume nada en Factus)
                active = get_active_numbering_range()
                if 'error' in active:
                    data = {'range': None, 'error': active['error']}
                else:
                    current = active.get('current') or 0
                    data = {'range': {
                        'id': active.get('id'), 'prefix': active.get('prefix') or '', 'from': active.get('from'), 'to': active.get('to'),
                        'current': current, 'resolution_number': active.get('resolution_number'),
                        'date_from': active.get('start_date') or active.get('date_from'),
                        'date_to': active.get('end_date') or active.get('date_to'),
                        'exhausted': bool(active.get('to') and current and int(current) > int(active['to'])),
                    }}
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
        company = Company.objects.first()
        context['observation_templates'] = {t.code: t.content for t in ObservationTemplate.objects.filter(is_active=True)}
        context['frmClient'] = ClientForm()
        context['list_url'] = self.success_url
        context['title'] = 'Nuevo registro de una Venta Electrónica'
        context['action'] = 'add'
        context['company'] = company
        # Datos reales de la compañía para la previsualización (nada escrito a mano en la pantalla)
        context['company_info'] = {
            'name': company.name, 'nit': company.ruc, 'address': company.address, 'mobile': company.mobile,
            'phone': company.phone, 'email': company.email, 'website': company.website,
            'logo': company.get_image_url() if company.image else '',
        } if company else {}
        context['final_consumer'] = self.get_final_consumer()
        context['module_name'] = MODULE_NAME
        return context


class SaleFeUpdateView(SaleFeCreateView):
    """Edita una factura electrónica que todavía NO fue validada (cliente, valores, cantidades, pago...)."""
    permission_required = 'pos.change_electronic_invoice'

    def dispatch(self, request, *args, **kwargs):
        self.sale = get_object_or_404(Sale, pk=kwargs['pk'], is_electronicinvoice=True)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Primero el permiso (el mismo criterio de la pantalla de crear) y después el estado de la factura
        if not request.user.is_superuser:
            group = request.session.get('group')
            if not group or not all(self.has_permission(group, perm) for perm in self.get_permissions()):
                messages.error(request, 'Tu perfil no cuenta con el permiso necesario para ingresar')
                return HttpResponseRedirect(self.get_last_url())
        try:
            salefe_service.check_can_edit(self.sale)
        except salefe_service.SaleFeError as e:
            return HttpResponse(
                f'<html><body style="font-family:sans-serif;max-width:560px;margin:60px auto">'
                f'<h3>No se puede editar esta factura</h3><p>{e}</p><p><a href="{self.success_url}">Volver al listado</a></p>'
                f'</body></html>', status=409)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if request.POST.get('action', '') != 'edit':
            return super().post(request, *args, **kwargs)   # búsqueda de productos y clientes, crear cliente...
        # GroupPermissionMixin solo revisa el permiso al abrir la pantalla; guardar cambios también lo exige.
        if not request.user.has_perm('pos.change_electronic_invoice'):
            return JsonResponse({'error': 'No tiene permiso para editar facturas electrónicas.'}, status=403)
        data = {}
        try:
            sale = salefe_service.save_from_request(request, sale=self.sale)
            data = {'print_url': str(reverse_lazy('sale_Fe_admin_print_invoice', kwargs={'pk': sale.id})), 'id': sale.id,
                    'warnings': []}
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def sale_payload(self):
        """La factura tal como la necesita el formulario para cargarla (sin tocar nada de Factus)."""
        sale = self.sale
        lines = []
        for d in sale.saledetail_set.select_related('product').order_by('id'):
            item = d.product.toJSON()
            item.update({'short_name': d.product.get_short_name(), 'cant': float(d.cant), 'pvp': float(d.price),
                         'dscto': float(d.dscto) * 100, 'value': d.product.get_full_name()})
            lines.append(item)
        client = sale.client
        return {
            'id': sale.id,
            # Todos los datos del cliente (documento, dirección, municipio...): la previsualización los muestra
            'client': {**client.toJSON(), 'id': client.id, 'text': client.get_full_name(), 'email': client.email or ''},
            'date_joined': sale.date_joined.strftime('%Y-%m-%d'),
            'paymentmethod': sale.paymentmethod, 'transfermethods': sale.transfermethods,
            'typemethods': sale.typemethods, 'service_type': sale.service_type,
            'expiration_date': sale.expiration_date.strftime('%Y-%m-%d') if sale.expiration_date else '',
            'dscto': float(sale.dscto) * 100, 'cash': float(sale.cash or 0), 'change': float(sale.change or 0),
            'propina': float(sale.propina or 0), 'nequi_value': float(sale.nequi_value or 0),
            'daviplata_value': float(sale.daviplata_value or 0), 'description': sale.description or '',
            'attachment': sale.attachment.name.split('/')[-1] if sale.attachment else '',
            'products': lines,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edición de la Venta Electrónica #{self.sale.id}'
        context['action'] = 'edit'
        context['edit_sale'] = self.sale_payload()
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
    permission_required = 'pos.delete_electronic_invoice'

    def post(self, request, *args, **kwargs):
        data = {}
        # GroupPermissionMixin solo revisa el permiso al abrir la pantalla; aquí se exige también al eliminar.
        if not request.user.has_perm('pos.delete_sale'):
            return JsonResponse({'error': 'No tienes permiso para hacer esto'}, status=403)
        try:
            # Devuelve el stock y no permite eliminar si hay abonos, notas crédito o factura ya enviada a Factus.
            delete_sale(self.get_object().pk)
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


class SaleFeDownloadPdfView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            sale = Sale.objects.get(id=self.kwargs['pk'])
            if not sale.factus_invoice_id:
                return HttpResponse('Esta factura aún no ha sido validada por Factus', status=400)

            content = download_invoice_pdf(sale.factus_invoice_id)
            if not content or isinstance(content, dict):
                message = content.get('error') if isinstance(content, dict) else 'No fue posible descargar el PDF'
                return HttpResponse(message, status=502)

            response = HttpResponse(content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="factura_{sale.factus_invoice_id}.pdf"'
            return response
        except Sale.DoesNotExist:
            return HttpResponse('La venta no existe', status=404)
