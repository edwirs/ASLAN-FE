"""Reglas de los documentos anexos (PDF) de las facturas electrónicas.

Se guardan con la factura para poder enviarlos en cada correo; para no llenar el disco del servidor se eliminan solos
a los ``RETENTION_DAYS`` días (comando ``limpiar_anexos``) y cada archivo tiene un tamaño máximo.
"""
RETENTION_DAYS = 90
MAX_MB = 5


def validate_pdf(uploaded):
    """Lanza ``ValueError`` con un mensaje para el usuario si el archivo no es un PDF o pesa más de ``MAX_MB``."""
    name = getattr(uploaded, 'name', '') or 'archivo'
    if not name.lower().endswith('.pdf'):
        raise ValueError(f'«{name}» no es un documento PDF.')
    size = getattr(uploaded, 'size', 0) or 0
    if size > MAX_MB * 1024 * 1024:
        raise ValueError(f'«{name}» pesa {size / (1024 * 1024):.2f} MB y el máximo por documento es {MAX_MB} MB.')
