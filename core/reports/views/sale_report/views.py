import json
from core.security.mixins import StrictPermissionMixin
from django.http import HttpResponse
from django.views.generic import FormView
from django.db.models import Sum, Q, F, FloatField, Value as V
from django.db.models.functions import Coalesce

from core.pos.models import Sale
from core.reports.forms import ReportForm

MODULE_NAME = 'R.Totales'


class SaleReportView(StrictPermissionMixin, FormView):
    permission_required = 'pos.report_sales_menu'
    template_name = 'sale_report/report.html'
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

                # Filtrar por rango de fechas
                if len(start_date) and len(end_date):
                    queryset = queryset.filter(date_joined__range=[start_date, end_date])

                # Serializar detalle de ventas
                for i in queryset:
                    data.append(i.toJSON())

                # ---- Totales ----
                totals = [
                {
                    "name": "Total Efectivo",
                    "value": float(
                        queryset.filter(paymentmethod="cash", transfermethods__isnull=True)
                        .aggregate(total=Coalesce(Sum("total", output_field=FloatField()), 0.0))["total"]
                    )
                    +
                    (
                        queryset.filter(paymentmethod="mixto")
                        .aggregate(total=Coalesce(Sum("cash", output_field=FloatField()), 0.0))["total"]
                    ),
                },
                {
                    "name": "Total Nequi",
                    "value": float(
                        queryset.filter(paymentmethod="transfer", transfermethods="nequi")
                        .aggregate(total=Coalesce(Sum("total", output_field=FloatField()), 0.0))["total"]
                        +
                        queryset.filter(nequi_value__gt=0)
                        .aggregate(total=Coalesce(Sum("nequi_value", output_field=FloatField()), 0.0))["total"]
                    ),
                },
                {
                    "name": "Total Daviplata",
                    "value": float(
                        queryset.filter(paymentmethod="transfer", transfermethods="daviplata")
                        .aggregate(total=Coalesce(Sum("total", output_field=FloatField()), 0.0))["total"]
                        +
                        queryset.filter(daviplata_value__gt=0)
                        .aggregate(total=Coalesce(Sum("daviplata_value", output_field=FloatField()), 0.0))["total"]
                    ),
                },
                {
                    "name": "Total Tarjetas",
                    "value": float(
                        queryset.filter(
                            paymentmethod__in=["creditCard", "debitCard"],
                            transfermethods__isnull=True
                        )
                        .aggregate(total=Coalesce(Sum("total", output_field=FloatField()), 0.0))["total"]
                    ),
                },
                {
                    "name": "Propinas",
                    "value": float(
                        queryset.aggregate(
                            total=Coalesce(Sum("propina", output_field=FloatField()), 0.0)
                        )["total"]
                    ),
                },
                {
                    "name": "Total",
                    "value": float(
                        queryset.aggregate(
                            total=Coalesce(
                                Sum(F("total") + F("propina")),
                                0.0,
                                output_field=FloatField()
                            )
                        )["total"]
                    ),
                },
            ]

                # empaquetamos la respuesta
                response = {
                    "sales": data,
                    "totals": totals
                }
            else:
                response = {"error": "No ha seleccionado ninguna opción"}
        except Exception as e:
            response = {"error": str(e)}

        return HttpResponse(json.dumps(response), content_type="application/json")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Reporte de Totales'
        context['module_name'] = MODULE_NAME
        return context
