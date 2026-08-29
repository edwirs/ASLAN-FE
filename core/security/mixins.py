from crum import get_current_request
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator

from config import settings


class GroupSessionMixin(object):
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        if 'group' not in request.session:
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
        return super().dispatch(request, *args, **kwargs)


class GroupPermissionMixin(GroupSessionMixin, object):
    permission_required = None

    def get_permissions(self):
        permissions = []
        if isinstance(self.permission_required, str):
            permissions.append(self.permission_required)
        else:
            permissions = list(self.permission_required)
        return permissions

    @staticmethod
    def has_permission(group, permission):
        """Comprueba un permiso de grupo, admitiendo ``app_label.codename``.

        Los codenames no son globalmente únicos: por ejemplo, ``tenants.Client``
        y ``pos.Client`` pueden tener ambos ``view_client``. Para los permisos
        calificados se debe comprobar también la aplicación que los define.
        """
        if '.' in permission:
            app_label, codename = permission.split('.', 1)
            return group.permissions.filter(
                content_type__app_label=app_label,
                codename=codename,
            ).exists()
        return group.permissions.filter(codename=permission).exists()

    def get_last_url(self):
        request = get_current_request()
        if 'url_last' in request.session:
            if request.session['url_last'] != request.path:
                return request.session['url_last']
        return settings.LOGIN_REDIRECT_URL

    def get(self, request, *args, **kwargs):
        if request.user.is_superuser:
            request.session['url_last'] = request.path
            return super().get(request, *args, **kwargs)
        group = request.session.get('group')
        permission_list = self.get_permissions()
        if not group or not all(self.has_permission(group, permission) for permission in permission_list):
            messages.error(request, 'Tu perfil no cuenta con el permiso necesario para ingresar')
            return HttpResponseRedirect(self.get_last_url())
        request.session['url_last'] = request.path
        return super().get(request, *args, **kwargs)
