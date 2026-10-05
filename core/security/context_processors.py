import logging
from datetime import datetime

from django.urls import NoReverseMatch, reverse

from core.security import registry
from core.security.models import Dashboard

logger = logging.getLogger(__name__)


def site_settings(request):
    return {
        'date_joined': datetime.now().date(),
        'dashboard': Dashboard.objects.first()
    }


def _build_menu(nodes, user):
    """Filtra el menú del registro según los permisos del usuario.

    Un ítem es visible si no exige permiso o el usuario lo tiene; una sección
    solo aparece si al menos uno de sus hijos es visible (así un padre nunca
    queda vacío ni oculto por una condición desalineada con sus hijos).
    """
    visible = []
    for node in nodes:
        if isinstance(node, registry.Section):
            children = _build_menu(node.children, user)
            if children:
                visible.append({'label': node.label, 'icon': node.icon, 'children': children})
            continue
        if node.view_perm is not None and not user.has_perm(node.view_perm):
            continue
        try:
            url = reverse(node.url_name)
        except NoReverseMatch:
            logger.error('Menú: la URL "%s" del módulo "%s" no existe', node.url_name, node.key)
            continue
        visible.append({'label': node.label, 'icon': node.icon, 'url': url})
    return visible


def sidebar_menu(request):
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {}
    return {'sidebar_menu': _build_menu(registry.MENU, user)}
