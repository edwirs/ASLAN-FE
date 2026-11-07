"""Piezas comunes de las importaciones y exportaciones de Excel (clientes, productos...).

Cada módulo define sus columnas como tuplas ``(clave, encabezado, obligatorio, ancho, texto)`` y aquí se resuelve
lo que no cambia: validar y leer el archivo (.xlsx / .xls), emparejar encabezados, escribir celdas de forma segura
y convertir valores de las celdas.
"""
import io
import math
import os
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill

ALLOWED_EXTENSIONS = ('.xlsx', '.xls')
MAX_FILE_SIZE = 5 * 1024 * 1024
MAX_ROWS = 5000

HEADER_FILL = PatternFill('solid', fgColor='1F4E79')
REQUIRED_FILL = PatternFill('solid', fgColor='C0392B')
HEADER_FONT = Font(bold=True, color='FFFFFF')


class ImportFileError(Exception):
    """El archivo no se puede leer; el mensaje es apto para mostrarse al usuario."""


def normalize(text):
    """Minúsculas, sin tildes, sin lo que va entre paréntesis ni signos: para comparar encabezados y valores."""
    text = unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode()
    text = re.sub(r'\(.*?\)', '', text.lower())
    return re.sub(r'[^a-z0-9]+', '', text)


def put(ws, row, col, value):
    """Escribe un valor como texto seguro: un texto que empiece por «=» nunca se guarda como fórmula."""
    cell = ws.cell(row=row, column=col, value=value)
    if isinstance(value, str) and value[:1] in ('=', '+', '-', '@'):
        cell.data_type = 's'
    return cell


def style_header(ws, headers):
    """Primera fila con los encabezados: azul, y rojo los obligatorios. ``headers``: [(texto, obligatorio)]."""
    for index, (header, required) in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=index, value=header)
        cell.font = HEADER_FONT
        cell.fill = REQUIRED_FILL if required else HEADER_FILL
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    ws.row_dimensions[1].height = 32
    ws.freeze_panes = 'A2'


def to_bytes(workbook):
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def clean(value):
    """Valor de una celda: '' si está vacía, date si es fecha, texto sin decimales sobrantes en lo demás."""
    if value is None or (isinstance(value, float) and math.isnan(value)) or value is pd.NaT:
        return ''
    if isinstance(value, (datetime, date)):
        return value.date() if isinstance(value, datetime) else value
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def read_rows(uploaded, columns, sheet_name):
    """Lee la hoja del archivo (.xlsx o .xls) y devuelve [(n° de fila en Excel, {clave: valor})].

    Valida extensión, tamaño y contenido real del archivo; los encabezados se emparejan sin importar mayúsculas,
    tildes ni asteriscos, y se ignoran las columnas que el módulo no conoce.
    """
    name = (getattr(uploaded, 'name', '') or '').lower()
    extension = os.path.splitext(name)[1]
    if extension not in ALLOWED_EXTENSIONS:
        raise ImportFileError('El archivo debe ser de Excel (.xlsx o .xls).')
    if uploaded.size > MAX_FILE_SIZE:
        raise ImportFileError(f'El archivo supera el máximo de {MAX_FILE_SIZE // (1024 * 1024)} MB.')
    signature = uploaded.read(8)
    uploaded.seek(0)
    if extension == '.xlsx' and not signature.startswith(b'PK'):
        raise ImportFileError('El archivo no es un .xlsx válido. Descargue la plantilla y vuelva a intentarlo.')
    if extension == '.xls' and not signature.startswith(b'\xd0\xcf\x11\xe0'):
        raise ImportFileError('El archivo no es un .xls válido. Descargue la plantilla y vuelva a intentarlo.')

    try:
        book = pd.ExcelFile(uploaded, engine='openpyxl' if extension == '.xlsx' else 'xlrd')
        sheet = sheet_name if sheet_name in book.sheet_names else book.sheet_names[0]
        frame = book.parse(sheet, dtype=object, header=0)
    except Exception:
        raise ImportFileError('No se pudo leer el archivo. Verifique que no esté dañado ni protegido con contraseña.')

    header_to_key = {normalize(header): key for key, header, *_ in columns}
    positions = {}
    for position, header in enumerate(frame.columns):
        key = header_to_key.get(normalize(header))
        if key and key not in positions:
            positions[key] = position
    missing = [header for key, header, required, *_ in columns if required and key not in positions]
    if missing:
        raise ImportFileError('Faltan columnas en el archivo: ' + ', '.join(missing) +
                              '. Use la plantilla descargada sin cambiar los encabezados.')
    if len(frame) > MAX_ROWS:
        raise ImportFileError(f'El archivo tiene {len(frame)} filas; el máximo es {MAX_ROWS} por importación.')

    rows = []
    for index, values in enumerate(frame.itertuples(index=False, name=None)):
        record = {key: clean(values[position]) for key, position in positions.items()}
        if any(v != '' for v in record.values()):
            rows.append((index + 2, record))   # fila 1 = encabezados
    return rows


def choice(value, options, default, label):
    """Devuelve el código de la opción cuyo código o nombre coincide con el texto (vacío = valor por defecto)."""
    if value == '':
        return default
    wanted = normalize(value)
    for code, text in options:
        if wanted in (normalize(code), normalize(text)):
            return code
    raise ValueError(f'{label} «{value}» no es válido. Use: ' + ', '.join(text for _, text in options) + '.')


YES_NO = (('si', 'Sí'), ('no', 'No'))


def yes_no(value, default, label):
    """True/False desde Sí/No (también acepta 1/0, verdadero/falso, x). Vacío = valor por defecto."""
    if value == '':
        return default
    wanted = normalize(value)
    if wanted in ('si', 's', 'yes', 'y', '1', 'true', 'verdadero', 'x'):
        return True
    if wanted in ('no', 'n', '0', 'false', 'falso'):
        return False
    raise ValueError(f'{label} debe ser Sí o No (se recibió «{value}»).')


def parse_money(value, label):
    """Decimal desde una celda numérica o un texto como «1500», «1.500», «1.500,50», «1,500.50» o «$ 2.000»."""
    if isinstance(value, (int, float, Decimal)):
        number = Decimal(str(value))
    else:
        text = re.sub(r'[\s$]', '', str(value))
        if re.fullmatch(r'\d{1,3}(\.\d{3})+(,\d+)?', text):        # 1.500  /  1.500,50  (punto = miles)
            text = text.replace('.', '').replace(',', '.')
        elif re.fullmatch(r'\d{1,3}(,\d{3})+(\.\d+)?', text):      # 1,500  /  1,500.50  (coma = miles)
            text = text.replace(',', '')
        elif re.fullmatch(r'\d+,\d+', text):                       # 1500,50  (coma = decimales)
            text = text.replace(',', '.')
        try:
            number = Decimal(text)
        except InvalidOperation:
            raise ValueError(f'{label} «{value}» no es un número válido.')
    if number < 0:
        raise ValueError(f'{label} no puede ser negativo.')
    return number.quantize(Decimal('0.01'))
