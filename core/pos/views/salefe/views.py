import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
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
from core.services.factus import create_invoice

MODULE_NAME = 'Ventas FE'


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
    success_url = reverse_lazy('sale_Fe_admin_create')
    permission_required = 'add_sale'

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', '')
        data = {}
        try:
            if action == 'add':
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
                    sale.is_electronicinvoice = True
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

                    # Enviar a Factus
                    factus_response = create_invoice(sale)
                    detail_resp = factus_response.get("detail", {})
                    data_resp = detail_resp.get("data", {})

                    if data_resp:
                        bill_data = data_resp.get("bill", {})
                        numbering_range = data_resp.get("numbering_range", {})

                        sale.factus_invoice_id = bill_data.get("number")
                        sale.factus_status = bill_data.get("status")
                        sale.factus_pdf_url = bill_data.get("public_url")
                        sale.factus_cufe = bill_data.get("cufe")
                        sale.factus_resolution = numbering_range.get("resolution_number")
                        sale.factus_qr_url = bill_data.get("qr")
                    else:
                        sale.factus_status = "error"
                    
                    sale.save()
                    data = {'print_url': str(reverse_lazy('sale_Fe_admin_print_invoice', kwargs={'pk': sale.id}))}

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
                    # Forzamos enviar el texto y el email para Select2
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
        context = super().get_context_data()
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
            context = {
                'sale': sale,
                'height': 450 + sale.saledetail_set.all().count() * 10
            }
            return render(request, 'salefe/format/ticket.html', context)
        except Sale.DoesNotExist:
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)