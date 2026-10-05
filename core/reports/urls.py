from django.urls import path

from core.reports.views.sale_report.views import SaleReportView
from core.reports.views.employee_report.views import EmployeeSaleReportView
from core.reports.views.sale_by_product_report.views import SaleByProductReportView
from core.reports.views.inventory_value_report.views import InventoryValueReportView
from core.reports.views.restock_report.views import RestockReportView
from core.reports.views.rotation_report.views import RotationReportView

urlpatterns = [
    path('sale/', SaleReportView.as_view(), name='sale_report'),
    path('employeesale/', EmployeeSaleReportView.as_view(), name='employee_sale_report'),
    path('saleByProduct/', SaleByProductReportView.as_view(), name='sale_by_product_report'),
    path('inventory/value/', InventoryValueReportView.as_view(), name='inventory_value_report'),
    path('inventory/restock/', RestockReportView.as_view(), name='restock_report'),
    path('inventory/rotation/', RotationReportView.as_view(), name='rotation_report'),
]
