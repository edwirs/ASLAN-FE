import json

from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.views.generic import TemplateView, CreateView

from core.production.forms import PlantInventoryImportForm
from core.production.models import PlantInventoryImport
from core.security.mixins import GroupPermissionMixin

from core.production.services.inventory_import_service import InventoryImportService

MODULE_NAME = 'Importación Inventario Plantas'


class PlantInventoryImportListView(GroupPermissionMixin, TemplateView):
    template_name = 'plant_inventory_import/list.html'
    permission_required = 'view_plant_inventory_import'

    def post(self, request, *args, **kwargs):
        data = []

        try:
            action = request.POST['action']

            if action == 'search':
                for i in PlantInventoryImport.objects.all().order_by('-id'):
                    data.append(i.toJSON())
            else:
                data = {
                    'error': 'No ha seleccionado ninguna opción'
                }

        except Exception as e:
            data = {
                'error': str(e)
            }

        return HttpResponse(
            json.dumps(data),
            content_type='application/json'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['title'] = 'Listado de Importaciones'
        context['list_url'] = reverse_lazy(
            'production:plant_inventory_import_list'
        )
        context['create_url'] = reverse_lazy(
            'production:plant_inventory_import_create'
        )
        context['module_name'] = MODULE_NAME

        return context

class PlantInventoryImportCreateView(
    GroupPermissionMixin,
    CreateView
):
    template_name = 'plant_inventory_import/create.html'
    form_class = PlantInventoryImportForm
    model = PlantInventoryImport

    success_url = reverse_lazy(
        'production:plant_inventory_import_list'
    )

    permission_required = 'add_plant_inventory_import'

    def post(self, request, *args, **kwargs):

        data = {}

        try:

            action = request.POST['action']

            if action == 'add':

                form = self.get_form()

                if form.is_valid():

                    obj = form.save(commit=False)
                    obj.imported_by = request.user
                    obj.save()

                    InventoryImportService.process(obj)

                    data['success'] = True
                else:
                    data['error'] = form.errors

            else:
                data['error'] = 'No ha seleccionado ninguna opción'

        except Exception as e:
            data['error'] = str(e)

        return HttpResponse(
            json.dumps(data),
            content_type='application/json'
        )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context['title'] = 'Nueva Importación de Inventario'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME

        return context