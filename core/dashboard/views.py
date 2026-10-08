import json
from datetime import datetime, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import FloatField, Sum, F
from django.db.models.functions import Coalesce, ExtractWeekDay, ExtractMonth, ExtractYear, ExtractWeek
from django.http import HttpResponse
from django.views.generic import TemplateView
from django.db.models import DecimalField
from django.utils.timezone import now, timedelta
from decimal import Decimal
from django.db.models import Count
import calendar

from core.pos.models import Sale, Product, SaleDetail, EmployeeTransaction
from core.security.models import Dashboard

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'panel.html'

    def get_real_income(self, start_date=None, end_date=None):
        from core.pos.models import SaleCreditPayment

        sales_filter = {}
        payments_filter = {}
        transactions_filter = {}

        if start_date and end_date:
            sales_filter["date_joined__range"] = [start_date, end_date]
            payments_filter["date_payment__range"] = [start_date, end_date]
            transactions_filter["created_at__range"] = [start_date, end_date]

        elif start_date:
            sales_filter["date_joined"] = start_date
            payments_filter["date_payment"] = start_date
            transactions_filter["created_at__date"] = start_date

        # ventas reales (no crédito)
        sales_total = (
            Sale.objects
            .filter(**sales_filter)
            .exclude(typemethods='credit')  # ajusta si tu valor real es otro
            .aggregate(
                total=Coalesce(
                    Sum(F('total') + F('propina')),
                    Decimal('0.00'),
                    output_field=DecimalField()
                )
            )['total']
        )

        # pagos de créditos
        credit_total = (
            SaleCreditPayment.objects
            .filter(**payments_filter)
            .aggregate(
                total=Coalesce(
                    Sum('total'),
                    Decimal('0.00'),
                    output_field=DecimalField()
                )
            )['total']
        )

        # DESCUENTOS EMPLEADOS
        discount_total = (
            EmployeeTransaction.objects
            .filter(
                source__in=['caja', 'inventory'],
                **transactions_filter
            )
            .aggregate(
                total=Coalesce(
                    Sum('amount'),
                    Decimal('0.00'),
                    output_field=DecimalField()
                )
            )['total']
        )

        return sales_total + credit_total - discount_total

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'get_graph_sales_year_month':
                data = []
                year = datetime.now().year
                queryset = Sale.objects.filter(date_joined__year=year)
                for m in range(1, 13):
                    total = queryset.filter(date_joined__month=m).aggregate(result=Coalesce(Sum(F('total') + F('propina')), 0.00, output_field=FloatField())).get('result')
                    data.append(float(total))
            elif action == 'get_graph_sales_products_year_month':
                data = []
                year = datetime.now().year

                for m in range(1, 13):
                    start = datetime(year, m, 1).date()
                    end = datetime(year, m, calendar.monthrange(year, m)[1]).date()

                    total = self.get_real_income(start, end)
                    data.append(float(total))
            elif action == 'get_graph_sales_weekday':
                data = []
                today = datetime.now().date()

                start_week = today - timedelta(days=today.weekday())
                end_week = start_week + timedelta(days=6)

                days_map = {
                    0: 'Lunes', 1: 'Martes', 2: 'Miércoles',
                    3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'
                }

                for i in range(7):
                    day = start_week + timedelta(days=i)
                    total = self.get_real_income(start_date=day)
                    data.append({'day': days_map[i], 'total': float(total)})
            elif action == 'get_graph_sales_week':
                data = []
                today = datetime.now().date()
                current_month = today.month
                current_year = today.year

                first_day = datetime(current_year, current_month, 1).date()
                last_day = datetime(current_year, current_month, calendar.monthrange(current_year, current_month)[1]).date()

                dates = [
                    first_day + timedelta(days=i)
                    for i in range((last_day - first_day).days + 1)
                ]

                weeks = sorted({d.isocalendar()[1] for d in dates})

                for w in weeks:
                    week_days = [d for d in dates if d.isocalendar()[1] == w]
                    start = min(week_days)
                    end = max(week_days)

                    total = self.get_real_income(start, end)

                    data.append({
                        'week': f"Semana {w}",
                        'total': float(total)
                    })
            elif action == 'get_sales_total_today':
                today = datetime.now().date()
                total = self.get_real_income(start_date=today)
                data = {'total': float(total)}
            elif action == 'get_sales_count_today':
                today = datetime.now().date()
                count = (
                    Sale.objects
                    .filter(date_joined=today)
                    .aggregate(count=Count('id'))['count']
                )
                data = {'count': count}
            elif action == 'get_product_total_today':
                today = datetime.now().date()
                best_seller = (
                    SaleDetail.objects
                    .filter(sale__date_joined=today)
                    .values('product__name')
                    .annotate(quantity=Sum('cant'))
                    .order_by('-quantity')
                    .first()
                )
                if best_seller:
                    data = {
                        'product': best_seller['product__name'],
                        'quantity': float(best_seller['quantity']) if best_seller['quantity'] % 1 else int(best_seller['quantity'])
                    }
                else:
                    data = {'product': None, 'quantity': 0}
            elif action == 'get_sales_total_week':
                today = datetime.now().date()
                start_week = today - timedelta(days=today.weekday())
                end_week = start_week + timedelta(days=6)          

                total = (
                    Sale.objects
                    .filter(date_joined__range=[start_week, end_week])
                    .count() 
                )
                data = {'total': total}
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            return HttpResponse(
                json.dumps({'error': str(e)}),
                content_type='application/json'
            )
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Panel de Administración'
        context['sales'] = Sale.objects.filter().order_by('-id')[0:10]
        context['dashboard'] = Dashboard.objects.first()
        return context
