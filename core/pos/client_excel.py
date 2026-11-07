"""Exportar e importar clientes en Excel (migración masiva de clientes).

La plantilla, la exportación y la importación comparten las mismas columnas (``COLUMNS``), así que lo exportado
se puede volver a importar. Cada cliente lleva UN solo contacto en estas hojas; la exportación agrega además una
hoja «Contactos» con todos los contactos que tenga cada cliente.
"""
from datetime import date, datetime

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from core.pos.choices import GENDER, PERSON_TYPE, TAX_RESPONSIBILITY
from core.pos.excel_utils import (ALLOWED_EXTENSIONS, MAX_FILE_SIZE, MAX_ROWS, ImportFileError, choice, normalize, put,
                                  style_header, to_bytes)
from core.pos.excel_utils import read_rows as read_sheet_rows
from core.pos.forms import ClientForm
from core.pos.models import Client, ClientContact, DocumentType, Municipio

SHEET_CLIENTS = 'Clientes'
SHEET_CONTACTS = 'Contactos'

# (clave, encabezado, obligatorio, ancho, columna de texto)
# «Texto» evita que Excel quite ceros a la izquierda o convierta documentos y teléfonos en números.
COLUMNS = (
    ('document_type', 'Tipo de documento *', True, 18, True),
    ('dni', 'Número de documento *', True, 22, True),
    ('dv', 'DV', False, 6, True),
    ('person_type', 'Tipo de persona', False, 18, False),
    ('tax_responsibility', 'Responsabilidad tributaria', False, 26, False),
    ('names', 'Nombre o razón social *', True, 36, False),
    ('commercial_name', 'Nombre comercial', False, 28, False),
    ('gender', 'Género', False, 12, False),
    ('birthdate', 'Fecha de nacimiento (AAAA-MM-DD)', False, 30, True),
    ('country', 'País', False, 14, False),
    ('municipality', 'Municipio (código DANE)', False, 22, True),
    ('address', 'Dirección', False, 32, False),
    ('mobile', 'Teléfono', False, 14, True),
    ('email', 'Correo electrónico', False, 28, False),
    ('contact_names', 'Contacto: nombre', False, 26, False),
    ('contact_email', 'Contacto: correo', False, 28, False),
    ('contact_position', 'Contacto: cargo', False, 20, False),
    ('contact_phone', 'Contacto: teléfono', False, 18, True),
)
REQUIRED = [c[0] for c in COLUMNS if c[2]]
CONTACT_KEYS = ('contact_names', 'contact_email', 'contact_position', 'contact_phone')
FIELD_LABELS = {
    'document_type': 'Tipo de documento', 'dni': 'Número de documento', 'dv': 'DV', 'person_type': 'Tipo de persona',
    'tax_responsibility': 'Responsabilidad tributaria', 'names': 'Nombre o razón social',
    'commercial_name': 'Nombre comercial', 'gender': 'Género', 'birthdate': 'Fecha de nacimiento', 'country': 'País',
    'municipality': 'Municipio', 'address': 'Dirección', 'mobile': 'Teléfono', 'email': 'Correo electrónico',
}

# --------------------------------------------------------------------------------------------------
# Plantilla
# --------------------------------------------------------------------------------------------------
def build_template():
    """Libro vacío con encabezados, listas desplegables, instrucciones y el listado de municipios."""
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET_CLIENTS
    style_header(ws, [(c[1], c[2]) for c in COLUMNS])
    for index, (_, _, _, width, as_text) in enumerate(COLUMNS, start=1):
        letter = get_column_letter(index)
        ws.column_dimensions[letter].width = width
        if as_text:
            ws.column_dimensions[letter].number_format = '@'

    # Listas (hoja oculta) para los desplegables
    lists = wb.create_sheet('Listas')
    document_types = list(DocumentType.objects.filter(is_active=True).order_by('id'))
    columns = {
        'A': ('Tipo de documento', [d.abbreviation for d in document_types]),
        'B': ('Tipo de persona', [label for _, label in PERSON_TYPE]),
        'C': ('Responsabilidad tributaria', [label for _, label in TAX_RESPONSIBILITY]),
        'D': ('Género', [label for _, label in GENDER]),
    }
    for letter, (title, values) in columns.items():
        lists[f'{letter}1'] = title
        for offset, value in enumerate(values, start=2):
            lists[f'{letter}{offset}'] = value
    lists.sheet_state = 'hidden'

    last = MAX_ROWS + 1
    for key, letter in (('document_type', 'A'), ('person_type', 'B'), ('tax_responsibility', 'C'), ('gender', 'D')):
        size = len(columns[letter][1]) + 1
        validation = DataValidation(type='list', formula1=f'=Listas!${letter}$2:${letter}${size}', allow_blank=True,
                                    errorStyle='warning', errorTitle='Valor no reconocido',
                                    error='Elija un valor de la lista.')
        ws.add_data_validation(validation)
        position = [c[0] for c in COLUMNS].index(key) + 1
        validation.add(f'{get_column_letter(position)}2:{get_column_letter(position)}{last}')

    # Instrucciones
    guide = wb.create_sheet('Instrucciones')
    guide.column_dimensions['A'].width = 34
    guide.column_dimensions['B'].width = 90
    rows = [
        ('IMPORTAR CLIENTES', ''),
        ('', ''),
        ('Cómo usar', 'Llene la hoja «Clientes» (una fila por cliente), guarde el archivo y súbalo en Clientes → '
                       'Configuraciones adicionales → Importar.'),
        ('Obligatorios', 'Los encabezados en rojo (con *): tipo de documento, número de documento y nombre o razón social.'),
        ('Contacto', 'Cada cliente admite UN solo contacto en esta plantilla (nombre, correo, cargo y teléfono). '
                     'Si pone nombre o correo del contacto, ambos son obligatorios.'),
        ('Tipo de documento', 'Acrónimo o código DIAN, por ejemplo CC, NIT o 13, 31. Está en la lista desplegable.'),
        ('Tipo de persona', 'Persona Natural o Persona Jurídica. Si lo deja vacío: Persona Natural.'),
        ('Responsabilidad tributaria', 'No responsable de IVA o Responsable de IVA. Si lo deja vacío: No responsable de IVA.'),
        ('Género', 'Masculino o Femenino. Si lo deja vacío: Masculino.'),
        ('Fecha de nacimiento', 'AAAA-MM-DD, por ejemplo 1990-05-31. Si lo deja vacío se usa la fecha de hoy.'),
        ('País', 'Si lo deja vacío: Colombia.'),
        ('Municipio', 'Código DANE de la hoja «Municipios», por ejemplo 05001 (también se acepta '
                      '«Departamento - Municipio»).'),
        ('Teléfono', 'Máximo 10 caracteres. El correo, máximo 50.'),
        ('Clientes que ya existen', 'Si el número de documento ya está registrado, esa fila se omite (no se modifica nada).'),
        ('Límites', f'Hasta {MAX_ROWS} clientes por archivo y {MAX_FILE_SIZE // (1024 * 1024)} MB.'),
        ('No cambie', 'El nombre de la hoja «Clientes» ni los encabezados de la primera fila.'),
    ]
    for index, (left, right) in enumerate(rows, start=1):
        guide.cell(row=index, column=1, value=left).font = Font(bold=True)
        guide.cell(row=index, column=2, value=right).alignment = Alignment(wrap_text=True, vertical='top')
    guide['A1'].font = Font(bold=True, size=14)

    # Municipios (para buscar el código)
    towns = wb.create_sheet('Municipios')
    style_header(towns, [('Código', False), ('Municipio', False), ('Departamento', False)])
    towns.column_dimensions['A'].width = 12
    towns.column_dimensions['B'].width = 34
    towns.column_dimensions['C'].width = 28
    towns.column_dimensions['A'].number_format = '@'
    for row, (code, name, dept) in enumerate(
            Municipio.objects.select_related('departamento').order_by('departamento__nombre', 'nombre')
            .values_list('codigo', 'nombre', 'departamento__nombre'), start=2):
        towns.cell(row=row, column=1, value=code)
        towns.cell(row=row, column=2, value=name)
        towns.cell(row=row, column=3, value=dept)
    return to_bytes(wb)


# --------------------------------------------------------------------------------------------------
# Exportación
# --------------------------------------------------------------------------------------------------
def build_export():
    """Todos los clientes con las mismas columnas de la plantilla, más una hoja con todos sus contactos."""
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET_CLIENTS
    style_header(ws, [(c[1], c[2]) for c in COLUMNS])
    for index, (_, _, _, width, as_text) in enumerate(COLUMNS, start=1):
        ws.column_dimensions[get_column_letter(index)].width = width

    person = dict(PERSON_TYPE)
    tax = dict(TAX_RESPONSIBILITY)
    gender = dict(GENDER)
    clients = (Client.objects.select_related('document_type', 'municipality').prefetch_related('contacts')
               .order_by('names', 'id'))
    contacts_ws = wb.create_sheet(SHEET_CONTACTS)
    style_header(contacts_ws, [(h, False) for h in ('Número de documento', 'Cliente', 'Contacto: nombre',
                                                    'Contacto: correo', 'Contacto: cargo', 'Contacto: teléfono')])
    for letter, width in zip('ABCDEF', (22, 36, 28, 30, 22, 18)):
        contacts_ws.column_dimensions[letter].width = width

    row = contact_row = 1
    for client in clients:
        row += 1
        contacts = list(client.contacts.all())
        first = contacts[0] if contacts else None
        values = {
            'document_type': client.document_type.abbreviation if client.document_type else '',
            'dni': client.dni, 'dv': client.dv or '',
            'person_type': person.get(client.person_type, client.person_type),
            'tax_responsibility': tax.get(client.tax_responsibility, client.tax_responsibility),
            'names': client.names, 'commercial_name': client.commercial_name or '',
            'gender': gender.get(client.gender, client.gender),
            'birthdate': client.birthdate.strftime('%Y-%m-%d') if client.birthdate else '',
            'country': client.country, 'municipality': client.municipality.codigo if client.municipality else '',
            'address': client.address or '', 'mobile': client.mobile or '', 'email': client.email or '',
            'contact_names': first.names if first else '', 'contact_email': first.email if first else '',
            'contact_position': (first.position or '') if first else '', 'contact_phone': (first.phone or '') if first else '',
        }
        for col, (key, *_rest) in enumerate(COLUMNS, start=1):
            put(ws, row, col, values[key]).number_format = '@'
        for contact in contacts:
            contact_row += 1
            for col, value in enumerate((client.dni, client.names, contact.names, contact.email,
                                         contact.position or '', contact.phone or ''), start=1):
                put(contacts_ws, contact_row, col, value).number_format = '@'
    return to_bytes(wb)


# --------------------------------------------------------------------------------------------------
# Importación
# --------------------------------------------------------------------------------------------------
def read_rows(uploaded):
    return read_sheet_rows(uploaded, COLUMNS, SHEET_CLIENTS)


def parse_date(value):
    if isinstance(value, date):
        return value
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(str(value), fmt).date()
        except ValueError:
            continue
    raise ValueError('La fecha de nacimiento debe tener el formato AAAA-MM-DD.')


class Catalogs:
    """Catálogos y documentos existentes, cargados una sola vez para validar miles de filas sin consultar cada vez."""

    def __init__(self):
        self.documents = {}
        for d in DocumentType.objects.filter(is_active=True):
            for key in (d.abbreviation, d.code, d.name):
                self.documents[normalize(key)] = d
        self.towns_by_code = {}
        self.towns_by_label = {}
        self.towns_by_name = {}
        for m in Municipio.objects.select_related('departamento'):
            self.towns_by_code[normalize(m.codigo)] = m
            self.towns_by_label[normalize(f'{m.departamento.nombre} {m.nombre}')] = m
            self.towns_by_name.setdefault(normalize(m.nombre), []).append(m)
        self.existing = set(Client.objects.values_list('dni', flat=True))

    def town(self, value):
        key = normalize(value)
        found = self.towns_by_code.get(key) or self.towns_by_label.get(key)
        if found:
            return found
        by_name = self.towns_by_name.get(key, [])
        if len(by_name) == 1:
            return by_name[0]
        if len(by_name) > 1:
            raise ValueError(f'El municipio «{value}» existe en varios departamentos; use su código DANE.')
        raise ValueError(f'El municipio «{value}» no existe; use el código DANE de la hoja «Municipios».')


def form_errors(form):
    parts = []
    for field, errors in form.errors.items():
        label = FIELD_LABELS.get(field, field)
        parts.append(f'{label}: ' + ' '.join(errors))
    return ' | '.join(parts)


def import_row(record, catalogs):
    """Valida y crea un cliente (y su contacto). Lanza ValueError con el motivo si la fila no sirve."""
    for key in REQUIRED:
        if record.get(key, '') == '':
            header = next(h for k, h, *_ in COLUMNS if k == key).replace(' *', '')
            raise ValueError(f'Falta «{header}».')

    document = catalogs.documents.get(normalize(record['document_type']))
    if document is None:
        raise ValueError(f'Tipo de documento «{record["document_type"]}» no válido; use un acrónimo como CC o NIT.')

    contact = {k: str(record.get(k, '')) for k in CONTACT_KEYS}
    if contact['contact_names'] or contact['contact_email']:
        if not contact['contact_names'] or not contact['contact_email']:
            raise ValueError('El contacto necesita nombre y correo (o deje ambos vacíos).')
        try:
            validate_email(contact['contact_email'])
        except ValidationError:
            raise ValueError(f'El correo del contacto «{contact["contact_email"]}» no es válido.')

    email = str(record.get('email', ''))
    if email:
        try:
            validate_email(email)
        except ValidationError:
            raise ValueError(f'El correo «{email}» no es válido.')

    data = {
        'document_type': document.pk,
        'dni': str(record['dni']),
        'dv': str(record.get('dv', '')),
        'person_type': choice(record.get('person_type', ''), PERSON_TYPE, PERSON_TYPE[0][0], 'El tipo de persona'),
        'tax_responsibility': choice(record.get('tax_responsibility', ''), TAX_RESPONSIBILITY,
                                     TAX_RESPONSIBILITY[0][0], 'La responsabilidad tributaria'),
        'names': str(record['names']),
        'commercial_name': str(record.get('commercial_name', '')),
        'gender': choice(record.get('gender', ''), GENDER, GENDER[0][0], 'El género'),
        'birthdate': (parse_date(record['birthdate']) if record.get('birthdate', '') != '' else date.today()).isoformat(),
        'country': str(record.get('country', '')) or 'Colombia',
        'municipality': catalogs.town(str(record['municipality'])).pk if record.get('municipality', '') != '' else '',
        'address': str(record.get('address', '')),
        'mobile': str(record.get('mobile', '')),
        'email': email,
        'is_active': 'on',   # sin esto el formulario guardaría el cliente como inactivo
    }
    form = ClientForm(data)
    if not form.is_valid():
        raise ValueError(form_errors(form))

    with transaction.atomic():
        client = forms.ModelForm.save(form)   # ClientForm.save() está personalizado y devuelve un diccionario
        if contact['contact_names']:
            item = ClientContact(client=client, names=contact['contact_names'], email=contact['contact_email'],
                                 position=contact['contact_position'] or None, phone=contact['contact_phone'] or None)
            try:
                item.full_clean()
            except ValidationError as e:
                raise ValueError('Contacto: ' + ' '.join(m for msgs in e.message_dict.values() for m in msgs))
            item.save()
    return client


def import_clients(uploaded):
    """Importa los clientes del archivo. Las filas válidas se crean; las demás se informan con su motivo."""
    rows = read_rows(uploaded)
    catalogs = Catalogs()
    seen = {}
    created, skipped, errors = 0, [], []
    for number, record in rows:
        dni = str(record.get('dni', ''))
        if dni and dni in seen:
            errors.append({'row': number, 'dni': dni, 'message': f'Documento repetido en el archivo (también en la fila {seen[dni]}).'})
            continue
        if dni:
            seen[dni] = number
        if dni and dni in catalogs.existing:
            skipped.append({'row': number, 'dni': dni, 'message': 'Ya existe un cliente con este documento.'})
            continue
        try:
            import_row(record, catalogs)
        except ValueError as e:
            errors.append({'row': number, 'dni': dni, 'message': str(e)})
            continue
        except Exception:
            errors.append({'row': number, 'dni': dni, 'message': 'No se pudo guardar esta fila.'})
            continue
        catalogs.existing.add(dni)
        created += 1
    return {'total': len(rows), 'created': created, 'skipped': skipped, 'errors': errors}
