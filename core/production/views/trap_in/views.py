import json
import datetime
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views.generic import ListView, TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse_lazy
from django.db import transaction # Importante para asegurar integridad
from core.production.models import ReadingInternalTrap, ReadingInternalTrapDetail, TrapIn, BiologicalTarget, Block

MODULE_NAME = 'Trampas Internas'

class ReadingInternalListView(ListView):
    model = ReadingInternalTrap
    template_name = 'trap_in/list.html'

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = []
        try:
            action = request.POST.get('action')
            if action == 'search':
                week_filter = request.POST.get('week_filter')
                if week_filter and '-W' in week_filter:
                    year, week = week_filter.split('-W')
                    queryset = ReadingInternalTrap.objects.filter(
                        date_reading__year=year, 
                        date_reading__week=week
                    )
                    data = [i.toJSON() for i in queryset]
            elif action == 'get_detail':
                queryset = ReadingInternalTrapDetail.objects.filter(reading_id=request.POST.get('id'))
                data = [i.toJSON() for i in queryset]
            else:
                data = {'error': 'Acción no permitida'}
        except Exception as e:
            data = {'error': str(e)}
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Historial de Lecturas Internas'
        context['list_url'] = reverse_lazy('production:reading_internal_list')
        context['create_url'] = reverse_lazy('production:reading_internal_create')
        context['module_name'] = MODULE_NAME
        return context

class ReadingInternalAddView(TemplateView):
    template_name = 'trap_in/create.html'
    success_url = reverse_lazy('production:reading_internal_list')

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Endpoint interno AJAX para traer las trampas por bloque
        action = request.GET.get('action')
        if action == 'get_traps_by_block':
            block_id = request.GET.get('block_id')

            # 1. Calculamos el inicio y fin de la semana actual
            today = timezone.localdate()
            # Si consideras que la semana empieza en lunes (0):
            start_of_week = today - datetime.timedelta(days=today.weekday())
            end_of_week = start_of_week + datetime.timedelta(days=6)

            # 2. Obtenemos los IDs de las trampas que YA tienen lectura en esta semana
            traps_with_reading_this_week = ReadingInternalTrap.objects.filter(
                date_reading__range=[start_of_week, end_of_week]
            ).values_list('trap_in_id', flat=True)

            # 3. Filtramos las trampas activas del bloque EXCLUYENDO las que ya fueron leídas esta semana
            traps = TrapIn.objects.filter(
                block_id=block_id, 
                is_active=True
            ).exclude(
                id__in=traps_with_reading_this_week
            ).values('id', 'name')

            return JsonResponse(list(traps), safe=False)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['blocks'] = Block.objects.filter(is_active=True).order_by('name') # Pasamos los bloques
        context['biological_targets'] = BiologicalTarget.objects.filter(
            is_active=True, 
            internal_trap=True 
        )
        context['title'] = 'Nueva Lectura de Trampas Internas'
        context['list_url'] = self.success_url
        context['module_name'] = MODULE_NAME
        return context

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            body_unicode = request.body.decode('utf-8')
            body_data = json.loads(body_unicode)
            
            with transaction.atomic():
                date_reading = body_data.get('date_reading')
                trap_id = body_data.get('trap_in_id')
                general_obs = body_data.get('observation', '').strip()
                targets_data = body_data.get('targets', {}) # Estructura: {target_id: {qty: X, obs: 'Y'}}

                if not trap_id:
                    raise Exception("Debe seleccionar una trampa.")

                # Creamos la cabecera para la trampa seleccionada
                reading = ReadingInternalTrap.objects.create(
                    trap_in_id=trap_id,
                    date_reading=date_reading,
                    observation=general_obs
                )
                
                # Guardamos los detalles combinando cantidad y observación
                for target_id, info in targets_data.items():
                    qty_int = int(info.get('qty', 0))
                    observation = info.get('obs', '').strip()

                    # Guardamos si hay cantidad mayor a 0 o si el usuario escribió una observación
                    if qty_int > 0 or observation:
                        ReadingInternalTrapDetail.objects.create(
                            reading=reading,
                            biological_target_id=target_id,
                            quantity=qty_int
                        )

                data['msg'] = 'Lectura guardada correctamente'
                data['success_url'] = str(self.success_url)
        except Exception as e:
            print("--- ERROR AL GUARDAR ---")
            print(str(e))
            data['error'] = str(e)
        return JsonResponse(data)