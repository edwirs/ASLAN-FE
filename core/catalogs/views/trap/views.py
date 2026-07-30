import json
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from core.catalogs.models import TrapICA, TrapCopitarsia, TrapIn, TrapOut, Block
from core.security.mixins import GroupPermissionMixin

MODULE_NAME = 'Gestión de Trampas'

class TrapListView(GroupPermissionMixin, TemplateView):
    template_name = 'trap/list.html'
    permission_required = 'view_trap_ica' # Puedes ajustar esto si tienes permisos separados

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action')
        try:
            if action == 'search_ica':
                data = [i.toJSON() for i in TrapICA.objects.all()]
            elif action == 'search_copitarsia':
                data = [i.toJSON() for i in TrapCopitarsia.objects.all()]
            elif action == 'search_in':
                data = [i.toJSON() for i in TrapIn.objects.all()]
            elif action == 'search_out':
                data = [i.toJSON() for i in TrapOut.objects.all()]
            elif action == 'add_ica':
                # Obtenemos 'on' si está marcado, de lo contrario None
                is_active = True if request.POST.get('is_active') == 'on' else False
                TrapICA.objects.create(
                    name=request.POST['name'], 
                    observation=request.POST['observation'],
                    is_active=is_active
                )
            elif action == 'add_copitarsia':
                is_active = True if request.POST.get('is_active') == 'on' else False
                TrapCopitarsia.objects.create(
                    name=request.POST['name'], 
                    observation=request.POST['observation'],
                    is_active=is_active
                )
            elif action == 'add_in':
                is_active = True if request.POST.get('is_active') == 'on' else False
                TrapIn.objects.create(
                    name=request.POST['name'], 
                    observation=request.POST['observation'],
                    is_active=is_active,
                    block_id=request.POST['block_id'] # Guardamos el ID del bloque
                )
            elif action == 'add_out':
                is_active = True if request.POST.get('is_active') == 'on' else False
                TrapOut.objects.create(
                    name=request.POST['name'], 
                    observation=request.POST['observation'],
                    is_active=is_active
                )
            elif action == 'edit_ica':
                id = request.POST.get('id') # Necesitas enviar el ID oculto
                obj = TrapICA.objects.get(pk=id)
                obj.name = request.POST['name']
                obj.observation = request.POST['observation']
                obj.is_active = True if request.POST.get('is_active') == 'on' else False
                obj.save()
            elif action == 'edit_copi':
                obj = TrapCopitarsia.objects.get(pk=request.POST['id'])
                obj.name = request.POST['name']
                obj.observation = request.POST['observation']
                obj.is_active = True if request.POST.get('is_active') == 'on' else False
                obj.save()
            elif action == 'edit_in':
                obj = TrapIn.objects.get(pk=request.POST['id'])
                obj.name = request.POST['name']
                obj.observation = request.POST['observation']
                obj.is_active = True if request.POST.get('is_active') == 'on' else False
                obj.block_id = request.POST['block_id'] # Actualizamos el bloque
                obj.save()
            elif action == 'edit_out':
                obj = TrapOut.objects.get(pk=request.POST['id'])
                obj.name = request.POST['name']
                obj.observation = request.POST['observation']
                obj.is_active = True if request.POST.get('is_active') == 'on' else False
                obj.save()
            else:
                data['error'] = 'Acción no válida'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Trampas'
        context['module_name'] = MODULE_NAME
        context['blocks'] = Block.objects.filter(is_active=True)
        # Si tienes URLs de creación separadas, puedes agregarlas aquí
        # context['create_url_ica'] = reverse_lazy('catalogs:trap_ica_create')
        # context['create_url_copitarsia'] = reverse_lazy('catalogs:trap_copitarsia_create')
        return context