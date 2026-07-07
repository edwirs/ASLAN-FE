import traceback
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from core.security.mixins import GroupPermissionMixin
from core.catalogs.models import AssuranceParameter  # Ajusta la ruta según tu app

MODULE_NAME = 'Parámetros de Aseguramiento'

class AssuranceParameterListView(GroupPermissionMixin, TemplateView):
    template_name = 'assurance_parameter/list.html'
    permission_required = 'view_assurance_parameter'  # Permiso de Django estándar

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Parámetros de Aseguramiento'
        context['module_name'] = MODULE_NAME
        context['list_url'] = reverse_lazy('catalogs:assurance_parameter_list')
        context['create_url'] = '#'
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        try:
            if action == 'list':
                parameters = AssuranceParameter.objects.all().order_by('-id')
                data = [p.to_json() for p in parameters]
                return JsonResponse(data, safe=False)

            elif action == 'save':
                pk = request.POST.get('id')
                name = request.POST.get('name', '').strip()
                description = request.POST.get('description', '').strip()
                is_active = request.POST.get('is_active') == 'true'

                if not name:
                    return JsonResponse({'error': 'El nombre del parámetro es obligatorio'}, status=400)

                # Validar duplicados excluyendo el registro actual si es edición
                errors = AssuranceParameter.objects.filter(name__iexact=name)
                if pk:
                    errors = errors.exclude(pk=pk)
                if errors.exists():
                    return JsonResponse({'error': 'Ya existe un parámetro con este nombre'}, status=400)

                if pk:
                    # Edición
                    param = AssuranceParameter.objects.get(pk=pk)
                    param.name = name
                    param.description = description
                    param.is_active = is_active
                    param.save()
                else:
                    # Creación
                    AssuranceParameter.objects.create(
                        name=name,
                        description=description,
                        is_active=is_active
                    )
                return JsonResponse({'success': True})

            elif action == 'toggle_status':
                pk = request.POST.get('id')
                param = AssuranceParameter.objects.get(pk=pk)
                param.is_active = not param.is_active
                param.save()
                return JsonResponse({'success': True, 'new_status': param.is_active})

            return JsonResponse({'error': 'Acción inválida'}, status=400)

        except Exception as e:
            print(traceback.format_exc())
            return JsonResponse({'error': str(e)}, status=500)