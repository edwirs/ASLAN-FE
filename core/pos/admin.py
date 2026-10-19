from django.contrib import admin

from core.pos.models import CashDrawerLog


@admin.register(CashDrawerLog)
class CashDrawerLogAdmin(admin.ModelAdmin):
    """Auditoría de aperturas del cajón: solo lectura."""
    list_display = ('created_at', 'user', 'source', 'printer')
    list_filter = ('source', 'user')
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
