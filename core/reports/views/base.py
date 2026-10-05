import json

from django.http import JsonResponse
from django.views.generic import TemplateView

from core.pos.models import Category
from core.security.mixins import StrictPermissionMixin
from core.user.models import User

COSTS_PERMISSION = 'pos.view_report_costs'


class ReportView(StrictPermissionMixin, TemplateView):
    """Vista base de un reporte: página con filtros + POST ``search_report`` que devuelve JSON.

    Las subclases definen ``title``, ``permission_required``, ``filters``, ``columns`` y ``compute``.
    Las columnas y datos marcados como costo solo llegan a quien tenga ``pos.view_report_costs``.
    """
    template_name = 'reports_generic/report.html'
    module_name = 'Reportes'
    title = ''
    export_name = 'reporte'
    table_title = 'Detalle'
    filters = ()
    columns = ()
    compute = None  # función (params, can_costs) -> dict

    def can_costs(self):
        return self.request.user.has_perm(COSTS_PERMISSION)

    def allowed_columns(self):
        costs = self.can_costs()
        return [c for c in self.columns if costs or not c.get('cost')]

    def post(self, request, *args, **kwargs):
        if request.POST.get('action') != 'search_report':
            return JsonResponse({'error': 'Acción no válida'})
        try:
            result = type(self).compute(request.POST, self.can_costs())
            result['columns'] = self.allowed_columns()
            return JsonResponse(result)
        except ValueError as e:
            return JsonResponse({'error': f'Filtro inválido: {e}'})
        except Exception as e:
            return JsonResponse({'error': str(e)})

    def resolve_filters(self):
        resolved = []
        for f in self.filters:
            f = dict(f)
            if f.get('options') == 'categories':
                f['options'] = [{'value': '', 'label': 'Todas'}] + [
                    {'value': str(c.pk), 'label': c.name} for c in Category.objects.order_by('name')]
            elif f.get('options') == 'employees':
                f['options'] = [{'value': '', 'label': 'Todos'}] + [
                    {'value': str(u.pk), 'label': u.names or u.username} for u in User.objects.filter(is_active=True).order_by('names')]
            resolved.append(f)
        return resolved

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = {
            'filters': self.resolve_filters(), 'columns': self.allowed_columns(),
            'export_name': self.export_name, 'title': self.title, 'table_title': self.table_title,
        }
        context['title'] = self.title
        context['module_name'] = self.module_name
        context['report_config'] = config
        return context
