from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, get_tenant_model, schema_context

from core.pos import attachments
from core.pos.models import Sale, SaleAttachment


class Command(BaseCommand):
    help = (
        'Elimina los documentos anexos (PDF) de las facturas con más de N días (por defecto %d) para no llenar el disco '
        'del servidor. Del anexo se conserva el nombre para avisar, al reenviar la factura, que ya no está. '
        'Se programa cada noche (cron); es seguro correrlo varias veces.' % attachments.RETENTION_DAYS
    )

    def add_arguments(self, parser):
        parser.add_argument('--dias', type=int, default=attachments.RETENTION_DAYS,
                            help='Días que se conservan los anexos (por defecto %d).' % attachments.RETENTION_DAYS)
        parser.add_argument('--schema', help='Solo esta empresa (por defecto, todas).')
        parser.add_argument('--dry-run', action='store_true', help='Muestra qué eliminaría sin borrar nada.')

    def handle(self, *args, **options):
        if options['schema']:
            schemas = [options['schema']]
        else:
            schemas = list(get_tenant_model().objects.exclude(schema_name=get_public_schema_name())
                           .values_list('schema_name', flat=True))
        total = 0
        for schema in schemas:
            with schema_context(schema):
                total += self.clean(schema, options['dias'], options['dry_run'])
        verb = 'se eliminarían' if options['dry_run'] else 'eliminados'
        self.stdout.write(self.style.SUCCESS(f'Anexos {verb}: {total}.'))

    def clean(self, schema, days, dry):
        cutoff = timezone.now() - timedelta(days=days)
        count = 0
        # Facturas antiguas que guardaban un solo archivo en el campo «attachment»: se pasan a anexos para tratarlas igual
        legacy = (Sale.objects.exclude(attachment='').exclude(attachment__isnull=True)
                  .filter(date_joined__lt=cutoff.date()))
        for sale in legacy:
            count += 1
            self.stdout.write(f'  [{schema}] factura {sale.id}: {sale.attachment.name}')
            if not dry:
                sale.ensure_attachment_rows()
                row = sale.attachments.filter(purged_at__isnull=True).first()
                if row:
                    row.purge()
                Sale.objects.filter(pk=sale.pk).update(attachment='')
        for attachment in SaleAttachment.objects.filter(purged_at__isnull=True, created__lt=cutoff).select_related('sale'):
            count += 1
            self.stdout.write(f'  [{schema}] factura {attachment.sale_id}: {attachment.get_name()}')
            if not dry:
                attachment.purge()
        return count
