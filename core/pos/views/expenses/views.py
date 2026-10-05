import json

from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import DeleteView, CreateView, UpdateView, FormView, TemplateView
from django.core.serializers.json import DjangoJSONEncoder

from core.pos.models import Expenses
from core.pos.forms import ExpensesForm
from core.reports.forms import ReportForm
from core.security.mixins import GroupPermissionMixin

MODULE_NAME = 'Gastos'

class ExpensesListView(GroupPermissionMixin, FormView):
    template_name = "expenses/list.html"
    form_class = ReportForm
    permission_required = 'pos.view_expenses'
    model = Expenses

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                start_date = request.POST['start_date']
                end_date = request.POST['end_date']
                queryset = Expenses.objects.all()
                if start_date and end_date:
                    queryset = queryset.filter(created_at__range=[start_date, end_date])

                for i in queryset.order_by('-id'):
                    data.append(i.toJSON())
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(
            json.dumps(data, cls=DjangoJSONEncoder),
            content_type='application/json'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de gastos'
        context['list_url'] = reverse_lazy('expenses_list')
        context['create_url'] = reverse_lazy('expenses_create')
        context['module_name'] = MODULE_NAME
        return context


class ExpensesCreateView(GroupPermissionMixin, CreateView):
    model = Expenses
    template_name = "expenses/create.html"
    form_class = ExpensesForm
    success_url = reverse_lazy('expenses_list')
    permission_required = 'add_expenses'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'add':
                form = self.get_form()
                if form.is_valid():
                    expense = form.save(commit=False)
                    expense.user = request.user   # 👈 cambio aquí
                    expense.save()
                    data = expense.toJSON()
                else:
                    data['error'] = form.errors.as_json()
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nuevo registro de un gasto'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['module_name'] = MODULE_NAME
        return context


class ExpensesUpdateView(GroupPermissionMixin, UpdateView):
    model = Expenses
    template_name = "expenses/create.html"
    form_class = ExpensesForm
    success_url = reverse_lazy("expenses_list")
    permission_required = 'change_expenses'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'edit':
                expense = self.get_form().save()
                data = expense.toJSON()
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edición de un gasto'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['module_name'] = MODULE_NAME
        return context

class ExpensesDeleteView(GroupPermissionMixin, DeleteView):
    model = Expenses
    template_name = "delete.html"
    success_url = reverse_lazy("expenses_list")
    permission_required = 'delete_expenses'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.get_object().delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminación de un gasto'
        context['list_url'] = self.success_url
        context['module_name'] = MODULE_NAME
        return context
