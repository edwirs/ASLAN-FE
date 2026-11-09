"""Estado comercial de una empresa: módulos contratados, vencimiento de la suscripción y anuncios vigentes.

Lo usan el middleware (bloquea módulos no contratados y empresas suspendidas), los procesadores de contexto (menú y avisos) y
el panel de la plataforma. Todo se calcula con la hora de Colombia.
"""
from zoneinfo import ZoneInfo

from django.conf import settings
from django.urls import Resolver404, resolve
from django.utils import timezone

TZ_NEGOCIO = ZoneInfo('America/Bogota')

MODULOS = ('restaurante', 'facturacion_electronica', 'nomina')
NOMBRE_MODULO = {'restaurante': 'Restaurante (mesas y cocina)', 'facturacion_electronica': 'Facturación electrónica', 'nomina': 'Nómina'}

# Ítems del menú lateral (clave en core/security/registry.py) que pertenecen a cada módulo.
ITEMS_DE_MODULO = {
    'restaurante': {'table_orders', 'kitchen', 'tables'},
    'facturacion_electronica': {'electronic_invoices', 'credit_notes', 'factus_credentials'},
    'nomina': {'employees', 'employee_transactions', 'payroll'},
}
# Nombres de URL (core/pos/urls.py) que pertenecen a cada módulo: por prefijo, o exactos.
PREFIJOS_DE_MODULO = {
    'restaurante': ('table_', 'order_', 'kitchen_'),
    'facturacion_electronica': ('sale_Fe_', 'credit_note_', 'factus_credential_'),
    'nomina': ('employee_transaction_', 'payroll_'),
}
EXACTOS_DE_MODULO = {
    'restaurante': {'update_order'},
    'facturacion_electronica': {'get_sale_Fe', 'update_sale_Fe'},
    'nomina': {'employee_list', 'employee_create', 'employee_update', 'employee_delete'},
}


def hoy():
    return timezone.localtime(timezone.now(), TZ_NEGOCIO).date()


def modulos_activos(empresa):
    """Conjunto de módulos que la empresa tiene contratados (None = no se sabe: no se filtra nada)."""
    if empresa is None or not hasattr(empresa, 'modulo_nomina'):
        return None
    return {m for m in MODULOS if getattr(empresa, f'modulo_{m}', False)}


def modulo_activo(request, modulo):
    """¿La empresa de esta petición tiene contratado el módulo? (si no se sabe la empresa, sí: no se oculta nada)."""
    activos = modulos_activos(getattr(request, 'tenant', None))
    return activos is None or modulo in activos


def items_ocultos(activos):
    """Claves de los ítems del menú que no deben mostrarse porque su módulo no está contratado."""
    if activos is None:
        return set()
    return set().union(*(items for modulo, items in ITEMS_DE_MODULO.items() if modulo not in activos))


def modulo_de_ruta(ruta):
    """Módulo al que pertenece una URL de las empresas (None = libre), según el nombre de la vista que la atiende."""
    try:
        nombre = resolve(ruta).url_name or ''
    except Resolver404:
        return None
    for modulo in MODULOS:
        if nombre in EXACTOS_DE_MODULO[modulo] or nombre.startswith(PREFIJOS_DE_MODULO[modulo]):
            return modulo
    return None


def estado_suscripcion(empresa):
    """{'nivel', 'dias', 'suspendida', 'mensaje'}: nivel ∈ sin_fecha · ok · por_vencer · gracia · vencida · suspendida.
    `dias` = días que faltan para vencer (negativo si ya venció)."""
    if getattr(empresa, 'suspendida', False):
        return {'nivel': 'suspendida', 'dias': None, 'suspendida': True, 'mensaje': 'El acceso de esta empresa está suspendido.'}
    hasta = getattr(empresa, 'paid_until', None)
    if not hasta:
        return {'nivel': 'sin_fecha', 'dias': None, 'suspendida': False, 'mensaje': ''}
    dias = (hasta - hoy()).days
    if dias > 7:
        return {'nivel': 'ok', 'dias': dias, 'suspendida': False, 'mensaje': ''}
    if dias >= 0:
        cuando = 'hoy' if dias == 0 else 'mañana' if dias == 1 else f'en {dias} días'
        return {'nivel': 'por_vencer', 'dias': dias, 'suspendida': False,
                'mensaje': f'Tu suscripción vence {cuando} ({hasta:%d/%m/%Y}). Comunícate con ASLAN para renovarla.'}
    atrasados = -dias
    if atrasados <= settings.GRACIA_DIAS or not settings.SUSPENDER_POR_VENCIMIENTO:
        restan = max(settings.GRACIA_DIAS - atrasados, 0)
        return {'nivel': 'gracia' if settings.SUSPENDER_POR_VENCIMIENTO else 'vencida', 'dias': dias, 'suspendida': False,
                'atrasados': atrasados, 'gracia_restante': restan,
                'mensaje': f'Tu suscripción venció el {hasta:%d/%m/%Y}. ' + (
                    f'Tienes {restan} día(s) para renovarla antes de que se suspenda el acceso.'
                    if settings.SUSPENDER_POR_VENCIMIENTO else 'Renuévala con ASLAN.')}
    return {'nivel': 'suspendida', 'dias': dias, 'suspendida': True,
            'mensaje': f'La suscripción venció el {hasta:%d/%m/%Y} y el período de gracia terminó.'}


def anuncios_para(empresa):
    """Anuncios vigentes para esta empresa (los de todas + los suyos), del más urgente al más suave."""
    from core.tenants.models import Anuncio

    if empresa is None or not hasattr(empresa, 'schema_name'):
        return []
    dia = hoy()
    filas = Anuncio.objects.filter(activo=True, desde__lte=dia, hasta__gte=dia, schema__in=['', empresa.schema_name])
    orden = {'urgente': 0, 'aviso': 1, 'info': 2}
    return sorted(filas, key=lambda a: (orden.get(a.nivel, 3), -a.pk))
