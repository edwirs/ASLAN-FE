import json

from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import DeleteView, CreateView, UpdateView, TemplateView
from django.core.serializers.json import DjangoJSONEncoder

from core.pos.models import ProductAutoAdd
from core.pos.forms import ProductAutoAddForm
from core.security.mixins import GroupPermissionMixin

MODULE_NAME = 'Productos a descontar'

class ProductAutoAddListView(GroupPermissionMixin, TemplateView):
    template_name = "productautoadd/list.html"
    permission_required = 'pos.view_productautoadd'
    model = ProductAutoAdd

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                data = list(ProductAutoAdd.objects.all().values(
                    'id',
                    'quantity',
                    'trigger_product__name',
                    'auto_product__name'
                ))
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(
            json.dumps(data, cls=DjangoJSONEncoder),
            content_type='application/json'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Parametrizacion de Productos'
        context['list_url'] = reverse_lazy('productautoadd_list')
        context['create_url'] = reverse_lazy('productautoadd_create')
        context['module_name'] = MODULE_NAME
        return context


class ProductAutoAddCreateView(GroupPermissionMixin, CreateView):
    model = ProductAutoAdd
    template_name = "productautoadd/create.html"
    form_class = ProductAutoAddForm
    success_url = reverse_lazy('productautoadd_list')
    permission_required = 'pos.add_productautoadd'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'add':
                data = self.get_form().save()
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nuevo registro de una Parametrización'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME
        return context


class ProductAutoAddUpdateView(GroupPermissionMixin, UpdateView):
    model = ProductAutoAdd
    template_name = "productautoadd/create.html"
    form_class = ProductAutoAddForm
    success_url = reverse_lazy("productautoadd_list")
    permission_required = 'pos.change_productautoadd'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'edit':
                data = self.get_form().save()
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edición de una Parametrización'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['module_name'] = MODULE_NAME
        return context

class ProductAutoAddDeleteView(GroupPermissionMixin, DeleteView):
    model = ProductAutoAdd
    template_name = "delete.html"
    success_url = reverse_lazy("productautoadd_list")
    permission_required = 'pos.delete_productautoadd'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.get_object().delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminación de una Parametrización'
        context['list_url'] = self.success_url
        context['module_name'] = MODULE_NAME
        return context
