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

from core.pos.forms import *
from core.pos.utilities import printer
from core.reports.forms import ReportForm
from core.pos.stock_lines import deduct_line, parse_quantity, resolve_lines
from core.security.mixins import GroupPermissionMixin
from core.pos.choices import PAYMENTMETHODS, TRANSFERMETHODS

MODULE_NAME = 'Ventas'

class SaleListView(GroupPermissionMixin, FormView):
    template_name = 'sale/admin/list.html'
    form_class = ReportForm
    permission_required = 'view_sale'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                start_date = request.POST['start_date']
                end_date = request.POST['end_date']
                service_type = request.POST['service_type']
                queryset = Sale.objects.filter(is_electronicinvoice=False)
                if len(start_date) and len(end_date):
                    queryset = queryset.filter(date_joined__range=[start_date, end_date])
                if service_type:
                    queryset = queryset.filter(service_type=service_type)
                for i in queryset.order_by('-id'):
                    data.append(i.toJSON())
            elif action == 'search_detail_products':
                data = []
                for i in SaleDetail.objects.filter(sale_id=request.POST['id']):
                    data.append(i.toJSON())
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Ventas'
        context['list_url'] = reverse_lazy('sale_admin_list')
        context['create_url'] = reverse_lazy('sale_admin_create')
        context['module_name'] = MODULE_NAME
        context['sale_form'] = SaleForm()
        return context
    
def get_sale(request, pk):
    try:
        sale = Sale.objects.get(pk=pk)
        data = sale.toJSON()
        return JsonResponse(data, safe=False)
    except Sale.DoesNotExist:
        return JsonResponse({'error': 'La venta no existe'}, status=404)
    
def update_sale(request, pk):
    try:
        sale = Sale.objects.get(pk=pk)
        sale.paymentmethod = request.POST.get('paymentmethod')

        nequi_value = float(request.POST.get('nequi_value') or 0)
        daviplata_value = float(request.POST.get('daviplata_value') or 0)

        if sale.paymentmethod in ['transfer', 'mixto']:
            sale.transfermethods = request.POST.get('transfermethods')
        else:
            sale.transfermethods = None

        # siempre actualizar valores
        sale.nequi_value = nequi_value
        sale.daviplata_value = daviplata_value

        sale.total = request.POST.get('total')
        sale.cash = request.POST.get('cash')
        sale.change = request.POST.get('change')
        sale.propina = request.POST.get('propina')

        sale.save()
        return JsonResponse({"success": True})
    except Sale.DoesNotExist:
        return JsonResponse({"error": "Venta no encontrada"})
    except Exception as e:
        return JsonResponse({"error": str(e)})


class SaleCreateView(GroupPermissionMixin, CreateView):
    model = Sale
    template_name = 'sale/admin/create.html'
    form_class = SaleForm
    success_url = reverse_lazy('sale_admin_create')
    permission_required = 'add_sale'

    def post(self, request, *args, **kwargs):
        action = request.POST['action']
        data = {}
        try:
            if action == 'add':
                with transaction.atomic():
                    company = Company.objects.first()
                    iva = float(company.iva) / 100
                    sale = Sale()
                    sale.company = company
                    sale.employee_id = request.user.id
                    sale.client_id = int(request.POST['client'])
                    sale.iva = iva
                    sale.dscto = float(request.POST['dscto']) / 100
                    sale.cash = float(request.POST['cash'])
                    sale.change = float(request.POST['change'])
                    sale.paymentmethod = (request.POST['paymentmethod'])
                    if sale.paymentmethod == 'transfer':
                        sale.transfermethods = (request.POST['transfermethods'])
                    elif sale.paymentmethod == 'mixto':
                        sale.nequi_value = (request.POST['nequi_value'])
                        sale.daviplata_value = (request.POST['daviplata_value'])
                    else:
                        sale.transfermethods = None
                    sale.typemethods = (request.POST['typemethods'])
                    if sale.typemethods == 'credit':
                        sale.expiration_date = (request.POST['expiration_date'])
                    else:
                        sale.expiration_date = None
                    description = request.POST.get('description', '')
                    if description:
                        sale.description = description
                    sale.service_type = (request.POST['service_type'])
                    sale.propina = float(request.POST['propina'])
                    sale.save()
                    # 🔥 ABRIR CAJÓN SOLO SI APLICA
                    if sale.paymentmethod in ['cash', 'mixto']:
                        printer.open_cash_drawer()
                    # El precio, el factor y el stock salen del catálogo (producto o presentación elegida);
                    # solo quien tiene permiso de editar precios puede cambiar el precio de la línea.
                    can_edit_price = request.user.has_perm('pos.edit_sale_price')
                    for line in resolve_lines(json.loads(request.POST['products']), allow_price_override=can_edit_price):
                        product, presentation = line['product'], line['presentation']
                        detail = SaleDetail()
                        detail.sale_id = sale.id
                        detail.product_id = product.id
                        detail.presentation = presentation
                        detail.presentation_name = line['presentation_name']
                        detail.factor = line['factor']
                        detail.own_stock = line['own_stock']
                        detail.cost = product.cost_per_sale_unit(presentation, line['factor'], line['own_stock'])
                        detail.cant = line['cant']
                        detail.price = float(line['price'])
                        detail.dscto = float(line['dscto']) / 100
                        detail.save()
                        sale.calculate_detail()
                        # Descuenta del stock del producto o de la variante, y de los productos automáticos
                        deduct_line(line)

                    sale.calculate_invoice()
                    data = {'print_url': str(reverse_lazy('sale_admin_print_invoice', kwargs={'pk': sale.id}))}
            elif action == 'search_products':
                ids = json.loads(request.POST['ids'])
                data = []
                term = request.POST['term']
                # En stock por variante, el producto sirve si alguna variante activa tiene existencias.
                variants_in_stock = Q(uses_presentations=True, presentation_mode=Product.MODE_VARIANTS,
                                      presentations__is_active=True, presentations__stock__gt=0)
                queryset = (Product.objects.filter(Q(stock__gt=0) | Q(is_service=True) | variants_in_stock)
                            .exclude(id__in=ids).distinct().order_by('code'))
                if len(term):
                    # Coincidencia exacta en code
                    exact_matches = queryset.filter(code__iexact=term)

                    # Unimos y limitamos a 10
                    queryset = (exact_matches).order_by('code')[:20]
                for i in queryset:
                    item = i.toJSON()
                    item['pvp'] = float(i.pvp)
                    item['value'] = i.get_full_name()
                    item['dscto'] = '0.00'
                    item['total_dscto'] = '0.00'
                    data.append(item)
            elif action == 'search_client':
                data = []
                term = request.POST['term']
                for i in Client.objects.filter(Q(names__icontains=term) | Q(dni__icontains=term)).order_by('names')[0:10]:
                    data.append(i.toJSON())
            elif action == 'create_client':
                with transaction.atomic():
                    form = ClientForm(self.request.POST)
                    contacts_formset = ClientContactFormSet(self.request.POST)
                    
                    if form.is_valid() and contacts_formset.is_valid():
                        client = form.save(commit=False)
                        client.save()
                        
                        contacts_formset.instance = client
                        contacts_formset.save()
                        
                        # Retornamos el objeto serializado del cliente recién creado
                        data = client.toJSON()
                    else:
                        errors = {}
                        if form.errors:
                            errors.update(form.errors)
                        if contacts_formset.errors:
                            errors.update({'contacts': contacts_formset.errors})
                        data['error'] = errors
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_final_consumer(self):
        queryset = Client.objects.filter(dni='222222222222')
        if queryset.exists():
            return json.dumps(queryset[0].toJSON())
        return {}

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['frmClient'] = ClientForm()
        context['frmClientContacts'] = ClientContactFormSet() # Añadido para el contexto si se requiere renderizar en modal o vista
        context['list_url'] = self.success_url
        context['title'] = 'Nuevo registro de una Venta'
        context['action'] = 'add'
        context['company'] = Company.objects.first()
        context['final_consumer'] = self.get_final_consumer()
        # Solo los productos con presentaciones activas necesitan el selector de presentación.
        context['product_options'] = {
            p.pk: p.sale_options()
            for p in Product.objects.filter(is_active=True, uses_presentations=True,
                                            presentations__is_active=True).distinct()
        }
        context['module_name'] = MODULE_NAME
        return context

class SaleDeliveredUpdateView(View):
    def post(self, request, *args, **kwargs):
        data = {}
        if not request.user.has_perm('app_label.delivered_sale'):
            return JsonResponse({'error': 'No tienes permiso para hacer esto'}, status=403)
        try:
            sale_id = kwargs.get('pk')
            sale = Sale.objects.get(pk=sale_id)
            sale.delivered = not sale.delivered  # Cambia el valor
            sale.save()
            data['success'] = True
            data['delivered'] = sale.delivered
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

class SaleDeleteView(GroupPermissionMixin, DeleteView):
    model = Sale
    template_name = 'delete.html'
    success_url = reverse_lazy('sale_admin_list')
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
class SalePrintInvoiceView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            sale = Sale.objects.get(id=self.kwargs['pk'])
            context = {
                'sale': sale,
                'height': 450 + sale.saledetail_set.all().count() * 10
            }
            return render(request, 'sale/format/ticket.html', context)
        except Sale.DoesNotExist:
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)