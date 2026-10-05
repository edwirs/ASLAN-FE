import json

from core.security.mixins import StrictPermissionMixin
from django.http import HttpResponse
from django.views.generic import FormView
from django.db.models import Sum

from core.pos.models import Sale
from core.reports.forms import ReportForm

MODULE_NAME = 'R.Ventas'


class EmployeeSaleReportView(StrictPermissionMixin, FormView):
    permission_required = 'pos.report_employee_menu'
    template_name = 'employee_report/report.html'
    form_class = ReportForm

    def post(self, request, *args, **kwargs):
        action = request.POST['action']
        data = {}
        try:
            if action == 'search_report':
                data = []
                start_date = request.POST['start_date']
                end_date = request.POST['end_date']
                queryset = Sale.objects.filter()
                if len(start_date) and len(end_date):
                    queryset = queryset.filter(date_joined__range=[start_date, end_date])
                for i in queryset:
                    data.append(i.toJSON())
                #grouped_sales = queryset.values('employee__id', 'employee__names') \
                #    .annotate(subtotal=Sum('subtotal'), total=Sum('total')) \
                #    .order_by('employee__names')

                #for item in grouped_sales:
                #    data.append({
                #       'employee': {'names': item['employee__names']},
                #        'subtotal': float(item['subtotal']),
                #        'total': float(item['total']),
                #    })
                    
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Reporte de Ventas por Empleado'
        context['module_name'] = MODULE_NAME
        return context
