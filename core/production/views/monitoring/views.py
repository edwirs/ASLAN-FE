import json
import traceback
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.utils import timezone

from core.catalogs.models import BiologicalTarget, Block, BlockBay, Bed, VarietyTargetGallery, MonitoringSettings
from core.production.models import Monitoring, MonitoringDetail, MonitoringConfiguration, PlantInventory
from core.security.mixins import GroupPermissionMixin


MODULE_NAME = 'Monitoreo'


class MonitoringListView(GroupPermissionMixin, TemplateView):
    template_name = 'monitoring/list.html'
    permission_required = 'view_monitoring'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()

        # 1. Obtener el último monitoreo con sus relaciones necesarias
        last_monitoring = Monitoring.objects.select_related(
            'block', 'bay', 'bed', 'monitored_by'
        ).prefetch_related(
            'details__biological_target',
            'details__severity_grade',
            'bed__sections'
        ).order_by('-monitoring_date', '-id').first()

        matrix_list = []
        
        if last_monitoring and last_monitoring.bed:
            # 2. Obtener todas las secciones (cuadros) activas de la cama, ordenadas
            sections = last_monitoring.bed.sections.filter(is_active=True).order_by('number')
            
            # 3. Obtener los IDs de las secciones que tienen activado el monitoreo en MonitoringSettings
            # Filtramos solo aquellas secciones que pertenecen a la cama actual
            monitored_section_ids = list(
                MonitoringSettings.objects.filter(
                    bed_section__in=sections, 
                    is_monitored=True
                ).values_list('bed_section_id', flat=True)
            )
            
            # 4. Crear mapa de detalles para acceso rápido (indexado por ID de sección)
            details_map = {sec.id: {'high': [], 'middle': [], 'low': []} for sec in sections}
            
            for detail in last_monitoring.details.all():
                sec_id = detail.bed_section_id
                # --- DEBUG: Vamos a ver qué texto tiene guardado realmente el campo 'third' ---
                # print(f"DEBUG: Detalle ID {detail.id}, Sección {sec_id}, Tercio guardado: '{detail.third}'")
                
                # Normalizamos el tercio (por si tiene espacios o mayúsculas)
                tercio = str(detail.third).lower().strip()
                
                if sec_id in details_map:
                    # Comprobamos si el valor normalizado coincide con nuestras llaves
                    if tercio in details_map[sec_id]:
                        details_map[sec_id][tercio].append({
                            'name': detail.biological_target.name,
                            'severity': detail.severity_grade.description if detail.severity_grade else None
                        })
                    else:
                        print(f"DEBUG: ¡ALERTA! El tercio '{tercio}' no coincide con nuestras llaves (high, middle, low).")

            # 5. Construir la lista final
            for sec in sections:
                # PRUEBA: Forzamos un dato ficticio en 'high' para ver si aparece en pantalla
                test_data = [{'name': 'PRUEBA', 'severity': 'Alta'}] if sec.id == sections[0].id else []
                
                matrix_list.append({
                    'number': sec.number,
                    'is_configured': sec.id in monitored_section_ids,
                    'high': details_map[sec.id]['high'] or test_data, # Si está vacío, pone el de prueba
                    'middle': details_map[sec.id]['middle'],
                    'low': details_map[sec.id]['low']
                }) 

        # 6. Cargar el contexto final
        context['title'] = 'Resumen del Último Monitoreo'
        context['module_name'] = MODULE_NAME
        context['list_url'] = reverse_lazy('production:monitoring_list')
        context['create_url'] = reverse_lazy('production:monitoring_create')
        
        context['monitoring'] = last_monitoring
        context['matrix_data'] = matrix_list
        context['week_number'] = today.isocalendar().week

        return context


class MonitoringCreateView(GroupPermissionMixin, TemplateView):
    template_name = 'monitoring/create.html'
    permission_required = 'add_monitoring'

    def get_week_side(self, block=None):
        today = timezone.localdate()
        week = today.isocalendar().week
        default_side = 'right' if week % 2 == 0 else 'left'

        if not block:
            return default_side

        configuration = MonitoringConfiguration.objects.filter(
            block=block,
            is_active=True
        ).first()

        if not configuration:
            return default_side

        return (
            configuration.even_week_side
            if week % 2 == 0
            else configuration.odd_week_side
        )

    def parse_location(self, location):
        parts = [
            item.strip()
            for item in str(location or '').split('.')
            if item.strip()
        ]

        if len(parts) < 3:
            return None

        try:
            return {
                'block': int(parts[0]),
                'bay': int(parts[1]),
                'bed': int(parts[2]),
            }
        except ValueError:
            return None

    def resolve_structure(self, location):
        parsed = self.parse_location(location)

        if not parsed:
            return {
                'parsed': None,
                'block': None,
                'bay': None,
                'bed': None,
                'sections': [],
                'error': 'La ubicación debe tener el formato bloque.nave.cama',
            }

        block_number = parsed['block']
        bay_number = parsed['bay']
        bed_number = parsed['bed']

        block_codes = [str(block_number), f'B{block_number}', f'B{block_number:02d}']
        bay_codes = [str(bay_number), f'N{bay_number}', f'N{bay_number:02d}']

        block = Block.objects.filter(code__in=block_codes).first()
        bay = BlockBay.objects.filter(block=block, code__in=bay_codes).first() if block else None
        bed = Bed.objects.filter(bay=bay, number=bed_number, is_active=True).first() if bay else None
        
        sections = []
        if bed:
            # FILTRO CORREGIDO: Solo secciones con monitoreo activo
            sections = [
                {'id': s.id, 'number': s.number}
                for s in bed.sections.filter(is_active=True, monitoringsettings__is_monitored=True).distinct().order_by('number')
            ]

        return {
            'parsed': parsed,
            'block': block,
            'bay': bay,
            'bed': bed,
            'sections': sections,
            'error': '' if bed and sections else 'La ubicación no tiene cuadros configurados para monitoreo',
        }

    def inventory_to_json(self, inventory):
        variety_name = str(inventory.variety) if hasattr(inventory, 'variety') and inventory.variety else ''
        return {
            'id': inventory.id,
            'location': inventory.location,
            'code': inventory.code or '',
            'variety': variety_name,
            'variety_id': inventory.variety.id if hasattr(inventory.variety, 'id') else None,
            'plot_id': inventory.plot_id or '',
            'plants': inventory.plants,
            'area': inventory.area or '',
            'genus': inventory.genus or '',
        }

    def search_locations(self, request):
        # Si el usuario ya escribió un código de variedad, filtramos las ubicaciones asociadas
        code = request.POST.get('code', '').strip()
        queryset = PlantInventory.objects.filter(is_active=True).exclude(location__in=[None, ''])
        
        if code:
            queryset = queryset.filter(code__iexact=code)
            
        items = queryset.values_list('location', flat=True).distinct().order_by('location')[:20]
        return JsonResponse({'items': list(items)})

    def search_variety_codes(self, request):
        # Si el usuario ya escribió una ubicación, filtramos los códigos asociados
        location = request.POST.get('location', '').strip()
        queryset = PlantInventory.objects.filter(is_active=True).exclude(code__in=[None, ''])
        
        if location:
            queryset = queryset.filter(location__iexact=location)
            
        items = queryset.values_list('code', flat=True).distinct().order_by('code')[:20]
        return JsonResponse({'items': list(items)})

    def get_inventory_context(self, request):
        location = request.POST.get('location', '').strip()
        code = request.POST.get('code', '').strip()

        queryset = PlantInventory.objects.filter(is_active=True)
        if location: queryset = queryset.filter(location__iexact=location)
        if code: queryset = queryset.filter(code__iexact=code)
        
        inventory = queryset.order_by('location', 'code').first()
        if not inventory:
            return JsonResponse({'error': 'No se encontró inventario'})

        structure = self.resolve_structure(inventory.location)
        return JsonResponse({
            'inventory': self.inventory_to_json(inventory),
            'structure': {
                'parsed': structure['parsed'],
                'block_id': structure['block'].id if structure['block'] else '',
                'block': str(structure['block']) if structure['block'] else '',
                'bay_id': structure['bay'].id if structure['bay'] else '',
                'bay': str(structure['bay']) if structure['bay'] else '',
                'bed_id': structure['bed'].id if structure['bed'] else '',
                'bed': str(structure['bed']) if structure['bed'] else '',
                'sections': structure['sections'],
                'error': structure['error'],
            },
            'monitoring': {
                'date': timezone.localdate().strftime('%Y-%m-%d'),
                'week': timezone.localdate().isocalendar().week,
                'bed_side': self.get_week_side(structure['block']),
            }
        })

    def get_biological_targets(self, request):
        targets = BiologicalTarget.objects.filter(is_active=True).select_related('category').prefetch_related('category__severity_grades').order_by('name')
        global_targets_with_photos = set(VarietyTargetGallery.objects.exclude(image='').values_list('biological_target_id', flat=True))

        items = []
        for target in targets:
            items.append({
                'id': target.id,
                'name': target.name,
                'category': target.category.name if target.category else 'Sin Categoría',
                'severity_grades': [{'id': g.id, 'description': g.description} for g in target.category.severity_grades.filter(is_active=True).order_by('grade_number')] if target.category else [],
                'has_photos': target.id in global_targets_with_photos
            })
        return JsonResponse({'items': items})

    def get_target_gallery(self, request):
        target_id = request.POST.get('target_id')
        gallery_records = VarietyTargetGallery.objects.filter(biological_target_id=target_id).select_related('variety')
        
        photos = [{'image_url': r.image.url, 'variety_name': str(r.variety)} for r in gallery_records if r.image]
        return JsonResponse({'photos': photos})

    def save_monitoring(self, request):
        payload = json.loads(request.POST.get('payload', '{}'))
        details = payload.get('details', [])
        if not details: return JsonResponse({'error': 'Agregue detalles'}, status=400)

        inventory = PlantInventory.objects.filter(is_active=True, location__iexact=payload.get('location')).first()
        structure = self.resolve_structure(inventory.location)
        
        with transaction.atomic():
            monitoring = Monitoring.objects.create(
                monitoring_date=timezone.localdate(),
                week=timezone.localdate().isocalendar().week,
                location=inventory.location,
                block=structure['block'],
                bay=structure['bay'],
                bed=structure['bed'],
                bed_side=self.get_week_side(structure['block']),
                variety_code=inventory.code or '',
                variety_name=inventory.variety or '',
                plot_id=inventory.plot_id,
                monitored_quantity=payload.get('monitored_quantity') or 0,
                monitoring_type='bed',
                monitored_by=request.user if request.user.is_authenticated else None,
            )

            for detail in details:
                MonitoringDetail.objects.create(
                    monitoring=monitoring,
                    bed_section_id=detail['bed_section_id'],
                    third=detail['third'],
                    biological_target_id=detail['biological_target_id'],
                    affected_quantity=0,
                    severity=Decimal(str(detail.get('severity') or 0)),
                    severity_grade_id=detail.get('severity_grade_id'),
                    observations=detail.get('observations') or '',
                )

        return JsonResponse({'success': True, 'redirect': str(reverse_lazy('production:monitoring_list'))})

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        try:
            if action == 'search_locations': return self.search_locations(request)
            if action == 'search_variety_codes': return self.search_variety_codes(request)
            if action == 'get_inventory_context': return self.get_inventory_context(request)
            if action == 'get_biological_targets': return self.get_biological_targets(request)
            if action == 'get_target_gallery': return self.get_target_gallery(request)
            if action == 'save_monitoring': return self.save_monitoring(request)
            return JsonResponse({'error': 'Acción inválida'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nuevo Monitoreo'
        context['module_name'] = MODULE_NAME
        context['list_url'] = reverse_lazy('production:monitoring_list')
        context['today'] = timezone.localdate()
        context['week_number'] = timezone.localdate().isocalendar().week
        return context