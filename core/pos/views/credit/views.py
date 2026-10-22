import json
from decimal import Decimal, InvalidOperation
from functools import wraps

from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.generic import FormView
from django.views import View

from core.pos.choices import PAYMENTMETHODS, TRANSFERMETHODS
from core.pos.models import CashClosing, Sale, SaleCreditPayment
from core.pos.forms import *
from core.pos.sale_deletion import SaleDeletionError, delete_sale
from core.reports.forms import ReportForm
from core.security.mixins import StrictPermissionMixin

MODULE_NAME = 'Créditos Ventas'
NO_PERMISSION = 'Su perfil no cuenta con el permiso necesario para realizar esta acción.'


def require_permission(permission):
    """Para las vistas de función del módulo: exige el permiso ``app.codename`` (responde JSON 403)."""
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.has_perm(permission):
                return JsonResponse({'error': NO_PERMISSION}, status=403)
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


def payment_is_closed(payment, last_closing):
    """True si el abono ya quedó dentro de un cierre de caja (misma regla con que el cierre elige sus abonos)."""
    if last_closing is None:
        return False
    if payment.created_at:
        return payment.created_at <= last_closing.created_at
    return payment.date_payment <= timezone.localtime(last_closing.created_at).date()


class SaleCreditReportView(StrictPermissionMixin, FormView):
    template_name = 'credit/report.html'
    form_class = ReportForm
    permission_required = 'pos.view_credit_report'

    def post(self, request, *args, **kwargs):
        action = request.POST['action']
        data = {}
        try:
            if action == 'search_report':
                data = []
                start_date = request.POST.get('start_date', '')
                end_date = request.POST.get('end_date', '')
                client_id = request.POST.get('client_id', '')

                queryset = Sale.objects.filter(typemethods='credit')
                if start_date and end_date:
                    queryset = queryset.filter(date_joined__range=[start_date, end_date])
                if client_id:
                    queryset = queryset.filter(client_id=client_id)

                for s in queryset:
                    total_paid = s.salecreditpayment_set.aggregate(total=Sum('total'))['total'] or 0
                    pending = float(s.total) - float(total_paid)

                    data.append({
                        "id": s.id,
                        "date_joined": s.date_joined.strftime('%Y-%m-%d'),
                        "expiration_date": s.expiration_date.strftime('%Y-%m-%d') if s.expiration_date else '',
                        "client": {
                            "dni": s.client.dni,
                            "names": s.client.names,
                        },
                        "total": float(s.total),
                        "paid": float(total_paid),
                        "pending": float(pending),
                    })
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Créditos de Ventas'
        context['module_name'] = MODULE_NAME
        context['sale_form'] = SaleForm()
        context['clients'] = Client.objects.all()
        return context


@require_permission('pos.view_credit_report')
def get_sale_credit(request, pk):
    try:
        sale = Sale.objects.get(pk=pk)
        total_payments = SaleCreditPayment.objects.filter(sale=sale).aggregate(total=Sum('total'))['total'] or 0
        pending = float(sale.total) - float(total_payments)
        data = {
            'id': sale.id,
            'date_joined': sale.date_joined.strftime('%Y-%m-%d'),
            'client': {
                'dni': sale.client.dni,
                'names': sale.client.names,
            },
            'paymentmethod': {
                'id': sale.paymentmethod,
                'name': sale.get_paymentmethod_display() if sale.paymentmethod else ''
            },
            'transfermethods': {
                'id': sale.transfermethods,
                'name': sale.get_transfermethods_display() if sale.transfermethods else ''
            },
            'pending': float(pending),
            'total': float(sale.total),
            'paid': float(total_payments),
            'error': ''
        }
        return JsonResponse(data, safe=False)
    except Sale.DoesNotExist:
        return JsonResponse({'error': 'La venta no existe'}, status=404)

@require_permission('pos.view_credit_report')
def get_sale_payments(request, pk):
    try:
        last_closing = CashClosing.objects.order_by('-id').first()
        payments = SaleCreditPayment.objects.filter(sale_id=pk).order_by('-date_payment', '-id')
        data = [
            {
                'id': p.id,
                'date_payment': p.date_payment.strftime('%Y-%m-%d'),
                'total': float(p.total),
                'paymentmethod': p.get_paymentmethod_display(),
                'transfermethods': p.get_transfermethods_display() if p.paymentmethod == 'transfer' and p.transfermethods else '',
                'closed': payment_is_closed(p, last_closing),
            }
            for p in payments
        ]
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


class SaleCreditAddPaymentView(StrictPermissionMixin, View):
    permission_required = 'pos.add_credit_payment'

    def post(self, request, *args, **kwargs):
        try:
            paymentmethod = request.POST.get("paymentmethod")
            transfermethods = request.POST.get("transfermethods")
            if paymentmethod not in dict(PAYMENTMETHODS):
                return JsonResponse({"error": "Seleccione un método de pago válido"})
            if paymentmethod == 'transfer' and transfermethods and transfermethods not in dict(TRANSFERMETHODS):
                return JsonResponse({"error": "Seleccione un método de transferencia válido"})
            try:
                total = Decimal(str(request.POST.get("total", "")).strip())
            except InvalidOperation:
                return JsonResponse({"error": "Ingrese un valor de pago válido"})
            if total <= 0:
                return JsonResponse({"error": "El valor del pago debe ser mayor a cero"})

            with transaction.atomic():
                # Se bloquea la venta para que dos abonos simultáneos no superen el saldo.
                sale = Sale.objects.select_for_update().get(pk=request.POST.get("sale_id"), typemethods='credit')
                paid = sale.salecreditpayment_set.aggregate(t=Sum('total'))['t'] or Decimal(0)
                pending = sale.total - paid
                if total > pending:
                    return JsonResponse({"error": f"El abono no puede superar el saldo pendiente (${pending})"})
                payment = SaleCreditPayment.objects.create(
                    sale=sale,
                    total=total,
                    paymentmethod=paymentmethod,
                    transfermethods=transfermethods if paymentmethod == 'transfer' and transfermethods else None
                )
            return JsonResponse({"success": True, "payment": payment.toJSON()})
        except Sale.DoesNotExist:
            return JsonResponse({"error": "El crédito no existe"})
        except Exception as e:
            return JsonResponse({"error": str(e)})


class SaleCreditPaymentDeleteView(StrictPermissionMixin, View):
    """Elimina un abono: su valor deja de contarse como recaudo (el saldo del crédito vuelve a subir)."""
    permission_required = 'pos.delete_credit_payment'

    def post(self, request, pk, *args, **kwargs):
        try:
            payment = SaleCreditPayment.objects.get(pk=pk)
        except SaleCreditPayment.DoesNotExist:
            return JsonResponse({'error': 'El abono no existe o ya fue eliminado'})
        payment.delete()
        return JsonResponse({'success': True})


class SaleCreditDeleteView(StrictPermissionMixin, View):
    """Elimina el crédito = elimina la venta y devuelve el stock. No procede si aún tiene abonos."""
    permission_required = 'pos.delete_credit'

    def post(self, request, pk, *args, **kwargs):
        if not Sale.objects.filter(pk=pk, typemethods='credit').exists():
            return JsonResponse({'error': 'El crédito no existe o ya fue eliminado'})
        try:
            delete_sale(pk)
        except SaleDeletionError as e:
            return JsonResponse({'error': str(e)})
        except Exception as e:
            return JsonResponse({'error': str(e)})
        return JsonResponse({'success': True})
