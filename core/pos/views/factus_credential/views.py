import json

from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import DeleteView, CreateView, UpdateView, TemplateView

from core.pos.forms import FactusCredentialForm
from core.pos.models import FactusCredential
from core.security.mixins import GroupPermissionMixin

MODULE_NAME = 'Credenciales Factus'


class FactusCredentialListView(GroupPermissionMixin, TemplateView):
    template_name = 'factus_credential/list.html'
    permission_required = 'pos.view_factuscredential'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action')
        try:
            if action == 'search':
                data = []
                for i in FactusCredential.objects.all().order_by('-is_active', 'name'):
                    data.append(i.toJSON())
            elif action == 'activate':
                credential = FactusCredential.objects.get(pk=request.POST.get('id'))
                credential.is_active = True
                credential.save()  # el save() del modelo desactiva las demás
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Credenciales de Factus'
        context['list_url'] = reverse_lazy('factus_credential_list')
        context['create_url'] = reverse_lazy('factus_credential_create')
        context['module_name'] = MODULE_NAME
        return context


class FactusCredentialCreateView(GroupPermissionMixin, CreateView):
    template_name = 'factus_credential/create.html'
    model = FactusCredential
    form_class = FactusCredentialForm
    success_url = reverse_lazy('factus_credential_list')
    permission_required = 'pos.add_factuscredential'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action')
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
        context['title'] = 'Nueva Credencial de Factus'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME
        return context


class FactusCredentialUpdateView(GroupPermissionMixin, UpdateView):
    template_name = 'factus_credential/create.html'
    model = FactusCredential
    form_class = FactusCredentialForm
    success_url = reverse_lazy('factus_credential_list')
    permission_required = 'pos.change_factuscredential'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action')
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
        context['title'] = 'Edición de una Credencial de Factus'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['module_name'] = MODULE_NAME
        return context


class FactusCredentialDeleteView(GroupPermissionMixin, DeleteView):
    model = FactusCredential
    template_name = 'delete.html'
    success_url = reverse_lazy('factus_credential_list')
    permission_required = 'pos.delete_factuscredential'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.get_object().delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminación de una Credencial de Factus'
        context['list_url'] = self.success_url
        context['module_name'] = MODULE_NAME
        return context
