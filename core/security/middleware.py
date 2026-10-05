import re

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse

# Rutas que un visitante sin sesión SÍ puede abrir. Todo lo demás exige login,
# de modo que una vista nueva (o una que olvidó su mixin) nunca queda expuesta.
PUBLIC_PATH_PATTERNS = tuple(re.compile(p) for p in (
    r'^/$',                          # inicio de sesión
    r'^/different/$',                # inicio de sesión con otro usuario
    r'^/reset/password/$',           # pedir enlace de recuperación
    r'^/update/password/[^/]+/?$',   # enlace de recuperación recibido por correo
    r'^/logout/$',
    r'^/admin/',                     # el admin de Django maneja su propio login
    r'^/media/dashboard/',           # logo que se muestra en la pantalla de login
))
PUBLIC_PREFIXES = (settings.STATIC_URL,)


class LoginRequiredMiddleware:
    """Niega por defecto el acceso a usuarios sin sesión."""

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def is_public(path):
        return path.startswith(PUBLIC_PREFIXES) or any(p.match(path) for p in PUBLIC_PATH_PATTERNS)

    def __call__(self, request):
        if request.user.is_authenticated or self.is_public(request.path_info):
            return self.get_response(request)

        # Peticiones AJAX / POST: responder JSON para que el frontend lo muestre,
        # en vez de devolver la página de login como si fuera la respuesta esperada.
        if request.method != 'GET' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse(
                {'error': 'Su sesión expiró o no ha iniciado sesión. Ingrese de nuevo.'},
                status=401,
            )
        return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
