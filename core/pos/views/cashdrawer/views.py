from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

from core.pos.models import CashDrawerLog
from core.security.mixins import GroupPermissionMixin

SOURCES = {'sale', 'salefe', 'bar', 'bar_auto', 'test'}
# Quien puede vender (facturas, facturas electrónicas o ventas rápidas) puede abrir el cajón.
ALLOWED_PERMISSIONS = ('add_sale', 'add_electronic_invoice', 'add_bar')


class CashDrawerLogView(LoginRequiredMixin, View):
    """Registra cada apertura del cajón (la apertura en sí la hace QZ Tray en el PC de caja)."""

    def has_access(self, request):
        if request.user.is_superuser:
            return True
        group = request.session.get('group')
        return bool(group) and any(GroupPermissionMixin.has_permission(group, p) for p in ALLOWED_PERMISSIONS)

    def post(self, request, *args, **kwargs):
        if not self.has_access(request):
            return JsonResponse({'error': 'No tienes permiso para hacer esto'}, status=403)
        source = request.POST.get('source', '')
        CashDrawerLog.objects.create(
            user=request.user,
            source=source if source in SOURCES else 'sale',
            printer=request.POST.get('printer', '')[:150],
        )
        return JsonResponse({'success': True})
