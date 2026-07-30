import json

from django.db import transaction
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import DeleteView, CreateView, UpdateView, TemplateView

from core.pos.forms import ClientForm, ClientContactFormSet
from core.pos.models import Client
from core.security.mixins import GroupPermissionMixin

MODULE_NAME = 'Clientes'


class ClientListView(GroupPermissionMixin, TemplateView):
    template_name = 'client/list.html'
    permission_required = 'view_client'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                for i in Client.objects.all():
                    data.append(i.toJSON())
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Clientes'
        context['list_url'] = reverse_lazy('client_list')
        context['create_url'] = reverse_lazy('client_create')
        context['module_name'] = MODULE_NAME
        return context


class ClientCreateView(GroupPermissionMixin, CreateView):
    template_name = 'client/create.html'
    model = Client
    form_class = ClientForm
    success_url = reverse_lazy('client_list')
    permission_required = 'add_client'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action')
        try:
            if action == 'add':
                form = self.form_class(request.POST, request.FILES)
                contacts_formset = ClientContactFormSet(request.POST)

                if form.is_valid() and contacts_formset.is_valid():
                    with transaction.atomic():
                        # 1. Ejecutamos el save personalizado de tu formulario para que guarde y retorne su diccionario o datos
                        data = form.save()
                        
                        # 2. Obtenemos la instancia real del modelo directamente desde form.instance
                        client_instance = form.instance
                        
                        # 3. Asignamos la instancia al formset y guardamos los contactos
                        contacts_formset.instance = client_instance
                        contacts_formset.save()
                else:
                    errors = dict(form.errors.items())
                    if contacts_formset.errors:
                        errors['formset'] = contacts_formset.errors
                    data['error'] = errors
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['list_url'] = self.success_url
        context['title'] = 'Nuevo registro de un Cliente'
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME
        if self.request.POST:
            context['contacts_formset'] = ClientContactFormSet(self.request.POST)
        else:
            context['contacts_formset'] = ClientContactFormSet()
        return context


class ClientUpdateView(GroupPermissionMixin, UpdateView):
    template_name = 'client/create.html'
    model = Client
    form_class = ClientForm
    success_url = reverse_lazy('client_list')
    permission_required = 'change_client'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action')
        try:
            if action == 'edit':
                form = self.form_class(request.POST, request.FILES, instance=self.object)
                contacts_formset = ClientContactFormSet(request.POST, instance=self.object)

                if form.is_valid() and contacts_formset.is_valid():
                    with transaction.atomic():
                        # 1. Ejecutamos el save del formulario existente
                        data = form.save()
                        
                        # 2. Extraemos la instancia pura del modelo desde form.instance
                        client_instance = form.instance
                        
                        # 3. Asociamos y guardamos los contactos con la instancia correcta
                        contacts_formset.instance = client_instance
                        contacts_formset.save()
                else:
                    errors = dict(form.errors.items())
                    if contacts_formset.errors:
                        errors['formset'] = contacts_formset.errors
                    data['error'] = errors
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['list_url'] = self.success_url
        context['title'] = 'Edición de un Cliente'
        context['action'] = 'edit'
        context['module_name'] = MODULE_NAME
        
        if self.request.POST:
            context['contacts_formset'] = ClientContactFormSet(request.POST, instance=self.object)
        else:
            context['contacts_formset'] = ClientContactFormSet(instance=self.object)
            
        return context


class ClientDeleteView(GroupPermissionMixin, DeleteView):
    model = Client
    template_name = 'delete.html'
    success_url = reverse_lazy('client_list')
    permission_required = 'delete_client'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.get_object().delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminación de un Cliente'
        context['list_url'] = self.success_url
        context['module_name'] = MODULE_NAME
        return context