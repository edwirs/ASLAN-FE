from django.http import JsonResponse
from core.pos.models import Table, Order

from django.views.generic import TemplateView
from django.views.decorators.http import require_POST
from django.contrib.auth.mixins import LoginRequiredMixin

class KitchenBoardView(LoginRequiredMixin, TemplateView):
    template_name = 'kitchen_order/list.html'

def kitchen_orders(request):
    orders = (
        Order.objects
        .filter(status__in=['open', 'sent'])
        .order_by('created_at')
        .prefetch_related('orderdetail_set__product')
    )

    data = []

    for order in orders:
        items = []
        for d in order.orderdetail_set.all():
            items.append({
                'product': d.display_name(),
                'qty': d.cant
            })

        data.append({
            'order_id': order.id,
            'table': order.table.name,
            'created_at': order.created_at.isoformat(),
            'observations': order.observations or '', 
            'items': items
        })

    return JsonResponse(data, safe=False)

@require_POST
def mark_order_ready(request, pk):
    try:
        order = Order.objects.get(pk=pk)
        order.status = 'ready'
        order.save()

        return JsonResponse({
            'success': True,
            'message': 'Pedido marcado como listo'
        })

    except Order.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Pedido no encontrado'
        }, status=404)