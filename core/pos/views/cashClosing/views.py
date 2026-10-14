import json
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q, Sum
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views import View
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, DetailView

from core.pos.forms import CashClosingForm
from core.pos.models import CashClosing, Company, Sale, SaleCreditPayment, Expenses
from core.reports.forms import ReportForm

MODULE_NAME = 'Cierres de caja'


# =========================================================
# LISTADO DE CIERRES
# =========================================================
class CashClosingListView(LoginRequiredMixin, PermissionRequiredMixin, FormView):

    template_name = 'cashClosing/admin/list.html'
    form_class = ReportForm
    permission_required = 'pos.view_cashclosing'

    def post(self, request, *args, **kwargs):
        try:
            action = request.POST['action']

            if action == 'search':
                data = []

                start_date = request.POST.get('start_date')
                end_date = request.POST.get('end_date')

                queryset = CashClosing.objects.all()

                if start_date and end_date:
                    queryset = queryset.filter(
                        created_at__date__range=[start_date, end_date]
                    )

                can_print = request.user.has_perm('pos.print_cashclosing')
                for i in queryset.order_by('-id'):
                    data.append({
                        'id': i.id,
                        'print_url': str(reverse_lazy('cashClosing_print_ticket', kwargs={'pk': i.id})) if can_print else '',

                        'created_at': i.created_at.strftime('%d/%m/%Y - %I:%M %p'),
                        'terminal': getattr(i, 'terminal', 'Principal'),
                        'user': {
                            'names': i.user.get_short_name()
                        },
                        'total_sales': float(i.total_sales),
                        'base_cash': float(i.base_cash),
                        'expected_cash': float(i.expected_cash),
                        'real_cash': float(i.real_cash),
                        'difference': float(i.difference),

                        # PROPINAS
                        'tips': float(getattr(i, 'tips', 0)),
                    })
            else:
                data['error'] = 'No ha seleccionado ninguna opción'

        except Exception as e:
            data = {
                'error': str(e)
            }

        return HttpResponse(
            json.dumps(data, cls=DjangoJSONEncoder),
            content_type='application/json'
        )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context['title'] = 'Listado de cierres de caja'
        context['create_url'] = reverse_lazy('cashClosing_create')
        context['list_url'] = reverse_lazy('cashClosing_list')
        context['module_name'] = MODULE_NAME

        return context


# =========================================================
# CREAR CIERRE DE CAJA
# =========================================================
class CashClosingCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):

    model = CashClosing
    form_class = CashClosingForm
    template_name = 'cashClosing/admin/create.html'
    success_url = reverse_lazy('cashClosing_list')

    permission_required = 'pos.add_cashclosing'

    # =====================================================
    # ULTIMO CIERRE
    # =====================================================
    def get_last_closing(self):

        return CashClosing.objects.order_by('-id').first()

    # =====================================================
    # QUERY VENTAS
    # =====================================================
    def get_sales_queryset(self):

        queryset = Sale.objects.all()

        last_closing = self.get_last_closing()

        if last_closing:

            queryset = queryset.filter(
                creation_date__gt=last_closing.created_at
            )

        return queryset

    # =====================================================
    # QUERY ABONOS A CRÉDITOS
    # =====================================================
    def get_payments_queryset(self):
        """Abonos recibidos desde el último cierre (el abono antiguo, sin hora, se ubica por su fecha de pago)."""
        queryset = SaleCreditPayment.objects.all()
        last_closing = self.get_last_closing()
        if last_closing:
            last_date = timezone.localtime(last_closing.created_at).date()
            queryset = queryset.filter(
                Q(created_at__gt=last_closing.created_at) |
                Q(created_at__isnull=True, date_payment__gt=last_date)
            )
        return queryset

    # =====================================================
    # TOTALES DE VENTAS (un solo cálculo para la pantalla y para guardar el cierre)
    # =====================================================
    @staticmethod
    def get_sales_totals(sales_queryset, payments_queryset=None):
        """Lo cobrado en el período, por método de pago.

        Las ventas a crédito (tipo de pago "Crédito") todavía no se han cobrado, así que no entran al
        efectivo, a las tarjetas, a las transferencias ni al total; se informan aparte como "por cobrar".
        Los abonos que se reciben por esos créditos sí son dinero que ingresa: se suman al método con que
        se pagaron (un abono "mixto" no trae el desglose, así que se cuenta como transferencia).
        """
        zero = Decimal('0.00')
        receivable = sales_queryset.filter(typemethods='credit')
        paid = sales_queryset.exclude(typemethods='credit')
        payments = payments_queryset if payments_queryset is not None else SaleCreditPayment.objects.none()

        def total_of(queryset, field='total'):
            return queryset.aggregate(result=Sum(field))['result'] or zero

        mixto = paid.filter(paymentmethod='mixto')
        credit_payments = total_of(payments)
        return {
            'total_sales': total_of(paid) + credit_payments,
            'cash_sales': total_of(paid.filter(paymentmethod='cash')) + total_of(mixto, 'cash')
                          + total_of(payments.filter(paymentmethod='cash')),
            'credit_sales': total_of(paid.filter(paymentmethod='creditCard'))
                            + total_of(payments.filter(paymentmethod='creditCard')),
            'debit_sales': total_of(paid.filter(paymentmethod='debitCard'))
                           + total_of(payments.filter(paymentmethod='debitCard')),
            'transfer_sales': (total_of(paid.filter(paymentmethod='transfer'))
                               + total_of(mixto, 'nequi_value') + total_of(mixto, 'daviplata_value')
                               + total_of(payments.filter(paymentmethod__in=['transfer', 'mixto']))),
            'credit_payments': credit_payments,
            'receivable_sales': total_of(receivable),
        }

    # =====================================================
    # QUERY GASTOS
    # =====================================================
    def get_expenses_queryset(self):

        queryset = Expenses.objects.filter(
            source='caja'
        )

        last_closing = self.get_last_closing()

        if last_closing:

            queryset = queryset.filter(
                created_at__gt=last_closing.created_at
            )

        return queryset

    # =====================================================
    # LIMPIAR DINERO
    # =====================================================
    def clean_money(self, value):

        if not value:
            return Decimal('0.00')

        value = str(value).replace('.', '').replace(',', '')

        return Decimal(value)

    # =====================================================
    # POST
    # =====================================================
    def post(self, request, *args, **kwargs):

        data = {}

        try:

            action = request.POST['action']

            if action == 'add':

                sales_queryset = self.get_sales_queryset()
                expenses_queryset = self.get_expenses_queryset()

                # =====================================
                # VALIDAR SI HAY VENTAS
                # =====================================

                if not sales_queryset.exists() and not self.get_payments_queryset().exists():

                    data['error'] = (
                        'No existen ventas ni abonos pendientes '
                        'para realizar un nuevo cierre'
                    )

                    return HttpResponse(
                        json.dumps(data),
                        content_type='application/json'
                    )

                # =====================================
                # TOTALES VENTAS (las ventas a crédito aún no se cobran: no suman)
                # =====================================

                totals = self.get_sales_totals(sales_queryset, self.get_payments_queryset())
                total_sales = totals['total_sales']
                cash_sales = totals['cash_sales']
                credit_sales = totals['credit_sales']
                debit_sales = totals['debit_sales']
                transfer_sales = totals['transfer_sales']

                # =====================================
                # GASTOS
                # =====================================

                expenses = expenses_queryset.aggregate(
                    result=Sum('amount')
                )['result'] or Decimal('0.00')

                # =====================================
                # BASE INICIAL
                # =====================================

                base_cash = self.clean_money(
                    request.POST.get('base_cash')
                )

                # =====================================
                # EFECTIVO REAL
                # =====================================

                real_cash = self.clean_money(
                    request.POST.get('real_cash')
                )

                # =====================================
                # EFECTIVO ESPERADO
                # =====================================

                expected_cash = (
                    base_cash +
                    cash_sales -
                    expenses
                )

                # =====================================
                # DIFERENCIA
                # =====================================

                difference = real_cash - expected_cash

                # =====================================
                # CREAR CIERRE
                # =====================================

                cash_closing = CashClosing()

                cash_closing.user = request.user

                cash_closing.base_cash = base_cash

                cash_closing.total_sales = total_sales

                cash_closing.cash_sales = cash_sales
                cash_closing.credit_sales = credit_sales
                cash_closing.debit_sales = debit_sales
                cash_closing.transfer_sales = transfer_sales
                cash_closing.credit_payments = totals['credit_payments']

                cash_closing.expenses = expenses

                cash_closing.expected_cash = expected_cash

                cash_closing.real_cash = real_cash

                cash_closing.difference = difference

                cash_closing.observations = request.POST.get(
                    'observations',
                    ''
                )

                cash_closing.save()

                data['success'] = True
                data['url'] = str(self.success_url)
                if request.user.has_perm('pos.print_cashclosing'):
                    data['print_url'] = str(reverse_lazy('cashClosing_print_ticket', kwargs={'pk': cash_closing.id}))

            else:

                data['error'] = 'No ha seleccionado ninguna opción'

        except Exception as e:

            data['error'] = str(e)

        return HttpResponse(
            json.dumps(data, cls=DjangoJSONEncoder),
            content_type='application/json'
        )

    # =====================================================
    # CONTEXTO
    # =====================================================
    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        sales_queryset = self.get_sales_queryset()
        expenses_queryset = self.get_expenses_queryset()

        # =====================================
        # TOTALES (las ventas a crédito aún no se cobran: no suman)
        # =====================================

        totals = self.get_sales_totals(sales_queryset, self.get_payments_queryset())
        total_sales = totals['total_sales']
        cash_sales = totals['cash_sales']
        credit_sales = totals['credit_sales']
        debit_sales = totals['debit_sales']
        transfer_sales = totals['transfer_sales']

        expenses = expenses_queryset.aggregate(
            result=Sum('amount')
        )['result'] or Decimal('0.00')

        expected_cash = cash_sales - expenses

        # =====================================
        # CONTEXTO
        # =====================================

        context['title'] = 'Nuevo cierre de caja'
        context['entity'] = 'Cierre de caja'
        context['list_url'] = reverse_lazy('cashClosing_list')
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME

        context['cash_sales'] = cash_sales
        context['credit_sales'] = credit_sales
        context['debit_sales'] = debit_sales
        context['transfer_sales'] = transfer_sales

        context['expenses'] = expenses
        context['total_sales'] = total_sales
        context['expected_cash'] = expected_cash
        context['receivable_sales'] = totals['receivable_sales']
        context['credit_payments'] = totals['credit_payments']

        return context

# =========================================================
# DETALLE CIERRE DE CAJA
# =========================================================
class CashClosingDetailView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    DetailView
):

    model = CashClosing
    template_name = 'cashClosing/admin/create.html'
    context_object_name = 'cash_closing'

    permission_required = 'pos.view_cashclosing'

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        obj = self.get_object()

        context['title'] = 'Detalle cierre de caja'
        context['entity'] = 'Detalle cierre'
        context['list_url'] = reverse_lazy('cashClosing_list')
        context['module_name'] = MODULE_NAME

        context['readonly'] = True
        context['action'] = 'view'
        if self.request.user.has_perm('pos.print_cashclosing'):
            context['print_url'] = reverse_lazy('cashClosing_print_ticket', kwargs={'pk': obj.pk})
        context['cash_sales'] = obj.cash_sales
        context['credit_sales'] = obj.credit_sales
        context['debit_sales'] = obj.debit_sales
        context['transfer_sales'] = obj.transfer_sales
        context['credit_payments'] = obj.credit_payments

        context['expenses'] = obj.expenses
        context['total_sales'] = obj.total_sales
        context['expected_cash'] = obj.expected_cash

        return context


# =========================================================
# TIRILLA (80 mm) DEL CIERRE DE CAJA
# =========================================================
@method_decorator(xframe_options_exempt, name='dispatch')  # se muestra dentro de un iframe oculto para imprimir
class CashClosingPrintView(LoginRequiredMixin, View):
    """Tirilla de 80 mm con toda la información del cierre; se muestra en un iframe y se imprime desde el navegador."""

    def get(self, request, *args, **kwargs):
        if not request.user.has_perm('pos.print_cashclosing'):
            return HttpResponseForbidden('Su perfil no tiene permiso para imprimir cierres de caja.')
        closing = get_object_or_404(CashClosing.objects.select_related('user'), pk=kwargs['pk'])

        # El período es el mismo que usó el cierre: desde el cierre anterior hasta este
        previous = CashClosing.objects.filter(id__lt=closing.id).order_by('-id').first()
        period_start = previous.created_at if previous else None
        sales = Sale.objects.filter(creation_date__lte=closing.created_at)
        if period_start:
            sales = sales.filter(creation_date__gt=period_start)

        # Detalle de gastos: solo se imprime si cuadra con el total guardado en el cierre
        expenses = Expenses.objects.filter(source='caja', created_at__lte=closing.created_at.date())
        if period_start:
            expenses = expenses.filter(created_at__gt=period_start)
        expense_list = list(expenses.order_by('id'))
        if sum((e.amount for e in expense_list), Decimal('0.00')) != closing.expenses:
            expense_list = []

        context = {
            'closing': closing,
            'difference_abs': abs(closing.difference),
            'company': Company.objects.first(),
            'period_start': period_start,
            'sales_count': sales.count(),
            'tips': sales.aggregate(result=Sum('propina'))['result'] or Decimal('0.00'),
            'expense_list': expense_list,
            'printed_at': timezone.now(),
        }
        return render(request, 'cashClosing/format/ticket.html', context)
