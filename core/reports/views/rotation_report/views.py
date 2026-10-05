from core.reports import services
from core.reports.views.base import ReportView


class RotationReportView(ReportView):
    permission_required = 'pos.report_rotation'
    module_name = 'R.Rotación'
    title = 'Rotación y productos sin movimiento'
    table_title = 'Detalle de rotación'
    export_name = 'rotacion_inventario'
    compute = staticmethod(services.rotation)
    filters = (
        {'name': 'days', 'label': 'Días a analizar', 'type': 'number', 'default': 90, 'width': 3},
        {'name': 'dormant', 'label': 'Sin movimiento desde (días)', 'type': 'number', 'default': 60, 'width': 3},
        {'name': 'category', 'label': 'Categoría', 'type': 'select', 'options': 'categories', 'width': 3},
    )
    columns = (
        {'key': 'name', 'title': 'Producto', 'type': 'text', 'bold': True, 'sub': 'category'},
        {'key': 'abc', 'title': 'ABC', 'type': 'badge', 'colors': {'A': 'success', 'B': 'info', 'C': 'secondary', '-': 'light'}},
        {'key': 'revenue', 'title': 'Ventas', 'type': 'money'},
        {'key': 'share', 'title': '% de ventas', 'type': 'percent', 'bar': True},
        {'key': 'stock', 'title': 'Stock', 'type': 'number'},
        {'key': 'days_inventory', 'title': 'Días de inventario', 'type': 'number'},
        {'key': 'status', 'title': 'Estado', 'type': 'badge',
         'colors': {'Activo': 'success', 'Lento': 'warning', 'Sin movimiento': 'danger',
                    'Sin ventas en el período': 'secondary', 'Agotado sin ventas': 'light'}},
        {'key': 'stuck', 'title': 'Capital detenido', 'type': 'money', 'cost': True},
        {'key': 'code', 'title': 'Código', 'type': 'text', 'detail': True},
        {'key': 'cumulative', 'title': '% acumulado', 'type': 'percent', 'detail': True},
        {'key': 'units', 'title': 'Unidades vendidas', 'type': 'number', 'detail': True},
        {'key': 'rotation', 'title': 'Rotación (veces)', 'type': 'number', 'detail': True},
        {'key': 'last_sale', 'title': 'Última venta', 'type': 'text', 'detail': True},
        {'key': 'days_since', 'title': 'Días sin vender', 'type': 'number', 'detail': True},
    )
