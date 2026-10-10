"""Catálogo único de permisos y módulos de ASLAN FE.

Es la fuente de verdad de tres cosas, para que nunca se desincronicen:

1. ``PERMISSIONS``: permisos de cada modelo, con su descripción en español.
   Los modelos los leen en ``Meta.permissions`` (vía ``perms_for``).
2. ``MENU``: estructura del sidebar. Cada ítem declara qué permiso lo hace
   visible; un padre aparece solo si al menos un hijo es visible.
3. ``Item.perms``: permisos que se administran por módulo en la pantalla de
   roles (matriz módulo x acción).

Este archivo es solo datos: no importa modelos, para poder usarse desde
``models.py`` sin dependencias circulares.

Convención: ``view_*`` Ver, ``add_*`` Crear, ``change_*`` Editar,
``delete_*`` Eliminar, más las acciones propias de cada módulo.
Los codenames que ya existían se conservan para no perder las asignaciones de
los roles actuales; solo cambia la descripción (a español).
"""
from dataclasses import dataclass
from typing import Optional, Tuple

# Rol del sistema: siempre tiene todos los permisos y no se puede editar ni borrar.
ADMIN_ROLE_NAME = 'Administrador'

_VERBS = {'view': 'Ver', 'add': 'Crear', 'change': 'Editar', 'delete': 'Eliminar'}
_CRUD = ('view', 'add', 'change', 'delete')


def crud(suffix, plural, actions=_CRUD):
    """Permisos estándar de un modelo: [(codename, descripción), ...]."""
    return [(f'{a}_{suffix}', f'{_VERBS[a]} {plural}') for a in actions]


def crud_q(app, suffix, actions=_CRUD):
    """Mismos permisos de ``crud`` pero como nombres calificados ``app.codename``."""
    return tuple(f'{app}.{a}_{suffix}' for a in actions)


def q(app, *codenames):
    return tuple(f'{app}.{c}' for c in codenames)


# --------------------------------------------------------------------------
# Permisos por modelo ('app_label.NombreModelo' -> [(codename, descripción)])
# --------------------------------------------------------------------------
PERMISSIONS = {
    # Personas
    'pos.Client': crud('client', 'clientes') + [
        ('consult_dian_client', 'Consultar clientes en la DIAN'),
    ],
    'pos.Provider': crud('provider', 'proveedores'),

    # Bodega
    'pos.Category': crud('category', 'categorías'),
    'pos.Product': crud('product', 'productos'),
    'pos.ProductAutoAdd': crud('productautoadd', 'productos con descuento'),

    # Facturas
    'pos.Sale': [
        # Facturas (POS)
        ('view_sale', 'Ver facturas'),
        ('add_sale', 'Crear facturas'),
        ('delete_sale', 'Eliminar facturas'),
        ('delivered_sale', 'Marcar facturas como entregadas'),
        ('discounts_sale', 'Aplicar descuentos en facturas'),
        ('edit_sale_price', 'Editar el precio de venta (facturas y ventas rápidas)'),
        ('view_sale_client', 'Ver facturas por cliente'),
        # Facturas electrónicas
        ('view_electronic_invoice', 'Ver facturas electrónicas'),
        ('add_electronic_invoice', 'Crear facturas electrónicas'),
        ('delete_electronic_invoice', 'Eliminar facturas electrónicas'),
        ('print_electronic_invoice', 'Imprimir facturas electrónicas'),
        ('download_electronic_invoice_pdf', 'Ver y descargar el PDF de facturas electrónicas'),
        ('resend_electronic_invoice_email', 'Reenviar facturas electrónicas por correo'),
        # Operaciones
        ('add_bar', 'Registrar ventas rápidas (barra)'),
        ('list_employee', 'Preseleccionarse como empleado en las ventas rápidas'),
        # Reportes
        ('report_sales_menu', 'Ver reporte de ventas totales'),
        ('report_employee_menu', 'Ver reporte de ventas por empleado'),
        ('report_employee_debe', 'Ver deudas de empleados en reportes'),
        ('report_employee_gain', 'Ver ganancias de empleados en reportes'),
        ('sale_by_product', 'Ver reporte de ventas por producto'),
        ('report_inventory_value', 'Ver reporte de inventario valorizado'),
        ('report_restock', 'Ver reporte de reposición sugerida'),
        ('report_rotation', 'Ver reporte de rotación y productos sin movimiento'),
        ('view_report_costs', 'Ver costos, utilidades y valor del inventario en reportes'),
    ],
    'pos.CreditNote': [
        ('view_creditnote', 'Ver notas crédito'),
        ('add_creditnote', 'Crear notas crédito'),
        ('delete_creditnote', 'Eliminar notas crédito no validadas'),
        ('print_creditnote', 'Imprimir notas crédito'),
        ('download_creditnote_pdf', 'Ver y descargar el PDF de notas crédito'),
        ('resend_creditnote_email', 'Reenviar notas crédito por correo'),
    ],
    'pos.Price': [
        ('view_price', 'Ver cotizaciones'),
        ('add_price', 'Crear cotizaciones'),
        ('delete_price', 'Eliminar cotizaciones'),
        ('view_price_client', 'Ver cotizaciones por cliente'),
    ],

    # Operaciones
    'pos.Order': [
        ('view_order', 'Ver pedidos de mesas'),
        ('add_order', 'Crear pedidos de mesas'),
        ('delete_order', 'Eliminar pedidos de mesas'),
        ('view_kitchen_board', 'Ver el tablero de cocina'),
        ('mark_order_ready', 'Marcar pedidos como listos en cocina'),
    ],
    'pos.CashClosing': crud('cashclosing', 'cierres de caja', ('view', 'add')) + [
        ('print_cashclosing', 'Imprimir cierres de caja'),
    ],

    # Inventario
    'pos.Buy': [
        ('view_buy', 'Ver compras'),
        ('add_buy', 'Crear compras'),
        ('delete_buy', 'Eliminar compras'),
        ('view_buy_provider', 'Ver compras por proveedor'),
    ],
    'pos.InventoryGroup': crud('inventorygroup', 'grupos de inventario'),
    'pos.Expenses': [
        ('view_expenses', 'Ver gastos'),
        ('add_expenses', 'Crear gastos'),
        ('change_expenses', 'Editar gastos'),
        ('delete_expenses', 'Eliminar gastos'),
    ],
    'pos.SaleCreditPayment': [
        ('view_credit_report', 'Ver la cartera de créditos'),
        ('add_credit_payment', 'Registrar abonos a créditos'),
    ],

    # Nómina
    'pos.Employee': crud('employee', 'empleados'),
    'pos.EmployeeTransaction': crud('employee_transaction', 'transacciones de empleados') + [
        ('approve_employee_transaction', 'Aprobar transacciones de empleados'),
        ('pay_employee_transaction', 'Pagar transacciones de empleados'),
        ('report_employee_transaction', 'Ver reporte de transacciones de empleados'),
    ],
    'pos.Payroll': crud('payroll', 'nóminas', ('view', 'add')),

    # Configuraciones
    'pos.Company': [
        ('view_company', 'Ver los datos de la empresa'),
        ('change_company', 'Editar los datos de la empresa'),
    ],
    'pos.FactusCredential': crud('factuscredential', 'credenciales de Factus'),
    'security.Dashboard': [
        ('view_dashboard', 'Ver la configuración del dashboard'),
        ('change_dashboard', 'Editar la configuración del dashboard'),
    ],
    'pos.Table': crud('table', 'mesas'),

    # Seguridad
    'user.User': crud('user', 'usuarios'),
    'security.Role': crud('role', 'roles'),
    'security.UserAccess': [
        ('view_user_access', 'Ver accesos de usuarios'),
        ('delete_user_access', 'Eliminar accesos de usuarios'),
    ],
}


def perms_for(model_key):
    """Tupla para ``Meta.permissions`` del modelo ``'app.Modelo'``."""
    return tuple(PERMISSIONS[model_key])


# --------------------------------------------------------------------------
# Menú lateral / módulos
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Item:
    key: str
    label: str
    url_name: str
    # Permiso ``app.codename`` que hace visible el ítem; None = cualquier
    # usuario autenticado (p. ej. cambiar su propia contraseña).
    view_perm: Optional[str]
    # Permisos que se administran para este módulo en la matriz de roles.
    perms: Tuple[str, ...] = ()
    icon: str = 'far fa-circle'


@dataclass(frozen=True)
class Section:
    label: str
    icon: str
    children: tuple = ()


MENU = (
    Section('Personas', 'fas fa-users', (
        Item('clients', 'Clientes', 'client_list', 'pos.view_client',
             crud_q('pos', 'client') + q('pos', 'consult_dian_client')),
        Item('providers', 'Proveedores', 'provider_list', 'pos.view_provider',
             crud_q('pos', 'provider')),
    )),
    Section('Bodega', 'fas fa-boxes', (
        Item('categories', 'Categorías', 'category_list', 'pos.view_category',
             crud_q('pos', 'category')),
        Item('products', 'Productos', 'product_list', 'pos.view_product',
             crud_q('pos', 'product')),
        Item('productautoadd', 'Productos descuento', 'productautoadd_list', 'pos.view_productautoadd',
             crud_q('pos', 'productautoadd')),
    )),
    Section('Facturas', 'fas fa-file-invoice', (
        Item('sales', 'Facturas', 'sale_admin_list', 'pos.view_sale',
             q('pos', 'view_sale', 'add_sale', 'delete_sale', 'delivered_sale', 'discounts_sale', 'edit_sale_price',
               'view_sale_client')),
        Item('electronic_invoices', 'Facturas Electrónicas', 'sale_Fe_admin_list', 'pos.view_electronic_invoice',
             q('pos', 'view_electronic_invoice', 'add_electronic_invoice', 'delete_electronic_invoice',
               'print_electronic_invoice', 'download_electronic_invoice_pdf', 'resend_electronic_invoice_email')),
        Item('credit_notes', 'Notas Crédito', 'credit_note_Fe_admin_list', 'pos.view_creditnote',
             q('pos', 'view_creditnote', 'add_creditnote', 'delete_creditnote',
               'print_creditnote', 'download_creditnote_pdf', 'resend_creditnote_email')),
        Item('quotes', 'Cotizaciones', 'price_admin_list', 'pos.view_price',
             q('pos', 'view_price', 'add_price', 'delete_price', 'view_price_client')),
    )),
    Section('Operaciones', 'fas fa-utensils', (
        Item('quick_sales', 'Ventas Rápidas', 'bar_admin_create', 'pos.add_bar',
             q('pos', 'add_bar', 'list_employee')),
        Item('table_orders', 'Ventas Mesas', 'order_list', 'pos.view_order',
             q('pos', 'view_order', 'add_order', 'delete_order')),
        Item('kitchen', 'Cocina', 'kitchen_board', 'pos.view_kitchen_board',
             q('pos', 'view_kitchen_board', 'mark_order_ready')),
        Item('cash_closing', 'Cierre de caja', 'cashClosing_list', 'pos.view_cashclosing',
             crud_q('pos', 'cashclosing', ('view', 'add')) + q('pos', 'print_cashclosing')),
    )),
    Section('Inventario', 'fas fa-warehouse', (
        Item('purchases', 'Compras', 'buy_admin_list', 'pos.view_buy',
             q('pos', 'view_buy', 'add_buy', 'delete_buy', 'view_buy_provider')),
        Item('inventory_admin', 'Administrador Inventario', 'inventory_management', 'pos.view_inventorygroup',
             crud_q('pos', 'inventorygroup')),
        Item('expenses', 'Gastos', 'expenses_list', 'pos.view_expenses',
             crud_q('pos', 'expenses')),
        Item('credits', 'Créditos', 'sale_credit_report', 'pos.view_credit_report',
             q('pos', 'view_credit_report', 'add_credit_payment')),
    )),
    Section('Nómina', 'fas fa-hand-holding-usd', (
        Item('employees', 'Empleados', 'employee_list', 'pos.view_employee',
             crud_q('pos', 'employee')),
        Item('employee_transactions', 'Transacciones', 'employee_transaction_list',
             'pos.view_employee_transaction',
             crud_q('pos', 'employee_transaction') + q('pos', 'approve_employee_transaction',
                                                       'pay_employee_transaction',
                                                       'report_employee_transaction')),
        Item('payroll', 'Nóminas', 'payroll_list', 'pos.view_payroll',
             crud_q('pos', 'payroll', ('view', 'add'))),
    )),
    Section('Reportes', 'fas fa-chart-pie', (
        Item('report_sales', 'Totales', 'sale_report', 'pos.report_sales_menu',
             q('pos', 'report_sales_menu')),
        Item('report_employee_sales', 'Ventas Empleados', 'employee_sale_report', 'pos.report_employee_menu',
             q('pos', 'report_employee_menu', 'report_employee_debe', 'report_employee_gain')),
        Item('report_sales_by_product', 'Ventas X Producto', 'sale_by_product_report', 'pos.sale_by_product',
             q('pos', 'sale_by_product', 'view_report_costs')),
        Item('report_inventory_value', 'Inventario Valorizado', 'inventory_value_report',
             'pos.report_inventory_value', q('pos', 'report_inventory_value')),
        Item('report_restock', 'Reposición Sugerida', 'restock_report', 'pos.report_restock',
             q('pos', 'report_restock')),
        Item('report_rotation', 'Rotación e Inactivos', 'rotation_report', 'pos.report_rotation',
             q('pos', 'report_rotation')),
    )),
    Section('Configuraciones', 'fas fa-wrench', (
        Section('Generales', 'fas fa-sliders-h', (
            Item('company', 'Compañia', 'company_update', 'pos.view_company',
                 q('pos', 'view_company', 'change_company')),
            Item('factus_credentials', 'Credenciales Factus', 'factus_credential_list',
                 'pos.view_factuscredential', crud_q('pos', 'factuscredential')),
            Item('dashboard_config', 'Conf. Dashboard', 'dashboard_update', 'security.view_dashboard',
                 q('security', 'view_dashboard', 'change_dashboard')),
            Item('profile', 'Actualizar Perfil', 'user_update_profile', None),
        )),
        Item('tables', 'Mesas', 'table_list', 'pos.view_table', crud_q('pos', 'table')),
    )),
    Section('Seguridad', 'fas fa-lock', (
        Item('users', 'Usuarios', 'user_list', 'user.view_user', crud_q('user', 'user')),
        Item('roles', 'Roles y Permisos', 'role_list', 'security.view_role', crud_q('security', 'role')),
        Item('user_access', 'Accesos', 'user_access_list', 'security.view_user_access',
             q('security', 'view_user_access', 'delete_user_access')),
        Item('password', 'Actualizar Contraseña', 'user_update_password', None),
    )),
)


def iter_items(nodes=MENU):
    """Recorre todos los ``Item`` del menú (aplanando las secciones)."""
    for node in nodes:
        if isinstance(node, Section):
            yield from iter_items(node.children)
        else:
            yield node


# --------------------------------------------------------------------------
# Compatibilidad: quien tenía el permiso antiguo recibe los nuevos
# (siempre solo se AGREGA, nunca se quita) para que ningún rol pierda acceso
# cuando un permiso compartido se separa por módulo.
# --------------------------------------------------------------------------
LEGACY_MAP = {
    # Las facturas electrónicas dejaron de compartir permisos con las facturas POS
    'pos.view_sale': q('pos', 'view_electronic_invoice', 'print_electronic_invoice',
                       'download_electronic_invoice_pdf', 'resend_electronic_invoice_email'),
    'pos.add_sale': q('pos', 'add_electronic_invoice'),
    'pos.delete_sale': q('pos', 'delete_electronic_invoice'),
    # Los cierres de caja ya se podían ver: quien los veía también puede imprimirlos
    'pos.view_cashclosing': q('pos', 'print_cashclosing'),
    # Acciones nuevas de notas crédito
    'pos.view_creditnote': q('pos', 'print_creditnote', 'download_creditnote_pdf', 'resend_creditnote_email'),
    # Consultar en la DIAN: quien podía crear/editar clientes
    'pos.add_client': q('pos', 'consult_dian_client'),
    'pos.change_client': q('pos', 'consult_dian_client'),
    # Productos con descuento usaba los permisos de producto
    'pos.view_product': q('pos', 'view_productautoadd'),
    'pos.add_product': q('pos', 'add_productautoadd'),
    'pos.change_product': q('pos', 'change_productautoadd'),
    'pos.delete_product': q('pos', 'delete_productautoadd'),
    # Administrador de inventario y edición de empresa colgaban de view_company
    'pos.view_company': q('pos', 'change_company', 'view_inventorygroup', 'add_inventorygroup',
                          'change_inventorygroup', 'delete_inventorygroup'),
    # Gastos y créditos colgaban de view_bill
    'pos.view_bill': q('pos', 'view_expenses', 'view_credit_report', 'add_credit_payment'),
    # Mesas y cocina colgaban de add_bar
    'pos.add_bar': q('pos', 'view_order', 'add_order', 'view_kitchen_board', 'mark_order_ready'),
    # Editar el dashboard se hacía con view_dashboard
    'security.view_dashboard': q('security', 'change_dashboard'),
}


# --------------------------------------------------------------------------
# Matriz de la pantalla de roles: módulo x columna
# --------------------------------------------------------------------------
MATRIX_COLUMNS = (
    ('view', 'Ver'), ('add', 'Crear'), ('change', 'Editar'), ('delete', 'Eliminar'),
)


# Pantallas cuyo acceso NO entra en el rol "Solo lectura": son de captura/edición o guardan
# datos sensibles (credenciales de Factus) o de administración (usuarios, roles, accesos), aunque su permiso de entrada se llame "ver".
READONLY_EXCLUDE = frozenset({
    'quick_sales', 'inventory_admin', 'company', 'factus_credentials', 'dashboard_config',
    'users', 'roles', 'user_access',
})
READONLY_ROLE_NAME = 'Solo lectura'


def readonly_permissions():
    """Permisos del rol "Solo lectura": solo entrar a ver los módulos, ninguna acción."""
    return sorted(
        i.view_perm for i in iter_items()
        if i.view_perm and i.perms and i.key not in READONLY_EXCLUDE
    )


def permission_labels():
    """{'app.codename': descripción} de todo el catálogo."""
    return {f"{k.split('.')[0]}.{c}": label for k, perms in PERMISSIONS.items() for c, label in perms}


def columns_for(item):
    """Reparte los permisos de un módulo en columnas Ver/Crear/Editar/Eliminar/Otras.

    El permiso ``view_perm`` va en "Ver" (da acceso a la pantalla); ``add_x``, ``change_x`` y
    ``delete_x`` van a su columna cuando ``x`` es el mismo sufijo que el de ver; el resto
    (imprimir, reenviar, consultar DIAN...) cae en "Otras acciones".
    Devuelve ``{'view': 'app.cod'|None, 'add': ..., 'change': ..., 'delete': ..., 'others': [(full, label)]}``.
    """
    labels = permission_labels()
    cols = {key: None for key, _ in MATRIX_COLUMNS}
    others = []
    suffix = item.view_perm.split('.', 1)[1].split('_', 1)[1] if item.view_perm else None
    for full in item.perms:
        codename = full.split('.', 1)[1]
        verb, _, rest = codename.partition('_')
        if full == item.view_perm:
            cols['view'] = full
        elif verb in ('add', 'change', 'delete') and rest == suffix and cols[verb] is None:
            cols[verb] = full
        else:
            others.append((full, labels[full]))
    cols['others'] = others
    return cols


def matrix_sections():
    """Módulos agrupados por sección del menú, listos para pintar la matriz."""
    sections = []

    def collect(nodes, label):
        rows = [
            {'key': i.key, 'label': i.label, 'readonly_ok': i.key not in READONLY_EXCLUDE, 'cols': cols, 'cols_list': [(k, cols[k]) for k, _ in MATRIX_COLUMNS]}
            for i in nodes if not isinstance(i, Section) and i.perms
            for cols in (columns_for(i),)
        ]
        if rows:
            sections.append({'label': label, 'rows': rows})
        for node in nodes:
            if isinstance(node, Section):
                collect(node.children, f'{label} › {node.label}')

    for node in MENU:
        if isinstance(node, Section):
            collect(node.children, node.label)
        elif node.perms:
            collect((node,), 'General')
    return sections


def validate():
    """Verifica la coherencia interna del catálogo. Devuelve lista de errores."""
    errors = []
    declared = {}
    for model_key, perms in PERMISSIONS.items():
        app = model_key.split('.')[0]
        for codename, label in perms:
            full = f'{app}.{codename}'
            if full in declared:
                errors.append(f'Permiso duplicado: {full}')
            declared[full] = label
            if not label.strip():
                errors.append(f'Permiso sin descripción: {full}')

    used = {}
    for item in iter_items():
        if item.view_perm is not None and item.view_perm not in item.perms:
            errors.append(f'{item.key}: view_perm {item.view_perm} no está en sus perms')
        for p in item.perms:
            if p not in declared:
                errors.append(f'{item.key}: permiso inexistente {p}')
            if p in used:
                errors.append(f'{p} aparece en dos módulos: {used[p]} y {item.key}')
            used[p] = item.key

    for p in declared:
        if p not in used:
            errors.append(f'Permiso sin módulo asignado: {p}')

    for old, new in LEGACY_MAP.items():
        for p in new:
            if p not in declared:
                errors.append(f'LEGACY_MAP apunta a un permiso inexistente: {p}')
    return errors
