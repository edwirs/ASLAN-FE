import base64
import logging

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.views import View

from core.pos.models import CashDrawerLog
from core.security.mixins import GroupPermissionMixin

SOURCES = {'sale', 'salefe', 'bar', 'bar_auto', 'test'}
# Quien puede vender (facturas, facturas electrónicas o ventas rápidas) puede abrir el cajón.
ALLOWED_PERMISSIONS = ('add_sale', 'add_electronic_invoice', 'add_bar')
MAX_SIGN_LENGTH = 10000
logger = logging.getLogger(__name__)


class CashDrawerAccessMixin(LoginRequiredMixin):
    def has_access(self, request):
        if request.user.is_superuser:
            return True
        group = request.session.get('group')
        return bool(group) and any(GroupPermissionMixin.has_permission(group, p) for p in ALLOWED_PERMISSIONS)


class CashDrawerCertificateView(CashDrawerAccessMixin, View):
    """Certificado público con el que QZ Tray identifica a este sistema (no es secreto)."""

    def get(self, request, *args, **kwargs):
        if not self.has_access(request):
            return HttpResponse('No tienes permiso para hacer esto', status=403, content_type='text/plain')
        try:
            with open(settings.QZ_CERTIFICATE_PATH, 'rb') as f:
                certificate = f.read()
        except OSError:
            logger.error('No existe el certificado de QZ Tray en %s. Ejecute: python manage.py generate_qz_cert',
                         settings.QZ_CERTIFICATE_PATH)
            return HttpResponse('Certificado de QZ Tray no configurado en el servidor', status=503, content_type='text/plain')
        response = HttpResponse(certificate, content_type='text/plain; charset=utf-8')
        if request.GET.get('download'):
            response['Content-Disposition'] = 'attachment; filename="aslan-qz-certificate.crt"'
        return response


class CashDrawerSignView(CashDrawerAccessMixin, View):
    """Firma (RSA + SHA-512) lo que QZ Tray pide firmar. Solo quien puede vender y con la llave del servidor."""

    def post(self, request, *args, **kwargs):
        if not self.has_access(request):
            return HttpResponse('No tienes permiso para hacer esto', status=403, content_type='text/plain')
        message = request.POST.get('request', '')
        if not message or len(message) > MAX_SIGN_LENGTH:
            return HttpResponse('Solicitud inválida', status=400, content_type='text/plain')
        try:
            with open(settings.QZ_PRIVATE_KEY_PATH, 'rb') as f:
                key = serialization.load_pem_private_key(f.read(), password=None)
            signature = key.sign(message.encode('utf-8'), padding.PKCS1v15(), hashes.SHA512())
        except (OSError, ValueError):
            logger.exception('No se pudo firmar la solicitud de QZ Tray (llave en %s)', settings.QZ_PRIVATE_KEY_PATH)
            return HttpResponse('Llave de QZ Tray no configurada en el servidor', status=503, content_type='text/plain')
        return HttpResponse(base64.b64encode(signature), content_type='text/plain')


class CashDrawerLogView(CashDrawerAccessMixin, View):
    """Registra cada apertura del cajón (la apertura en sí la hace QZ Tray en el PC de caja)."""

    def post(self, request, *args, **kwargs):
        if not self.has_access(request):
            return JsonResponse({'error': 'No tienes permiso para hacer esto'}, status=403)
        source = request.POST.get('source', '')
        CashDrawerLog.objects.create(
            user=request.user,
            source=source if source in SOURCES else 'sale',
            printer=request.POST.get('printer', '')[:150],
        )
        return JsonResponse({'success': True})
