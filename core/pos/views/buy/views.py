import json
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, FormView

from core.pos.forms import *
from core.pos.utilities import printer
from core.reports.forms import ReportForm
from core.security.mixins import GroupPermissionMixin

MODULE_NAME = 'Compras'


class BuyListView(GroupPermissionMixin, FormView):
    template_name = 'buy/admin/list.html'
    form_class = ReportForm
    permission_required = 'view_buy'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                start_date = request.POST['start_date']
                end_date = request.POST['end_date']
                queryset = Buy.objects.filter()
                if len(start_date) and len(end_date):
                    queryset = queryset.filter(date_joined__range=[start_date, end_date])
                for i in queryset.order_by('-id'):
                    data.append(i.toJSON())
            elif action == 'search_detail_products':
                data = []
                for i in BuyDetail.objects.filter(buy_id_id=request.POST['id']):
                    data.append(i.toJSON())
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Compras'
        context['list_url'] = reverse_lazy('buy_admin_list')
        context['create_url'] = reverse_lazy('buy_admin_create')
        context['module_name'] = MODULE_NAME
        return context


class BuyCreateView(GroupPermissionMixin, CreateView):
    model = Buy
    template_name = 'buy/admin/create.html'
    form_class = BuyForm
    success_url = reverse_lazy('buy_admin_list')
    permission_required = 'add_buy'

    def post(self, request, *args, **kwargs):
        action = request.POST['action']
        data = {}
        try:
            if action == 'add':
                with transaction.atomic():
                    company = Company.objects.first()
                    iva = float(company.iva) / 100
                    buy = Buy()
                    buy.company = company
                    buy.employee_id = request.user.id
                    buy.provider_id = int(request.POST['provider'])
                    buy.iva = iva
                    buy.dscto = float(request.POST['dscto']) / 100
                    buy.cash = float(request.POST['cash'])
                    buy.change = float(request.POST['change'])
                    buy.paymentmethod = (request.POST['paymentmethod'])
                    buy.transfermethods = (request.POST['transfermethods'])
                    buy.save()
                    update_costs = request.POST.get('update_costs') == 'on'
                    products, holders = {}, {}
                    for i in json.loads(request.POST['products']):
                        # Una sola instancia por producto/presentación: dos líneas del mismo stock
                        # en la compra no deben pisarse entre sí.
                        pid = int(i['id'])
                        if pid not in products:
                            products[pid] = Product.objects.select_for_update().get(pk=pid)
                        product = products[pid]
                        qty = int(i['cant'])
                        if qty < 1:
                            raise Exception(f"Cantidad inválida para '{product.name}'.")
                        presentation, factor = None, Decimal(1)
                        own = product.has_own_stock_variants()
                        if i.get('presentation_id'):
                            presentation = ProductPresentation.objects.filter(
                                pk=i['presentation_id'], product=product, is_active=True,
                                product__uses_presentations=True).first()
                            if presentation is None:
                                raise Exception(f"La presentación elegida de '{product.name}' ya no está disponible.")
                            if not own:
                                factor = presentation.factor
                        price = float(i['price'])

                        detail = BuyDetail()
                        detail.buy_id_id = buy.id
                        detail.product_id = product.id
                        detail.presentation = presentation
                        detail.presentation_name = presentation.name if presentation else (
                            product.unit_name if own else '')
                        detail.factor = factor
                        detail.own_stock = own
                        detail.cant = qty
                        detail.price = price
                        detail.dscto = float(i['dscto']) / 100
                        detail.save()
                        buy.calculate_detail()

                        # El stock sube en unidad base (conversión) o en el de la variante comprada
                        if own and presentation is not None:
                            if presentation.pk not in holders:
                                holders[presentation.pk] = ProductPresentation.objects.select_for_update().get(
                                    pk=presentation.pk)
                            holder = holders[presentation.pk]
                        else:
                            holder = product
                        holder.stock += factor * qty
                        holder.save(update_fields=['stock'])

                        if update_costs and price > 0:
                            # Último costo: el de la presentación y, si es conversión, el de la unidad base
                            if presentation is not None:
                                presentation.price = Decimal(str(price)).quantize(Decimal('0.01'))
                                presentation.save(update_fields=['price'])
                            if presentation is None or not own:
                                product.price = (Decimal(str(price)) / factor).quantize(Decimal('0.01'))
                                product.save(update_fields=['price'])
                    buy.calculate_invoice()
                    data = {'print_url': str(reverse_lazy('buy_admin_print_invoice', kwargs={'pk': buy.id}))}
            elif action == 'search_products':
                ids = json.loads(request.POST['ids'])
                data = []
                term = request.POST['term']
                queryset = Product.objects.filter(is_service=False).exclude(id__in=ids).order_by('code')
                if len(term):
                    queryset = queryset.filter(Q(name__icontains=term) | Q(code__icontains=term))
                    queryset = queryset[:10]
                for i in queryset:
                    item = i.toJSON()
                    item['pvp'] = float(i.pvp)
                    item['options'] = i.sale_options()
                    item['value'] = i.get_full_name()
                    item['dscto'] = '0.00'
                    item['total_dscto'] = '0.00'
                    data.append(item)
            elif action == 'search_provider':
                data = []
                term = request.POST['term']
                for i in Provider.objects.filter(Q(names__icontains=term) | Q(dni__icontains=term)).order_by('names')[0:10]:
                    data.append(i.toJSON())
            elif action == 'create_provider':
                form = ProviderForm(self.request.POST)
                data = form.save()
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_final_consumer(self):
        queryset = Provider.objects.filter(dni='1070964494')
        if queryset.exists():
            return json.dumps(queryset[0].toJSON())
        return {}

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['frmProvider'] = ProviderForm()
        context['list_url'] = self.success_url
        context['title'] = 'Nuevo registro de una compra'
        context['action'] = 'add'
        context['company'] = Company.objects.first()
        context['final_consumer'] = self.get_final_consumer()
        context['module_name'] = MODULE_NAME
        return context


class BuyDeleteView(GroupPermissionMixin, DeleteView):
    model = Buy
    template_name = 'delete.html'
    success_url = reverse_lazy('buy_admin_list')
    permission_required = 'delete_buy'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            with transaction.atomic():
                buy = self.get_object()
                # La compra subió el stock; al eliminarla se devuelve (en unidad base o de la variante).
                returns = {}
                for detail in buy.buydetail_set.select_related('product', 'presentation'):
                    if detail.own_stock and detail.presentation_id:
                        key = ('presentation', detail.presentation_id)
                    elif detail.own_stock and detail.presentation_name != detail.product.unit_name:
                        continue  # la variante comprada ya no existe: no hay stock que devolver
                    else:
                        key = ('product', detail.product_id)
                    returns[key] = returns.get(key, Decimal(0)) + detail.factor * detail.cant
                for (kind, pk), units in returns.items():
                    if kind == 'presentation':
                        holder = ProductPresentation.objects.select_for_update().select_related('product').get(pk=pk)
                        label, product = f'{holder.product.name} - {holder.name}', holder.product
                    else:
                        holder = Product.objects.select_for_update().get(pk=pk)
                        label, product = holder.name, holder
                    if product.is_service:
                        continue
                    if holder.stock < units:
                        raise Exception(
                            f"No se puede eliminar la compra: de '{label}' ingresaron {units} "
                            f"y hoy solo hay {holder.stock} (ya se vendió parte).")
                    holder.stock -= units
                    holder.save(update_fields=['stock'])
                buy.delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminación de una compra'
        context['list_url'] = self.success_url
        context['module_name'] = MODULE_NAME
        return context


class BuyPrintInvoiceView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            buy = Buy.objects.get(id=self.kwargs['pk'])
            context = {'price': buy, 'height': 450 + buy.pricedetail_set.all().count() * 10}
            pdf_file = printer.create_pdf(context=context, template_name='buy/format/ticket.html')
            return HttpResponse(pdf_file, content_type='application/pdf')
        except:
            pass
        return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
