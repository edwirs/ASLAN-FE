from django.urls import path

from core.production.views.plant_inventory_import.views import *
from core.production.views.plant_inventory.views import *
from core.production.views.mipe.views import *
from core.production.views.monitoring.views import *
from core.production.views.assurance.views import *
from core.production.views.monitoring_coverage.views import *
from core.production.views.trap_menu.views import *
from core.production.views.trap_ica.views import *
from core.production.views.trap_copitarsia.views import *
from core.production.views.trap_in.views import *
from core.production.views.trap_out.views import *

app_name = 'production'

urlpatterns = [
    # importar
    path('plant_inventory_import/',PlantInventoryImportListView.as_view(),name='plant_inventory_import_list'),
    path('plant_inventory_import/add/',PlantInventoryImportCreateView.as_view(),name='plant_inventory_import_create'),

    # inventario actual
    path('plant_inventory/',PlantInventoryListView.as_view(),name='plant_inventory_filter'),

    # mipe
    path('mipe/',MipeDashboardView.as_view(),name='mipe_dashboard'),
    path('mipe/monitoring/',MonitoringListView.as_view(),name='monitoring_list'),
    path('mipe/monitoring/add/',MonitoringCreateView.as_view(),name='monitoring_create'),

    # mipe - aseguramiento (NUEVAS RUTAS)
    path('mipe/assurance/', AssuranceListView.as_view(), name='mipe_assurance'),
    path('mipe/assurance/add/', AssuranceCreateView.as_view(), name='assurance_create'),
    path('mipe/assurance/update/<int:pk>/', AssuranceCreateView.as_view(), name='assurance_update'),

    # mipe - cobertura monitoreo
    path('mipe/monitoring_coverage/', MonitoringCoverageReportView.as_view(), name='monitoring_coverage'),

    #trampas
    path('trap/menu/', TrapDashboardView.as_view(), name='trap_menu'),
    path('trap/ica/list/', ReadingICAListView.as_view(), name='reading_ica_list'),
    path('trap/ica/create/', ReadingICAAddView.as_view(), name='reading_ica_create'),
    path('trap/copitarsia/list/', ReadingCopitarsiaListView.as_view(), name='reading_copitarsia_list'),
    path('trap/copitarsia/create/', ReadingCopitarsiaAddView.as_view(), name='reading_copitarsia_create'),
    path('trap/internal/list/', ReadingInternalListView.as_view(), name='reading_internal_list'),
    path('trap/internal/create/', ReadingInternalAddView.as_view(), name='reading_internal_create'),
    path('trap/external/list/', ReadingExternalListView.as_view(), name='reading_external_list'),
    path('trap/external/create/', ReadingExternalAddView.as_view(), name='reading_external_create'),
]
