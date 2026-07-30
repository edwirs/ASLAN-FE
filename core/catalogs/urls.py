from django.urls import path

from core.catalogs.views.biological_target_category.views import *
from core.catalogs.views.biological_target.views import *
from core.catalogs.views.mipe_modules.views import *
from core.catalogs.views.block.views import *
from core.catalogs.views.severity_grade.views import *
from core.catalogs.views.variety_catalog.views import *
from core.catalogs.views.assurance_parameter.views import *
from core.catalogs.views.trap.views import *

app_name = 'catalogs'

urlpatterns = [
    # categorias blancos biologicos
    path('biological_target_category/',BiologicalTargetCategoryListView.as_view(),name='biological_target_category_list'),
    path('biological_target_category/add/', BiologicalTargetCategoryCreateView.as_view(), name='biological_target_category_create'),
    path('biological_target_category/update/<int:pk>/', BiologicalTargetCategoryUpdateView.as_view(), name='biological_target_category_update'),
    path('biological_target_category/delete/<int:pk>/', BiologicalTargetCategoryDeleteView.as_view(), name='biological_target_category_delete'),

    # blancos biologicos
    path('biological_target/',BiologicalTargetListView.as_view(),name='biological_target_list'),
    path('biological_target/add/', BiologicalTargetCreateView.as_view(), name='biological_target_create'),
    path('biological_target/update/<int:pk>/', BiologicalTargetUpdateView.as_view(), name='biological_target_update'),
    path('biological_target/delete/<int:pk>/', BiologicalTargetDeleteView.as_view(), name='biological_target_delete'),

    # grados de severidad
    path('severity_grade/',SeverityGradeListView.as_view(),name='severity_grade_list'),
    path('severity_grade/add/', SeverityGradeCreateView.as_view(), name='severity_grade_create'),
    path('severity_grade/update/<int:pk>/', SeverityGradeUpdateView.as_view(), name='severity_grade_update'),
    path('severity_grade/delete/<int:pk>/', SeverityGradeDeleteView.as_view(), name='bseverity_grade_delete'),

    #modulos mipe
    path('mipe_module/',MipeModuleListView.as_view(),name='mipe_module_list'),
    path('mipe_module/add/', MipeModuleCreateView.as_view(), name='mipe_module_create'),
    path('mipe_module/update/<int:pk>/', MipeModuleUpdateView.as_view(), name='mipe_module_update'),
    path('mipe_module/delete/<int:pk>/', MipeModuleDeleteView.as_view(), name='mipe_module_delete'),

    #configuración bloques
    path('block/',BlockListView.as_view(),name='block_list'),
    path('block/structure/',BlockStructureCreateView.as_view(),name='block_structure_create'),
    path('block/structure/update/<int:pk>/', BlockStructureCreateView.as_view(), name='block_structure_update'),

    # catalogo de variedades
    path('variedades/administrar/', VarietyCatalogView.as_view(), name='variety_catalog_manage'),

    # parametros de aseguramiento
    path('assurance/parameters/', AssuranceParameterListView.as_view(), name='assurance_parameter_list'),

    # trampas
    path('trap/list/', TrapListView.as_view(), name='trap_list'),
    path('trap/ica/add/', TrapListView.as_view(), name='trap_ica_create'),
    path('trap/copitarsia/add/', TrapListView.as_view(), name='trap_copi_create'),
]