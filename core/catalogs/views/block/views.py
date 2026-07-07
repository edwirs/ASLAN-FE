import json

from django.db import transaction
from django.http import HttpResponse
from django.views.generic import TemplateView, FormView
from django.urls import reverse_lazy

from core.catalogs.forms import BlockStructureForm
from core.catalogs.models import Block
from core.catalogs.models import BlockBay
from core.catalogs.models import Bed
from core.catalogs.models import BedSection
from core.security.mixins import GroupPermissionMixin

MODULE_NAME = 'Bloques'

class BlockListView(GroupPermissionMixin,TemplateView):
    template_name = 'block/list.html'
    permission_required = 'view_block'

    def post(self, request, *args, **kwargs):

        data = []

        try:

            action = request.POST['action']

            if action == 'search':

                for i in Block.objects.all().order_by('code'):

                    data.append({
                        'id': i.id,
                        'code': i.code,
                        'name': i.name,
                        'has_sides': i.has_sides,
                        'is_active': i.is_active,
                    })

            else:

                data['error'] = 'No ha seleccionado ninguna opción'

        except Exception as e:

            data = {
                'error': str(e)
            }

        return HttpResponse(
            json.dumps(data),
            content_type='application/json'
        )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context['title'] = 'Listado de Bloques'
        context['create_url'] = reverse_lazy('catalogs:block_structure_create')
        context['module_name'] = MODULE_NAME

        return context

class BlockStructureCreateView(FormView):

    template_name = 'block/structure.html'
    form_class = BlockStructureForm

    def post(self, request, *args, **kwargs):

        data = {}

        try:

            action = request.POST['action']

            if action == 'create':

                form = self.form_class(request.POST)

                if not form.is_valid():
                    data['error'] = form.errors.as_json()
                    return HttpResponse(
                        json.dumps(data),
                        content_type='application/json'
                    )

                code = form.cleaned_data['code']
                name = form.cleaned_data['name']
                has_sides = form.cleaned_data['has_sides']
                bay_quantity = form.cleaned_data['bay_quantity']
                bed_quantity = form.cleaned_data['bed_quantity']
                section_quantity = form.cleaned_data['section_quantity']

                with transaction.atomic():

                    block = Block.objects.create(
                        code=code,
                        name=name,
                        has_sides=has_sides
                    )

                    middle = bay_quantity // 2

                    for bay in range(1, bay_quantity + 1):

                        side = None

                        if has_sides:

                            if bay <= middle:
                                side = 'A'
                            else:
                                side = 'B'

                        bay_obj = BlockBay.objects.create(
                            block=block,
                            code=f'N{bay}',
                            side=side,
                            bed_quantity=bed_quantity
                        )

                        for bed in range(1, bed_quantity + 1):

                            bed_obj = Bed.objects.create(
                                bay=bay_obj,
                                number=bed,
                                parity='even' if bed % 2 == 0 else 'odd'
                            )

                            for section in range(1, section_quantity + 1):

                                BedSection.objects.create(
                                    bed=bed_obj,
                                    number=section
                                )

                data['success'] = True

            else:

                data['error'] = 'Acción inválida'

        except Exception as e:

            data['error'] = str(e)

        return HttpResponse(
            json.dumps(data),
            content_type='application/json'
        )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context['title'] = 'Estructura Bloques'
        context['module_name'] = 'MIPE'

        return context
