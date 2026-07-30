import json
from django.http import JsonResponse, HttpResponse
from django.views.generic import ListView, TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse_lazy
from core.production.models import ReadingICA, TrapICA
from django.db.models import Count, Max

MODULE_NAME = 'Trampas ICA'

class ReadingICAListView(ListView):
    model = ReadingICA
    template_name = 'trap_ica/list.html'

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST.get('action')
            
            if action == 'search':
                week_filter = request.POST.get('week_filter')
                if week_filter and '-W' in week_filter:
                    year, week = week_filter.split('-W')
                    queryset = ReadingICA.objects.filter(
                        date_reading__year=year,
                        date_reading__week=week
                    )
                    # Convertimos a lista y formateamos la fecha a string
                    data = []
                    for item in queryset.values('date_reading') \
                            .annotate(total_traps=Count('id'), last_observation=Max('observation')) \
                            .order_by('-date_reading'):
                        
                        # Convertimos la fecha a string YYYY-MM-DD
                        item['date_reading'] = item['date_reading'].strftime('%Y-%m-%d')
                        data.append(item)
                else:
                    data = []

            elif action == 'get_detail':
                date_reading = request.POST.get('date')
                # Si tu modelo no tiene toJSON, devolvemos un formato manual
                queryset = ReadingICA.objects.filter(date_reading=date_reading)
                data = [{'trap_name': i.trap.name, 'quantity': i.quantity, 'observation': i.observation} for i in queryset]
            
            else:
                data['error'] = 'Acción no permitida'
        except Exception as e:
            data['error'] = str(e)
            
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Historial de Lecturas ICA'
        context['list_url'] = reverse_lazy('production:reading_ica_list') 
        context['create_url'] = reverse_lazy('production:reading_ica_create')
        context['module_name'] = MODULE_NAME
        return context

class ReadingICAAddView(TemplateView):
    template_name = 'trap_ica/create.html'
    success_url = reverse_lazy('production:reading_ica_list')

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['traps'] = TrapICA.objects.filter(is_active=True)
        context['title'] = 'Lectura de Trampas ICA'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME
        return context

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            date_reading = request.POST.get('date_reading')
            observation = request.POST.get('observation', '')
            
            for key, value in request.POST.items():
                if key.startswith('quantity_') and value and int(value) >= 0:
                    trap_id = key.split('_')[1]
                    ReadingICA.objects.create(
                        trap_id=trap_id,
                        quantity=int(value),
                        observation=observation,
                        date_reading=date_reading
                    )
            data['msg'] = 'Registros guardados correctamente'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)