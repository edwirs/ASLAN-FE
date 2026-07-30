import json
import datetime
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.forms.models import model_to_dict
from core.production.models import ReadingExternalTrap, ReadingExternalTrapDetail, TrapOut, BiologicalTarget, Block

MODULE_NAME = 'Trampas Externas'

class ReadingExternalListView(ListView):
    model = ReadingExternalTrap
    template_name = 'trap_out/list.html'

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
                    queryset = ReadingExternalTrap.objects.filter(
                        date_reading__year=year, 
                        date_reading__week=week
                    )
                    data = [i.toJSON() for i in queryset]
            elif action == 'get_detail':
                queryset = ReadingExternalTrapDetail.objects.filter(reading_id=request.POST.get('id'))
                data = [i.toJSON() for i in queryset]
            else:
                data = {'error': 'Acción no permitida'}
        except Exception as e:
            data = {'error': str(e)}
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Historial de Lecturas Externas'
        context['list_url'] = reverse_lazy('production:reading_external_list')
        context['create_url'] = reverse_lazy('production:reading_external_create')
        context['module_name'] = MODULE_NAME
        return context

class ReadingExternalAddView(TemplateView):
    template_name = 'trap_out/create.html'
    success_url = reverse_lazy('production:reading_external_list')

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        action = request.GET.get('action')
        
        # 1. AJAX para listar trampas externas disponibles en la semana actual
        if action == 'get_available_traps':
            today = timezone.localdate()
            start_of_week = today - datetime.timedelta(days=today.weekday())
            end_of_week = start_of_week + datetime.timedelta(days=6)

            # IDs de trampas externas que YA tienen lectura esta semana
            traps_with_reading_this_week = ReadingExternalTrap.objects.filter(
                date_reading__range=[start_of_week, end_of_week]
            ).values_list('trap_out_id', flat=True)

            # Excluimos las ya leídas y solo traemos las activas
            traps = TrapOut.objects.filter(
                is_active=True
            ).exclude(
                id__in=traps_with_reading_this_week
            ).values('id', 'name')

            return JsonResponse(list(traps), safe=False)
            
        # 2. AJAX para DataTables (Listado general de lecturas externas)
        if action == 'search':
            data = []
            try:
                week_filter = request.POST.get('week_filter') # Opcional si usas filtros
                queryset = ReadingExternalTrap.objects.all().order_by('-date_reading')
                for i in queryset:
                    data.append(i.toJSON())
            except Exception as e:
                print(e)
            return JsonResponse(data, safe=False)

        # 3. AJAX para obtener el detalle (blancos biológicos) para la expansión de la tabla
        if action == 'get_detail':
            data = []
            try:
                reading_id = request.GET.get('id') or request.POST.get('id')
                details = ReadingExternalTrapDetail.objects.filter(reading_id=reading_id)
                for d in details:
                    data.append(d.toJSON())
            except Exception as e:
                print(e)
            return JsonResponse(data, safe=False)

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['biological_targets'] = BiologicalTarget.objects.filter(
            is_active=True, 
            external_trap=True 
        )
        context['title'] = 'Nueva Lectura de Trampas Externas'
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
                trap_out_id = body_data.get('trap_out_id')
                general_obs = body_data.get('observation', '').strip()
                targets_data = body_data.get('targets', {}) # Estructura: {target_id: {qty: X}}

                if not trap_out_id:
                    raise Exception("Debe seleccionar una trampa externa.")

                # Creamos la cabecera de la lectura
                reading = ReadingExternalTrap.objects.create(
                    trap_out_id=trap_out_id,
                    date_reading=date_reading,
                    observation=general_obs
                )
                
                # Guardamos los detalles con cantidad > 0
                for target_id, info in targets_data.items():
                    qty_int = int(info.get('qty', 0))

                    if qty_int > 0:
                        ReadingExternalTrapDetail.objects.create(
                            reading=reading,
                            biological_target_id=target_id,
                            quantity=qty_int
                        )

                data['msg'] = 'Lectura de trampa externa guardada correctamente'
                data['success_url'] = str(self.success_url)
        except Exception as e:
            print("--- ERROR AL GUARDAR ---")
            print(str(e))
            data['error'] = str(e)
        return JsonResponse(data)