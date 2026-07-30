import json
import time

from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import DeleteView, CreateView, UpdateView, TemplateView

from core.catalogs.forms import BiologicalTargetForm
from core.catalogs.models import BiologicalTarget
from core.security.mixins import GroupPermissionMixin

MODULE_NAME = 'Blancos Biológicos'

class BiologicalTargetListView(TemplateView):
    template_name = 'biological_target/list.html'
    permission_required = 'view_biological_target'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                for i in BiologicalTarget.objects.all():
                    data.append(i.toJSON())
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Blancos Biológicos'
        context['list_url'] = reverse_lazy('catalogs:biological_target_list')
        context['create_url'] = reverse_lazy('catalogs:biological_target_create')
        context['module_name'] = MODULE_NAME
        
        return context

class BiologicalTargetCreateView(GroupPermissionMixin, CreateView):
    template_name = 'biological_target/create.html'
    model = BiologicalTarget
    form_class = BiologicalTargetForm
    success_url = reverse_lazy('catalogs:biological_target_list')
    permission_required = 'add_biological_target'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'add':
                data = self.get_form().save()
            elif action == 'get_category': 
                from core.catalogs.models import BiologicalTargetCategory
                cat_id = request.POST['id']
                category = BiologicalTargetCategory.objects.get(pk=cat_id)
                data = {'handle_traps': category.handle_traps}
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nuevo registro de un blanco Biológico'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME
        return context


class BiologicalTargetUpdateView(GroupPermissionMixin, UpdateView):
    template_name = 'biological_target/create.html'
    model = BiologicalTarget
    form_class = BiologicalTargetForm
    success_url = reverse_lazy('catalogs:biological_target_list')
    permission_required = 'change_biological_target'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'edit':
                data = self.get_form().save()
            elif action == 'get_category':
                from core.catalogs.models import BiologicalTargetCategory
                cat_id = request.POST['id']
                category = BiologicalTargetCategory.objects.get(pk=cat_id)
                data = {'handle_traps': category.handle_traps}
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edición de un Blanco Biológico'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['module_name'] = MODULE_NAME
        return context


class BiologicalTargetDeleteView(GroupPermissionMixin, DeleteView):
    model = BiologicalTarget
    template_name = 'delete.html'
    success_url = reverse_lazy('catalogs:biological_target_list')
    permission_required = 'delete_biological_target'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.get_object().delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminación de un Blanco Biológico'
        context['list_url'] = self.success_url
        context['module_name'] = MODULE_NAME
        return context