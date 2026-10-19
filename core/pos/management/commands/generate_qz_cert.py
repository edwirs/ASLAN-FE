import os
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        'Genera el certificado y la llave privada con que el servidor firma las peticiones a QZ Tray '
        '(cajón monedero). Se ejecuta una sola vez en el servidor; el certificado público es el que se '
        'instala o recuerda en QZ Tray de cada PC de caja.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Sobrescribe un par existente (invalida lo ya aprobado en los PC).')
        parser.add_argument('--days', type=int, default=3650, help='Vigencia del certificado en días (por defecto 10 años).')

    def handle(self, *args, **options):
        key_path = settings.QZ_PRIVATE_KEY_PATH
        cert_path = settings.QZ_CERTIFICATE_PATH
        if (os.path.exists(key_path) or os.path.exists(cert_path)) and not options['force']:
            raise CommandError(f'Ya existe un par en {key_path}. Use --force solo si quiere reemplazarlo '
                               '(habría que aprobar de nuevo el certificado en cada PC de caja).')

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, 'ASLAN POS'),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'ASLAN'),
        ])
        now = datetime.now(timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=options['days']))
            .sign(key, hashes.SHA256())
        )

        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        os.makedirs(os.path.dirname(cert_path), exist_ok=True)
        fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                      serialization.NoEncryption()))
        with open(cert_path, 'wb') as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        self.stdout.write(self.style.SUCCESS('Par generado.'))
        self.stdout.write(f'  Llave privada (NO compartir ni versionar): {key_path}')
        self.stdout.write(f'  Certificado público: {cert_path}')
