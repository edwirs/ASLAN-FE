import json
import traceback
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, TemplateView, UpdateView
from django.utils import timezone
from django.db.models import Prefetch
from core.reports.forms import ReportForm

from core.security.mixins import GroupPermissionMixin
from core.catalogs.models import AssuranceParameter
from core.production.models import Assurance, AssuranceDetail, Monitoring, MonitoringDetail, PlantInventory, Block, BlockBay, Bed

MODULE_NAME = 'Aseguramiento en Campo'

class AssuranceListView(GroupPermissionMixin, ListView):
    model = Assurance
    form_class = ReportForm
    template_name = 'assurance/list.html'
    permission_required = 'view_assurance'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Aseguramiento en Campo'
        context['module_name'] = MODULE_NAME
        context['create_url'] = reverse_lazy('production:assurance_create')
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        try:
            if action == 'list':
                start_date = request.POST.get('start_date', '')
                end_date = request.POST.get('end_date', '')
                
                # Iniciamos con todos los registros
                queryset = Assurance.objects.all()
                
                # Aplicamos filtro por rango si existen las fechas
                if start_date and end_date:
                    queryset = queryset.filter(assurance_date__range=[start_date, end_date])
                
                data = [a.toJSON() for a in queryset.order_by('-id')]
                return JsonResponse(data, safe=False)
            
            return JsonResponse({'error': 'Acción inválida'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class AssuranceCreateView(GroupPermissionMixin, TemplateView):
    template_name = 'assurance/create.html'
    permission_required = 'add_assurance'
    success_url = reverse_lazy('production:mipe_assurance')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        if pk:
            assurance = Assurance.objects.get(pk=pk)
            context['title'] = 'Editar Registro de Aseguramiento'
            context['action'] = 'update'
            context['assurance'] = assurance
            
            # AGREGA ESTO: Serializamos los datos del objeto para el JS
            context['assurance_json'] = json.dumps({
                'id': assurance.id,
                'location': assurance.location,
                'variety_code': assurance.variety_code,
                # Si no tienes inventory_id, no lo incluyas o usa un campo que sí exista
                'details': [
                    {
                        'parameter_id': d.parameter_id, 
                        'complies': d.complies, 
                        'observations': d.observations
                    }
                    for d in AssuranceDetail.objects.filter(assurance=assurance)
                ]
            })
        else:
            # Si no hay pk, estamos creando
            context['title'] = 'Nuevo Registro de Aseguramiento'
            context['action'] = 'add'
        context['module_name'] = MODULE_NAME
        context['list_url'] = self.success_url
        context['today'] = timezone.localdate()
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        pk = self.kwargs.get('pk')
        try:
            # =========================================================================
            # 1. BUSCAR LOCALIZACIONES MONITOREADAS (Para llenar el datalist de Monitoreo)
            # =========================================================================
            if action == 'search_locations':
                term = request.POST.get('term', '').strip()
                code = request.POST.get('code', '').strip()

                queryset = Monitoring.objects.all()
                if code:
                    queryset = queryset.filter(variety_code__icontains=code)
                if term:
                    queryset = queryset.filter(location__icontains=term)

                locations = queryset.exclude(location__isnull=True).exclude(location='').values_list(
                    'location', flat=True
                ).distinct().order_by('location')[:20]
                
                return JsonResponse({'items': list(locations)})

            # =========================================================================
            # 2. BUSCAR CÓDIGOS DE VARIEDAD MONITOREADOS (Para llenar el datalist de Monitoreo)
            # =========================================================================
            elif action == 'search_variety_codes':
                term = request.POST.get('term', '').strip()
                location = request.POST.get('location', '').strip()

                queryset = Monitoring.objects.all()
                if location:
                    queryset = queryset.filter(location__icontains=location)
                if term:
                    queryset = queryset.filter(variety_code__icontains=term)

                codes = queryset.exclude(variety_code__isnull=True).exclude(variety_code='').values_list(
                    'variety_code', flat=True
                ).distinct().order_by('variety_code')[:20]

                return JsonResponse({'items': list(codes)})

            # =========================================================================
            # 3. OBTENER LOS PARÁMETROS DE ASEGURAMIENTO (CHECKLIST)
            # =========================================================================
            elif action == 'get_biological_targets':
                parameters_qs = AssuranceParameter.objects.filter(is_active=True).order_by('id')
                items = [{
                    'id': p.id,
                    'name': p.name,
                    'description': getattr(p, 'description', '') or 'Parámetro de control',
                } for p in parameters_qs]
                
                return JsonResponse({'items': items})

            # =========================================================================
            # 4. CARGAR CONTEXTO DETALLADO
            # =========================================================================
            elif action == 'get_inventory_context':
                location = request.POST.get('location', '').strip()
                code = request.POST.get('code', '').strip()

                inventory = PlantInventory.objects.filter(location__iexact=location, code__iexact=code, is_active=True).first()
                if not inventory:
                    return JsonResponse({'error': 'No se encontró el inventario.'})

                last_monitoring = Monitoring.objects.filter(
                    location__iexact=location, 
                    variety_code__iexact=code
                ).order_by('-monitoring_date', '-id').first()

                matrix_data = []
                if last_monitoring:
                    # Traemos todos los detalles del monitoreo
                    details = MonitoringDetail.objects.filter(monitoring=last_monitoring)
                    
                    # OBTENER TODOS LOS CUADROS QUE EXISTEN EN ESTE MONITOREO
                    # Cambiamos a order_by para que salgan en orden secuencial
                    sections = details.values_list('bed_section_id', 'bed_section__number').distinct().order_by('bed_section__number')
                    
                    for s_id, s_number in sections:
                        d_section = details.filter(bed_section_id=s_id)
                        
                        section = {
                            'number': s_number,
                            'high': [{'name': d.biological_target.name, 'severity': d.severity} 
                                     for d in d_section.filter(third='high')],
                            'middle': [{'name': d.biological_target.name, 'severity': d.severity} 
                                       for d in d_section.filter(third='middle')],
                            'low': [{'name': d.biological_target.name, 'severity': d.severity} 
                                    for d in d_section.filter(third='low')]
                        }
                        matrix_data.append(section)

                response_data = {
                    'inventory': {
                        'id': inventory.id,
                        'location': inventory.location,
                        'code': inventory.code or '',
                        'variety': inventory.variety or '',
                        'plot_id': inventory.plot_id or 'N/A',
                        'plants': inventory.plants,
                    },
                    'structure': {'block': '-', 'bay': '-', 'bed': inventory.location},
                    'matrix_data': matrix_data,
                    'monitoring_summary': "Cargado correctamente",
                }
                return JsonResponse(response_data)

            # =========================================================================
            # 5. GUARDAR ASEGURAMIENTO
            # =========================================================================
            elif action == 'save_assurance':
                inventory_id = request.POST.get('inventory_id')
                details_json = request.POST.get('details', '[]')
                # Obtenemos el pk de la URL (si es edición)
                pk = self.kwargs.get('pk') 

                if not inventory_id:
                    return JsonResponse({'error': 'Faltan parámetros de inventario requeridos.'}, status=400)

                try:
                    inventory = PlantInventory.objects.get(pk=inventory_id)
                    details_data = json.loads(details_json)

                    with transaction.atomic():
                        # Lógica de Crear o Editar
                        if pk:
                            # EDITAR: Recuperamos el existente
                            assurance = Assurance.objects.get(pk=pk)
                            # Eliminamos detalles previos para reemplazarlos (más seguro y limpio)
                            AssuranceDetail.objects.filter(assurance=assurance).delete()
                        else:
                            # CREAR: Instanciamos nuevo
                            assurance = Assurance()
                            assurance.assurance_date = timezone.localdate()
                            assurance.week = timezone.localdate().isocalendar()[1]
                            assurance.audited_by = request.user if request.user.is_authenticated else None

                        # Actualizamos/Asignamos los campos (en ambos casos)
                        assurance.location = inventory.location
                        assurance.variety_code = inventory.code
                        assurance.variety_name = inventory.variety
                        assurance.plot_id = inventory.plot_id
                        assurance.save()

                        # Guardamos los nuevos detalles
                        for item in details_data:
                            AssuranceDetail.objects.create(
                                assurance=assurance,
                                parameter_id=item['parameter_id'],
                                complies=bool(item.get('complies')),
                                observations=item.get('observations', '').strip()
                            )

                    return JsonResponse({'success': True, 'redirect_url': str(self.success_url)})
                
                except PlantInventory.DoesNotExist:
                    return JsonResponse({'error': 'El inventario seleccionado no existe.'}, status=404)
                except Exception as e:
                    return JsonResponse({'error': f'Error al guardar: {str(e)}'}, status=500)

            return JsonResponse({'error': 'Acción inválida'}, status=400)

        except Exception as e:
            print(traceback.format_exc())
            return JsonResponse({'error': str(e)}, status=500)