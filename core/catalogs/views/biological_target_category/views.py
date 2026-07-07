import json
import time

from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import DeleteView, CreateView, UpdateView, TemplateView

from core.catalogs.forms import BiologicalTargetCategoryForm
from core.catalogs.models import BiologicalTargetCategory
from core.security.mixins import GroupPermissionMixin

MODULE_NAME = 'Categorías Blancos Biológicos'

class BiologicalTargetCategoryListView(TemplateView):
    template_name = 'biological_target_category/list.html'
    permission_required = 'view_biological_target_category'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                for i in BiologicalTargetCategory.objects.all():
                    data.append(i.toJSON())
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Categorías'
        context['list_url'] = reverse_lazy('catalogs:biological_target_category_list')
        context['create_url'] = reverse_lazy('catalogs:biological_target_category_create')
        context['module_name'] = MODULE_NAME
        
        return context

class BiologicalTargetCategoryCreateView(GroupPermissionMixin, CreateView):
    template_name = 'biological_target_category/create.html'
    model = BiologicalTargetCategory
    form_class = BiologicalTargetCategoryForm
    success_url = reverse_lazy('catalogs:biological_target_category_list')
    permission_required = 'add_biological_target_category'

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
        context['title'] = 'Nuevo registro de una Categoría'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME
        return context


class BiologicalTargetCategoryUpdateView(GroupPermissionMixin, UpdateView):
    template_name = 'biological_target_category/create.html'
    model = BiologicalTargetCategory
    form_class = BiologicalTargetCategoryForm
    success_url = reverse_lazy('catalogs:biological_target_category_list')
    permission_required = 'change_biological_target_category'

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
        context['title'] = 'Edición de una Categoría'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['module_name'] = MODULE_NAME
        return context


class BiologicalTargetCategoryDeleteView(GroupPermissionMixin, DeleteView):
    model = BiologicalTargetCategory
    template_name = 'delete.html'
    success_url = reverse_lazy('catalogs:biological_target_category_list')
    permission_required = 'delete_biological_target_category'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.get_object().delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminación de una Categoría'
        context['list_url'] = self.success_url
        context['module_name'] = MODULE_NAME
        return context