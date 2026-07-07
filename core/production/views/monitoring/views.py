import json
import traceback
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.utils import timezone

from core.catalogs.models import BiologicalTarget, Block, BlockBay, Bed, VarietyTargetGallery
from core.production.models import Monitoring, MonitoringDetail, MonitoringConfiguration, PlantInventory
from core.security.mixins import GroupPermissionMixin


MODULE_NAME = 'Monitoreo'


class MonitoringListView(GroupPermissionMixin, TemplateView):
    template_name = 'monitoring/list.html'
    permission_required = 'view_monitoring'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()

        last_monitoring = Monitoring.objects.select_related(
            'block', 'bay', 'bed', 'monitored_by'
        ).prefetch_related(
            'details__biological_target',
            'details__severity_grade',
            'bed__sections'
        ).order_by('-monitoring_date', '-id').first()

        matrix_data = {}
        if last_monitoring and last_monitoring.bed:
            sections = last_monitoring.bed.sections.filter(is_active=True).order_by('number')
            
            for sec in sections:
                matrix_data[sec.id] = {
                    'number': sec.number,
                    'high': [],
                    'middle': [],
                    'low': []
                }

            for detail in last_monitoring.details.all():
                if detail.bed_section_id in matrix_data:
                    matrix_data[detail.bed_section_id][detail.third].append({
                        'name': detail.biological_target.name,
                        'severity': detail.severity_grade.description if detail.severity_grade else None
                    })

        context['title'] = 'Resumen del Último Monitoreo'
        context['module_name'] = MODULE_NAME
        context['list_url'] = reverse_lazy('production:monitoring_list')
        context['create_url'] = reverse_lazy('production:monitoring_create')
        
        context['monitoring'] = last_monitoring
        context['matrix_data'] = matrix_data.values() if matrix_data else None
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

        block_codes = [
            str(block_number),
            f'B{block_number}',
            f'B{block_number:02d}',
        ]

        bay_codes = [
            str(bay_number),
            f'N{bay_number}',
            f'N{bay_number:02d}',
        ]

        block = Block.objects.filter(code__in=block_codes).first()
        bay = None
        bed = None
        sections = []

        if block:
            bay = BlockBay.objects.filter(
                block=block,
                code__in=bay_codes
            ).first()

        if bay:
            bed = Bed.objects.filter(
                bay=bay,
                number=bed_number,
                is_active=True
            ).first()

        if bed:
            sections = [
                {
                    'id': section.id,
                    'number': section.number,
                }
                for section in bed.sections.filter(is_active=True).order_by('number')
            ]

        return {
            'parsed': parsed,
            'block': block,
            'bay': bay,
            'bed': bed,
            'sections': sections,
            'error': '' if bed and sections else 'La ubicación existe, pero no tiene cama/cuadros configurados',
        }

    def inventory_to_json(self, inventory):
        if hasattr(inventory, 'variety') and inventory.variety:
            if hasattr(inventory.variety, 'id'):
                variety_id = inventory.variety.id
                variety_name = str(inventory.variety)
            else:
                variety_id = None
                variety_name = str(inventory.variety)
        else:
            variety_id = None
            variety_name = ''

        return {
            'id': inventory.id,
            'location': inventory.location,
            'code': inventory.code or '',
            'variety': variety_name,
            'variety_id': variety_id,
            'plot_id': inventory.plot_id or '',
            'plants': inventory.plants,
            'area': inventory.area or '',
            'genus': inventory.genus or '',
        }

    def search_locations(self, request):
        queryset = PlantInventory.objects.filter(is_active=True)
        code = request.POST.get('code', '').strip()
        term = request.POST.get('term', '').strip()

        if code:
            queryset = queryset.filter(code__iexact=code)

        if term:
            queryset = queryset.filter(location__icontains=term)

        locations = queryset.exclude(
            location__isnull=True
        ).exclude(
            location=''
        ).values_list(
            'location',
            flat=True
        ).distinct().order_by('location')[:20]

        return JsonResponse({'items': list(locations)})

    def search_variety_codes(self, request):
        queryset = PlantInventory.objects.filter(is_active=True)
        location = request.POST.get('location', '').strip()
        term = request.POST.get('term', '').strip()

        if location:
            queryset = queryset.filter(location__iexact=location)

        if term:
            queryset = queryset.filter(code__icontains=term)

        codes = queryset.exclude(
            code__isnull=True
        ).exclude(
            code=''
        ).values_list(
            'code',
            flat=True
        ).distinct().order_by('code')[:20]

        return JsonResponse({'items': list(codes)})

    def get_inventory_context(self, request):
        location = request.POST.get('location', '').strip()
        code = request.POST.get('code', '').strip()

        queryset = PlantInventory.objects.filter(is_active=True)

        if location:
            queryset = queryset.filter(location__iexact=location)

        if code:
            queryset = queryset.filter(code__iexact=code)

        if not location and not code:
            return JsonResponse({'error': 'Ingrese una ubicación o un código de variedad'})

        inventory = queryset.order_by('location', 'code').first()

        if not inventory:
            return JsonResponse({'error': 'No se encontró inventario con esos filtros'})

        structure = self.resolve_structure(inventory.location)
        block = structure['block']
        bay = structure['bay']
        bed = structure['bed']

        return JsonResponse({
            'inventory': self.inventory_to_json(inventory),
            'structure': {
                'parsed': structure['parsed'],
                'block_id': block.id if block else '',
                'block': str(block) if block else '',
                'bay_id': bay.id if bay else '',
                'bay': str(bay) if bay else '',
                'bed_id': bed.id if bed else '',
                'bed': str(bed) if bed else '',
                'sections': structure['sections'],
                'error': structure['error'],
            },
            'monitoring': {
                'date': timezone.localdate().strftime('%Y-%m-%d'),
                'week': timezone.localdate().isocalendar().week,
                'bed_side': self.get_week_side(block),
            }
        })

    def get_biological_targets(self, request):
        # CAMBIO: La validación ahora es global para el catálogo de apoyo visual
        targets = BiologicalTarget.objects.filter(is_active=True).select_related('category').prefetch_related('category__severity_grades').order_by('name')

        # Obtenemos un set de todos los blancos que tienen AL MENOS una foto sin importar la variedad
        global_targets_with_photos = set(
            VarietyTargetGallery.objects.exclude(image='')
            .values_list('biological_target_id', flat=True)
        )

        items = []
        for target in targets:
            nombre_categoria = target.category.name if target.category else 'Sin Categoría'
            
            grades_list = []
            if target.category:
                grades = target.category.severity_grades.filter(is_active=True).order_by('grade_number')
                for g in grades:
                    grades_list.append({
                        'id': g.id,
                        'grade_number': g.grade_number,
                        'name': g.name,
                        'min_value': float(g.min_value),
                        'max_value': float(g.max_value),
                        'description': g.description
                    })

            items.append({
                'id': target.id,
                'name': target.name,
                'code': getattr(target, 'code', ''),
                'category': nombre_categoria,
                'severity_grades': grades_list,
                'has_photos': target.id in global_targets_with_photos  # Validación global
            })

        return JsonResponse({'items': items})

    def get_target_gallery(self, request):
        # ACCIÓN NUEVA: Devuelve todas las imágenes de apoyo asociadas al blanco seleccionado
        target_id = request.POST.get('target_id')
        if not target_id:
            return JsonResponse({'error': 'Falta el identificador del blanco biológico'}, status=400)

        gallery_records = VarietyTargetGallery.objects.filter(biological_target_id=target_id).select_related('variety')
        
        photos = []
        for record in gallery_records:
            if record.image:
                variety_name = str(record.variety) if hasattr(record, 'variety') and record.variety else "General / Común"
                photos.append({
                    'image_url': record.image.url,
                    'variety_name': variety_name
                })
                
        return JsonResponse({'photos': photos})

    def save_monitoring(self, request):
        payload = json.loads(request.POST.get('payload', '{}'))
        details = payload.get('details', [])

        if not details:
            return JsonResponse({'error': 'Agregue al menos un blanco biológico'})

        location = payload.get('location', '').strip()
        code = payload.get('variety_code', '').strip()

        inventory_queryset = PlantInventory.objects.filter(is_active=True)

        if location:
            inventory_queryset = inventory_queryset.filter(location__iexact=location)

        if code:
            inventory_queryset = inventory_queryset.filter(code__iexact=code)

        inventory = inventory_queryset.order_by('location', 'code').first()

        if not inventory:
            return JsonResponse({'error': 'No se encontró el inventario seleccionado'})

        structure = self.resolve_structure(inventory.location)

        if not structure['bed']:
            return JsonResponse({'error': structure['error']})

        today = timezone.localdate()
        week = today.isocalendar().week

        with transaction.atomic():
            monitoring = Monitoring.objects.create(
                monitoring_date=today,
                week=week,
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
                    affected_quantity=detail.get('affected_quantity') or 0,
                    severity=Decimal(str(detail.get('severity') or 0)),
                    severity_grade_id=detail.get('severity_grade_id'),
                    observations=detail.get('observations') or '',
                )

        return JsonResponse({
            'success': True,
            'redirect': str(reverse_lazy('production:monitoring_list')),
        })

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')

        try:
            if action == 'search_locations':
                return self.search_locations(request)
            if action == 'search_variety_codes':
                return self.search_variety_codes(request)
            if action == 'get_inventory_context':
                return self.get_inventory_context(request)
            if action == 'get_biological_targets':
                return self.get_biological_targets(request)
            if action == 'get_target_gallery':  # Mapeo de la nueva acción
                return self.get_target_gallery(request)
            if action == 'save_monitoring':
                return self.save_monitoring(request)

            return JsonResponse({'error': 'Acción inválida'})
        except Exception as e:
            print(traceback.format_exc())
            return JsonResponse({'error': str(e)}, status=500)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nuevo Monitoreo'
        context['module_name'] = MODULE_NAME
        context['list_url'] = reverse_lazy('production:monitoring_list')
        context['today'] = timezone.localdate()
        context['week_number'] = timezone.localdate().isocalendar().week

        return context