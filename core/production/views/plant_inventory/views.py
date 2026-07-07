import json

from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.views.generic import TemplateView, CreateView

from core.production.forms import PlantInventoryFilterForm
from core.production.models import PlantInventory
from core.security.mixins import GroupPermissionMixin

from core.production.services.inventory_import_service import InventoryImportService

MODULE_NAME = 'Inventario Plantas'

class PlantInventoryListView(GroupPermissionMixin, TemplateView):

    template_name = 'plant_inventory/list.html'
    permission_required = 'view_plant_inventory'

    def post(self, request, *args, **kwargs):

        data = []

        try:

            action = request.POST['action']

            if action == 'search':

                queryset = PlantInventory.objects.all()

                code = request.POST.get('code')
                plot_id = request.POST.get('plot_id')
                location = request.POST.get('location')
                genus = request.POST.get('genus')
                area = request.POST.get('area')

                if not any([code, plot_id, location, genus, area]):
                    return HttpResponse(
                        json.dumps([]),
                        content_type='application/json'
                    )

                if code:
                    queryset = queryset.filter(code__icontains=code)

                if plot_id:
                    queryset = queryset.filter(plot_id__icontains=plot_id)

                if location:
                    queryset = queryset.filter(location__icontains=location)

                if genus:
                    queryset = queryset.filter(genus__icontains=genus)

                if area:
                    queryset = queryset.filter(area__icontains=area)

                for i in queryset.order_by('code'):

                    data.append({
                        'code': i.code,
                        'plot_id': i.plot_id,
                        'location': i.location,
                        'variety': i.variety,
                        'genus': i.genus,
                        'area': i.area,
                        'plants': i.plants,
                    })

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

        context['title'] = 'Consulta Inventario Plantas'
        context['module_name'] = MODULE_NAME

        return context