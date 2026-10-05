from core.reports import services
from core.reports.views.base import ReportView


class RestockReportView(ReportView):
    permission_required = 'pos.report_restock'
    module_name = 'R.Reposición'
    title = 'Reposición sugerida'
    table_title = 'Qué comprar'
    export_name = 'reposicion_sugerida'
    compute = staticmethod(services.restock)
    filters = (
        {'name': 'days', 'label': 'Días de ventas a analizar', 'type': 'number', 'default': 30, 'width': 3},
        {'name': 'cover', 'label': 'Días que quiere cubrir', 'type': 'number', 'default': 15, 'width': 3},
        {'name': 'category', 'label': 'Categoría', 'type': 'select', 'options': 'categories', 'width': 3},
        {'name': 'only_needed', 'label': 'Solo lo que hay que reponer', 'type': 'checkbox', 'default': True, 'width': 3},
    )
    columns = (
        {'key': 'priority', 'title': 'Prioridad', 'type': 'badge',
         'colors': {'Crítico': 'danger', 'Urgente': 'warning', 'Pronto': 'info', 'Cubierto': 'success'}},
        {'key': 'name', 'title': 'Producto', 'type': 'text', 'bold': True, 'sub': 'variant'},
        {'key': 'stock', 'title': 'Stock', 'type': 'number'},
        {'key': 'coverage', 'title': 'Días de stock', 'type': 'number'},
        {'key': 'suggested_text', 'title': 'Comprar (sugerido)', 'type': 'text', 'bold': True},
        {'key': 'est_cost', 'title': 'Inversión est.', 'type': 'money', 'cost': True},
        {'key': 'code', 'title': 'Código', 'type': 'text', 'detail': True},
        {'key': 'min', 'title': 'Stock mínimo', 'type': 'number', 'detail': True},
        {'key': 'sold', 'title': 'Vendido en el período', 'type': 'number', 'detail': True},
        {'key': 'avg_daily', 'title': 'Promedio diario', 'type': 'number', 'detail': True},
        {'key': 'last_provider', 'title': 'Último proveedor', 'type': 'text', 'detail': True},
        {'key': 'last_date', 'title': 'Última compra', 'type': 'text', 'detail': True},
        {'key': 'last_cost', 'title': 'Último costo', 'type': 'money', 'cost': True, 'detail': True},
    )
