import json
import time

from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import DeleteView, CreateView, UpdateView, TemplateView

from core.catalogs.forms import SeverityGradeForm
from core.catalogs.models import SeverityGrade
from core.security.mixins import GroupPermissionMixin

MODULE_NAME = 'Grados de Severidad'

class SeverityGradeListView(TemplateView):
    template_name = 'severity_grade/list.html'
    permission_required = 'view_severity_grade'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                for i in SeverityGrade.objects.all():
                    data.append(i.toJSON())
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Grados de Severidad'
        context['list_url'] = reverse_lazy('catalogs:severity_grade_list')
        context['create_url'] = reverse_lazy('catalogs:severity_grade_create')
        context['module_name'] = MODULE_NAME
        
        return context

class SeverityGradeCreateView(GroupPermissionMixin, CreateView):
    template_name = 'severity_grade/create.html'
    model = SeverityGrade
    form_class = SeverityGradeForm
    success_url = reverse_lazy('catalogs:severity_grade_list')
    permission_required = 'add_severity_grade'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'add':
                data = self.get_form().save()
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nuevo registro de un Grado de Severidad'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME
        return context


class SeverityGradeUpdateView(GroupPermissionMixin, UpdateView):
    template_name = 'severity_grade/create.html'
    model = SeverityGrade
    form_class = SeverityGradeForm
    success_url = reverse_lazy('catalogs:severity_grade_list')
    permission_required = 'change_severity_grade'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'edit':
                data = self.get_form().save()
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edición de un Grado de Severidad'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['module_name'] = MODULE_NAME
        return context


class SeverityGradeDeleteView(GroupPermissionMixin, DeleteView):
    model = SeverityGrade
    template_name = 'delete.html'
    success_url = reverse_lazy('catalogs:severity_grade_list')
    permission_required = 'delete_severity_grade'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.get_object().delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminación de un Grado de Severidad'
        context['list_url'] = self.success_url
        context['module_name'] = MODULE_NAME
        return context