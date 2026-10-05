from core.reports import services
from core.reports.views.base import ReportView


class InventoryValueReportView(ReportView):
    permission_required = 'pos.report_inventory_value'
    module_name = 'R.Inventario'
    title = 'Inventario valorizado'
    table_title = 'Detalle del inventario'
    export_name = 'inventario_valorizado'
    compute = staticmethod(services.inventory_value)
    filters = (
        {'name': 'category', 'label': 'Categoría', 'type': 'select', 'options': 'categories', 'width': 3},
        {'name': 'state', 'label': 'Estado', 'type': 'select', 'width': 3, 'options': [
            {'value': '', 'label': 'Todos'}, {'value': 'Agotado', 'label': 'Agotados'},
            {'value': 'Bajo', 'label': 'Stock bajo'}, {'value': 'Normal', 'label': 'Normal'}]},
        {'name': 'inactive', 'label': 'Incluir productos inactivos', 'type': 'checkbox', 'width': 3},
    )
    columns = (
        {'key': 'name', 'title': 'Producto', 'type': 'text', 'bold': True, 'sub': 'category'},
        {'key': 'variant', 'title': 'Unidad / variante', 'type': 'text'},
        {'key': 'stock', 'title': 'Stock', 'type': 'number'},
        {'key': 'state', 'title': 'Estado', 'type': 'badge',
         'colors': {'Agotado': 'danger', 'Bajo': 'warning', 'Normal': 'success'}},
        {'key': 'value_cost', 'title': 'Valor a costo', 'type': 'money', 'cost': True},
        {'key': 'value_sale', 'title': 'Valor a venta', 'type': 'money', 'cost': True},
        {'key': 'code', 'title': 'Código', 'type': 'text', 'detail': True},
        {'key': 'min', 'title': 'Stock mínimo', 'type': 'number', 'detail': True},
        {'key': 'equivalences', 'title': 'Equivale a', 'type': 'text', 'detail': True},
        {'key': 'cost_unit', 'title': 'Costo unitario', 'type': 'money', 'cost': True, 'detail': True},
        {'key': 'pvp', 'title': 'Precio de venta', 'type': 'money', 'detail': True},
        {'key': 'potential', 'title': 'Utilidad potencial', 'type': 'money', 'cost': True, 'detail': True},
    )
