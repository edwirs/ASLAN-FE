from django.core.management.base import BaseCommand
from django_tenants.utils import get_public_schema_name, get_tenant_model, schema_context

from core.pos.models import Product
from core.pos.units import DECIMAL_UNITS


class Command(BaseCommand):
    help = (
        'Activa "¿Permite cantidades decimales?" en los productos que ya existen y cuya unidad base se vende en '
        'fracciones (%s). Es seguro repetirlo: no apaga nada y no toca los que ya lo tienen.' % ', '.join(DECIMAL_UNITS)
    )

    def add_arguments(self, parser):
        parser.add_argument('--schema', help='Solo este esquema (por defecto, todos los tenants).')
        parser.add_argument('--dry-run', action='store_true', help='Muestra qué productos cambiaría, sin guardar.')

    def handle(self, *args, **options):
        schemas = [options['schema']] if options['schema'] else list(
            get_tenant_model().objects.exclude(schema_name=get_public_schema_name())
            .values_list('schema_name', flat=True))
        for schema in schemas:
            with schema_context(schema):
                qs = Product.objects.filter(unit_name__in=DECIMAL_UNITS, allow_decimals=False, is_service=False)
                self.stdout.write(self.style.MIGRATE_HEADING(f'== Tenant "{schema}" =='))
                for p in qs.order_by('name'):
                    self.stdout.write(f'  {p.code} - {p.name} ({p.unit_name})')
                total = qs.count()
                if not options['dry_run']:
                    qs.update(allow_decimals=True)
                prefix = '[simulación] ' if options['dry_run'] else ''
                self.stdout.write(f'  {prefix}productos activados: {total}')
