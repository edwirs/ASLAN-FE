from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django_tenants.utils import get_public_schema_name, get_tenant_model, schema_context
from PIL import Image

from core.pos.images import USER_MAX_SIDE, shrink_image
from core.user.models import User


class Command(BaseCommand):
    help = (
        'Reduce las fotos de usuario ya cargadas (máximo %d px por lado, WebP). Es seguro repetirlo: '
        'lo que ya es pequeño no se toca.' % USER_MAX_SIDE
    )

    def add_arguments(self, parser):
        parser.add_argument('--schema', help='Solo este esquema (por defecto, todos los tenants).')
        parser.add_argument('--dry-run', action='store_true', help='Muestra qué haría sin guardar nada.')

    def handle(self, *args, **options):
        schemas = [options['schema']] if options['schema'] else list(
            get_tenant_model().objects.exclude(schema_name=get_public_schema_name())
            .values_list('schema_name', flat=True))
        for schema in schemas:
            with schema_context(schema):
                self.stdout.write(self.style.MIGRATE_HEADING(f'== Tenant "{schema}" =='))
                done = skipped = failed = saved = 0
                for user in User.objects.exclude(image='').exclude(image__isnull=True):
                    try:
                        path, before = user.image.path, user.image.size
                        with Image.open(path) as img:
                            small = max(img.size) <= USER_MAX_SIDE and img.format == 'WEBP'
                        if small:
                            skipped += 1
                            continue
                        with open(path, 'rb') as fh:
                            content = shrink_image(fh, name=user.image.name, max_side=USER_MAX_SIDE)
                        if not options['dry_run']:
                            old = user.image.name
                            user.image.save(content.name, ContentFile(content.read()), save=True)
                            user.image.storage.delete(old)
                        saved += max(before - content.size, 0)
                        done += 1
                    except Exception as e:  # archivo faltante o dañado: se informa y se sigue
                        failed += 1
                        self.stdout.write(self.style.WARNING(f'  {user.username}: {e}'))
                prefix = '[simulación] ' if options['dry_run'] else ''
                self.stdout.write(f'  {prefix}reducidas: {done} | ya pequeñas: {skipped} | con error: {failed} | '
                                  f'ahorro: {saved / 1024:.0f} KB')
