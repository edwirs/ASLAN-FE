import json
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, FormView, TemplateView

from core.pos.forms import *
from core.pos.stock_lines import deduct_line, resolve_lines
from core.pos.utilities import printer
from core.reports.forms import ReportForm
from core.security.mixins import GroupPermissionMixin

MODULE_NAME = 'Ventas Rápidas'

class BarCreateView(GroupPermissionMixin, CreateView):
    model = Sale
    template_name = 'bar/admin/create.html'
    form_class = BarForm
    success_url = reverse_lazy('bar_admin_create')
    permission_required = 'add_bar'

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
                    if request.user.username == 'meseros' or request.user.username == 'meseros2':
                        sale.employee_id = request.POST.get('employee')
                    else:
                        sale.employee_id = request.user.id
                    sale.client = Client.get_final_consumer()
                    sale.iva = iva
                    sale.dscto = float(request.POST['dscto']) / 100
                    # Método de pago: mismos campos y reglas que el módulo Ventas
                    sale.cash = float(request.POST.get('cash') or 0)
                    sale.change = float(request.POST.get('change') or 0)
                    sale.propina = float(request.POST.get('propina') or 0)
                    sale.paymentmethod = (request.POST['paymentmethod'])
                    if sale.paymentmethod == 'transfer':
                        sale.transfermethods = (request.POST['transfermethods'])
                    elif sale.paymentmethod == 'mixto':
                        sale.nequi_value = float(request.POST.get('nequi_value') or 0)
                        sale.daviplata_value = float(request.POST.get('daviplata_value') or 0)
                    else:
                        sale.transfermethods = None
                    sale.typemethods = request.POST.get('typemethods') or 'fullpayment'
                    if sale.typemethods == 'credit':
                        sale.expiration_date = request.POST.get('expiration_date') or None
                        if not sale.expiration_date:
                            raise Exception('Ingrese la fecha de vencimiento de la venta a crédito.')
                    else:
                        sale.expiration_date = None

                    if request.POST.get('switchDescuento') == 'on':
                        sale.autorization_discount = (request.POST['autorization_discount'])
                    elif request.POST.get('switchCortesia') == 'on':
                        sale.autorization_discount = (request.POST['autorization_discount'])
                    else:
                        sale.autorization_discount = None
                        
                    description = request.POST.get('description', '')
                    if description:
                        sale.description = description
                    sale.save()
                    lines = resolve_lines(json.loads(request.POST['products']),
                                          allow_price_override=request.user.has_perm('pos.edit_sale_price'))
                    for line in lines:
                        product, presentation = line['product'], line['presentation']
                        qty, factor, base_units = line['cant'], line['factor'], line['base_units']

                        # Crear detalle de venta (precio siempre desde el catálogo, no desde el navegador)
                        detail = SaleDetail()
                        detail.sale_id = sale.id
                        detail.product_id = product.id
                        detail.presentation = presentation
                        detail.presentation_name = line['presentation_name']
                        detail.factor = factor
                        detail.own_stock = line['own_stock']
                        detail.cost = product.cost_per_sale_unit(presentation, factor, line['own_stock'])
                        detail.cant = qty
                        detail.price = float(line['price'])
                        detail.dscto = float(line['dscto']) / 100
                        detail.save()

                        sale.calculate_detail()

                        # Descontar del inventario (stock del producto o de la variante) y de los descuentos automáticos
                        deduct_line(line)
                    sale.calculate_invoice()
                    # Aplicar descuento personalizado (después de calcular total)
                    discount_value = float(request.POST.get('discount_value', 0))
                    if discount_value > 0:
                        sale.discount_value = discount_value
                        sale.total -= discount_value
                        sale.save()
                    if request.POST.get('switchCortesia') == 'on':
                        sale.discount_value = sale.total
                        sale.total = 0
                        sale.save()
                    data = {'print_url': str(reverse_lazy('sale_admin_print_invoice', kwargs={'pk': sale.id}))}
            elif action == 'search_products':
                ids = json.loads(request.POST['ids'])
                data = []
                term = request.POST['term']
                queryset = Product.objects.filter(Q(stock__gt=0)).exclude(id__in=ids).order_by('code')
                if len(term):
                    queryset = queryset.filter(Q(name__icontains=term) | Q(code__icontains=term))
                    queryset = queryset[:10]
                for i in queryset:
                    item = i.toJSON()
                    item['pvp'] = float(i.pvp)
                    item['value'] = i.get_full_name()
                    item['dscto'] = '0.00'
                    item['total_dscto'] = '0.00'
                    data.append(item)
            elif action == 'search_product_barcode':
                barcode = (request.POST.get('barcode') or '').strip()
                presentation = ProductPresentation.objects.select_related('product').filter(
                    barcode=barcode, is_active=True, product__is_active=True,
                    product__uses_presentations=True).first()
                if presentation:
                    item = presentation.product.toJSON()
                    item['presentation'] = presentation.toOption(presentation.product.has_own_stock_variants())
                    return JsonResponse(item, safe=False)
                product = Product.objects.filter(barcode=barcode, is_active=True).first()
                if product is None:
                    return JsonResponse({'error': 'Producto no encontrado'})
                return JsonResponse(product.toJSON(), safe=False)
            elif action == 'search_client':
                data = []
                term = request.POST['term']
                for i in Client.objects.filter(Q(names__icontains=term) | Q(dni__icontains=term)).order_by('names')[0:10]:
                    data.append(i.toJSON())
            elif action == 'create_client':
                form = ClientForm(self.request.POST)
                data = form.save()
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['frmClient'] = ClientForm()
        context['list_url'] = self.success_url
        context['title'] = 'Nuevo registro de una Venta'
        context['action'] = 'add'
        context['company'] = Company.objects.first()
        context['categories'] = Category.objects.all().order_by('name')
        context['module_name'] = MODULE_NAME

        user = self.request.user

        # Grupos de inventario del usuario
        user_groups = InventoryGroup.objects.filter(userinventorygroup__user=user)

        # Obtener los stocks por producto que estén en esos grupos
        # product_stocks = ProductInventoryGroupStock.objects.filter(group__in=user_groups).select_related('product', 'group').order_by('product__id')
        product_stocks = Product.objects.filter(
            is_active=True
        ).select_related('category').prefetch_related('presentations').order_by('id')
        # Crear una estructura tipo: { product_id: {'product': ..., 'total_stock': ..., 'by_group': [...] } }
        product_data = {}
        for ps in product_stocks:
            pid = ps.id
            if pid not in product_data:
                product_data[pid] = {
                    'product': ps,
                    'total_stock': 0,
                    'by_group': []
                }
            product_data[pid]['total_stock'] += ps.total_stock()
            product_data[pid]['by_group'].append({'group': ps.name, 'stock': ps.stock})

        context['products_grouped'] = product_data.values()

        context['products'] = Product.objects.filter(Q(stock__gt=0) | Q(is_service=True)).order_by('id')
        # Solo los productos con presentaciones activas necesitan el selector en el POS.
        context['product_options'] = {
            p.pk: p.sale_options()
            for p in Product.objects.filter(is_active=True, uses_presentations=True,
                                            presentations__is_active=True).distinct()
        }
        return context
