import json
import time

from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import DeleteView, CreateView, UpdateView, TemplateView

from core.catalogs.forms import MipeModuleForm
from core.catalogs.models import MipeModule
from core.security.mixins import GroupPermissionMixin

MODULE_NAME = 'Modulos Mipe'

class MipeModuleListView(TemplateView):
    template_name = 'mipe_modules/list.html'
    permission_required = 'view_mipe_module'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                for i in MipeModule.objects.all():
                    data.append(i.toJSON())
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Modulos Mipe'
        context['list_url'] = reverse_lazy('catalogs:mipe_module_list')
        context['create_url'] = reverse_lazy('catalogs:mipe_module_create')
        context['module_name'] = MODULE_NAME
        
        return context

class MipeModuleCreateView(GroupPermissionMixin, CreateView):
    template_name = 'mipe_modules/create.html'
    model = MipeModule
    form_class = MipeModuleForm
    success_url = reverse_lazy('catalogs:mipe_module_list')
    permission_required = 'add_mipe_module'

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
        context['title'] = 'Nuevo registro de un modulo Mipe'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME
        return context


class MipeModuleUpdateView(GroupPermissionMixin, UpdateView):
    template_name = 'mipe_modules/create.html'
    model = MipeModule
    form_class = MipeModuleForm
    success_url = reverse_lazy('catalogs:mipe_module_list')
    permission_required = 'change_mipe_module'

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
        context['title'] = 'Edición de un modulo Mipe'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['module_name'] = MODULE_NAME
        return context


class MipeModuleDeleteView(GroupPermissionMixin, DeleteView):
    model = MipeModule
    template_name = 'delete.html'
    success_url = reverse_lazy('catalogs:mipe_module_list')
    permission_required = 'delete_mipe_module'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.get_object().delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminación de un modulo Mipe'
        context['list_url'] = self.success_url
        context['module_name'] = MODULE_NAME
        return context