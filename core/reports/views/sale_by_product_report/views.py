from core.reports import services
from core.reports.views.base import ReportView


class SaleByProductReportView(ReportView):
    permission_required = 'pos.sale_by_product'
    module_name = 'R.Productos'
    title = 'Ventas por producto'
    table_title = 'Detalle por producto'
    export_name = 'ventas_por_producto'
    compute = staticmethod(services.sales_by_product)
    filters = (
        {'name': 'date_range', 'label': 'Fechas', 'type': 'daterange', 'default': 'month', 'width': 4},
        {'name': 'category', 'label': 'Categoría', 'type': 'select', 'options': 'categories', 'width': 2},
        {'name': 'employee', 'label': 'Vendedor', 'type': 'select', 'options': 'employees', 'width': 2},
        {'name': 'electronic', 'label': 'Tipo de venta', 'type': 'select', 'width': 2, 'options': [
            {'value': '', 'label': 'Todas'}, {'value': 'yes', 'label': 'Electrónicas'}, {'value': 'no', 'label': 'No electrónicas'}]},
        {'name': 'group', 'label': 'Agrupar por', 'type': 'select', 'width': 2, 'options': [
            {'value': 'product', 'label': 'Producto'}, {'value': 'presentation', 'label': 'Producto y presentación'}]},
    )
    columns = (
        {'key': 'name', 'title': 'Producto', 'type': 'text', 'bold': True, 'sub': 'category', 'tag': 'presentation'},
        {'key': 'net_qty', 'title': 'Cantidad', 'type': 'number'},
        {'key': 'net_sales', 'title': 'Ventas netas', 'type': 'money'},
        {'key': 'share', 'title': '% de ventas', 'type': 'percent', 'bar': True},
        {'key': 'profit', 'title': 'Utilidad', 'type': 'money', 'cost': True},
        {'key': 'margin', 'title': 'Margen', 'type': 'percent', 'cost': True},
        # Se ven al desplegar la fila (y salen en el Excel/PDF)
        {'key': 'code', 'title': 'Código', 'type': 'text', 'detail': True},
        {'key': 'breakdown', 'title': 'Vendido por presentación', 'type': 'text', 'detail': True, 'showWhen': ['group', 'product']},
        {'key': 'sales_count', 'title': 'N° de ventas', 'type': 'number', 'detail': True},
        {'key': 'avg_price', 'title': 'Precio promedio', 'type': 'money', 'detail': True},
        {'key': 'ret_qty', 'title': 'Unidades devueltas', 'type': 'number', 'detail': True},
        {'key': 'cost', 'title': 'Costo', 'type': 'money', 'cost': True, 'detail': True},
        {'key': 'stock', 'title': 'Stock actual', 'type': 'text', 'detail': True},
    )
