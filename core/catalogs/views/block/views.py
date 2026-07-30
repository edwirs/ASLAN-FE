import json
from django.db import transaction
from django.http import JsonResponse
from django.views.generic import TemplateView, FormView
from django.urls import reverse_lazy

from core.catalogs.forms import BlockStructureForm
from core.catalogs.models import Block, BlockBay, Bed, BedSection, MonitoringSettings
from core.security.mixins import GroupPermissionMixin

MODULE_NAME = 'Bloques'

class BlockListView(GroupPermissionMixin, TemplateView):
    template_name = 'block/list.html'
    permission_required = 'view_block'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'search':
                data = [i.toJSON() for i in Block.objects.all().order_by('code')]
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Bloques'
        context['create_url'] = reverse_lazy('catalogs:block_structure_create')
        context['module_name'] = MODULE_NAME
        return context

class BlockStructureCreateView(FormView):
    template_name = 'block/structure.html'
    form_class = BlockStructureForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if 'pk' in self.kwargs:
            self.object = Block.objects.get(pk=self.kwargs['pk'])
            first_bay = self.object.blockbay_set.first()
            
            # CAMBIO: Usamos 'beds' en lugar de 'bed_set'
            first_bed = first_bay.beds.first() if first_bay else None
            
            kwargs.update({
                'initial': {
                    'code': self.object.code,
                    'name': self.object.name,
                    'has_sides': self.object.has_sides,
                    'bay_quantity': self.object.blockbay_set.count(),
                    'bed_quantity': first_bay.bed_quantity if first_bay else 0,
                    
                    # TAMBIÉN AQUÍ: Usamos 'sections' en lugar de 'bedsection_set'
                    # (Porque en tu modelo BedSection definiste related_name='sections')
                    'section_quantity': first_bed.sections.count() if first_bed else 0
                }
            })
        return kwargs

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST.get('action')
            if action == 'create':
                form = self.form_class(request.POST)
                if not form.is_valid():
                    return JsonResponse({'error': form.errors}, status=400)

                selected_sections = request.POST.getlist('selected_sections[]')

                with transaction.atomic():
                    if 'pk' in self.kwargs:
                        Block.objects.get(pk=self.kwargs['pk']).delete()

                    block = Block.objects.create(
                        code=form.cleaned_data['code'],
                        name=form.cleaned_data['name'],
                        has_sides=form.cleaned_data['has_sides']
                    )

                    middle = form.cleaned_data['bay_quantity'] // 2
                    for bay_num in range(1, form.cleaned_data['bay_quantity'] + 1):
                        side = 'A' if (form.cleaned_data['has_sides'] and bay_num <= middle) else ('B' if form.cleaned_data['has_sides'] else None)
                        bay_obj = BlockBay.objects.create(block=block, code=f'{bay_num}', side=side, bed_quantity=form.cleaned_data['bed_quantity'])

                        for bed_num in range(1, form.cleaned_data['bed_quantity'] + 1):
                            bed_obj = Bed.objects.create(bay=bay_obj, number=bed_num, parity='even' if bed_num % 2 == 0 else 'odd')

                            for sec_num in range(1, form.cleaned_data['section_quantity'] + 1):
                                section_obj = BedSection.objects.create(bed=bed_obj, number=sec_num)
                                if f"{bay_num}-{bed_num}-{sec_num}" in selected_sections:
                                    MonitoringSettings.objects.create(bed_section=section_obj, is_monitored=True)

                data['success'] = True
            else:
                data['error'] = 'Acción inválida'
        except Exception as e:
            data['error'] = str(e)
            return JsonResponse(data, status=500)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Estructura Bloques'
        context['module_name'] = MODULE_NAME
        if 'pk' in self.kwargs:
            context['block_id'] = self.kwargs['pk']
            # Extraemos las secciones monitoreadas para el JS
            monitored = MonitoringSettings.objects.filter(bed_section__bed__bay__block_id=self.kwargs['pk'])
            # Asumimos que los códigos de nave son 'N1', 'N2'... tomamos el número final
            context['monitored_sections'] = [
                f"{m.bed_section.bed.bay.code.replace('N','')}-{m.bed_section.bed.number}-{m.bed_section.number}" 
                for m in monitored
            ]
        return context