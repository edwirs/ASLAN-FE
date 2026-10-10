from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django_tenants.utils import get_public_schema_name, get_tenant_model, schema_context

from core.pos.models import Departamento, DocumentType, Municipio


class Command(BaseCommand):
    help = (
        'Copia los catálogos fijos (tipos de documento, departamentos y municipios) de un tenant que ya los '
        'tiene a otros tenants que están vacíos o incompletos. Solo agrega lo que falta (por código); no '
        'modifica ni borra nada. Conserva los mismos ids cuando están libres. Es idempotente.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--from', dest='source', required=True,
                            help='Schema que tiene los datos (por ejemplo "opita").')
        parser.add_argument('--to', nargs='*', default=None,
                            help='Schemas destino. Por defecto, todos los demás tenants.')
        parser.add_argument('--dry-run', action='store_true', help='Muestra qué haría sin guardar nada.')

    def handle(self, *args, **options):
        tenants = list(
            get_tenant_model().objects.exclude(schema_name=get_public_schema_name())
            .values_list('schema_name', flat=True)
        )
        source = options['source']
        if source not in tenants:
            raise CommandError(f'El schema origen "{source}" no existe. Disponibles: {", ".join(tenants)}')
        targets = options['to'] or [s for s in tenants if s != source]
        unknown = [s for s in targets if s not in tenants]
        if unknown:
            raise CommandError(f'Schemas destino inexistentes: {", ".join(unknown)}')
        targets = [s for s in targets if s != source]
        if not targets:
            self.stdout.write('No hay schemas destino.')
            return

        with schema_context(source):
            doc_types = list(DocumentType.objects.order_by('id').values())
            departments = list(Departamento.objects.order_by('id').values())
            municipalities = list(Municipio.objects.order_by('id').values())
            dept_code_by_id = {d['id']: d['codigo'] for d in departments}
        self.stdout.write(
            f'Origen "{source}": {len(doc_types)} tipos de documento, {len(departments)} departamentos, '
            f'{len(municipalities)} municipios.')
        if not (doc_types or departments or municipalities):
            raise CommandError('El schema origen no tiene datos para copiar.')

        for schema in targets:
            self.stdout.write(self.style.MIGRATE_HEADING(f'== Destino "{schema}" =='))
            with schema_context(schema):
                try:
                    with transaction.atomic():
                        self.copy(doc_types, departments, municipalities, dept_code_by_id, options['dry_run'])
                        if options['dry_run']:
                            transaction.set_rollback(True)
                except Exception as exc:
                    raise CommandError(f'Falló en "{schema}" (se revirtió): {exc}')

    def copy(self, doc_types, departments, municipalities, dept_code_by_id, dry):
        prefix = '[simulación] ' if dry else ''

        created = self._copy_rows(DocumentType, doc_types, 'code')
        self.stdout.write(f'  {prefix}tipos de documento nuevos: {created}')

        created = self._copy_rows(Departamento, departments, 'codigo')
        self.stdout.write(f'  {prefix}departamentos nuevos: {created}')

        dept_id_by_code = dict(Departamento.objects.values_list('codigo', 'id'))
        rows = []
        for m in municipalities:
            row = dict(m)
            row['departamento_id'] = dept_id_by_code[dept_code_by_id[m['departamento_id']]]
            rows.append(row)
        created = self._copy_rows(Municipio, rows, 'codigo')
        self.stdout.write(f'  {prefix}municipios nuevos: {created}')

    def _copy_rows(self, model, rows, key):
        existing_keys = set(model.objects.values_list(key, flat=True))
        used_ids = set(model.objects.values_list('id', flat=True))
        new_objects = []
        for row in rows:
            if row[key] in existing_keys:
                continue
            data = dict(row)
            if data['id'] in used_ids:
                data.pop('id')
            else:
                used_ids.add(data['id'])
            new_objects.append(model(**data))
        # Con id explícito se inserta tal cual; los que perdieron su id usan la secuencia.
        with_id = [o for o in new_objects if o.id is not None]
        without_id = [o for o in new_objects if o.id is None]
        model.objects.bulk_create(with_id)
        # Los ids se insertaron explícitos: se alinea la secuencia para que los siguientes registros no choquen.
        with connection.cursor() as cursor:
            for sql in connection.ops.sequence_reset_sql(self.style, [model]):
                cursor.execute(sql)
        model.objects.bulk_create(without_id)
        return len(new_objects)
