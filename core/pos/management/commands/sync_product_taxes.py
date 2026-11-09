from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import get_public_schema_name, get_tenant_model, schema_context

from core.pos import taxes
from core.pos.models import Company, Product


class Command(BaseCommand):
    help = (
        'Asigna un impuesto propio a los productos que todavía no lo tienen (los creados antes del campo «Impuesto»), '
        'según lo que cobraban hasta hoy: los que cobraban impuesto quedan con la tarifa de IVA configurada en la '
        'Compañía (19 % → IVA 19, 5 % → IVA 5, 0 % → Excluido) y los que no cobraban quedan en Excluido. '
        'Se corre UNA vez por empresa, para que las facturas no cambien de un día para otro; después la Compañía ya no '
        'interviene. Es idempotente: no toca los productos que ya tienen impuesto.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--schema', help='Solo este esquema (por defecto, todas las empresas).')
        parser.add_argument('--dry-run', action='store_true', help='Muestra qué haría sin guardar nada.')

    def handle(self, *args, **options):
        if options['schema']:
            schemas = [options['schema']]
        else:
            schemas = list(get_tenant_model().objects.exclude(schema_name=get_public_schema_name())
                           .values_list('schema_name', flat=True))
        for schema in schemas:
            self.stdout.write(self.style.MIGRATE_HEADING(f'== Empresa "{schema}" =='))
            with schema_context(schema), transaction.atomic():
                self.sync(options['dry_run'])

    def sync(self, dry):
        company = Company.objects.first()
        rate = company.iva if company is not None else 0
        key = taxes.key_for_company_rate(rate)
        pending = Product.objects.filter(tax='')
        taxed, free = pending.filter(with_tax=True).count(), pending.filter(with_tax=False).count()
        if not (taxed or free):
            self.stdout.write('  Todos los productos ya tienen impuesto.')
            return
        label = taxes.TAX_BY_KEY[key].label
        prefix = '[simulación] ' if dry else ''
        self.stdout.write(f'  {prefix}Compañía con IVA {rate} %: {taxed} producto(s) que cobraban impuesto → {label}')
        self.stdout.write(f'  {prefix}{free} producto(s) que no cobraban impuesto → {taxes.TAX_BY_KEY[taxes.LEGACY_NO_TAX].label}')
        if taxed and Product.objects.filter(tax='', with_tax=True).exists() and float(rate) not in (0.0, 5.0, 19.0):
            self.stdout.write(self.style.WARNING(
                f'  La tarifa {rate} % no está en el catálogo: esos productos quedan en {label}. Revíselos si hace falta.'))
        if dry:
            return
        pending.filter(with_tax=True).update(tax=key, with_tax=taxes.is_taxed(key))
        pending.filter(with_tax=False).update(tax=taxes.LEGACY_NO_TAX)
        self.stdout.write(self.style.SUCCESS('  Listo.'))
