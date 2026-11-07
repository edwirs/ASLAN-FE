"""Exportar e importar productos y servicios en Excel (migración masiva del catálogo).

El stock inicial de todo producto importado es 0: el inventario se carga después (compras, ajustes). Lo que sí se
define en el archivo es si cada fila es un producto o un servicio (sin inventario). La exportación usa las mismas
columnas que la plantilla, más el stock actual como dato informativo (la importación lo ignora).
"""
from django import forms
from django.db import transaction
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from core.pos.excel_utils import (MAX_FILE_SIZE, MAX_ROWS, YES_NO, ImportFileError, normalize, parse_money, put,
                                  read_rows as read_sheet_rows, style_header, to_bytes, yes_no)
from core.pos.forms import ProductForm
from core.pos.models import Category, Product
from core.pos.units import DECIMAL_UNITS, DEFAULT_UNIT, STANDARD_UNITS, canonical_unit

SHEET_PRODUCTS = 'Productos'
SHEET_CATEGORIES = 'Categorías'
DEFAULT_CATEGORY = 'SERVICIOS'   # se crea sola cuando no existe ninguna categoría

# (clave, encabezado, obligatorio, ancho, columna de texto)
COLUMNS = (
    ('code', 'Código *', True, 16, True),
    ('name', 'Nombre *', True, 36, False),
    ('category', 'Categoría *', True, 24, False),
    ('barcode', 'Código de barras', False, 22, True),
    ('description', 'Descripción', False, 36, False),
    ('price', 'Precio de compra', False, 16, False),
    ('pvp', 'Precio de venta', False, 16, False),
    ('is_service', '¿Es servicio? (Sí/No)', False, 20, False),
    ('with_tax', '¿Cobra impuesto? (Sí/No)', False, 24, False),
    ('unit_name', 'Unidad de medida', False, 18, False),
    ('allow_decimals', '¿Permite decimales? (Sí/No)', False, 26, False),
    ('min_stock', 'Stock mínimo', False, 14, False),
    ('is_active', 'Activo (Sí/No)', False, 16, False),
)
REQUIRED = [c[0] for c in COLUMNS if c[2]]
YES_NO_KEYS = ('is_service', 'with_tax', 'allow_decimals', 'is_active')
FIELD_LABELS = {
    'code': 'Código', 'name': 'Nombre', 'category': 'Categoría', 'barcode': 'Código de barras',
    'description': 'Descripción', 'price': 'Precio de compra', 'pvp': 'Precio de venta', 'unit_name': 'Unidad de medida',
    'min_stock': 'Stock mínimo', 'stock': 'Stock',
}
STOCK_HEADER = 'Stock actual (solo informativo)'


def ensure_default_category():
    """Para importar hace falta al menos una categoría: si no existe ninguna se crea «SERVICIOS». True si la creó."""
    if Category.objects.exists():
        return False
    Category.objects.create(name=DEFAULT_CATEGORY)
    return True


# --------------------------------------------------------------------------------------------------
# Plantilla
# --------------------------------------------------------------------------------------------------
def build_template():
    ensure_default_category()
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET_PRODUCTS
    style_header(ws, [(c[1], c[2]) for c in COLUMNS])
    for index, (_, _, _, width, as_text) in enumerate(COLUMNS, start=1):
        letter = get_column_letter(index)
        ws.column_dimensions[letter].width = width
        if as_text:
            ws.column_dimensions[letter].number_format = '@'

    # Listas (hoja oculta) para los desplegables
    lists = wb.create_sheet('Listas')
    categories = list(Category.objects.order_by('name').values_list('name', flat=True))
    columns = {'A': ('Sí/No', [label for _, label in YES_NO]), 'B': ('Unidad', list(STANDARD_UNITS)),
               'C': ('Categoría', categories)}
    for letter, (title, values) in columns.items():
        lists[f'{letter}1'] = title
        for offset, value in enumerate(values, start=2):
            lists[f'{letter}{offset}'] = value
    lists.sheet_state = 'hidden'

    keys = [c[0] for c in COLUMNS]
    last = MAX_ROWS + 1
    targets = [(key, 'A') for key in YES_NO_KEYS] + [('unit_name', 'B'), ('category', 'C')]
    for key, letter in targets:
        size = len(columns[letter][1]) + 1
        is_category = key == 'category'
        # La categoría debe existir: el desplegable es estricto. Las demás listas solo avisan.
        validation = DataValidation(type='list', formula1=f'=Listas!${letter}$2:${letter}${size}', allow_blank=True,
                                    errorStyle='stop' if is_category else 'warning',
                                    errorTitle='Categoría no válida' if is_category else 'Valor no reconocido',
                                    error='Elija una categoría de la lista (hoja «Categorías»). Si necesita otra, '
                                          'créela antes en Bodega → Categorías.' if is_category
                                          else 'Elija un valor de la lista.')
        ws.add_data_validation(validation)
        col = get_column_letter(keys.index(key) + 1)
        validation.add(f'{col}2:{col}{last}')

    # Hoja visible con las categorías que existen, para consultarlas mientras se llena la plantilla
    names = wb.create_sheet(SHEET_CATEGORIES)
    style_header(names, [('Categorías disponibles', False), ('Descripción', False)])
    names.column_dimensions['A'].width = 34
    names.column_dimensions['B'].width = 60
    for row, (name, description) in enumerate(Category.objects.order_by('name').values_list('name', 'description'), start=2):
        names.cell(row=row, column=1, value=name)
        names.cell(row=row, column=2, value=description or '')

    guide = wb.create_sheet('Instrucciones')
    guide.column_dimensions['A'].width = 30
    guide.column_dimensions['B'].width = 92
    rows = [
        ('IMPORTAR PRODUCTOS Y SERVICIOS', ''),
        ('', ''),
        ('Cómo usar', 'Llene la hoja «Productos» (una fila por producto o servicio), guarde el archivo y súbalo en '
                       'Productos → ⚙ → Importar.'),
        ('Obligatorios', 'Los encabezados en rojo (con *): código, nombre y categoría.'),
        ('Stock inicial', 'Todos los productos se crean con stock 0. Las cantidades se cargan después con una compra o '
                          'un ajuste de inventario.'),
        ('¿Es servicio?', 'Sí = servicio, sin inventario (no descuenta stock al vender). No = producto con inventario. '
                          'Vacío = No.'),
        ('Categoría', 'Debe ser una de las categorías de la hoja «Categorías» (también en la lista desplegable). '
                      'Si necesita otra, créela antes en Bodega → Categorías y descargue la plantilla de nuevo. '
                      'Las filas con una categoría que no exista no se importan.'),
        ('Precios', 'Números sin el símbolo $ y sin separador de miles, por ejemplo 12500 o 12500,50. '
                    'Precio de venta vacío = 0.'),
        ('¿Cobra impuesto?', 'Sí o No. Vacío = Sí.'),
        ('Unidad de medida', 'Unidad, Kilo, Litro, Caja... (lista desplegable). Vacío = Unidad.'),
        ('¿Permite decimales?', 'Sí si se vende en fracciones (0,5 kilo). Vacío: Sí cuando la unidad es Kilo, Libra, '
                                'Litro, Metro, etc.; en los demás casos No.'),
        ('Stock mínimo', 'Opcional. Cantidad bajo la cual el producto se marca como «bajo» en los reportes.'),
        ('Activo', 'Sí o No. Vacío = Sí.'),
        ('Productos que ya existen', 'Si el código ya está registrado, esa fila se omite (no se modifica nada).'),
        ('Código de barras', 'Opcional, pero no puede repetirse entre productos.'),
        ('No incluye', 'Imágenes ni presentaciones (cajas, six pack, variantes): se agregan luego editando el producto.'),
        ('Límites', f'Hasta {MAX_ROWS} productos por archivo y {MAX_FILE_SIZE // (1024 * 1024)} MB.'),
        ('No cambie', 'El nombre de la hoja «Productos» ni los encabezados de la primera fila.'),
    ]
    for index, (left, right) in enumerate(rows, start=1):
        guide.cell(row=index, column=1, value=left).font = Font(bold=True)
        guide.cell(row=index, column=2, value=right).alignment = Alignment(wrap_text=True, vertical='top')
    guide['A1'].font = Font(bold=True, size=14)
    return to_bytes(wb)


# --------------------------------------------------------------------------------------------------
# Exportación
# --------------------------------------------------------------------------------------------------
def build_export():
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET_PRODUCTS
    headers = [(c[1], c[2]) for c in COLUMNS] + [(STOCK_HEADER, False)]
    style_header(ws, headers)
    for index, column in enumerate(COLUMNS, start=1):
        ws.column_dimensions[get_column_letter(index)].width = column[3]
    ws.column_dimensions[get_column_letter(len(COLUMNS) + 1)].width = 28

    def sino(value):
        return 'Sí' if value else 'No'

    for row, product in enumerate(Product.objects.select_related('category').order_by('name', 'id'), start=2):
        values = {
            'code': product.code, 'name': product.name, 'category': product.category.name,
            'barcode': product.barcode or '', 'description': product.description or '',
            'price': float(product.price), 'pvp': float(product.pvp), 'is_service': sino(product.is_service),
            'with_tax': sino(product.with_tax), 'unit_name': product.unit_name or DEFAULT_UNIT,
            'allow_decimals': sino(product.allow_decimals),
            'min_stock': float(product.min_stock) if product.min_stock is not None else '',
            'is_active': sino(product.is_active),
        }
        for col, (key, _h, _r, _w, as_text) in enumerate(COLUMNS, start=1):
            cell = put(ws, row, col, values[key])
            if as_text:
                cell.number_format = '@'
        put(ws, row, len(COLUMNS) + 1, float(product.stock) if not product.is_service else '')
    return to_bytes(wb)


# --------------------------------------------------------------------------------------------------
# Importación
# --------------------------------------------------------------------------------------------------
def read_rows(uploaded):
    return read_sheet_rows(uploaded, COLUMNS, SHEET_PRODUCTS)


class Catalogs:
    """Categorías, códigos y códigos de barras existentes, cargados una sola vez."""

    def __init__(self):
        self.categories = {normalize(c.name): c for c in Category.objects.all()}
        self.codes = set(Product.objects.values_list('code', flat=True))
        self.barcodes = set(Product.objects.exclude(barcode__isnull=True).exclude(barcode='')
                            .values_list('barcode', flat=True))

    def category(self, name):
        """La categoría con ese nombre (sin importar mayúsculas ni tildes); si no existe, la fila no se importa."""
        found = self.categories.get(normalize(name))
        if found is None:
            available = sorted(c.name for c in self.categories.values())
            shown = ', '.join(available[:8]) + (f' y {len(available) - 8} más' if len(available) > 8 else '')
            raise ValueError(f'La categoría «{name}» no existe. Categorías disponibles: {shown}.')
        return found


def form_errors(form):
    return ' | '.join(f'{FIELD_LABELS.get(field, field)}: ' + ' '.join(errors) for field, errors in form.errors.items())


def import_row(record, catalogs):
    """Valida y crea un producto o servicio con stock 0. Lanza ValueError con el motivo si la fila no sirve."""
    for key in REQUIRED:
        if record.get(key, '') == '':
            header = next(h for k, h, *_ in COLUMNS if k == key).replace(' *', '')
            raise ValueError(f'Falta «{header}».')

    is_service = yes_no(record.get('is_service', ''), False, '«¿Es servicio?»')
    with_tax = yes_no(record.get('with_tax', ''), True, '«¿Cobra impuesto?»')
    is_active = yes_no(record.get('is_active', ''), True, '«Activo»')
    unit = canonical_unit(str(record.get('unit_name', ''))) or DEFAULT_UNIT
    allow_decimals = yes_no(record.get('allow_decimals', ''), unit in DECIMAL_UNITS, '«¿Permite decimales?»')
    price = parse_money(record['price'], 'El precio de compra') if record.get('price', '') != '' else 0
    pvp = parse_money(record['pvp'], 'El precio de venta') if record.get('pvp', '') != '' else 0
    min_stock = ''
    if record.get('min_stock', '') != '' and not is_service:
        min_stock = parse_money(record['min_stock'], 'El stock mínimo')

    barcode = str(record.get('barcode', ''))
    if barcode and barcode in catalogs.barcodes:
        raise ValueError(f'El código de barras «{barcode}» ya pertenece a otro producto.')

    data = {
        'code': str(record['code']), 'name': str(record['name']), 'barcode': barcode,
        'description': str(record.get('description', '')), 'price': price, 'pvp': pvp,
        'stock': '0',   # el stock inicial siempre es 0; el inventario se carga después
        'unit_name': unit, 'min_stock': min_stock, 'presentation_mode': '',
    }
    for key, value in (('is_service', is_service), ('with_tax', with_tax), ('is_active', is_active),
                       ('allow_decimals', allow_decimals and not is_service)):
        if value:
            data[key] = 'on'   # una casilla ausente en el formulario se guarda como «no»

    data['category'] = catalogs.category(str(record['category'])).pk
    form = ProductForm(data)
    if not form.is_valid():
        raise ValueError(form_errors(form))
    with transaction.atomic():
        product = forms.ModelForm.save(form)   # ProductForm.save() está personalizado y devuelve un diccionario
    return product


def import_products(uploaded):
    """Importa los productos del archivo. Las filas válidas se crean; las demás se informan con su motivo."""
    rows = read_rows(uploaded)
    default_created = ensure_default_category()
    catalogs = Catalogs()
    seen_codes, seen_barcodes = {}, {}
    created, skipped, errors = 0, [], []
    for number, record in rows:
        code = str(record.get('code', ''))
        if code and code in seen_codes:
            errors.append({'row': number, 'dni': code, 'message': f'Código repetido en el archivo (también en la fila {seen_codes[code]}).'})
            continue
        if code:
            seen_codes[code] = number
        if code and code in catalogs.codes:
            skipped.append({'row': number, 'dni': code, 'message': 'Ya existe un producto con este código.'})
            continue
        barcode = str(record.get('barcode', ''))
        if barcode and barcode in seen_barcodes:
            errors.append({'row': number, 'dni': code, 'message': f'Código de barras repetido en el archivo (también en la fila {seen_barcodes[barcode]}).'})
            continue
        try:
            import_row(record, catalogs)
        except ValueError as e:
            errors.append({'row': number, 'dni': code, 'message': str(e)})
            continue
        except Exception:
            errors.append({'row': number, 'dni': code, 'message': 'No se pudo guardar esta fila.'})
            continue
        if barcode:
            seen_barcodes[barcode] = number
            catalogs.barcodes.add(barcode)
        catalogs.codes.add(code)
        created += 1
    notes = []
    if default_created:
        notes.append(f'No había categorías: se creó «{DEFAULT_CATEGORY}».')
    return {'total': len(rows), 'created': created, 'skipped': skipped, 'errors': errors, 'notes': notes}
