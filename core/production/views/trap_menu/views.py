from django.views.generic import TemplateView

class TrapDashboardView(TemplateView):
    template_name = 'trap_menu/menu.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Gestión de Trampas'
        # Definimos los botones aquí
        context['trap_modules'] = [
            {'name': 'Trampas ICA', 'icon': 'fas fa-bug', 'url': '/production/trap/ica/list/'},
            {'name': 'Trampas Copitarsia', 'icon': 'fas fa-leaf', 'url': '/production/trap/copitarsia/list'},
            {'name': 'Trampas Internas', 'icon': 'fas fa-home', 'url': '/production/trap/internal/list'},
            {'name': 'Trampas Externas', 'icon': 'fas fa-tree', 'url': '/production/trap/external/list'},
        ]
        return context