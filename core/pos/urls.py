from django.urls import path

from core.pos.views.category.views import *
from core.pos.views.client.views import *
from core.pos.views.company.views import *
from core.pos.views.product.views import *
from core.pos.views.sale.views import *
from core.pos.views.salefe.views import *
from core.pos.views.creditnotefe.views import *
from core.pos.views.price.views import *
from core.pos.views.buy.views import *
from core.pos.views.provider.views import *
from core.pos.views.productAutoAdd.views import *
from core.pos.views.expenses.views import *
from core.pos.views.employee.views import *
from core.pos.views.payroll.views import *
from core.pos.views.sale.views import get_sale, update_sale
from core.pos.views.salefe.views import get_sale_Fe, update_sale_Fe
from core.pos.views.credit.views import *
from core.pos.views.credit.views import get_sale_credit, get_sale_payments
from core.pos.views.bar.views import *
from core.pos.views.inventory_manager.views import *
from core.pos.views.productAutoAdd.views import *
from core.pos.views.table.views import *
from core.pos.views.order.views import *
from core.pos.views.kitchen_order.views import *
from core.pos.views.employee_transaction.views import *
from core.pos.views.cashClosing.views import *

urlpatterns = [
    # category
    path('category/', CategoryListView.as_view(), name='category_list'),
    path('category/add/', CategoryCreateView.as_view(), name='category_create'),
    path('category/update/<int:pk>/', CategoryUpdateView.as_view(), name='category_update'),
    path('category/delete/<int:pk>/', CategoryDeleteView.as_view(), name='category_delete'),
    # product
    path('product/', ProductListView.as_view(), name='product_list'),
    path('product/add/', ProductCreateView.as_view(), name='product_create'),
    path('product/update/<int:pk>/', ProductUpdateView.as_view(), name='product_update'),
    path('product/delete/<int:pk>/', ProductDeleteView.as_view(), name='product_delete'),
    # company
    path('company/update/', CompanyUpdateView.as_view(), name='company_update'),
    # client
    path('client/', ClientListView.as_view(), name='client_list'),
    path('client/add/', ClientCreateView.as_view(), name='client_create'),
    path('client/update/<int:pk>/', ClientUpdateView.as_view(), name='client_update'),
    path('client/delete/<int:pk>/', ClientDeleteView.as_view(), name='client_delete'),
    path('client/consult_dian/', consult_dian_acquirer, name='client_consult_dian'),
    # provider
    path('provider/', ProviderListView.as_view(), name='provider_list'),
    path('provider/add/', ProviderCreateView.as_view(), name='provider_create'),
    path('provider/update/<int:pk>/', ProviderUpdateView.as_view(), name='provider_update'),
    path('provider/delete/<int:pk>/', ProviderDeleteView.as_view(), name='provider_delete'),
    # sale
    path('sale/admin/', SaleListView.as_view(), name='sale_admin_list'),
    path('sale/admin/add/', SaleCreateView.as_view(), name='sale_admin_create'),
    path('sale/admin/delete/<int:pk>/', SaleDeleteView.as_view(), name='sale_admin_delete'),
    path('sale/admin/delivered/<int:pk>/', SaleDeliveredUpdateView.as_view(), name='sale_admin_delivered'),
    path('sale/admin/print/invoice/<int:pk>/', SalePrintInvoiceView.as_view(), name='sale_admin_print_invoice'),
    path('sale/admin/get_sale/<int:pk>/', get_sale, name='get_sale'),
    path('sale/admin/update_sale/<int:pk>/', update_sale, name='update_sale'),
    # sale factura electronica
    path('salefe/admin/', SaleFeListView.as_view(), name='sale_Fe_admin_list'),
    path('salefe/admin/add/', SaleFeCreateView.as_view(), name='sale_Fe_admin_create'),
    path('salefe/admin/delete/<int:pk>/', SaleFeDeleteView.as_view(), name='sale_Fe_admin_delete'),
    path('salefe/admin/delivered/<int:pk>/', SaleFeDeliveredUpdateView.as_view(), name='sale_Fe_admin_delivered'),
    path('salefe/admin/print/invoice/<int:pk>/', SaleFePrintInvoiceView.as_view(), name='sale_Fe_admin_print_invoice'),
    path('salefe/admin/download/pdf/<int:pk>/', SaleFeDownloadPdfView.as_view(), name='sale_Fe_admin_download_pdf'),
    path('salefe/admin/get_sale/<int:pk>/', get_sale_Fe, name='get_sale_Fe'),
    path('salefe/admin/update_sale/<int:pk>/', update_sale_Fe, name='update_sale_Fe'),
    # nota credito electronica
    path('creditnotefe/admin/', CreditNoteFeListView.as_view(), name='credit_note_Fe_admin_list'),
    path('creditnotefe/admin/add/', CreditNoteFeCreateView.as_view(), name='credit_note_Fe_admin_create'),
    path('creditnotefe/admin/delete/<int:pk>/', CreditNoteFeDeleteView.as_view(), name='credit_note_Fe_admin_delete'),
    path('creditnotefe/admin/print/<int:pk>/', CreditNoteFePrintView.as_view(), name='credit_note_Fe_admin_print'),
    path('creditnotefe/admin/download/pdf/<int:pk>/', CreditNoteFeDownloadPdfView.as_view(), name='credit_note_Fe_admin_download_pdf'),
    # price
    path('price/admin/', PriceListView.as_view(), name='price_admin_list'),
    path('price/admin/add/', PriceCreateView.as_view(), name='price_admin_create'),
    path('price/admin/delete/<int:pk>/', PriceDeleteView.as_view(), name='price_admin_delete'),
    path('price/admin/print/invoice/<int:pk>/', PricePrintInvoiceView.as_view(), name='price_admin_print_invoice'),
    # buy
    path('buy/admin/', BuyListView.as_view(), name='buy_admin_list'),
    path('buy/admin/add/', BuyCreateView.as_view(), name='buy_admin_create'),
    path('buy/admin/delete/<int:pk>/', BuyDeleteView.as_view(), name='buy_admin_delete'),
    path('buy/admin/print/invoice/<int:pk>/', BuyPrintInvoiceView.as_view(), name='buy_admin_print_invoice'),
    # productAutoAdd
    path("productAutoAdd/", ProductAutoAddListView.as_view(), name='productautoadd_list'),
    path("productAutoAdd/add/", ProductAutoAddCreateView.as_view(), name='productautoadd_create'),
    path("productAutoAdd/update/<int:pk>/", ProductAutoAddUpdateView.as_view(), name='productautoadd_update'),
    path("productAutoAdd/delete/<int:pk>/", ProductAutoAddDeleteView.as_view(), name='productautoadd_delete'),
    # expenses
    path("expenses/", ExpensesListView.as_view(), name='expenses_list'),
    path("expenses/add/", ExpensesCreateView.as_view(), name='expenses_create'),
    path("expenses/update/<int:pk>/", ExpensesUpdateView.as_view(), name='expenses_update'),
    path("expenses/delete/<int:pk>/", ExpensesDeleteView.as_view(), name='expenses_delete'),
    # credit
    path('credit/', SaleCreditReportView.as_view(), name='sale_credit_report'),
    path('credit/admin/get_sale_credit/<int:pk>/', get_sale_credit, name='get_sale_credit'),
    path('credit/admin/get_sale_payments/<int:pk>/', get_sale_payments, name='get_sale_payments'),
    path("credit/admin/add_payment/", SaleCreditAddPaymentView.as_view(), name="add_payment"),
    # empleados
    path('employee/', EmployeeListView.as_view(), name='employee_list'),
    path('employee/add/', EmployeeCreateView.as_view(), name='employee_create'),
    path('employee/update/<int:pk>/', EmployeeUpdateView.as_view(), name='employee_update'),
    path('employee/delete/<int:pk>/', EmployeeDeleteView.as_view(), name='employee_delete'),
    # nomina
    path('payroll/', PayrollListView.as_view(), name='payroll_list'),
    path('payroll/add/', PayrollCreateView.as_view(), name='payroll_create'),
    path('payroll/view/<slug:period>/<slug:period_type>/', PayrollDetailView.as_view(), name='payroll_view'),
    # bar
    path('bar/admin/add/', BarCreateView.as_view(), name='bar_admin_create'),
    #inventory manager
    path('inventory/management/', InventoryManagementView.as_view(), name='inventory_management'),
    # productAutoAdd
    path('productAutoAdd/', ProductAutoAddListView.as_view(), name='productautoadd_list'),
    path('productAutoAdd/add/', ProductAutoAddCreateView.as_view(), name='productautoadd_create'),
    path('productAutoAdd/update/<int:pk>/', ProductAutoAddUpdateView.as_view(), name='productautoadd_update'),
    path('productAutoAdd/delete/<int:pk>/', ProductAutoAddDeleteView.as_view(), name='productautoadd_delete'),
    # mesas
    path('table/', TableListView.as_view(), name='table_list'),
    path('table/add/', TableCreateView.as_view(), name='table_create'),
    path('table/update/<int:pk>/', TableUpdateView.as_view(), name='table_update'),
    path('table/delete/<int:pk>/', TableDeleteView.as_view(), name='table_delete'),
    # ventas rapidas
    path('order/', OrderListView.as_view(), name='order_list'),
    path('order/table/<int:table_id>/', OrderBarraView.as_view(), name='order_table'),
    path('order/update/', OrderCreateView.as_view(), name='update_order'),
    # cocina
    path('kitchen/', KitchenBoardView.as_view(), name='kitchen_board'),
    path('kitchen/orders/', kitchen_orders, name='kitchen_orders'),
    path('kitchen/order/<int:pk>/ready/', mark_order_ready, name='order_ready'),
    # transacciones empleados
    path('employeeTransaction', EmployeeTransactionListView.as_view(), name='employee_transaction_list'),
    path('employeeTransaction/add/', EmployeeTransactionCreateView.as_view(), name='employee_transaction_create'),
    path('employeeTransaction/update/<int:pk>/', EmployeeTransactionUpdateView.as_view(), name='employee_transaction_update'),
    path('employeeTransaction/delete/<int:pk>/', EmployeeTransactionDeleteView.as_view(), name='employee_transaction_delete'),
    path('employeeTransaction/print/transaction/<int:pk>/', EmployeeTransactionPrintView.as_view(), name='employee_transaction_print'),
    # cierre de caja
    path('cashClosing', CashClosingListView.as_view(), name='cashClosing_list'),
    path('cashClosing/add/', CashClosingCreateView.as_view(), name='cashClosing_create'),
    path('cashClosing/detail/<int:pk>/', CashClosingDetailView.as_view(), name='cashClosing_detail'),
    path('cashClosing/print/transaction/<int:pk>/', EmployeeTransactionPrintView.as_view(), name='cashClosing_print'),
    
]
