import json

from django.db import transaction
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import DeleteView, CreateView, UpdateView, TemplateView

from core.pos.forms import ProductForm
from core.pos.models import Product
from core.pos.presentations import parse_presentations, sync_presentations
from core.security.mixins import GroupPermissionMixin

MODULE_NAME = 'Productos'


class PresentationsMixin:
    """Guarda el producto y sus presentaciones en una sola transacción."""

    def save_with_presentations(self, request):
        form = self.get_form()
        with transaction.atomic():
            if not form.is_valid():
                return {'error': '; '.join(f'{f}: {" ".join(e)}' for f, e in form.errors.items())}
            # Con el switch apagado las presentaciones guardadas se conservan (por si se reactiva)
            # pero no se ofrecen en ninguna venta ni se validan los datos del editor.
            uses = form.cleaned_data.get('uses_presentations')
            rows = parse_presentations(request.POST.get('presentations'), product=form.instance,
                                       mode=form.cleaned_data.get('presentation_mode')) if uses else None
            if uses and not rows:
                raise ValueError('Agregue al menos una presentación o apague "¿Maneja presentaciones?".')
            data = form.save()
            if 'error' in data:
                transaction.set_rollback(True)
                return data
            if uses:
                sync_presentations(form.instance, rows)
        return data

    def presentations_context(self):
        product = getattr(self, 'object', None)
        rows = []
        if product is not None and product.pk:
            rows = [{
                'id': p.pk, 'name': p.name, 'factor': float(p.factor), 'pvp': float(p.pvp),
                'price': float(p.price), 'barcode': p.barcode or '', 'is_active': p.is_active,
                'stock': float(p.stock),
            } for p in product.presentations.all().order_by('factor', 'id')]
        return rows


class ProductListView(GroupPermissionMixin, TemplateView):
    template_name = 'product/list.html'
    permission_required = 'view_product'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                for i in Product.objects.prefetch_related('presentations'):
                    item = i.toJSON()
                    item['presentations_count'] = len([p for p in i.presentations.all() if p.is_active]) if i.uses_presentations else 0
                    item['stock_summary'] = i.stock_summary()
                    data.append(item)
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Productos'
        context['list_url'] = reverse_lazy('product_list')
        context['create_url'] = reverse_lazy('product_create')
        context['module_name'] = MODULE_NAME
        return context


class ProductCreateView(PresentationsMixin, GroupPermissionMixin, CreateView):
    template_name = 'product/create.html'
    model = Product
    form_class = ProductForm
    success_url = reverse_lazy('product_list')
    permission_required = 'add_product'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'add':
                data = self.save_with_presentations(request)
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['presentations'] = self.presentations_context()
        context['title'] = 'Nuevo registro de un Producto'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME
        return context


class ProductUpdateView(PresentationsMixin, GroupPermissionMixin, UpdateView):
    template_name = 'product/create.html'
    model = Product
    form_class = ProductForm
    success_url = reverse_lazy('product_list')
    permission_required = 'change_product'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'edit':
                data = self.save_with_presentations(request)
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['presentations'] = self.presentations_context()
        context['title'] = 'Edición de un Producto'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['module_name'] = MODULE_NAME
        return context


class ProductDeleteView(GroupPermissionMixin, DeleteView):
    model = Product
    template_name = 'delete.html'
    success_url = reverse_lazy('product_list')
    permission_required = 'delete_product'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.get_object().delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminación de un Producto'
        context['list_url'] = self.success_url
        context['module_name'] = MODULE_NAME
        return context
