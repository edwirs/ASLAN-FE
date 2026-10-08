import json
from django.http import JsonResponse
from django.urls import reverse
from django.views.generic import CreateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction

from core.pos.forms import *
from core.pos.forms import OrderBarraForm
from core.pos.models import Table, Order, OrderDetail, InventoryGroup, Product, Company, Client, Sale, SaleDetail
from core.pos.stock_lines import deduct_line, resolve_lines
from core.security.mixins import GroupPermissionMixin

MODULE_NAME = 'Ordenes'

class OrderListView(LoginRequiredMixin, TemplateView):
    template_name = 'order/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tables = Table.objects.filter(is_active=True)
        data = []

        for table in tables:
            order = Order.objects.filter(
                table=table,
                status__in=['open', 'sent', 'ready']
            ).order_by('-id').first()

            data.append({
                'id': table.id,
                'name': table.name,
                'has_order': bool(order),
                'total': order.total if order else 0,
                'order_id': order.id if order else None,
                'employee': order.employee.get_short_name() if order else None
            })

        context['tables'] = data
        context['sale_form'] = SaleForm()
        context['module_name'] = MODULE_NAME
        return context

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST.get('action')

            if action == 'create_sale':
                with transaction.atomic():
                    order_id = request.POST.get('order_id')
                    order = Order.objects.get(id=order_id)

                    # 🛡️ VALIDACIÓN DE ESTADO
                    if order.status != 'ready':
                        data['error'] = f'No se puede facturar: El pedido está en estado "{order.get_status_display()}". Debe estar "Listo" para proceder.'
                        return JsonResponse(data)
                        
                    company = Company.objects.first()

                    # 1. Crear la Venta (Sale)
                    sale = Sale()
                    sale.company = company
                    # Buscamos cliente de la orden o el consumidor final
                    sale.client = order.client if order.client else Client.get_final_consumer()
                    sale.employee = request.user
                    sale.paymentmethod = request.POST.get('paymentmethod')
                    sale.transfermethods = request.POST.get('transfermethods')
                    sale.cash = float(request.POST.get('cash', 0))
                    sale.propina = float(request.POST.get('propina', 0))
                    sale.change = float(request.POST.get('change', 0))
                    sale.total = float(order.total)
                    sale.save()

                    # 2. Crear Detalles de Venta desde la Orden (precio, presentación y tipo de stock tal como se pidieron)
                    order_details = list(order.orderdetail_set.select_related('product'))
                    lines = resolve_lines([{
                        'id': d.product_id, 'presentation_id': d.presentation_id, 'presentation_name': d.presentation_name,
                        'cant': d.cant, 'price': d.price, 'factor': d.factor, 'own_stock': d.own_stock,
                    } for d in order_details], snapshot=True)  # valida el stock (sumando líneas) antes de facturar
                    for line in lines:
                        product = line['product']
                        sd = SaleDetail()
                        sd.sale = sale
                        sd.product = product
                        sd.presentation = line['presentation']
                        sd.presentation_name = line['presentation_name']
                        sd.factor = line['factor']
                        sd.own_stock = line['own_stock']
                        sd.cost = product.cost_per_sale_unit(line['presentation'], line['factor'], line['own_stock'])
                        sd.cant = line['cant']
                        sd.price = line['price']
                        # Lógica de IVA según el producto
                        sd.iva = 0.19 if product.with_tax else 0
                        sd.total = float(line['cant'] * line['price'])
                        sd.save()
                        deduct_line(line)

                    # 3. Recalcular totales de la venta
                    sale.calculate_invoice()

                    # 4. Cerrar la Orden
                    order.status = 'closed'
                    order.save()

                    data['redirect'] = reverse('order_list')
            else:
                data['error'] = 'Acción no válida'

        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

class OrderBarraView(LoginRequiredMixin, TemplateView):
    template_name = 'order/create.html'

    def get_final_consumer(self):
        queryset = Client.objects.filter(dni='222222222222')
        if queryset.exists():
            return json.dumps(queryset[0].toJSON())
        return {}
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        table_id = self.kwargs['table_id']
        table = Table.objects.get(id=table_id)
        details = []

        order = Order.objects.filter(
            table=table,
            status__in=['open', 'sent', 'ready']
        ).order_by('-id').first()
        if not order:
            order = Order.objects.create(
                table=table,
                employee=self.request.user,
                status='open'
            )

        if order:
            for d in order.orderdetail_set.select_related('product', 'presentation'):
                product = d.product
                holder = d.presentation if (d.own_stock and d.presentation_id) else product
                options = product.sale_options()
                details.append({
                    'id': product.id,
                    'name': product.name,
                    'cant': float(d.cant),
                    'allow_decimals': product.allow_decimals,
                    'pvp': float(d.price),
                    'total': float(d.cant * d.price),
                    'presentation_id': d.presentation_id,
                    'presentation_name': d.presentation_name,
                    'factor': float(d.factor),
                    'own_stock': d.own_stock,
                    'stock': float(holder.stock),
                    'unit': product.unit_name or 'Unidad',
                    'is_service': product.is_service,
                    'has_options': len(options) > 1,
                })

        context['order'] = order
        context['table'] = table
        context['order_details'] = json.dumps(details)

        user = self.request.user
        user_groups = InventoryGroup.objects.filter(userinventorygroup__user=user)
        product_stocks = Product.objects.filter(
            is_active=True
        ).select_related('category').prefetch_related('presentations').order_by('id')

        product_data = []
        for p in product_stocks:
            product_data.append({
                'product': p,
                'total_stock': float(p.total_stock()),
            })

        context['products_grouped'] = product_data
        # Solo los productos con presentaciones activas necesitan el selector.
        context['product_options'] = {
            p['product'].pk: p['product'].sale_options()
            for p in product_data
            if p['product'].uses_presentations and any(x.is_active for x in p['product'].presentations.all())
        }

        context['client'] = order.client if order and order.client else None
        context['title'] = f'Mesa # {table.id} / Cliente: {order.client}'
        context['action'] = 'add'
        context['company'] = Company.objects.first()
        context['categories'] = Category.objects.all().order_by('name')
        context['final_consumer'] = self.get_final_consumer()
        context['frmBar'] = OrderBarraForm(instance=order)
        context['module_name'] = MODULE_NAME
        return context

class OrderCreateView(GroupPermissionMixin, CreateView):
    # Se mantiene para la acción de actualización de productos desde la vista de toma de pedido
    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST.get('action')
            if action == 'update_order':
                with transaction.atomic():
                    order_id = request.POST.get('order_id')
                    observations = request.POST.get('observations', '')
                    products = json.loads(request.POST.get('products'))
                    order = Order.objects.get(id=order_id)

                    # Valida stock y presentación (el precio sale del catálogo); el stock se descuenta al facturar
                    lines = resolve_lines(products)
                    order.orderdetail_set.all().delete()
                    total = 0
                    for line in lines:
                        total += line['cant'] * line['price']
                        OrderDetail.objects.create(
                            order=order,
                            product=line['product'],
                            presentation=line['presentation'],
                            presentation_name=line['presentation_name'],
                            factor=line['factor'],
                            own_stock=line['own_stock'],
                            cant=line['cant'],
                            price=line['price'],
                        )
                    order.total = total
                    order.observations = observations
                    # Reenviar a cocina si estaba lista
                    if order.status == 'ready':
                        order.status = 'sent'
                    order.save()
                    data['redirect'] = reverse('order_list')
            else:
                data['error'] = 'Acción no válida'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)