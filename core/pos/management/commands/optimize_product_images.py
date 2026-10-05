from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django_tenants.utils import get_public_schema_name, get_tenant_model, schema_context

from core.pos.images import MAX_SIDE, shrink_image
from core.pos.models import Product


class Command(BaseCommand):
    help = (
        'Reduce las imágenes de producto ya cargadas (máximo %d px por lado, WebP) para que las pantallas de '
        'venta carguen rápido. Es seguro repetirlo: lo que ya es pequeño no se toca.' % MAX_SIDE
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
                done = skipped = failed = 0
                saved = 0
                for product in Product.objects.exclude(image='').exclude(image__isnull=True):
                    try:
                        path = product.image.path
                        before = product.image.size
                        from PIL import Image
                        with Image.open(path) as img:
                            small = max(img.size) <= MAX_SIDE and img.format == 'WEBP'
                        if small:
                            skipped += 1
                            continue
                        with open(path, 'rb') as fh:
                            content = shrink_image(fh, name=product.image.name)
                        after = content.size
                        if not options['dry_run']:
                            old = product.image.name
                            product.image.save(content.name, ContentFile(content.read()), save=True)
                            product.image.storage.delete(old)
                        saved += max(before - after, 0)
                        done += 1
                    except Exception as e:  # archivo faltante o dañado: se informa y se sigue
                        failed += 1
                        self.stdout.write(self.style.WARNING(f'  {product.code}: {e}'))
                prefix = '[simulación] ' if options['dry_run'] else ''
                self.stdout.write(f'  {prefix}reducidas: {done} | ya pequeñas: {skipped} | con error: {failed} | '
                                  f'ahorro: {saved / 1024:.0f} KB')
