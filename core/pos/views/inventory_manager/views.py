import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Q
from django.views.generic import TemplateView
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.contrib import messages

from core.pos.forms import *
from core.security.mixins import GroupPermissionMixin

from core.security.mixins import GroupPermissionMixin

class InventoryManagementView(GroupPermissionMixin,TemplateView):
    template_name = 'inventory_management/management.html'
    success_url = settings.LOGIN_REDIRECT_URL
    permission_required = 'pos.view_inventorygroup'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Administración Inventario'

        context['users'] = User.objects.all()
        context['group_form'] = InventoryGroupForm()
        context['user_group_form'] = UserInventoryGroupForm()
        context['stock_form'] = ProductInventoryGroupStockForm()

        context['groups'] = InventoryGroup.objects.all()
        context['user_groups'] = UserInventoryGroup.objects.select_related('user', 'group')
        context['group_stocks'] = ProductInventoryGroupStock.objects.select_related('product', 'group')

        return context

    def post(self, request, *args, **kwargs):
        if 'add_group' in request.POST:
            form = InventoryGroupForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Grupo de inventario creado correctamente.")
            else:
                messages.error(request, "Error al crear grupo.")

        elif 'add_user_group' in request.POST:
            form = UserInventoryGroupForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Usuario asignado al grupo correctamente.")
            else:
                messages.error(request, "Error al asignar usuario al grupo.")

        elif 'add_stock_group' in request.POST:
            form = ProductInventoryGroupStockForm(request.POST)
            if form.is_valid():
                product = form.cleaned_data['product']
                group = form.cleaned_data['group']
                new_stock = form.cleaned_data['stock']

                # Sumar el stock ya asignado a otros grupos (excluyendo este grupo)
                existing_assignments = ProductInventoryGroupStock.objects.filter(product=product).exclude(group=group)
                assigned_total = sum(item.stock for item in existing_assignments)

                # Obtener el stock total disponible del producto
                total_stock = product.stock  # Asegúrate que el modelo Product tenga este campo

                if (assigned_total + new_stock) > total_stock:
                    messages.error(request, f'El stock total asignado ({assigned_total + new_stock}) excede el stock disponible del producto ({total_stock}).')
                else:
                    # Guardar (crear o actualizar)
                    ProductInventoryGroupStock.objects.update_or_create(
                        product=product,
                        group=group,
                        defaults={'stock': new_stock}
                    )
                    messages.success(request, "Stock asignado al grupo correctamente.")
            else:
                messages.error(request, "Error al asignar stock al grupo.")
        # -------------------------------------------
        # AGREGAR / EDITAR / ELIMINAR GRUPOS
        # -------------------------------------------
        elif 'add_group' in request.POST:
            form = InventoryGroupForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Grupo creado correctamente.")
            else:
                messages.error(request, "Error al crear grupo.")

        elif 'edit_group' in request.POST:
            group = InventoryGroup.objects.get(id=request.POST['group_id'])
            form = InventoryGroupForm(request.POST, instance=group)
            if form.is_valid():
                form.save()
                messages.success(request, "Grupo editado correctamente.")
            else:
                messages.error(request, "Error al editar grupo.")

        elif 'delete_group' in request.POST:
            InventoryGroup.objects.filter(id=request.POST['group_id']).delete()
            messages.success(request, "Grupo eliminado.")
        # -------------------------------------------
        # AGREGAR / EDITAR / ELIMINAR USER GROUP
        # -------------------------------------------
        elif 'add_user_group' in request.POST:
            form = UserInventoryGroupForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Usuario asignado correctamente.")
            else:
                messages.error(request, "Error al asignar usuario.")

        elif 'edit_user_group' in request.POST:
            ug = UserInventoryGroup.objects.get(id=request.POST['ug_id'])
            form = UserInventoryGroupForm(request.POST, instance=ug)
            if form.is_valid():
                form.save()
                messages.success(request, "Asignación editada.")
            else:
                messages.error(request, "Error al editar asignación.")

        elif 'delete_user_group' in request.POST:
            UserInventoryGroup.objects.filter(id=request.POST['ug_id']).delete()
            messages.success(request, "Asignación eliminada.")
        # -------------------------------------------
        # STOCK POR GRUPO
        # -------------------------------------------
        elif 'add_stock_group' in request.POST:
            form = ProductInventoryGroupStockForm(request.POST)
            if form.is_valid():
                product = form.cleaned_data['product']
                group = form.cleaned_data['group']
                new_stock = form.cleaned_data['stock']

                existing_assignments = ProductInventoryGroupStock.objects.filter(product=product).exclude(group=group)
                assigned_total = sum(item.stock for item in existing_assignments)
                total_stock = product.stock

                if assigned_total + new_stock > total_stock:
                    messages.error(request, "El stock asignado excede lo disponible.")
                else:
                    ProductInventoryGroupStock.objects.update_or_create(
                        product=product,
                        group=group,
                        defaults={'stock': new_stock}
                    )
                    messages.success(request, "Stock asignado correctamente.")
            else:
                messages.error(request, "Error en el formulario.")

        elif 'delete_group_stock' in request.POST:
            ProductInventoryGroupStock.objects.filter(id=request.POST['stock_id']).delete()
            messages.success(request, "Stock eliminado.")

        return redirect('inventory_management')