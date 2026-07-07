from django.views.generic import TemplateView
from django.urls import NoReverseMatch, reverse

from core.catalogs.models import MipeModule
from core.security.mixins import GroupPermissionMixin


class MipeDashboardView(
    GroupPermissionMixin,
    TemplateView
):
    template_name = 'mipe/dashboard.html'

    permission_required = 'view_mipe_module'

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context['title'] = 'MIPE'
        context['module_name'] = 'MIPE'

        modules = MipeModule.objects.filter(
            is_active=True
        ).order_by('order')

        for module in modules:

            try:
                module.navigation_url = reverse(module.url_name)
            except NoReverseMatch:
                module.navigation_url = ''

        context['modules'] = modules

        return context
