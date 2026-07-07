import json
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.utils import timezone
from core.production.models import Block, Monitoring # Asegúrate de importar tus modelos

class MonitoringCoverageReportView(TemplateView):
    template_name = 'monitoring_coverage/report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Reporte de Cobertura de Monitoreo'
        context['today'] = timezone.localdate().strftime('%d/%m/%Y')
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        
        if action == 'get_graph_data':
            # Rango de fechas recibido desde el frontend
            date_range = request.POST.get('date_range', '')
            try:
                start_date, end_date = date_range.split(' - ')
                # Conversión de formato d/m/Y a Y-m-d para Django
                start_date = timezone.datetime.strptime(start_date.strip(), '%d/%m/%Y').date()
                end_date = timezone.datetime.strptime(end_date.strip(), '%d/%m/%Y').date()
            except:
                start_date = end_date = timezone.localdate()

            # Lógica de cálculo por bloque
            # Obtenemos todos los bloques con sus camas totales y monitoreadas
            data = []
            categories = []
            target_data = []
            real_data = []

            # Optimizamos consulta: contamos camas únicas por bloque en el periodo
            blocks = Block.objects.annotate(
                total_beds=Count('blockbay'),
                monitored_beds=Count('monitoring', filter=Q(
                    monitoring__monitoring_date__range=[start_date, end_date]
                ), distinct=True)
            )

            for block in blocks:
                # Meta: 50% de las camas totales sembradas
                target = float(block.total_beds) * 0.50
                real = float(block.monitored_beds)
                
                categories.append(block.name)
                target_data.append(round(target, 1))
                real_data.append(round(real, 1))

            return JsonResponse({
                'categories': categories,
                'target_data': target_data,
                'real_data': real_data
            }, safe=False)

        return JsonResponse({}, status=400)